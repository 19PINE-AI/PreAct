"""Muscle-Mem baseline implementation.

Records linear action sequences during exploration and replays them
blindly during subsequent runs. On any failure, discards the entire
cache and falls back to full CUA mode.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from preact.baselines.base import BaselineResult
from preact.schemas import ActionSpec

logger = logging.getLogger(__name__)


class MuscleMemBaseline:
    """Muscle-Mem (Dunteman, 2025) — blind linear replay with fallback.

    Exploration: Records the sequence of actions taken by the CUA.
    Replay: Plays back the exact same actions without any verification.
    Fallback: Discards the cache entirely and re-runs CUA.
    """

    name = "Muscle-Mem"

    def __init__(self):
        self._cached_sequences: dict[str, list[dict[str, Any]]] = {}

    async def run_exploration(
        self, task: str, env: Any, llm: Any, **kwargs: Any
    ) -> BaselineResult:
        """Record a CUA run and cache the action sequence."""
        start = time.monotonic()
        start_tokens_in = llm.total_input_tokens
        start_tokens_out = llm.total_output_tokens

        from preact.cua.loop import CUALoop
        from preact.recorder.recorder import InteractionRecorder

        recorder = InteractionRecorder(env)
        cua = CUALoop(env, llm, recorder)
        cua_result = await cua.run(task, record=True)

        # Extract the linear action sequence from the trace
        if cua_result.success and cua_result.trace:
            sequence = []
            for step in cua_result.trace.steps:
                action_data = {
                    "type": step.action.type.value,
                    "target": step.action.target,
                    "text": step.action.text,
                    "key": step.action.key,
                    "ms": step.action.ms,
                    "direction": step.action.direction,
                    "amount": step.action.amount,
                }
                sequence.append(action_data)
            self._cached_sequences[task] = sequence
            logger.info("Cached %d actions for task", len(sequence))

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
        """Replay the cached action sequence blindly."""
        start = time.monotonic()
        start_tokens_in = llm.total_input_tokens
        start_tokens_out = llm.total_output_tokens

        sequence = self._cached_sequences.get(task)
        if not sequence:
            return BaselineResult(
                success=False,
                mode="replay",
                error="No cached sequence (exploration not run)",
            )

        actions_executed = 0
        success = False
        error = None

        try:
            # Wait for page to be ready before blind replay
            await asyncio.sleep(0.5)
            for action_data in sequence:
                await self._execute_action(action_data, env)
                actions_executed += 1
                await asyncio.sleep(0.15)  # Brief delay between actions
            success = True
        except Exception as e:
            error = str(e)
            logger.info("Blind replay failed at action %d: %s", actions_executed, e)

            # Muscle-Mem's fallback: discard cache, run full CUA
            logger.info("Discarding cache and falling back to CUA")
            del self._cached_sequences[task]

            from preact.cua.loop import CUALoop

            cua = CUALoop(env, llm)
            cua_result = await cua.run(task, record=False)
            success = cua_result.success
            if cua_result.error:
                error = cua_result.error

        replay_time = (time.monotonic() - start) * 1000

        return BaselineResult(
            success=success,
            mode="replay",
            actions_executed=actions_executed,
            total_time_ms=replay_time,
            total_input_tokens=llm.total_input_tokens - start_tokens_in,
            total_output_tokens=llm.total_output_tokens - start_tokens_out,
            actions_via_cache=actions_executed if success else 0,
            actions_via_llm=0 if success else actions_executed,
            fallback_count=0 if success else 1,
            error=error,
        )

    async def _execute_action(
        self, action_data: dict[str, Any], env: Any
    ) -> None:
        """Execute a single cached action (no verification)."""
        action_type = action_data.get("type", "")
        target = action_data.get("target")
        text = action_data.get("text")
        key = action_data.get("key")
        ms = action_data.get("ms")

        if action_type == "action_click" and target:
            await env.click(target)
        elif action_type == "action_type" and target and text:
            await env.type_text(target, text)
        elif action_type == "action_keypress" and key:
            await env.press_key(key)
        elif action_type == "action_scroll":
            direction = action_data.get("direction", "down")
            amount = action_data.get("amount", 3)
            await env.scroll(direction, amount)
        elif action_type == "wait":
            await asyncio.sleep((ms or 500) / 1000.0)

    async def reset(self) -> None:
        self._cached_sequences.clear()

    def has_cached_artifact(self, task: str) -> bool:
        return task in self._cached_sequences
