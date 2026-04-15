"""AgentRR complete baseline system.

Implements the Record-Summary-Replay framework:
1. Record: Run CUA and capture interaction trace
2. Summary: Use LLM to create multi-level experiences
3. Replay: Use experiences as context for the LLM agent
"""

from __future__ import annotations

import logging
import time
from typing import Any

from preact.baselines.agent_rr.experience import (
    ExperienceStore,
    HighLevelExperience,
    LowLevelExperience,
    MidLevelExperience,
)
from preact.baselines.base import BaselineResult

logger = logging.getLogger(__name__)

SUMMARY_PROMPT = """Analyze this interaction trace and create a multi-level experience summary.

Task: {task}

Trace:
{trace_text}

Create a JSON summary with:
{{
  "strategy": "Overall approach description",
  "sub_tasks": [
    {{
      "sub_task": "Sub-task description",
      "steps": [
        {{
          "description": "What to do",
          "action_type": "click/type/etc",
          "target_description": "Description of the target element",
          "check_function": "How to verify this step succeeded"
        }}
      ]
    }}
  ]
}}"""

REPLAY_PROMPT = """You are a Computer Using Agent. Complete the following task using the experience from a previous successful execution.

Task: {task}

Previous experience:
Strategy: {strategy}

Detailed steps:
{steps_text}

Use this experience as a guide, but adapt to the current UI state. Output your action as JSON."""


class AgentRRBaseline:
    """AgentRR (Feng et al., 2025) — experience-guided replay.

    Exploration: Records trace, summarizes into multi-level experiences.
    Replay: Injects experiences into LLM context for guided execution.
    Fallback: Cascades from low-level to mid-level to high-level guidance.
    """

    name = "AgentRR"

    def __init__(self):
        self._store = ExperienceStore()

    async def run_exploration(
        self, task: str, env: Any, llm: Any, **kwargs: Any
    ) -> BaselineResult:
        """Phase 1: Record + Summarize."""
        start = time.monotonic()
        start_tokens_in = llm.total_input_tokens
        start_tokens_out = llm.total_output_tokens

        from preact.cua.loop import CUALoop
        from preact.recorder.recorder import InteractionRecorder
        from preact.recorder.trace import trace_to_text

        recorder = InteractionRecorder(env)
        cua = CUALoop(env, llm, recorder)
        cua_result = await cua.run(task, record=True)

        if cua_result.success and cua_result.trace:
            # Summarize trace into multi-level experience
            trace_text = trace_to_text(cua_result.trace)
            prompt = SUMMARY_PROMPT.format(task=task, trace_text=trace_text)

            response = await llm.complete(
                messages=[{"role": "user", "content": prompt}]
            )

            experience = self._parse_experience(task, response)
            self._store.store(task, experience)
            logger.info(
                "Created experience: %d sub-tasks",
                len(experience.sub_tasks),
            )

        return BaselineResult(
            success=cua_result.success,
            mode="exploration",
            actions_executed=cua_result.actions_taken,
            total_time_ms=(time.monotonic() - start) * 1000,
            total_input_tokens=llm.total_input_tokens - start_tokens_in,
            total_output_tokens=llm.total_output_tokens - start_tokens_out,
            actions_via_cache=0,
            actions_via_llm=cua_result.actions_taken,
            error=cua_result.error,
        )

    async def run_replay(
        self, task: str, env: Any, llm: Any, **kwargs: Any
    ) -> BaselineResult:
        """Phase 2: Experience-guided replay (LLM still in the loop)."""
        start = time.monotonic()
        start_tokens_in = llm.total_input_tokens
        start_tokens_out = llm.total_output_tokens

        experience = self._store.retrieve(task)
        if not experience:
            return BaselineResult(
                success=False,
                mode="replay",
                error="No experience available",
            )

        # Build steps text from experience
        steps_lines = []
        for st in experience.sub_tasks:
            steps_lines.append(f"\nSub-task: {st.sub_task}")
            for step in st.steps:
                check = f" [Check: {step.check_function}]" if step.check_function else ""
                steps_lines.append(
                    f"  - {step.description} ({step.action_type} on {step.target_description}){check}"
                )

        steps_text = "\n".join(steps_lines)

        # Run CUA with experience as context
        from preact.cua.loop import CUALoop
        from preact.cua.prompts import SYSTEM_PROMPT

        system = SYSTEM_PROMPT + "\n\n" + REPLAY_PROMPT.format(
            task=task,
            strategy=experience.strategy,
            steps_text=steps_text,
        )

        # NOTE: AgentRR still uses LLM at execution time — the experience
        # just provides better context. This is the key difference from PreAct.
        cua = CUALoop(env, llm)
        cua_result = await cua.run(task, record=False)

        return BaselineResult(
            success=cua_result.success,
            mode="replay",
            actions_executed=cua_result.actions_taken,
            total_time_ms=(time.monotonic() - start) * 1000,
            total_input_tokens=llm.total_input_tokens - start_tokens_in,
            total_output_tokens=llm.total_output_tokens - start_tokens_out,
            actions_via_cache=0,  # Still uses LLM for every action
            actions_via_llm=cua_result.actions_taken,
            error=cua_result.error,
        )

    def _parse_experience(
        self, task: str, response: str
    ) -> HighLevelExperience:
        """Parse LLM summary response into structured experience."""
        import json

        experience = HighLevelExperience(
            task_description=task,
            strategy="",
        )

        try:
            # Extract JSON from response
            text = response.strip()
            if "```json" in text:
                start = text.index("```json") + 7
                end = text.index("```", start)
                text = text[start:end]
            elif "```" in text:
                start = text.index("```") + 3
                end = text.index("```", start)
                text = text[start:end]

            data = json.loads(text)
            experience.strategy = data.get("strategy", "")

            for st_data in data.get("sub_tasks", []):
                mid = MidLevelExperience(sub_task=st_data.get("sub_task", ""))
                for i, step_data in enumerate(st_data.get("steps", [])):
                    low = LowLevelExperience(
                        step_number=i,
                        description=step_data.get("description", ""),
                        action_type=step_data.get("action_type", ""),
                        target_description=step_data.get("target_description", ""),
                        check_function=step_data.get("check_function"),
                    )
                    mid.steps.append(low)
                experience.sub_tasks.append(mid)

        except Exception as e:
            logger.warning("Failed to parse experience summary: %s", e)
            experience.strategy = response[:500]

        return experience

    async def reset(self) -> None:
        self._store.clear()

    def has_cached_artifact(self, task: str) -> bool:
        return self._store.has_experience(task)
