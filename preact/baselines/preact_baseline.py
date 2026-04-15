"""PreAct as a baseline system for evaluation.

Wraps the PreAct agent to implement the BaselineSystem protocol
for fair comparison with other systems.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from preact.baselines.base import BaselineResult
from preact.config import PreActConfig
from preact.core.agent import PreActAgent

logger = logging.getLogger(__name__)


class PreActBaseline:
    """PreAct wrapped as a baseline for evaluation.

    The RAG store persists across runs (this is the point — program reuse),
    but the environment and LLM are updated on each call since the evaluation
    harness creates fresh browser instances per run.
    """

    name = "PreAct"

    def __init__(self):
        self._agent: PreActAgent | None = None
        self._config = PreActConfig()

    def _ensure_agent(self, env: Any, llm: Any) -> PreActAgent:
        """Create or update the agent with current env/llm."""
        if not self._agent:
            self._agent = PreActAgent(env, llm, self._config)
        else:
            # Update environment and LLM references for new browser sessions
            self._agent.env = env
            self._agent.llm = llm
            self._agent.recorder.env = env
            self._agent.executor.env = env
            self._agent.executor.llm = llm
            self._agent.cua.env = env
            self._agent.cua.llm = llm
            if self._agent.cua.recorder:
                self._agent.cua.recorder.env = env
        return self._agent

    async def run_exploration(
        self, task: str, env: Any, llm: Any, **kwargs: Any
    ) -> BaselineResult:
        """Run 1: CUA exploration + compilation."""
        start = time.monotonic()
        start_tokens_in = llm.total_input_tokens
        start_tokens_out = llm.total_output_tokens

        agent = self._ensure_agent(env, llm)
        result = await agent.execute_task(
            task,
            parameters=kwargs.get("parameters"),
            force_cua=True,
        )

        answer = ""
        if result.cua_result:
            answer = result.cua_result.answer

        return BaselineResult(
            success=result.success,
            mode="exploration",
            actions_executed=result.cua_result.actions_taken if result.cua_result else 0,
            total_time_ms=(time.monotonic() - start) * 1000,
            total_input_tokens=llm.total_input_tokens - start_tokens_in,
            total_output_tokens=llm.total_output_tokens - start_tokens_out,
            actions_via_cache=0,
            actions_via_llm=result.cua_result.actions_taken if result.cua_result else 0,
            error=result.error,
            extra={
                "program_id": result.program_id,
                "program_was_new": result.program_was_new,
                "answer": answer,
            },
        )

    async def run_replay(
        self, task: str, env: Any, llm: Any, **kwargs: Any
    ) -> BaselineResult:
        """Run 2: RPA execution from compiled state machine."""
        start = time.monotonic()
        start_tokens_in = llm.total_input_tokens
        start_tokens_out = llm.total_output_tokens

        agent = self._ensure_agent(env, llm)
        result = await agent.execute_task(
            task,
            parameters=kwargs.get("parameters"),
        )

        actions_rpa = 0
        actions_cua = 0
        if result.execution_result:
            actions_rpa = result.execution_result.actions_via_rpa
        if result.cua_result:
            actions_cua = result.cua_result.actions_taken

        # Extract answer: prefer CUA answer (from fallback), as RPA can't extract text
        answer = ""
        if result.cua_result and result.cua_result.answer:
            answer = result.cua_result.answer

        return BaselineResult(
            success=result.success,
            mode=result.mode,
            actions_executed=actions_rpa + actions_cua,
            total_time_ms=(time.monotonic() - start) * 1000,
            total_input_tokens=llm.total_input_tokens - start_tokens_in,
            total_output_tokens=llm.total_output_tokens - start_tokens_out,
            actions_via_cache=actions_rpa,
            actions_via_llm=actions_cua,
            fallback_count=len(result.execution_result.fallback_events)
            if result.execution_result
            else 0,
            error=result.error,
            extra={
                "program_id": result.program_id,
                "program_was_extended": result.program_was_extended,
                "answer": answer,
                "graph_coverage": result.execution_result.graph_coverage
                if result.execution_result
                else 0,
            },
        )

    async def reset(self) -> None:
        self._agent = None

    def has_cached_artifact(self, task: str) -> bool:
        if self._agent:
            return self._agent.store.has_relevant_match(task)
        return False
