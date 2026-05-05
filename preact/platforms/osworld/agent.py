"""PreAct Agent for OSWorld.

Orchestrates CUA-compile-store-replay pipeline for desktop OS tasks.
Follows the same architecture as the Android agent but adapted for
OSWorld's pyautogui actions and accessibility tree format.
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
    cua_tokens: int = 0
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
        cua_backend: str = "claude_cu",
    ):
        self.env = env
        self.llm = llm
        self.store = store
        self.max_cua_steps = max_cua_steps
        # "claude_cu" = native Anthropic Computer Use beta tool (SOTA recipe)
        # "legacy_a11y" = numbered a11y-tree + semantic action parser
        self.cua_backend = cua_backend
        # Agentic selector — reads program descriptions and picks one via
        # tool-calling. PREACT_SELECTOR_MODE=embedding swaps to a
        # sentence-transformer cosine baseline for ablation.
        import os as _os_sel
        _sel_mode = _os_sel.environ.get("PREACT_SELECTOR_MODE", "agentic").lower()
        if _sel_mode == "embedding":
            from preact.rag.embedding_selector import EmbeddingSelector
            self.selector = EmbeddingSelector(llm, store) if store else None
        else:
            from preact.rag.selector import ProgramSelector
            self.selector = ProgramSelector(llm, store) if store else None

    async def execute_task(
        self,
        instruction: str,
        parameters: Optional[dict[str, Any]] = None,
        force_cua: bool = False,
    ) -> OSTaskResult:
        """Execute an OS task using the PreAct pipeline."""
        start_time = time.time()
        self.llm.reset_usage()

        # Step 1: Let the selector agent pick a program by description.
        program = None
        if not force_cua and self.selector:
            try:
                program = await self.selector.select(
                    task=instruction, platform="osworld"
                )
                if program and not parameters:
                    parameters = self._extract_parameters(
                        instruction, program.metadata.parameters
                    )
            except Exception as e:
                logger.warning("Selector failed: %s", e)

        # Step 2: Execute
        if program:
            result = await self._execute_with_rpa(instruction, program, parameters or {})
        else:
            result = await self._execute_with_cua(instruction)

        result.total_time_ms = (time.time() - start_time) * 1000
        result.total_tokens = self.llm.total_tokens + getattr(result, "cua_tokens", 0)
        return result

    async def _execute_with_cua(self, instruction: str) -> OSTaskResult:
        """Dispatch to the configured CUA backend."""
        if self.cua_backend == "claude_cu":
            from preact.platforms.osworld.claude_cua import ClaudeComputerUseCUA
            cua = ClaudeComputerUseCUA()
            result = await cua.run(instruction, self.env, max_steps=self.max_cua_steps)
            result.cua_tokens = cua.total_tokens
            return result
        return await self._execute_with_cua_legacy(instruction)

    async def _execute_with_cua_legacy(self, instruction: str) -> OSTaskResult:
        """Execute task using CUA (LLM + semantic action vocabulary).

        Bug fixes in this method:
          * Bug 3: LLM is asked for a semantic action (click(id=N) etc.);
            parser maps id=N back to coordinates from the a11y list. Raw
            pyautogui.* is accepted as a backwards-compat fallback. The
            path used ("semantic:click" / "pyautogui" / "raw") is recorded
            into action_history for auditability.
          * Bug 4: a11y tree capped at 12000 chars (was 3000) and shown
            in the dense line-per-element format.
          * Bug 6: stuck detection now also compares sha1 of screenshots.
          * Additional A: warn the LLM when the a11y tree is empty.
        """
        logger.info("Running CUA for: %s", instruction[:80])

        action_history: list[str] = []
        step_data: list[dict] = []
        screenshot_hashes: list[str] = []
        answer = ""
        forbidden_actions: dict[str, int] = {}

        for step in range(self.max_cua_steps):
            # Get current state — a11y must be fetched first so annotated
            # screenshot uses the same element indices the LLM will see.
            elements = self.env._get_a11y_elements()
            a11y_text = self.env.get_a11y_elements_text()
            if hasattr(self.env, "annotated_screenshot"):
                try:
                    screenshot = await self.env.annotated_screenshot()
                except Exception as e:
                    logger.warning("annotated_screenshot failed: %s; raw", e)
                    screenshot = await self.env.screenshot()
            else:
                screenshot = await self.env.screenshot()

            # Track screenshot hash (Bug 6)
            screenshot_hash = (
                hashlib.sha1(screenshot).hexdigest() if screenshot else ""
            )
            screenshot_hashes.append(screenshot_hash)

            # Format history
            history_text = "\n".join(action_history[-5:]) if action_history else "None"

            # Detect stuck loops — covers (a) A A A, (b) A B A B oscillation,
            # (c) A B C A B C 3-cycle. The oscillation cases are the ones
            # that matter in practice: the LLM picks id=X and id=Y alternately,
            # which the old "3 consecutive identical" check never caught.
            stuck_warning = ""
            cmds_hist = [
                h.split(": ", 1)[1] if ": " in h else h
                for h in action_history
            ]
            cycle_info = None
            if len(cmds_hist) >= 3 and cmds_hist[-1] == cmds_hist[-2] == cmds_hist[-3]:
                cycle_info = (1, [cmds_hist[-1]])
            elif (
                len(cmds_hist) >= 4
                and cmds_hist[-1] == cmds_hist[-3]
                and cmds_hist[-2] == cmds_hist[-4]
                and cmds_hist[-1] != cmds_hist[-2]
            ):
                cycle_info = (2, [cmds_hist[-2], cmds_hist[-1]])
            elif (
                len(cmds_hist) >= 6
                and cmds_hist[-1] == cmds_hist[-4]
                and cmds_hist[-2] == cmds_hist[-5]
                and cmds_hist[-3] == cmds_hist[-6]
                and len({cmds_hist[-1], cmds_hist[-2], cmds_hist[-3]}) == 3
            ):
                cycle_info = (3, [cmds_hist[-3], cmds_hist[-2], cmds_hist[-1]])
            # Guard: only apply the UI-hash identity check to MULTI-step
            # cycles (ABAB digit-entry made real progress). For a pure
            # 1-cycle (AAA) — same action emitted N times — always flag it
            # as stuck: same action + no progress is stuck regardless of
            # minor screen animation. Otherwise dynamic pages (loading
            # spinners, focus rings) would silence legit stuck detection.
            if cycle_info is not None and cycle_info[0] >= 2 and len(screenshot_hashes) >= 2:
                cl = cycle_info[0]
                needed = cl * 2
                if len(screenshot_hashes) >= needed:
                    tail = screenshot_hashes[-needed:]
                    first, second = tail[:cl], tail[cl:]
                    if any(
                        h1 and h2 and h1 != h2
                        for h1, h2 in zip(first, second)
                    ):
                        cycle_info = None
            if cycle_info is not None:
                cycle_len, unique_cmds = cycle_info
                for cmd in unique_cmds:
                    forbidden_actions[cmd] = forbidden_actions.get(cmd, 0) + 1
                recovery_actions = [
                    "import pyautogui; pyautogui.scroll(-3)",
                    "import pyautogui; pyautogui.press('escape')",
                    "import pyautogui; pyautogui.hotkey('alt', 'left')",
                    "import pyautogui; pyautogui.press('f5')",
                ]
                total = sum(forbidden_actions.values())
                recovery = recovery_actions[total % len(recovery_actions)]
                logger.info(
                    "Stuck (cycle_len=%d, cmds=%s) — recovery: %s",
                    cycle_len, unique_cmds, recovery,
                )
                self.env._exec_pyautogui(recovery)
                await asyncio.sleep(0.5)
                action_history.append(
                    f"Step {step+1}: AUTO_RECOVERY {recovery} (broke {cycle_len}-cycle)"
                )
                continue

            # Screenshot-hash-based stuck detection (Bug 6)
            screen_unchanged_note = ""
            if (
                len(screenshot_hashes) >= 2
                and screenshot_hashes[-1]
                and screenshot_hashes[-1] == screenshot_hashes[-2]
                and action_history  # an action was attempted between them
            ):
                screen_unchanged_note = (
                    "\n\nNOTE: Your previous action did not change the screen. "
                    "Try a different element or approach."
                )

            # Empty-a11y warning (Additional A)
            empty_a11y_note = ""
            if not elements:
                empty_a11y_note = (
                    "\n\nWARNING: accessibility tree is empty — you must rely "
                    "on the screenshot and use raw_click(x,y) format."
                )

            forbidden_note = ""
            forbidden_ids: set[str] = set()
            forbidden_coords: set[tuple[int, int]] = set()
            if forbidden_actions:
                # Forbidden entries look like "[semantic:click] click(956,90)".
                # Extract both id=N patterns AND the resolved (cx,cy) — the
                # latter is what catches the "many different ids all hit the
                # same spot" stuck-click pattern.
                for cmd in forbidden_actions:
                    m = re.search(r"id=(\d+)", cmd)
                    if m:
                        forbidden_ids.add(m.group(1))
                    m = re.search(r"\((-?\d+)\s*,\s*(-?\d+)\)", cmd)
                    if m:
                        forbidden_coords.add((int(m.group(1)), int(m.group(2))))
                items = "\n".join(
                    f"  - {cmd} (ineffective after {n} tries)"
                    for cmd, n in sorted(
                        forbidden_actions.items(), key=lambda kv: -kv[1]
                    )[:5]
                )
                forbidden_note = (
                    "🚫 CRITICAL — FORBIDDEN ACTIONS. These produced NO progress "
                    "and are BLOCKED this step. DO NOT emit any of them:\n"
                    + items
                    + "\n\n"
                )
            # Mark forbidden ids in the a11y listing so LLM sees them inline.
            # Also mark any element whose center is within ~12px of a
            # forbidden coord — catches the "list reshuffled, same spot,
            # different id" case that otherwise evades the per-id ban.
            a11y_shown = a11y_text[:12000]
            if forbidden_ids or forbidden_coords:
                marked_indices: set[int] = set()
                if forbidden_coords:
                    for i, e in enumerate(elements):
                        cx = e.get("x", 0) + e.get("width", 0) // 2
                        cy = e.get("y", 0) + e.get("height", 0) // 2
                        for fx, fy in forbidden_coords:
                            if abs(cx - fx) <= 12 and abs(cy - fy) <= 12:
                                marked_indices.add(i)
                                break
                for fid in forbidden_ids:
                    try:
                        marked_indices.add(int(fid))
                    except ValueError:
                        pass
                for idx in sorted(marked_indices, reverse=True):
                    a11y_shown = a11y_shown.replace(
                        f"[{idx}]", f"[{idx}-FORBIDDEN]"
                    )

            # Build prompt (Bug 4: cap 12000). Forbidden-note goes FIRST so
            # it is seen before the UI elements listing.
            prompt = forbidden_note + USER_PROMPT_CUA.format(
                instruction=instruction,
                step=step + 1,
                max_steps=self.max_cua_steps,
                action_history=history_text,
                a11y_elements=a11y_shown,
            ) + stuck_warning + screen_unchanged_note + empty_a11y_note

            # Call LLM with vision. Cap max_tokens=600: high enough that
            # Claude can emit a reasoning preamble AND the action line
            # (parser scans all lines for the action), low enough to stay
            # cheap and fast. max_tokens=300 truncated preambles mid-
            # sentence before the action.
            try:
                response = await self.llm.complete_with_vision(
                    prompt, [screenshot], system=SYSTEM_PROMPT_CUA,
                    max_tokens=600,
                )
            except Exception as e:
                logger.warning("LLM call failed at step %d: %s", step + 1, e)
                action_history.append(f"Step {step+1}: LLM_ERROR: {e}")
                continue

            response = response.strip()
            logger.info("Step %d: %s", step + 1, response[:100])

            traj_dir = getattr(self, "_trajectory_dir", None)
            if traj_dir:
                import os as _os
                _os.makedirs(traj_dir, exist_ok=True)
                base = _os.path.join(traj_dir, f"step{step+1:02d}")
                try:
                    with open(base + ".png", "wb") as _f:
                        _f.write(screenshot)
                    with open(base + ".txt", "w") as _f:
                        _f.write("=== A11Y ===\n" + a11y_text + "\n\n")
                        _f.write("=== PROMPT ===\n" + prompt + "\n\n")
                        _f.write("=== RESPONSE ===\n" + response + "\n")
                except Exception as _e:
                    logger.warning("trajectory dump failed: %s", _e)

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

            # Extract element info for audit
            elem_info = self._extract_element_info(response, elements)

            step_data.append({
                "action": response,
                "element_info": elem_info,
            })

            # Dispatch action (Bug 3 — semantic first, pyautogui fallback)
            try:
                dispatched = await self._dispatch_cua_action(response, elements)
                path = dispatched.get("path", "unknown")
                summary = dispatched.get("summary", response[:80])
                await asyncio.sleep(0.3)
                action_history.append(f"Step {step+1}: [{path}] {summary}")
            except ValueError as e:
                # Selector/index not found — surface into history so the LLM sees it
                logger.warning("Action unresolved at step %d: %s", step + 1, e)
                action_history.append(f"Step {step+1}: UNRESOLVED: {e}")
                # Ban the invalid id so the LLM can't re-emit it forever.
                # The cycle detector only fires after an ABAB pattern (4
                # steps wasted); immediate banning prevents the repeat.
                m_bad = re.search(r"id=(\d+)", response)
                if m_bad:
                    forbidden_actions[f"id={m_bad.group(1)}"] = (
                        forbidden_actions.get(f"id={m_bad.group(1)}", 0) + 1
                    )
            except Exception as e:
                logger.warning("Action failed at step %d: %s", step + 1, e)
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

            # PREACT_RUNTIME_MODE=flat_script (Exp A ablation): bypass
            # per-state verification entirely to mimic ActionEngine-style
            # flat-script linear execution.
            import os
            _flat_script = os.environ.get('PREACT_RUNTIME_MODE', 'state_machine').lower() == 'flat_script'

            # Verify current state
            if not _flat_script and current_state.verification.type == VerificationType.EXPECT_ELEMENT:
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
        """Execute a PreAct ActionSpec on OSWorld.

        Preference order:
          1. raw_command (verbatim pyautogui from recording) for action types
             where the semantic form commonly drops detail — keypress,
             hotkeys, and type (which semantic collapses Ctrl+S / multi-key
             sequences into a single press).
          2. semantic action using the live a11y tree (resolves dynamic
             coordinates).
          3. raw_command as a last-resort fallback if semantic raises.

        The rationale: keystroke actions carry no dynamic state, so the
        recorded command is guaranteed correct. Click/type benefit from
        re-resolving selectors against the current tree.
        """
        at = action.type
        raw = (action.raw_command or "").strip()

        # Prefer raw for keypress/hotkey (semantic compile drops Ctrl/Alt modifiers).
        if raw and at == ActionType.ACTION_KEYPRESS:
            self.env._exec_pyautogui(raw if raw.startswith("import ") else f"import pyautogui\n{raw}")
            return

        try:
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
        except Exception as e:
            if raw:
                logger.warning("Semantic action %s failed (%s) — raw fallback", at, e)
                self.env._exec_pyautogui(raw if raw.startswith("import ") else f"import pyautogui\n{raw}")
                return
            raise

    def _resolve(self, target: Optional[str], params: dict) -> str:
        if not target:
            return ""
        for k, v in params.items():
            target = target.replace(f"${{{k}}}", str(v))
        return target

    async def compile(
        self, instruction: str, step_data: list[dict], app_context: str = ""
    ) -> Optional[RPAProgram]:
        """Compile CUA step trace into an RPAProgram (does NOT store).

        Split from the old compile_and_store so the caller can run a
        pre-store verification replay: compile → reset env → replay →
        re-evaluate → store only if still passes.
        """
        if not step_data:
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
                self._attach_raw_commands(program, step_data)
                from preact.rag.compile_utils import sanitize_literals
                program = sanitize_literals(program, instruction)
            return program
        except Exception as e:
            logger.warning("Compilation failed: %s", e)
            return None

    async def store_program(self, program: RPAProgram) -> Optional[str]:
        """Persist a compiled program to RAG (tagged osworld)."""
        if not self.store:
            return None
        pid = await self.store.store(program, platform="osworld")
        logger.info("Stored program: %s (%d states)", pid[:8], len(program.states))
        return pid

    async def replay_program(
        self, instruction: str, program: RPAProgram
    ) -> OSTaskResult:
        """Run the compiled program against the current env (no CUA fallback).

        Used for pre-store verification — if this run doesn't re-pass the
        evaluator, the program is lossy and must not be stored.
        """
        return await self._execute_with_rpa(instruction, program, {})

    async def compile_and_store(
        self, instruction: str, step_data: list[dict], app_context: str = ""
    ) -> Optional[str]:
        """Legacy one-shot compile+store (no verification replay).

        Kept so existing callers and tests keep working. New callers
        should use `compile()` + `store_program()` with a verification
        replay in between.
        """
        program = await self.compile(instruction, step_data, app_context)
        if not program:
            return None
        return await self.store_program(program)

    def _attach_raw_commands(
        self, program: RPAProgram, step_data: list[dict]
    ) -> None:
        """Pair each transition with the raw pyautogui command from the trace.

        Strategy:
          - Collect CUA-produced commands in order (keep only executed steps
            with a non-empty command string).
          - If transition_count == cmd_count, zip 1-to-1 (common case).
          - Otherwise match each transition to the next unconsumed command
            whose pyautogui op matches the transition's action type
            (click→click, type→write, keypress→press/keyDown/hotkey).

        Missing matches are OK — transitions without raw_command simply
        fall back to the semantic path at replay time.
        """
        cmds = [
            (i, (s.get("command") or "").strip())
            for i, s in enumerate(step_data)
            if (s.get("command") or "").strip()
        ]
        if not cmds:
            return

        type_to_ops = {
            ActionType.ACTION_CLICK: ("click", "leftClick", "mouseClick"),
            ActionType.ACTION_DOUBLE_CLICK: ("doubleClick",),
            ActionType.ACTION_TYPE: ("write", "typewrite"),
            ActionType.ACTION_KEYPRESS: ("press", "keyDown", "keyUp", "hotkey"),
            ActionType.ACTION_SCROLL: ("scroll", "hscroll", "vscroll"),
            ActionType.ACTION_DRAG: ("drag", "moveTo"),
            ActionType.ACTION_NAVIGATE: ("run", "subprocess"),
        }

        if len(program.transitions) == len(cmds):
            for t, (_, cmd) in zip(program.transitions, cmds):
                t.action.raw_command = cmd
            return

        consumed = [False] * len(cmds)
        for t in program.transitions:
            wanted = type_to_ops.get(t.action.type, ())
            if not wanted:
                continue
            for j, (_, cmd) in enumerate(cmds):
                if consumed[j]:
                    continue
                if any(f"pyautogui.{op}" in cmd for op in wanted):
                    t.action.raw_command = cmd
                    consumed[j] = True
                    break

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
        # Pin task_description to the *original* user instruction so RAG
        # queries match against the real request text (the compiler tends
        # to rewrite it into an abstract summary that doesn't embed close
        # to the user's natural phrasing).
        data["metadata"]["task_description"] = instruction
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

    def _extract_element_info(self, response: str, elements: Any) -> dict:
        """Extract element info for audit from action response and a11y list.

        `elements` may be the raw a11y element list (preferred) or a text
        string (legacy). When a semantic id=N is used we pull name/role
        from the matching element.
        """
        info: dict = {}
        m_id = re.search(r"id\s*=\s*(\d+)", response)
        if m_id and isinstance(elements, list):
            try:
                idx = int(m_id.group(1))
                if 0 <= idx < len(elements):
                    e = elements[idx]
                    info["name"] = e.get("name", "")
                    info["role"] = e.get("role", "")
                    info["x"] = e.get("x", 0) + e.get("width", 0) // 2
                    info["y"] = e.get("y", 0) + e.get("height", 0) // 2
                    return info
            except (ValueError, IndexError):
                pass
        # Fall back to scanning for coordinates
        match = re.search(r"(\d{2,4})\s*,\s*(\d{2,4})", response)
        if match:
            info["x"] = int(match.group(1))
            info["y"] = int(match.group(2))
        return info

    # ─── Semantic action dispatch (Bug 3) ────────────────────────────────

    _SEMANTIC_HEAD_RE = re.compile(
        r"^\s*(click|double_click|right_click|type|key|hotkey|scroll|drag|wait|"
        r"raw_click|raw_double_click|raw_right_click|raw_move)\s*\(",
        re.IGNORECASE,
    )

    async def _dispatch_cua_action(
        self, response: str, elements: list[dict]
    ) -> dict:
        """Parse and execute a CUA action.

        Returns a dict with at least:
          - path: "semantic:<op>" | "pyautogui" | "raw"
          - summary: short human-readable description

        Raises ValueError when a referenced id=N / target is missing.
        """
        # Strip code fences / leading "Action:" prefixes the LLM may add
        clean = response.strip()
        if clean.startswith("```"):
            m = re.search(r"```(?:\w+)?\s*(.*?)```", clean, re.DOTALL)
            if m:
                clean = m.group(1).strip()

        # Scan ALL non-empty lines for the first one that starts with a
        # known action head, so reasoning preambles like "I need to..."
        # don't swallow the actual action. Also drop "Action:" prefix.
        action_line = None
        for raw_line in clean.splitlines():
            line = re.sub(
                r"^(action|next)\s*[:=]\s*", "", raw_line.strip(),
                flags=re.IGNORECASE,
            )
            if not line:
                continue
            if (self._SEMANTIC_HEAD_RE.match(line)
                    or line.startswith("pyautogui.")
                    or line in {"DONE", "FAIL"}
                    or line.startswith("ANSWER:")):
                action_line = line
                break
        if action_line is None:
            # last resort: first non-empty line (legacy behavior)
            for raw_line in clean.splitlines():
                if raw_line.strip():
                    action_line = raw_line.strip()
                    break
            action_line = action_line or clean

        head_match = self._SEMANTIC_HEAD_RE.match(action_line)
        if head_match:
            return await self._dispatch_semantic(action_line, elements)

        # Fallback: legacy pyautogui extraction (scans the whole response)
        cmd = self._extract_pyautogui_cmd(clean)
        if cmd:
            self.env._exec_pyautogui(cmd)
            return {"path": "pyautogui", "summary": cmd[:80]}

        raise ValueError(f"Could not parse action: {response[:120]!r}")

    def _resolve_id(self, s: str, elements: list[dict]) -> tuple[int, int]:
        """Resolve id=N from semantic args to (cx, cy). Raises ValueError."""
        m = re.search(r"id\s*=\s*(\d+)", s)
        if not m:
            raise ValueError(f"no id= in args: {s!r}")
        idx = int(m.group(1))
        if idx < 0 or idx >= len(elements):
            raise ValueError(
                f"id={idx} out of range (a11y list has {len(elements)} elements)"
            )
        e = elements[idx]
        cx = e.get("x", 0) + e.get("width", 0) // 2
        cy = e.get("y", 0) + e.get("height", 0) // 2
        return cx, cy

    def _resolve_xy(self, s: str) -> tuple[int, int]:
        """Resolve raw x,y coordinates from args string.

        Accepts both positional (`100, 200`) and named (`x=100, y=200`)
        forms — LLMs emit both shapes.
        """
        # Named form: x=N, y=M (either order)
        mx = re.search(r"x\s*=\s*(-?\d+)", s)
        my = re.search(r"y\s*=\s*(-?\d+)", s)
        if mx and my:
            return int(mx.group(1)), int(my.group(1))
        # Positional form: first two numbers separated by a comma
        m = re.search(r"(-?\d+)\s*,\s*(-?\d+)", s)
        if not m:
            raise ValueError(f"no x,y in args: {s!r}")
        return int(m.group(1)), int(m.group(2))

    @staticmethod
    def _extract_text_arg(s: str) -> str:
        """Extract text="..." or text='...' from semantic args."""
        m = re.search(r'text\s*=\s*"((?:\\.|[^"\\])*)"', s)
        if m:
            return m.group(1).encode().decode("unicode_escape", errors="replace")
        m = re.search(r"text\s*=\s*'((?:\\.|[^'\\])*)'", s)
        if m:
            return m.group(1).encode().decode("unicode_escape", errors="replace")
        # Fallback: any quoted string
        m = re.search(r'"((?:\\.|[^"\\])*)"', s)
        if m:
            return m.group(1).encode().decode("unicode_escape", errors="replace")
        return ""

    async def _dispatch_semantic(
        self, line: str, elements: list[dict]
    ) -> dict:
        """Execute a semantic action line like `click(id=5)`."""
        m = re.match(r"^\s*(\w+)\s*\((.*)\)\s*$", line, re.DOTALL)
        if not m:
            raise ValueError(f"malformed semantic call: {line!r}")
        op = m.group(1).lower()
        args = m.group(2)

        if op == "click":
            cx, cy = self._resolve_id(args, elements)
            self.env._exec_pyautogui(f"import pyautogui; pyautogui.click({cx}, {cy})")
            return {"path": "semantic:click", "summary": f"click({cx},{cy})"}

        if op == "double_click":
            cx, cy = self._resolve_id(args, elements)
            self.env._exec_pyautogui(
                f"import pyautogui; pyautogui.doubleClick({cx}, {cy})"
            )
            return {"path": "semantic:double_click", "summary": f"dblclick({cx},{cy})"}

        if op == "right_click":
            cx, cy = self._resolve_id(args, elements)
            self.env._exec_pyautogui(
                f"import pyautogui; pyautogui.rightClick({cx}, {cy})"
            )
            return {"path": "semantic:right_click", "summary": f"rclick({cx},{cy})"}

        if op == "type":
            text = self._extract_text_arg(args)
            if "id=" in args:
                cx, cy = self._resolve_id(args, elements)
                self.env._exec_pyautogui(
                    f"import pyautogui; pyautogui.click({cx}, {cy})"
                )
                await asyncio.sleep(0.2)
            # Handle newlines: split on \n, write chunks, press enter between
            self._type_multiline(text)
            return {"path": "semantic:type", "summary": f"type({text[:40]!r})"}

        if op == "key":
            # key(enter) or key(name=enter)
            name = re.sub(r"^\s*name\s*=\s*", "", args.strip())
            name = name.strip().strip('"').strip("'").lower() or "enter"
            self.env._exec_pyautogui(
                f"import pyautogui; pyautogui.press('{name}')"
            )
            return {"path": "semantic:key", "summary": f"key({name})"}

        if op == "hotkey":
            # hotkey(ctrl+s) or hotkey("ctrl+s")
            combo = args.strip().strip('"').strip("'")
            combo = re.sub(r"^\s*keys\s*=\s*", "", combo)
            combo = combo.strip().strip('"').strip("'")
            keys = [k.strip().lower() for k in combo.split("+") if k.strip()]
            if not keys:
                raise ValueError(f"empty hotkey: {args!r}")
            key_args = ", ".join(f"'{k}'" for k in keys)
            self.env._exec_pyautogui(f"import pyautogui; pyautogui.hotkey({key_args})")
            return {"path": "semantic:hotkey", "summary": f"hotkey({'+'.join(keys)})"}

        if op == "scroll":
            direction = "down"
            amount = 3
            md = re.search(r"direction\s*=\s*([a-zA-Z]+)", args)
            if md:
                direction = md.group(1).lower()
            else:
                # positional: scroll(down, 3)
                mp = re.match(r"\s*([a-zA-Z]+)", args)
                if mp:
                    direction = mp.group(1).lower()
            ma = re.search(r"amount\s*=\s*(-?\d+)", args)
            if ma:
                amount = int(ma.group(1))
            else:
                nums = re.findall(r"-?\d+", args)
                if nums:
                    amount = int(nums[0])
            sign = -1 if direction in ("down", "left") else 1
            self.env._exec_pyautogui(
                f"import pyautogui; pyautogui.scroll({sign * abs(amount)})"
            )
            return {"path": "semantic:scroll", "summary": f"scroll({direction},{amount})"}

        if op == "drag":
            mf = re.search(r"from\s*=\s*(\d+)", args)
            mt = re.search(r"to\s*=\s*(\d+)", args)
            if not (mf and mt):
                raise ValueError(f"drag needs from=N and to=N: {args!r}")
            fi, ti = int(mf.group(1)), int(mt.group(1))
            for idx in (fi, ti):
                if idx < 0 or idx >= len(elements):
                    raise ValueError(
                        f"drag: id={idx} out of range (a11y has {len(elements)})"
                    )
            fe, te = elements[fi], elements[ti]
            fx = fe.get("x", 0) + fe.get("width", 0) // 2
            fy = fe.get("y", 0) + fe.get("height", 0) // 2
            tx = te.get("x", 0) + te.get("width", 0) // 2
            ty = te.get("y", 0) + te.get("height", 0) // 2
            dx, dy = tx - fx, ty - fy
            self.env._exec_pyautogui(
                f"import pyautogui; pyautogui.moveTo({fx},{fy}); "
                f"pyautogui.drag({dx},{dy},duration=0.5)"
            )
            return {"path": "semantic:drag", "summary": f"drag({fi}->{ti})"}

        if op == "wait":
            mm = re.search(r"(\d+)", args)
            ms = int(mm.group(1)) if mm else 500
            await asyncio.sleep(ms / 1000.0)
            return {"path": "semantic:wait", "summary": f"wait({ms}ms)"}

        if op == "raw_click":
            x, y = self._resolve_xy(args)
            self.env._exec_pyautogui(f"import pyautogui; pyautogui.click({x}, {y})")
            return {"path": "raw", "summary": f"raw_click({x},{y})"}

        if op == "raw_double_click":
            x, y = self._resolve_xy(args)
            self.env._exec_pyautogui(
                f"import pyautogui; pyautogui.doubleClick({x}, {y})"
            )
            return {"path": "raw", "summary": f"raw_dclick({x},{y})"}

        if op == "raw_right_click":
            x, y = self._resolve_xy(args)
            self.env._exec_pyautogui(
                f"import pyautogui; pyautogui.rightClick({x}, {y})"
            )
            return {"path": "raw", "summary": f"raw_rclick({x},{y})"}

        if op == "raw_move":
            x, y = self._resolve_xy(args)
            self.env._exec_pyautogui(
                f"import pyautogui; pyautogui.moveTo({x}, {y})"
            )
            return {"path": "raw", "summary": f"raw_move({x},{y})"}

        raise ValueError(f"unknown semantic op: {op}")

    def _type_multiline(self, text: str) -> None:
        """Type text, handling newlines by pressing Enter between chunks."""
        if not text:
            return
        chunks = text.split("\n")
        for i, chunk in enumerate(chunks):
            if chunk:
                escaped = chunk.replace("\\", "\\\\").replace("'", "\\'")
                self.env._exec_pyautogui(
                    f"import pyautogui; pyautogui.write('{escaped}')"
                )
            if i < len(chunks) - 1:
                self.env._exec_pyautogui("import pyautogui; pyautogui.press('enter')")

    def _extract_parameters(self, instruction: str, param_names: list[str]) -> dict:
        params = {}
        for name in param_names:
            match = re.search(r'"([^"]+)"', instruction)
            if match:
                params[name] = match.group(1)
        return params
