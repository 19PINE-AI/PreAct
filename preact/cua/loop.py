"""Standard CUA Loop — observe-reason-act agent.

Implements the baseline CUA agent that captures screenshots, sends them
to Claude Sonnet for reasoning, and executes the resulting actions.
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
from preact.cua.action_parser import is_done_action, is_done_success, get_done_answer, parse_action
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
    answer: str = ""  # Text answer for information retrieval tasks
    error: str | None = None
    trace: Any = None  # InteractionTrace, if recorded


class CUALoop:
    """Standard Observe-Reason-Act CUA agent.

    Maintains a conversation history so the LLM can see what actions
    it has already taken and their effects (via screenshots).

    Each step:
    1. Capture screenshot from environment
    2. Send screenshot + history to Claude Sonnet
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
        answer = ""
        error = None

        # Conversation history for multi-turn reasoning
        action_history: list[str] = []

        try:
            for step in range(1, max_steps + 1):
                # Wait for UI to stabilize
                await asyncio.sleep(self.config.screenshot_delay_ms / 1000.0)

                # 1. Observe: capture screenshot
                screenshot = await self.env.screenshot()

                # 2. Build context with action history and interactive elements
                history_text = ""
                if action_history:
                    history_text = "Previous actions taken:\n" + "\n".join(
                        f"  Step {i+1}: {a}" for i, a in enumerate(action_history)
                    ) + "\n\nContinue from where you left off. Do NOT repeat actions already taken."

                # Extract interactive elements from DOM to help with xpath generation
                elements_text = ""
                try:
                    elements_text = await self._get_interactive_elements()
                except Exception:
                    pass

                context = history_text
                if elements_text:
                    context += ("\n\nInteractive elements on page "
                                "(use these xpaths):\n" + elements_text)

                prompt = USER_PROMPT.format(
                    task=task,
                    step_number=step,
                    max_steps=max_steps,
                    context=context,
                )

                # 3. Reason: send screenshot + context to LLM
                # Inject current base URL for navigate actions
                system = SYSTEM_PROMPT
                try:
                    current_url = await self.env.get_page_url()
                    from urllib.parse import urlparse
                    parsed = urlparse(current_url)
                    base_url = f"{parsed.scheme}://{parsed.netloc}"
                    system = system.replace(
                        '"/admin/', f'"{base_url}/admin/'
                    )
                except Exception:
                    pass

                llm_response = await self.llm.complete_with_vision(
                    text_prompt=prompt,
                    images=[screenshot],
                    system=system,
                    max_tokens=300,
                )

                # 4. Parse action
                action = parse_action(llm_response)
                if not action:
                    logger.warning(
                        "Step %d: Failed to parse action: %s",
                        step,
                        llm_response[:200],
                    )
                    action_history.append(f"[failed to parse: {llm_response[:80]}]")
                    continue

                # Check if task is done
                if is_done_action(action):
                    success = is_done_success(action)
                    reason = action.description or ""
                    answer = get_done_answer(action)
                    logger.info(
                        "CUA loop done at step %d: success=%s, reason=%s, answer=%s",
                        step,
                        success,
                        reason,
                        answer[:200] if answer else "(empty)",
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
            answer=answer,
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
        answer = ""
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

                # Inject current base URL for navigate actions
                fallback_system = SYSTEM_PROMPT
                try:
                    current_url = await self.env.get_page_url()
                    from urllib.parse import urlparse
                    parsed = urlparse(current_url)
                    base_url = f"{parsed.scheme}://{parsed.netloc}"
                    fallback_system = fallback_system.replace(
                        '"/admin/', f'"{base_url}/admin/'
                    )
                except Exception:
                    pass

                llm_response = await self.llm.complete_with_vision(
                    text_prompt=prompt,
                    images=[screenshot],
                    system=fallback_system,
                    max_tokens=300,
                )

                action = parse_action(llm_response)
                if not action:
                    continue

                if is_done_action(action):
                    success = is_done_success(action)
                    reason = action.description or ""
                    answer = get_done_answer(action)
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
            answer=answer,
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
        elif t == ActionType.ACTION_MOVE:
            return f"hover({action.target})"
        elif t == ActionType.ACTION_SCROLL:
            return f"scroll({action.direction}, {action.amount})"
        elif t == ActionType.WAIT:
            return f"wait({action.ms}ms)"
        elif t == ActionType.ACTION_NAVIGATE:
            return f"navigate({action.text})"
        else:
            return f"{t.value}({action.target or ''})"

    async def _execute_action(self, action: ActionSpec) -> None:
        """Execute a single action against the environment."""
        t = action.type

        if t == ActionType.ACTION_CLICK:
            if action.target:
                # Handle clicks on <option> elements by converting to select_option
                if "option" in action.target.lower() and (
                    "@value=" in action.target or "text()" in action.target
                ):
                    try:
                        await self.env.click(action.target)
                    except Exception:
                        # Extract value from xpath and find parent select
                        import re
                        val_match = re.search(r"@value=['\"]([^'\"]+)['\"]", action.target)
                        text_match = re.search(r"text\(\)\s*,\s*['\"]([^'\"]+)['\"]", action.target)
                        val = (val_match or text_match)
                        if val:
                            # Try to find parent select and select the option
                            select_xpath = action.target.rsplit("/option", 1)[0] if "/option" in action.target else "//select"
                            try:
                                await self.env.select_option(select_xpath, val.group(1))
                            except Exception:
                                raise
                else:
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

        elif t == ActionType.ACTION_NAVIGATE:
            if action.text:
                await self.env.navigate(action.text)

        else:
            logger.warning("Unhandled action type in CUA: %s", t)

    async def _get_interactive_elements(self) -> str:
        """Extract interactive elements from DOM for xpath guidance.

        Returns a compact list of clickable/typeable elements with their
        actual IDs and names so the LLM can generate correct xpaths.
        """
        elements = await self.env.evaluate_js("""() => {
            const results = [];
            const selectors = [
                'input[type=text]:not([type=hidden])',
                'input[type=search]',
                'input:not([type])',
                'select',
                'button:not([disabled])',
                'a[href]',
                'textarea',
            ];
            for (const sel of selectors) {
                for (const el of document.querySelectorAll(sel)) {
                    if (el.offsetParent === null && el.tagName !== 'INPUT') continue;
                    const tag = el.tagName.toLowerCase();
                    const id = el.id;
                    const name = el.name;
                    const ph = el.placeholder;
                    const text = (el.textContent || '').trim().slice(0, 40);
                    const label = el.getAttribute('aria-label') || '';
                    const title = el.title || '';
                    let xpath = '';
                    if (id) {
                        xpath = `//*[@id='${id}']`;
                    } else if (name) {
                        xpath = `//${tag}[@name='${name}']`;
                    } else if (ph) {
                        xpath = `//${tag}[@placeholder='${ph}']`;
                    } else if (label) {
                        xpath = `//${tag}[@aria-label='${label}']`;
                    } else if (text && tag !== 'a') {
                        xpath = `//${tag}[contains(text(),'${text.slice(0,25)}')]`;
                    }
                    if (!xpath) continue;
                    const desc = [tag];
                    if (id) desc.push('id=' + id);
                    if (name) desc.push('name=' + name);
                    if (ph) desc.push('placeholder=' + ph);
                    if (text && tag !== 'input') desc.push('"' + text.slice(0,30) + '"');
                    results.push(xpath + ' (' + desc.join(', ') + ')');
                    if (results.length >= 30) break;
                }
                if (results.length >= 30) break;
            }
            return results.join('\\n');
        }""")
        return elements if isinstance(elements, str) else ""
