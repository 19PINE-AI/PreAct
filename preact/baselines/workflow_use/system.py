"""Workflow-Use baseline implementation.

Records browser interactions, compiles them into deterministic linear scripts
with variable support, and replays them. Falls back to full agent mode
on any failure with no model update.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from preact.baselines.base import BaselineResult

logger = logging.getLogger(__name__)


@dataclass
class WorkflowScript:
    """A compiled linear script with variable support."""

    task: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    variables: dict[str, str] = field(default_factory=dict)


class WorkflowUseBaseline:
    """Workflow-Use (browser-use, 2025) — linear script replay.

    Exploration: Records interaction, compiles to linear script with variables.
    Replay: Executes script with CSS selector matching.
    Fallback: Full agent mode (no model update).
    """

    name = "Workflow-Use"

    def __init__(self):
        self._scripts: dict[str, WorkflowScript] = {}

    async def run_exploration(
        self, task: str, env: Any, llm: Any, **kwargs: Any
    ) -> BaselineResult:
        """Record and compile to linear script."""
        start = time.monotonic()
        start_tokens_in = llm.total_input_tokens
        start_tokens_out = llm.total_output_tokens

        from preact.cua.loop import CUALoop
        from preact.recorder.recorder import InteractionRecorder

        recorder = InteractionRecorder(env)
        cua = CUALoop(env, llm, recorder)
        cua_result = await cua.run(task, record=True)

        if cua_result.success and cua_result.trace:
            # Compile trace to linear script
            script = WorkflowScript(task=task)

            for step in cua_result.trace.steps:
                script_step = {
                    "type": step.action.type.value,
                    "target": step.action.target or step.target_xpath,
                    "text": step.action.text,
                    "key": step.action.key,
                    "ms": step.action.ms,
                    "direction": step.action.direction,
                    "amount": step.action.amount,
                }
                script.steps.append(script_step)

                # Detect variables (typed text)
                if step.action.text and len(step.action.text) > 2:
                    var_name = f"var_{len(script.variables)}"
                    script.variables[var_name] = step.action.text

            self._scripts[task] = script
            logger.info(
                "Compiled script: %d steps, %d variables",
                len(script.steps),
                len(script.variables),
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
            extra={"answer": cua_result.answer},
        )

    async def run_replay(
        self, task: str, env: Any, llm: Any, **kwargs: Any
    ) -> BaselineResult:
        """Replay the linear script."""
        start = time.monotonic()
        start_tokens_in = llm.total_input_tokens
        start_tokens_out = llm.total_output_tokens

        script = self._scripts.get(task)
        if not script:
            return BaselineResult(
                success=False,
                mode="replay",
                error="No script available",
            )

        actions_executed = 0
        success = False
        error = None
        fallback = False

        try:
            for step_data in script.steps:
                await self._execute_step(step_data, env)
                actions_executed += 1
                await asyncio.sleep(0.15)
            success = True
        except Exception as e:
            error = str(e)
            logger.info("Script replay failed at step %d: %s", actions_executed, e)
            fallback = True

            # Workflow-Use fallback: full agent mode (NO model update)
            from preact.cua.loop import CUALoop

            cua = CUALoop(env, llm)
            cua_result = await cua.run(task, record=False)
            success = cua_result.success
            if cua_result.error:
                error = cua_result.error

        return BaselineResult(
            success=success,
            mode="replay",
            actions_executed=actions_executed,
            total_time_ms=(time.monotonic() - start) * 1000,
            total_input_tokens=llm.total_input_tokens - start_tokens_in,
            total_output_tokens=llm.total_output_tokens - start_tokens_out,
            actions_via_cache=actions_executed if not fallback else 0,
            actions_via_llm=0 if not fallback else actions_executed,
            fallback_count=1 if fallback else 0,
            error=error,
        )

    async def _execute_step(
        self, step_data: dict[str, Any], env: Any
    ) -> None:
        """Execute a single script step with semantic selector matching."""
        action_type = step_data.get("type", "")
        target = step_data.get("target")
        text = step_data.get("text")
        key = step_data.get("key")

        if action_type == "action_click" and target:
            # Workflow-Use uses semantic selectors
            exists = await env.element_exists(target, timeout_ms=3000)
            if not exists:
                raise RuntimeError(f"Element not found: {target}")
            await env.click(target)

        elif action_type == "action_type" and target and text:
            exists = await env.element_exists(target, timeout_ms=3000)
            if not exists:
                raise RuntimeError(f"Element not found: {target}")
            await env.type_text(target, text)

        elif action_type == "action_keypress" and key:
            await env.press_key(key)

        elif action_type == "action_scroll":
            direction = step_data.get("direction", "down")
            amount = step_data.get("amount", 3)
            await env.scroll(direction, amount)

        elif action_type == "wait":
            ms = step_data.get("ms", 500)
            await asyncio.sleep(ms / 1000.0)

    async def reset(self) -> None:
        self._scripts.clear()

    def has_cached_artifact(self, task: str) -> bool:
        return task in self._scripts
