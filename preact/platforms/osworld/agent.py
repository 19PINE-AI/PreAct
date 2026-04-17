"""PreAct Agent for OSWorld.

Orchestrates CUA-compile-store-replay pipeline for desktop OS tasks.
Follows the same architecture as the Android agent but adapted for
OSWorld's pyautogui actions and accessibility tree format.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from preact.llm.client import LLMClient
from preact.platforms.osworld.environment import (
    OSWorldEnvironment,
    _elements_to_text,
    _find_element,
)
from preact.platforms.osworld.prompts import (
    SYSTEM_PROMPT_COMPILE,
    SYSTEM_PROMPT_CUA,
    USER_PROMPT_COMPILE,
    USER_PROMPT_CUA,
    format_os_trace,
)
from preact.rag.store import ProgramStore
from preact.schemas import (
    ActionSpec,
    ActionType,
    RPAProgram,
    State,
    StateVerification,
    Transition,
    VerificationType,
)

logger = logging.getLogger(__name__)


@dataclass
class OSTaskResult:
    """Result of executing a task on OSWorld."""
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


class PreActOSAgent:
    """PreAct agent for OSWorld tasks.

    Implements the progressive learning pipeline for desktop OS:
    1. Check RAG for matching program
    2. If found: replay via RPA executor, fallback to CUA on failure
    3. If not found: run CUA (pyautogui), compile trace, store program
    """

    def __init__(
        self,
        env: OSWorldEnvironment,
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
        instruction: str,
        parameters: Optional[dict[str, Any]] = None,
        force_cua: bool = False,
    ) -> OSTaskResult:
        """Execute an OS task using the PreAct pipeline."""
        start_time = time.time()
        self.llm.reset_usage()

        # Step 1: Check RAG
        program = None
        if not force_cua and self.store:
            try:
                matches = await self.store.query(instruction, k=1)
                if matches:
                    program = matches[0]
                    logger.info(
                        "Found matching program: %s (%d states)",
                        program.metadata.program_id[:8],
                        len(program.states),
                    )
                    if not parameters:
                        parameters = self._extract_parameters(
                            instruction, program.metadata.parameters
                        )
            except Exception as e:
                logger.warning("RAG lookup failed: %s", e)

        # Step 2: Execute
        if program:
            result = await self._execute_with_rpa(instruction, program, parameters or {})
        else:
            result = await self._execute_with_cua(instruction)

        result.total_time_ms = (time.time() - start_time) * 1000
        result.total_tokens = self.llm.total_tokens
        return result

    async def _execute_with_cua(self, instruction: str) -> OSTaskResult:
        """Execute task using CUA (LLM + pyautogui)."""
        logger.info("Running CUA for: %s", instruction[:80])

        action_history = []
        step_data = []
        answer = ""

        for step in range(self.max_cua_steps):
            # Get current state
            screenshot = await self.env.screenshot()
            a11y_text = self.env.get_a11y_elements_text()

            # Format history
            history_text = "\n".join(action_history[-5:]) if action_history else "None"

            # Detect repeated actions (stuck detection)
            stuck_warning = ""
            if len(action_history) >= 2:
                recent_cmds = []
                for h in action_history[-3:]:
                    parts = h.split(": ", 1)
                    recent_cmds.append(parts[1] if len(parts) > 1 else h)
                if len(set(recent_cmds)) == 1 and len(recent_cmds) >= 2:
                    stuck_count = 0
                    last_cmd = recent_cmds[-1]
                    for h in reversed(action_history):
                        parts = h.split(": ", 1)
                        cmd = parts[1] if len(parts) > 1 else h
                        if cmd == last_cmd:
                            stuck_count += 1
                        else:
                            break
                    if stuck_count >= 4:
                        # Force auto-recovery: try scrolling or going back
                        recovery_actions = [
                            "import pyautogui; pyautogui.scroll(-3)",
                            "import pyautogui; pyautogui.press('escape')",
                            "import pyautogui; pyautogui.hotkey('alt', 'left')",
                        ]
                        recovery = recovery_actions[stuck_count % len(recovery_actions)]
                        logger.info("Auto-recovery (stuck %d times): %s", stuck_count, recovery)
                        self.env._exec_pyautogui(recovery)
                        await asyncio.sleep(0.5)
                        action_history.append(f"Step {step+1}: AUTO_RECOVERY {recovery}")
                        continue
                    stuck_warning = (
                        "\n\n⚠️ WARNING: You have repeated the SAME action "
                        f"{stuck_count} times and the screen has NOT changed. "
                        "Your clicks are NOT working. You MUST try something "
                        "COMPLETELY DIFFERENT:\n"
                        "- Try scrolling down to reveal more content\n"
                        "- Try using a keyboard shortcut instead of clicking\n"
                        "- Try clicking on a DIFFERENT element\n"
                        "- Try pressing Escape or navigating back\n"
                        "- Try a totally different approach to the task"
                    )

            # Build prompt
            prompt = USER_PROMPT_CUA.format(
                instruction=instruction,
                step=step + 1,
                max_steps=self.max_cua_steps,
                action_history=history_text,
                a11y_elements=a11y_text[:3000],  # Limit token usage
            ) + stuck_warning

            # Call LLM with vision
            try:
                response = await self.llm.complete_with_vision(
                    prompt, [screenshot], system=SYSTEM_PROMPT_CUA
                )
            except Exception as e:
                logger.warning("LLM call failed at step %d: %s", step + 1, e)
                continue

            response = response.strip()
            logger.info("Step %d: %s", step + 1, response[:100])

            # Handle terminal responses
            if response.upper() == "DONE":
                return OSTaskResult(
                    success=True,
                    mode="cua",
                    answer=answer,
                    actions_executed=step + 1,
                    actions_via_cua=step + 1,
                    step_data=step_data,
                )

            if response.upper() == "FAIL":
                return OSTaskResult(
                    success=False,
                    mode="cua",
                    answer=answer,
                    actions_executed=step + 1,
                    actions_via_cua=step + 1,
                    step_data=step_data,
                    error="Agent reported infeasible",
                )

            if response.upper().startswith("ANSWER:"):
                answer = response[7:].strip()
                action_history.append(f"Step {step+1}: ANSWER={answer}")
                continue

            # Extract and find element info for the action
            elem_info = self._extract_element_info(response, a11y_text)

            step_data.append({
                "action": response,
                "element_info": elem_info,
            })

            # Execute pyautogui command
            try:
                # Extract the pyautogui command
                cmd = self._extract_pyautogui_cmd(response)
                if cmd:
                    self.env._exec_pyautogui(cmd)
                    await asyncio.sleep(0.5)
                    action_history.append(f"Step {step+1}: {cmd[:80]}")
                else:
                    logger.warning("Could not extract pyautogui command: %s", response[:100])
                    action_history.append(f"Step {step+1}: PARSE_ERROR")
            except Exception as e:
                logger.warning("Action failed: %s", e)
                action_history.append(f"Step {step+1}: FAILED: {e}")

        # Max steps reached
        return OSTaskResult(
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
        instruction: str,
        program: RPAProgram,
        parameters: dict[str, Any],
    ) -> OSTaskResult:
        """Execute task using compiled RPA program."""
        logger.info(
            "Executing RPA: %d states, %d transitions",
            len(program.states),
            len(program.transitions),
        )

        current_state = program.get_initial_state()
        if not current_state:
            return await self._execute_with_cua(instruction)

        actions_rpa = 0
        max_iterations = len(program.states) * 3 + 10

        for iteration in range(max_iterations):
            # Terminal check
            if current_state.verification.type == VerificationType.TERMINAL_STATE:
                logger.info("Reached terminal state: %s", current_state.id)
                return OSTaskResult(
                    success=True,
                    mode="rpa",
                    program_id=program.metadata.program_id,
                    actions_executed=actions_rpa,
                    actions_via_rpa=actions_rpa,
                    graph_coverage=1.0,
                )

            # Verify current state
            if current_state.verification.type == VerificationType.EXPECT_ELEMENT:
                selector = current_state.verification.xpath
                if selector:
                    for pname, pval in parameters.items():
                        selector = selector.replace(f"${{{pname}}}", str(pval))

                    exists = await self.env.element_exists(
                        selector,
                        timeout_ms=current_state.verification.timeout_ms,
                    )
                    if not exists:
                        logger.warning("State verification failed: %s", current_state.id)
                        cua_result = await self._execute_with_cua(instruction)
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
                break

            transition = None
            for t in transitions:
                if t.to_state != current_state.id:
                    transition = t
                    break
            if not transition:
                transition = transitions[0]

            # Execute action
            try:
                await self._execute_os_action(transition.action, parameters)
                actions_rpa += 1
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.warning("RPA action failed: %s", e)
                cua_result = await self._execute_with_cua(instruction)
                cua_result.mode = "hybrid"
                cua_result.actions_via_rpa = actions_rpa
                return cua_result

            next_state = program.get_state(transition.to_state)
            if not next_state:
                break
            current_state = next_state

        return OSTaskResult(
            success=False,
            mode="rpa",
            program_id=program.metadata.program_id,
            actions_executed=actions_rpa,
            actions_via_rpa=actions_rpa,
            error="Max iterations",
        )

    async def _execute_os_action(
        self,
        action: ActionSpec,
        parameters: dict[str, Any],
    ) -> None:
        """Execute a PreAct ActionSpec on OSWorld."""
        at = action.type

        if at == ActionType.ACTION_CLICK:
            target = self._resolve(action.target, parameters)
            await self.env.click(target)

        elif at == ActionType.ACTION_TYPE:
            target = self._resolve(action.target, parameters)
            text = action.text
            if action.parameter_name and action.parameter_name in parameters:
                text = str(parameters[action.parameter_name])
            if text:
                await self.env.type_text(target, text)

        elif at == ActionType.ACTION_KEYPRESS:
            await self.env.press_key(action.key or "Enter")

        elif at == ActionType.ACTION_SCROLL:
            await self.env.scroll(action.direction or "down", action.amount or 3)

        elif at == ActionType.ACTION_NAVIGATE:
            url = action.text or ""
            if action.parameter_name and action.parameter_name in parameters:
                url = str(parameters[action.parameter_name])
            await self.env.navigate(url)

        elif at == ActionType.WAIT:
            await self.env.wait_ms(action.ms or 1000)

        elif at == ActionType.INSPECT_TEXT:
            screenshot = await self.env.screenshot()
            prompt = action.prompt or "What is shown on screen?"
            response = await self.llm.complete_with_vision(prompt, [screenshot])
            logger.info("inspect_text: %s", response[:100])

    def _resolve(self, target: Optional[str], params: dict) -> str:
        if not target:
            return ""
        for k, v in params.items():
            target = target.replace(f"${{{k}}}", str(v))
        return target

    async def compile_and_store(
        self, instruction: str, step_data: list[dict], app_context: str = ""
    ) -> Optional[str]:
        """Compile CUA steps into program and store."""
        if not step_data or not self.store:
            return None

        trace_text = format_os_trace(step_data)
        user_prompt = USER_PROMPT_COMPILE.format(trace_text=trace_text)

        try:
            response = await self.llm.complete(
                messages=[{"role": "user", "content": user_prompt}],
                system=SYSTEM_PROMPT_COMPILE,
            )
            program = self._parse_program(response, instruction, app_context)
            if program:
                pid = await self.store.store(program)
                logger.info("Stored program: %s (%d states)", pid[:8], len(program.states))
                return pid
        except Exception as e:
            logger.warning("Compilation failed: %s", e)
        return None

    def _parse_program(self, response: str, instruction: str, app_ctx: str) -> Optional[RPAProgram]:
        """Parse LLM response into RPAProgram."""
        json_str = self._extract_json(response)
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            return None

        if isinstance(data, list):
            data = data[0] if data else {}
        if "metadata" not in data:
            data["metadata"] = {}
        data["metadata"].setdefault("task_description", instruction)
        data["metadata"].setdefault("application_context", app_ctx)
        if "human_interventions" in data:
            data["human_interventions"] = [
                hi for hi in data["human_interventions"]
                if isinstance(hi, dict) and "before_state" in hi and "prompt" in hi
            ]
        self._fix_actions(data)

        try:
            return RPAProgram.model_validate(data)
        except Exception as e:
            logger.error("Program validation failed: %s", e)
            return None

    def _fix_actions(self, data: dict) -> None:
        valid = {t.value for t in ActionType}
        mapping = {
            "click": "action_click", "type": "action_type", "scroll": "action_scroll",
            "navigate": "action_navigate", "keypress": "action_keypress",
            "press": "action_keypress", "hotkey": "action_keypress",
        }
        for t in data.get("transitions", []):
            action = t.get("action", {})
            if isinstance(action, str):
                t["action"] = {"type": mapping.get(action, "wait")}
            elif isinstance(action, dict):
                atype = action.get("type", "")
                if atype not in valid:
                    action["type"] = mapping.get(atype, "wait")

    def _extract_json(self, text: str) -> str:
        text = text.strip()
        if "```json" in text:
            s = text.index("```json") + 7
            e = text.find("```", s)
            if e != -1:
                return text[s:e].strip()
        if "```" in text:
            s = text.index("```") + 3
            e = text.find("```", s)
            if e != -1:
                return text[s:e].strip()
        for sc, ec in [("{", "}"), ("[", "]")]:
            if sc in text:
                s = text.index(sc)
                d = 0
                for i in range(s, len(text)):
                    if text[i] == sc:
                        d += 1
                    elif text[i] == ec:
                        d -= 1
                        if d == 0:
                            return text[s:i+1]
        return text

    def _extract_pyautogui_cmd(self, response: str) -> Optional[str]:
        """Extract pyautogui command from LLM response."""
        response = response.strip()
        cmd = None
        # Direct pyautogui call
        if response.startswith("pyautogui."):
            cmd = response
        else:
            # Code block
            match = re.search(r"```(?:python)?\s*(.*?)```", response, re.DOTALL)
            if match:
                code = match.group(1).strip()
                if "pyautogui" in code:
                    cmd = code
            else:
                # Inline pyautogui call
                match = re.search(r"(pyautogui\.\w+\([^)]*\))", response)
                if match:
                    cmd = match.group(1)
        if cmd:
            # Fix common LLM mistakes: y(68) -> y=68, x(211) -> x=211
            cmd = re.sub(r'\b([xy])\((\d+)\)', r'\1=\2', cmd)
            # Validate syntax by trying to compile
            try:
                compile(f"import pyautogui; {cmd}", "<cmd>", "exec")
            except SyntaxError as e:
                logger.warning("Invalid pyautogui syntax '%s': %s", cmd[:80], e)
                return None
            return f"import pyautogui; {cmd}"
        return None

    def _extract_element_info(self, response: str, a11y_text: str) -> dict:
        """Extract element info from action response context."""
        info = {}
        # Try to find coordinates in the action
        match = re.search(r"(\d{2,4})\s*,\s*(\d{2,4})", response)
        if match:
            info["x"] = int(match.group(1))
            info["y"] = int(match.group(2))
        return info

    def _extract_parameters(self, instruction: str, param_names: list[str]) -> dict:
        params = {}
        for name in param_names:
            match = re.search(r'"([^"]+)"', instruction)
            if match:
                params[name] = match.group(1)
        return params
