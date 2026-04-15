"""Standard CUA baseline — pure LLM agent with no caching.

This is the baseline that all other systems are compared against.
It runs the full observe-reason-act loop for every execution,
showing no improvement between Run 1 and Run 2.
"""

from __future__ import annotations

import time
from typing import Any

from preact.baselines.base import BaselineResult
from preact.cua.loop import CUALoop


class StandardCUABaseline:
    """Pure CUA baseline — no caching, no replay."""

    name = "Standard CUA"

    def __init__(self):
        self._cua: CUALoop | None = None

    async def run_exploration(
        self, task: str, env: Any, llm: Any, **kwargs: Any
    ) -> BaselineResult:
        """Run the full CUA loop (same as replay — no learning)."""
        return await self._run(task, env, llm, **kwargs)

    async def run_replay(
        self, task: str, env: Any, llm: Any, **kwargs: Any
    ) -> BaselineResult:
        """Identical to exploration — no caching."""
        return await self._run(task, env, llm, **kwargs)

    async def _run(
        self, task: str, env: Any, llm: Any, **kwargs: Any
    ) -> BaselineResult:
        from preact.cua.loop import CUALoop

        cua = CUALoop(env, llm)
        start_tokens_in = llm.total_input_tokens
        start_tokens_out = llm.total_output_tokens

        result = await cua.run(task, record=False)

        return BaselineResult(
            success=result.success,
            mode="exploration",
            actions_executed=result.actions_taken,
            total_time_ms=result.total_time_ms,
            total_input_tokens=llm.total_input_tokens - start_tokens_in,
            total_output_tokens=llm.total_output_tokens - start_tokens_out,
            actions_via_cache=0,
            actions_via_llm=result.actions_taken,
            error=result.error,
        )

    async def reset(self) -> None:
        pass

    def has_cached_artifact(self, task: str) -> bool:
        return False
