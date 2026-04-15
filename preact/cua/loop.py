"""Standard CUA Loop — observe-reason-act agent.

Implements the baseline CUA agent that captures screenshots, sends them
to Gemini 3 Flash for reasoning, and executes the resulting actions.
Integrates with the Interaction Recorder for trace collection.

IMPORTANT: Maintains conversation history across steps so the LLM
knows what actions it has already taken.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from preact.config import CUAConfig
from preact.cua.action_parser import is_done_action, is_done_success, parse_action
from preact.cua.prompts import SYSTEM_PROMPT, USER_PROMPT, USER_PROMPT_FALLBACK
from preact.schemas import ActionSpec, ActionType

if TYPE_CHECKING:
    from preact.environment.base import ComputerEnvironment
    from preact.llm.client import LLMClient
    from preact.recorder.recorder import InteractionRecorder

logger = logging.getLogger(__name__)


@dataclass
class CUAResult:
    """Result from a CUA loop execution."""

    success: bool
    actions_taken: int
    total_time_ms: float
    reason: str = ""
    error: str | None = None
    trace: Any = None  # InteractionTrace, if recorded


class CUALoop:
    """Standard Observe-Reason-Act CUA agent.

    Maintains a conversation history so the LLM can see what actions
    it has already taken and their effects (via screenshots).

    Each step:
    1. Capture screenshot from environment
    2. Send screenshot + history to Gemini 3 Flash
    3. Parse the LLM's action response
    4. Execute the action via the environment
    5. Record the step in the Interaction Recorder
    """

    def __init__(
        self,
        env: ComputerEnvironment,
        llm: LLMClient,
        recorder: InteractionRecorder | None = None,
        config: CUAConfig | None = None,
    ):
        self.env = env
        self.llm = llm
        self.recorder = recorder
        self.config = config or CUAConfig()

    async def run(
        self,
        task: str,
        max_steps: int | None = None,
        record: bool = True,
    ) -> CUAResult:
        """Run the full CUA loop for a task.

        Args:
            task: The task description to accomplish.
            max_steps: Maximum number of actions to take.
            record: Whether to record the interaction trace.

        Returns:
            CUAResult with success/failure and statistics.
        """
        max_steps = max_steps or self.config.max_steps
        start_time = time.monotonic()

        if record and self.recorder:
            url = ""
            try:
                url = await self.env.get_page_url()
            except Exception:
                pass
            self.recorder.start_recording(task, application_context=url)

        actions_taken = 0
        success = False
        reason = ""
        error = None

        # Conversation history for multi-turn reasoning
        action_history: list[str] = []

        try:
            for step in range(1, max_steps + 1):
                # Wait for UI to stabilize
                await asyncio.sleep(self.config.screenshot_delay_ms / 1000.0)

                # 1. Observe: capture screenshot
                screenshot = await self.env.screenshot()

                # 2. Build context with action history
                history_text = ""
                if action_history:
                    history_text = "Previous actions taken:\n" + "\n".join(
                        f"  Step {i+1}: {a}" for i, a in enumerate(action_history)
                    ) + "\n\nContinue from where you left off. Do NOT repeat actions already taken."

                prompt = USER_PROMPT.format(
                    task=task,
                    step_number=step,
                    max_steps=max_steps,
                    context=history_text,
                )

                # 3. Reason: send screenshot + context to LLM
                llm_response = await self.llm.complete_with_vision(
                    text_prompt=prompt,
                    images=[screenshot],
                    system=SYSTEM_PROMPT,
                )

                # 4. Parse action
                action = parse_action(llm_response)
                if not action:
                    logger.warning("Step %d: Failed to parse action", step)
                    action_history.append(f"[failed to parse: {llm_response[:80]}]")
                    continue

                # Check if task is done
                if is_done_action(action):
                    success = is_done_success(action)
                    reason = action.description or ""
                    logger.info(
                        "CUA loop done at step %d: success=%s, reason=%s",
                        step,
                        success,
                        reason,
                    )
                    break

                # 5. Execute action
                action_desc = self._describe_action(action)
                try:
                    await self._execute_action(action)
                    action_history.append(action_desc)
                    actions_taken += 1
                except Exception as e:
                    logger.warning("Step %d action failed: %s", step, e)
                    action_history.append(f"{action_desc} [FAILED: {str(e)[:60]}]")
                    continue

                # 6. Record
                if record and self.recorder:
                    xpath = action.target
                    await self.recorder.record_step(
                        action=action,
                        llm_reasoning=llm_response,
                        target_xpath=xpath,
                    )

                await asyncio.sleep(self.config.action_delay_ms / 1000.0)

            else:
                reason = f"Max steps ({max_steps}) reached"
                logger.warning("CUA loop: %s", reason)

        except Exception as e:
            error = str(e)
            logger.error("CUA loop error: %s", e, exc_info=True)

        total_time = (time.monotonic() - start_time) * 1000

        # Stop recording and capture trace
        trace = None
        if record and self.recorder and self.recorder.is_recording:
            trace = self.recorder.stop_recording(success=success)

        return CUAResult(
            success=success,
            actions_taken=actions_taken,
            total_time_ms=total_time,
            reason=reason,
            error=error,
            trace=trace,
        )

    async def run_from_context(
        self,
        task: str,
        failed_context: str = "",
        max_steps: int | None = None,
        record: bool = True,
    ) -> CUAResult:
        """Resume CUA from a specific context (for fallback from RPA).

        Used when the RPA executor encounters a state verification failure
        and needs the CUA to take over and resolve the situation.
        """
        max_steps = max_steps or min(self.config.max_steps, 15)
        start_time = time.monotonic()

        if record and self.recorder:
            url = ""
            try:
                url = await self.env.get_page_url()
            except Exception:
                pass
            self.recorder.start_recording(
                f"Recovery: {task}", application_context=url
            )

        actions_taken = 0
        success = False
        reason = ""
        error = None
        action_history: list[str] = []

        try:
            for step in range(1, max_steps + 1):
                await asyncio.sleep(self.config.screenshot_delay_ms / 1000.0)

                screenshot = await self.env.screenshot()

                history_text = ""
                if action_history:
                    history_text = "Previous recovery actions:\n" + "\n".join(
                        f"  Step {i+1}: {a}" for i, a in enumerate(action_history)
                    )

                prompt = USER_PROMPT_FALLBACK.format(
                    task=task,
                    failed_context=failed_context,
                    step_number=step,
                    max_steps=max_steps,
                )
                if history_text:
                    prompt += "\n\n" + history_text

                llm_response = await self.llm.complete_with_vision(
                    text_prompt=prompt,
                    images=[screenshot],
                    system=SYSTEM_PROMPT,
                )

                action = parse_action(llm_response)
                if not action:
                    continue

                if is_done_action(action):
                    success = is_done_success(action)
                    reason = action.description or ""
                    break

                action_desc = self._describe_action(action)
                try:
                    await self._execute_action(action)
                    action_history.append(action_desc)
                    actions_taken += 1
                except Exception as e:
                    action_history.append(f"{action_desc} [FAILED: {str(e)[:60]}]")

                if record and self.recorder:
                    await self.recorder.record_step(
                        action=action,
                        llm_reasoning=llm_response,
                        target_xpath=action.target,
                    )

                await asyncio.sleep(self.config.action_delay_ms / 1000.0)
            else:
                reason = f"Max recovery steps ({max_steps}) reached"

        except Exception as e:
            error = str(e)
            logger.error("CUA fallback error: %s", e, exc_info=True)

        total_time = (time.monotonic() - start_time) * 1000

        trace = None
        if record and self.recorder and self.recorder.is_recording:
            trace = self.recorder.stop_recording(success=success)

        return CUAResult(
            success=success,
            actions_taken=actions_taken,
            total_time_ms=total_time,
            reason=reason,
            error=error,
            trace=trace,
        )

    def _describe_action(self, action: ActionSpec) -> str:
        """Create a human-readable description of an action for history."""
        t = action.type
        if t == ActionType.ACTION_CLICK:
            return f"click({action.target})"
        elif t == ActionType.ACTION_TYPE:
            return f"type({action.target}, '{action.text}')"
        elif t == ActionType.ACTION_KEYPRESS:
            return f"keypress({action.key})"
        elif t == ActionType.ACTION_SCROLL:
            return f"scroll({action.direction}, {action.amount})"
        elif t == ActionType.WAIT:
            return f"wait({action.ms}ms)"
        else:
            return f"{t.value}({action.target or ''})"

    async def _execute_action(self, action: ActionSpec) -> None:
        """Execute a single action against the environment."""
        t = action.type

        if t == ActionType.ACTION_CLICK:
            if action.target:
                await self.env.click(action.target)

        elif t == ActionType.ACTION_DOUBLE_CLICK:
            if action.target:
                await self.env.double_click(action.target)

        elif t == ActionType.ACTION_TYPE:
            if action.target and action.text:
                try:
                    await self.env.type_text(action.target, action.text)
                except Exception:
                    # Might be a <select> element — try select_option
                    try:
                        await self.env.select_option(action.target, action.text)
                    except Exception:
                        # Last resort — click and type via keyboard
                        await self.env.click(action.target)
                        await self.env.press_key("Control+a")
                        for char in action.text:
                            await self.env.press_key(char)

        elif t == ActionType.ACTION_KEYPRESS:
            if action.key:
                await self.env.press_key(action.key)

        elif t == ActionType.ACTION_SCROLL:
            await self.env.scroll(
                direction=action.direction or "down",
                amount=action.amount or 3,
            )

        elif t == ActionType.WAIT:
            if action.ms:
                await asyncio.sleep(action.ms / 1000.0)

        elif t == ActionType.ACTION_MOVE:
            if action.target:
                await self.env.move_to(action.target)

        else:
            logger.warning("Unhandled action type in CUA: %s", t)
