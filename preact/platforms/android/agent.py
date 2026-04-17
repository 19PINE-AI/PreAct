"""PreAct Agent for AndroidWorld.

Orchestrates the CUA-compile-store-replay pipeline for Android tasks.
Follows the same architecture as the browser PreActAgent but adapted
for Android's accessibility tree and action format.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from preact.llm.client import LLMClient
from preact.platforms.android.environment import AndroidEnvironment
from preact.platforms.android.prompts import (
    SYSTEM_PROMPT_COMPILE,
    SYSTEM_PROMPT_CUA,
    USER_PROMPT_COMPILE,
    USER_PROMPT_CUA,
    USER_PROMPT_CUA_FALLBACK,
    format_trace_for_compilation,
)
from preact.rag.store import ProgramStore
from preact.schemas import (
    ActionSpec,
    ActionType,
    ProgramMetadata,
    RPAProgram,
    State,
    StateVerification,
    Transition,
    VerificationType,
)

logger = logging.getLogger(__name__)


@dataclass
class AndroidTaskResult:
    """Result of executing a task on Android."""
    success: bool
    mode: str  # "cua", "rpa", "hybrid"
    answer: str = ""
    program_id: Optional[str] = None
    program_was_new: bool = False
    total_time_ms: float = 0
    total_tokens: int = 0
    actions_executed: int = 0
    actions_via_rpa: int = 0
    actions_via_cua: int = 0
    graph_coverage: float = 0.0
    error: Optional[str] = None
    step_data: list[dict] = field(default_factory=list)


class PreActAndroidAgent:
    """PreAct agent for AndroidWorld tasks.

    Implements the progressive learning pipeline:
    1. Check RAG for matching program
    2. If found: replay via RPA executor, fallback to CUA on failure
    3. If not found: run CUA, compile trace, store program
    """

    def __init__(
        self,
        env: AndroidEnvironment,
        llm: LLMClient,
        store: Optional[ProgramStore] = None,
        max_cua_steps: int = 15,
    ):
        self.env = env
        self.llm = llm
        self.store = store
        self.max_cua_steps = max_cua_steps

    async def execute_task(
        self,
        goal: str,
        parameters: Optional[dict[str, Any]] = None,
        force_cua: bool = False,
    ) -> AndroidTaskResult:
        """Execute an Android task using the PreAct pipeline.

        Args:
            goal: Natural language task description.
            parameters: Optional pre-extracted parameters.
            force_cua: Skip RAG lookup and always use CUA.

        Returns:
            AndroidTaskResult with execution details.
        """
        start_time = time.time()
        self.llm.reset_usage()

        # Step 1: Check RAG for matching program
        program = None
        if not force_cua and self.store:
            try:
                matches = await self.store.query(goal, k=1)
                if matches:
                    program = matches[0]
                    logger.info(
                        "Found matching program: %s (v%d, %d states)",
                        program.metadata.program_id[:8],
                        program.metadata.version,
                        len(program.states),
                    )
                    # Extract parameters from goal
                    if not parameters:
                        parameters = self._extract_parameters(
                            goal, program.metadata.parameters
                        )
            except Exception as e:
                logger.warning("RAG lookup failed: %s", e)

        # Step 2: Execute
        if program:
            result = await self._execute_with_rpa(goal, program, parameters or {})
        else:
            result = await self._execute_with_cua(goal)

        result.total_time_ms = (time.time() - start_time) * 1000
        result.total_tokens = self.llm.total_tokens
        return result

    async def _execute_with_cua(self, goal: str) -> AndroidTaskResult:
        """Execute task using CUA (LLM-driven exploration)."""
        logger.info("Running CUA for: %s", goal[:80])

        action_history = []
        step_data = []
        answer = ""
        screenshot_hashes: list[str] = []
        no_effect_note = ""
        # Track ineffective actions: when stuck-recovery fires, we add the
        # repeated action to this set so subsequent prompts explicitly forbid it.
        forbidden_actions: dict[str, int] = {}

        for step in range(self.max_cua_steps):
            # Get current state (works with both native and HTTP adapters)
            screenshot = await self.env.screenshot()
            ui_text = self.env.get_ui_elements_text()

            # Hash the post-action screenshot. If the last 3 screenshots all
            # hash the same AND at least one action was attempted, the last
            # action had no visible effect — tell the LLM so it doesn't loop.
            try:
                screenshot_hashes.append(hashlib.sha1(screenshot).hexdigest())
            except Exception:
                screenshot_hashes.append("")
            if (
                len(screenshot_hashes) >= 3
                and len(action_history) >= 1
                and screenshot_hashes[-1]
                and screenshot_hashes[-1] == screenshot_hashes[-2] == screenshot_hashes[-3]
            ):
                no_effect_note = (
                    "\n\nNOTE: Your last action produced NO visible change on screen "
                    "(screenshot is byte-identical to the previous two). "
                    "Try a DIFFERENT element or a different approach — do not repeat "
                    "the same action. If you were clicking by coordinate, try an element "
                    "index or a different location."
                )
            else:
                no_effect_note = ""

            # Format history
            history_text = "\n".join(action_history[-5:]) if action_history else "None"

            # Detect repeated actions (stuck detection)
            stuck_warning = ""
            if len(action_history) >= 2:
                recent = action_history[-3:] if len(action_history) >= 3 else action_history[-2:]
                recent_cmds = [h.split(": ", 1)[1] if ": " in h else h for h in recent]
                if len(set(recent_cmds)) == 1:
                    stuck_count = 0
                    last_cmd = recent_cmds[-1]
                    for h in reversed(action_history):
                        cmd = h.split(": ", 1)[1] if ": " in h else h
                        if cmd == last_cmd:
                            stuck_count += 1
                        else:
                            break
                    if stuck_count >= 3:
                        # Add the repeated cmd to forbidden list so the LLM
                        # is explicitly told not to retry it.
                        forbidden_actions[last_cmd] = forbidden_actions.get(last_cmd, 0) + stuck_count
                        # Force auto-recovery
                        recovery_actions = [
                            {"action_type": "scroll", "direction": "down"},
                            {"action_type": "navigate_back"},
                            {"action_type": "scroll", "direction": "up"},
                        ]
                        recovery = recovery_actions[stuck_count % len(recovery_actions)]
                        logger.info("Auto-recovery (stuck %d times): %s", stuck_count, recovery)
                        await self._execute_cua_action(recovery)
                        await asyncio.sleep(0.5)
                        action_history.append(f"Step {step+1}: AUTO_RECOVERY {recovery['action_type']}")
                        continue
                    stuck_warning = (
                        "\n\n⚠️ WARNING: You have repeated the SAME action "
                        f"{stuck_count} times and the screen has NOT changed. "
                        "Your clicks are NOT working. You MUST try something "
                        "COMPLETELY DIFFERENT:\n"
                        "- Try scrolling to reveal more content\n"
                        "- Try pressing back and navigating differently\n"
                        "- Try clicking a DIFFERENT element on screen\n"
                        "- Try opening a different app\n"
                        "- Try a totally different approach to the task"
                    )

            forbidden_note = ""
            if forbidden_actions:
                items = "\n".join(
                    f"  - {cmd} (ineffective after {n} tries)"
                    for cmd, n in sorted(
                        forbidden_actions.items(), key=lambda kv: -kv[1]
                    )[:5]
                )
                forbidden_note = (
                    "\n\n🚫 FORBIDDEN ACTIONS — these produced no progress; "
                    "DO NOT repeat them. Pick a DIFFERENT element/approach:\n"
                    + items
                )

            # Build prompt
            prompt = USER_PROMPT_CUA.format(
                goal=goal,
                step=step + 1,
                max_steps=self.max_cua_steps,
                action_history=history_text,
                ui_elements=ui_text,
            ) + stuck_warning + no_effect_note + forbidden_note

            # Call LLM with vision
            try:
                response = await self.llm.complete_with_vision(
                    prompt, [screenshot], system=SYSTEM_PROMPT_CUA
                )
            except Exception as e:
                logger.warning("LLM call failed at step %d: %s", step + 1, e)
                continue

            # Parse action
            action_dict = self._parse_action(response)
            if not action_dict:
                logger.warning("Failed to parse action: %s", response[:200])
                continue

            action_type = action_dict.get("action_type", "")
            logger.info(
                "Step %d: %s %s",
                step + 1,
                action_type,
                json.dumps({k: v for k, v in action_dict.items() if k != "action_type"})[:100],
            )

            # Record step data
            elem_info = {}
            if action_dict.get("index") is not None:
                elem_info = {"index": action_dict["index"]}

            step_data.append({
                "action": action_dict,
                "element_info": elem_info,
                "ui_elements_text": ui_text[:500],
            })

            # Handle terminal actions
            if action_type == "status":
                done = action_dict.get("goal_status") == "complete"
                action_history.append(f"Step {step+1}: status={action_dict.get('goal_status')}")
                return AndroidTaskResult(
                    success=done,
                    mode="cua",
                    answer=answer,
                    actions_executed=step + 1,
                    actions_via_cua=step + 1,
                    step_data=step_data,
                )

            if action_type == "answer":
                answer = action_dict.get("text", "")
                action_history.append(f"Step {step+1}: answer='{answer}'")
                # Don't execute, just record
                continue

            # Execute action via environment adapter
            try:
                await self._execute_cua_action(action_dict)
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.warning("Action execution failed: %s", e)
                action_history.append(f"Step {step+1}: {action_type} FAILED: {e}")
                continue

            # Include action details in history so LLM can detect repeated actions
            action_detail = action_type
            if action_type == "click":
                if action_dict.get("x") is not None:
                    action_detail = f"click at ({action_dict['x']}, {action_dict['y']})"
                elif action_dict.get("index") is not None:
                    action_detail = f"click index={action_dict['index']}"
            elif action_type == "input_text":
                action_detail = f"input_text \"{action_dict.get('text', '')}\""
            elif action_type == "open_app":
                action_detail = f"open_app \"{action_dict.get('app_name', '')}\""
            elif action_type == "scroll":
                action_detail = f"scroll {action_dict.get('direction', 'down')}"
            action_history.append(f"Step {step+1}: {action_detail}")

        # Max steps reached
        logger.info("CUA: max steps reached")
        return AndroidTaskResult(
            success=False,
            mode="cua",
            answer=answer,
            actions_executed=self.max_cua_steps,
            actions_via_cua=self.max_cua_steps,
            step_data=step_data,
            error="Max steps reached",
        )

    async def _execute_with_rpa(
        self,
        goal: str,
        program: RPAProgram,
        parameters: dict[str, Any],
    ) -> AndroidTaskResult:
        """Execute task using compiled RPA program.

        Traverses the state machine, verifying states and executing actions.
        Falls back to CUA if state verification fails.
        """
        logger.info(
            "Executing RPA program: %d states, %d transitions",
            len(program.states),
            len(program.transitions),
        )

        # Find initial state
        current_state = program.get_initial_state()
        if not current_state:
            logger.error("Program has no initial state")
            return await self._execute_with_cua(goal)

        actions_rpa = 0
        actions_cua = 0
        states_visited = []
        max_iterations = len(program.states) * 3 + 10

        for iteration in range(max_iterations):
            states_visited.append(current_state.id)

            # Check terminal
            if current_state.verification.type == VerificationType.TERMINAL_STATE:
                logger.info("Reached terminal state: %s", current_state.id)
                # Extract answer from context data
                answer = ""
                # Look at any stored data from inspect_text actions
                # (Would need execution context — simplified here)
                return AndroidTaskResult(
                    success=True,
                    mode="rpa",
                    answer=answer,
                    program_id=program.metadata.program_id,
                    actions_executed=actions_rpa,
                    actions_via_rpa=actions_rpa,
                    graph_coverage=1.0,
                )

            # Verify current state
            if current_state.verification.type == VerificationType.EXPECT_ELEMENT:
                selector = current_state.verification.xpath
                if selector:
                    # Resolve parameters in selector
                    for param_name, param_value in parameters.items():
                        selector = selector.replace(f"${{{param_name}}}", str(param_value))

                    exists = await self.env.element_exists(
                        selector,
                        timeout_ms=current_state.verification.timeout_ms,
                    )
                    if not exists:
                        logger.warning(
                            "State verification failed: %s (selector: %s)",
                            current_state.id,
                            selector[:80],
                        )
                        # Fallback to CUA
                        cua_result = await self._execute_with_cua(goal)
                        cua_result.mode = "hybrid"
                        cua_result.actions_via_rpa = actions_rpa
                        cua_result.program_id = program.metadata.program_id
                        if actions_rpa + cua_result.actions_via_cua > 0:
                            cua_result.graph_coverage = actions_rpa / (
                                actions_rpa + cua_result.actions_via_cua
                            )
                        return cua_result

            # Select transition
            transitions = program.get_transitions_from(current_state.id)
            if not transitions:
                logger.warning("No transitions from state: %s", current_state.id)
                break

            # Pick first non-self-loop transition (or unconditional)
            transition = None
            for t in transitions:
                if t.to_state != current_state.id:
                    transition = t
                    break
            if not transition:
                transition = transitions[0]

            # Execute action
            action = transition.action
            try:
                await self._execute_android_action(action, parameters)
                actions_rpa += 1
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.warning("RPA action failed: %s", e)
                # Fallback to CUA
                cua_result = await self._execute_with_cua(goal)
                cua_result.mode = "hybrid"
                cua_result.actions_via_rpa = actions_rpa
                cua_result.program_id = program.metadata.program_id
                return cua_result

            # Move to next state
            next_state = program.get_state(transition.to_state)
            if not next_state:
                logger.warning("Next state not found: %s", transition.to_state)
                break
            current_state = next_state

        logger.warning("Max iterations reached in RPA execution")
        return AndroidTaskResult(
            success=False,
            mode="rpa",
            program_id=program.metadata.program_id,
            actions_executed=actions_rpa,
            actions_via_rpa=actions_rpa,
            error="Max iterations",
        )

    async def _execute_cua_action(self, action_dict: dict) -> None:
        """Execute a parsed CUA action dict via the environment adapter.

        Works with both native AndroidEnvironment and AndroidHTTPEnvironment.
        Unknown or unsupported action types RAISE so the CUA loop records
        the failure in action_history and the LLM sees the mistake.
        """
        action_type = action_dict.get("action_type", "")

        if action_type == "click":
            idx = action_dict.get("index")
            if idx is not None:
                await self.env.click(f"index={idx}")
            elif action_dict.get("x") is not None:
                await self.env.click(f"x={action_dict['x']}&&y={action_dict['y']}")
            else:
                raise ValueError("click action missing both index and x/y")
        elif action_type == "input_text":
            text = action_dict.get("text", "")
            idx = action_dict.get("index")
            if idx is not None:
                await self.env.type_text(f"index={idx}", text)
            elif action_dict.get("x") is not None:
                await self.env.click(f"x={action_dict['x']}&&y={action_dict['y']}")
                await asyncio.sleep(0.3)
                await self.env.type_text("", text)
            else:
                await self.env.type_text("", text)
        elif action_type == "scroll":
            direction = action_dict.get("direction", "down")
            await self.env.scroll(direction, 1)
        elif action_type == "open_app":
            app_name = action_dict.get("app_name", "")
            await self.env.navigate(app_name)
        elif action_type == "navigate_back":
            await self.env.go_back()
        elif action_type == "navigate_home":
            await self.env.press_key("home")
        elif action_type == "keyboard_enter":
            await self.env.press_key("enter")
        elif action_type == "long_press":
            idx = action_dict.get("index")
            x = action_dict.get("x")
            y = action_dict.get("y")
            if hasattr(self.env, "long_press"):
                if idx is not None:
                    await self.env.long_press(f"index={idx}")
                elif x is not None and y is not None:
                    await self.env.long_press((int(x), int(y)))
                else:
                    raise ValueError("long_press missing index and x/y")
            elif idx is not None and hasattr(self.env, "right_click"):
                await self.env.right_click(f"index={idx}")
            else:
                raise ValueError("environment does not support long_press")
        elif action_type == "double_tap" or action_type == "double_click":
            idx = action_dict.get("index")
            if idx is not None and hasattr(self.env, "double_click"):
                await self.env.double_click(f"index={idx}")
            elif action_dict.get("x") is not None and hasattr(self.env, "double_click"):
                await self.env.double_click(
                    f"x={action_dict['x']}&&y={action_dict['y']}"
                )
            else:
                raise ValueError("environment does not support double_tap for this target")
        elif action_type == "triple_click":
            idx = action_dict.get("index")
            x = action_dict.get("x")
            y = action_dict.get("y")
            if hasattr(self.env, "triple_click"):
                if idx is not None:
                    await self.env.triple_click(f"index={idx}")
                elif x is not None and y is not None:
                    await self.env.triple_click((int(x), int(y)))
                else:
                    raise ValueError("triple_click missing index and x/y")
            else:
                # Generic fallback: click three times quickly
                if idx is not None:
                    for _ in range(3):
                        await self.env.click(f"index={idx}")
                        await asyncio.sleep(0.08)
                elif x is not None and y is not None:
                    for _ in range(3):
                        await self.env.click(f"x={x}&&y={y}")
                        await asyncio.sleep(0.08)
                else:
                    raise ValueError("triple_click missing index and x/y")
        elif action_type == "clear":
            # Select-all + delete on the focused (or specified) editable field.
            idx = action_dict.get("index")
            if hasattr(self.env, "clear"):
                if idx is not None:
                    await self.env.clear(f"index={idx}")
                else:
                    await self.env.clear("")
            else:
                # Fallback: clear_and_type with empty string
                target = f"index={idx}" if idx is not None else ""
                if hasattr(self.env, "clear_and_type"):
                    await self.env.clear_and_type(target, "")
                else:
                    raise ValueError("environment does not support clear")
        elif action_type == "wait":
            await self.env.wait_ms(1000)
        elif action_type in ("status", "answer"):
            # Terminal / bookkeeping actions handled by caller; this function
            # should never be invoked for them, but guard against misuse.
            return
        else:
            raise ValueError(f"Unknown CUA action type: {action_type!r}")

    async def _execute_android_action(
        self,
        action: ActionSpec,
        parameters: dict[str, Any],
    ) -> None:
        """Execute a PreAct ActionSpec on Android.

        Uses the environment adapter's common interface methods,
        so works with both native and HTTP-based environments.
        """
        action_type = action.type

        if action_type == ActionType.ACTION_CLICK:
            target = self._resolve_target(action.target, parameters)
            await self.env.click(target)

        elif action_type == ActionType.ACTION_TYPE:
            target = self._resolve_target(action.target, parameters)
            text = action.text
            if action.parameter_name and action.parameter_name in parameters:
                text = str(parameters[action.parameter_name])
            if text:
                await self.env.type_text(target, text)

        elif action_type == ActionType.ACTION_KEYPRESS:
            key = action.key or "Enter"
            await self.env.press_key(key)

        elif action_type == ActionType.ACTION_SCROLL:
            direction = action.direction or "down"
            amount = action.amount or 1
            if action.target:
                await self.env.scroll_element(
                    self._resolve_target(action.target, parameters),
                    direction, amount,
                )
            else:
                await self.env.scroll(direction, amount)

        elif action_type == ActionType.ACTION_NAVIGATE:
            app_name = action.text or ""
            if action.parameter_name and action.parameter_name in parameters:
                app_name = str(parameters[action.parameter_name])
            await self.env.navigate(app_name)

        elif action_type == ActionType.WAIT:
            ms = action.ms or 1000
            await self.env.wait_ms(ms)

        elif action_type == ActionType.INSPECT_TEXT:
            # Use LLM to extract text from current screen
            screenshot = await self.env.screenshot()
            prompt = action.prompt or "What text is shown on screen?"
            response = await self.llm.complete_with_vision(
                prompt, [screenshot]
            )
            # Store result (simplified — would use ExecutionContext in full impl)
            logger.info("inspect_text result: %s", response[:100])

        else:
            logger.warning("Unsupported action type: %s", action_type)

    def _resolve_target(self, target: Optional[str], parameters: dict[str, Any]) -> str:
        """Resolve parameter references in target selector."""
        if not target:
            return ""
        for param_name, param_value in parameters.items():
            target = target.replace(f"${{{param_name}}}", str(param_value))
        return target

    async def compile_and_store(
        self,
        goal: str,
        step_data: list[dict],
        app_context: str = "",
    ) -> Optional[str]:
        """Compile CUA steps into a program and store in RAG.

        Args:
            goal: Task description.
            step_data: Recorded step data from CUA execution.
            app_context: App package or name.

        Returns:
            Program ID if successfully compiled and stored.
        """
        if not step_data or not self.store:
            return None

        # Format trace for compilation
        trace_text = format_trace_for_compilation(step_data)

        user_prompt = USER_PROMPT_COMPILE.format(trace_text=trace_text)

        try:
            response = await self.llm.complete(
                messages=[{"role": "user", "content": user_prompt}],
                system=SYSTEM_PROMPT_COMPILE,
            )

            program = self._parse_program(response, goal, app_context)
            if program:
                program_id = await self.store.store(program)
                logger.info(
                    "Compiled and stored program: %s (%d states, %d transitions)",
                    program_id[:8],
                    len(program.states),
                    len(program.transitions),
                )
                return program_id

        except Exception as e:
            logger.warning("Compilation failed: %s", e)

        return None

    def _parse_program(
        self, response: str, goal: str, app_context: str
    ) -> Optional[RPAProgram]:
        """Parse LLM response into RPAProgram."""
        # Extract JSON
        json_str = self._extract_json(response)
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse compilation response: %s", e)
            return None

        if isinstance(data, list):
            data = data[0] if data else {}

        # Ensure metadata
        if "metadata" not in data:
            data["metadata"] = {}

        metadata = data["metadata"]
        metadata.setdefault("task_description", goal)
        metadata.setdefault("application_context", app_context)

        # Clean up human_interventions
        if "human_interventions" in data:
            valid = []
            for hi in data["human_interventions"]:
                if isinstance(hi, dict) and "before_state" in hi and "prompt" in hi:
                    valid.append(hi)
            data["human_interventions"] = valid

        # Fix action types
        self._fix_actions(data)

        try:
            return RPAProgram.model_validate(data)
        except Exception as e:
            logger.error("Failed to validate program: %s", e)
            return None

    def _fix_actions(self, data: dict) -> None:
        """Fix common LLM mistakes in action fields."""
        valid_types = {t.value for t in ActionType}
        for t in data.get("transitions", []):
            action = t.get("action", {})
            if isinstance(action, str):
                t["action"] = {"type": action, "target": ""}
            elif isinstance(action, dict):
                atype = action.get("type", "")
                if atype not in valid_types:
                    # Try to map common Android action names
                    mapping = {
                        "click": "action_click",
                        "tap": "action_click",
                        "type": "action_type",
                        "input": "action_type",
                        "input_text": "action_type",
                        "scroll": "action_scroll",
                        "navigate": "action_navigate",
                        "open_app": "action_navigate",
                        "back": "action_keypress",
                        "enter": "action_keypress",
                    }
                    mapped = mapping.get(atype, "wait")
                    action["type"] = mapped
                    if mapped == "action_keypress" and "key" not in action:
                        action["key"] = atype.capitalize()

    def _extract_json(self, text: str) -> str:
        """Extract JSON from LLM response."""
        text = text.strip()

        if "```json" in text:
            start = text.index("```json") + 7
            closing = text.find("```", start)
            if closing != -1:
                return text[start:closing].strip()

        if "```" in text:
            start = text.index("```") + 3
            closing = text.find("```", start)
            if closing != -1:
                return text[start:closing].strip()

        for start_char, end_char in [("{", "}"), ("[", "]")]:
            if start_char in text:
                start = text.index(start_char)
                depth = 0
                for i in range(start, len(text)):
                    if text[i] == start_char:
                        depth += 1
                    elif text[i] == end_char:
                        depth -= 1
                        if depth == 0:
                            return text[start : i + 1]

        return text

    def _parse_action(self, response: str) -> Optional[dict]:
        """Parse LLM response into an action dict."""
        json_str = self._extract_json(response)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Try to find JSON in the response
            match = re.search(r'\{[^{}]*"action_type"[^{}]*\}', response)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        return None

    def _extract_parameters(
        self, goal: str, parameter_names: list[str]
    ) -> dict[str, Any]:
        """Extract parameter values from the goal text."""
        params = {}
        for name in parameter_names:
            # Try quoted values
            patterns = [
                rf'"{name}"\s*[:=]\s*"([^"]+)"',
                rf"'{name}'\s*[:=]\s*'([^']+)'",
                rf'{name}\s+(?:is|=)\s+"([^"]+)"',
                rf'{name}\s+(?:is|=)\s+(\S+)',
            ]

            # Try common patterns
            if name in ("name", "contact_name"):
                match = re.search(r'for\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', goal)
                if match:
                    params[name] = match.group(1)
                    continue

            if name in ("number", "phone", "phone_number"):
                match = re.search(r'(\+?[\d\s\-()]{7,})', goal)
                if match:
                    params[name] = match.group(1).strip()
                    continue

            if name in ("message", "text", "note"):
                match = re.search(r'(?:message|text|note)\s+"([^"]+)"', goal, re.I)
                if match:
                    params[name] = match.group(1)
                    continue
                match = re.search(r'"([^"]{5,})"', goal)
                if match:
                    params[name] = match.group(1)
                    continue

            if name in ("email", "email_address"):
                match = re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', goal)
                if match:
                    params[name] = match.group()
                    continue

            if name in ("time", "alarm_time"):
                match = re.search(r'(\d{1,2}:\d{2}(?:\s*[AaPp][Mm])?)', goal)
                if match:
                    params[name] = match.group(1)
                    continue

            if name in ("date",):
                match = re.search(
                    r'(\w+\s+\d{1,2},?\s+\d{4}|\d{1,2}/\d{1,2}/\d{2,4})', goal
                )
                if match:
                    params[name] = match.group(1)
                    continue

            if name in ("search_term", "query", "keyword"):
                match = re.search(r'"([^"]+)"', goal)
                if match:
                    params[name] = match.group(1)
                    continue

            # Generic: try extracting quoted strings
            for pattern in patterns:
                match = re.search(pattern, goal, re.I)
                if match:
                    params[name] = match.group(1)
                    break

        if params:
            logger.info("Extracted parameters: %s", params)
        return params
