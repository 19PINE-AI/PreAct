"""Agent Core — central orchestrator for PreAct.

Receives user tasks, queries the RAG DB for matching programs,
decides between model-based execution and exploratory learning,
manages fallback transitions, and triggers graph refinement.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from preact.config import PreActConfig
from preact.core.refinement import refine_graph
from preact.cua.loop import CUALoop, CUAResult
from preact.executor.engine import RPAExecutor
from preact.generator.compiler import ModelGenerator
from preact.llm.client import LLMClient
from preact.rag.store import ProgramStore
from preact.recorder.recorder import InteractionRecorder
from preact.recorder.trace import save_trace
from preact.schemas import ExecutionResult, FallbackEvent, RPAProgram

logger = logging.getLogger(__name__)


@dataclass
class TaskResult:
    """Complete result from a PreAct task execution."""

    success: bool
    mode: str  # "rpa", "cua", "hybrid" (rpa with fallbacks)
    execution_result: ExecutionResult | None = None
    cua_result: CUAResult | None = None
    program_id: str | None = None
    program_was_new: bool = False
    program_was_extended: bool = False
    total_time_ms: float = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    error: str | None = None


class PreActAgent:
    """Central orchestrator implementing the PreAct execution flow.

    Flow:
    1. Receive task → query RAG for matching program
    2. If found → execute via RPA Executor
       - On state failure → fallback to CUA, then extend graph
    3. If not found → run full CUA loop, compile trace to program
    4. Store/update program in RAG

    This implements the progressive learning paradigm:
    - First encounter: full CUA exploration + compilation
    - Subsequent encounters: fast RPA execution with targeted fallback
    - UI changes: single-cycle adaptation via graph extension
    """

    def __init__(
        self,
        env: Any,  # ComputerEnvironment
        llm: LLMClient,
        config: PreActConfig | None = None,
    ):
        self.env = env
        self.llm = llm
        self.config = config or PreActConfig()

        # Initialize components
        self.recorder = InteractionRecorder(env, self.config.recorder)
        self.generator = ModelGenerator(llm)
        self.store = ProgramStore(llm, self.config.rag)
        self.executor = RPAExecutor(env, llm)
        self.cua = CUALoop(env, llm, self.recorder, self.config.cua)

    async def execute_task(
        self,
        task: str,
        parameters: dict[str, Any] | None = None,
        force_cua: bool = False,
        force_rpa: bool = False,
    ) -> TaskResult:
        """Main entry point: execute a task using the PreAct pipeline.

        Args:
            task: High-level task description.
            parameters: Named parameters for the task.
            force_cua: Force CUA mode (skip RAG lookup).
            force_rpa: Force RPA mode (fail if no program found).

        Returns:
            TaskResult with full execution details.
        """
        start_time = time.monotonic()
        self.llm.reset_usage()

        logger.info("Task: %s", task)

        # ─── Step 1: Query RAG for matching program ───────────────
        program = None
        if not force_cua:
            app_context = ""
            try:
                app_context = await self.env.get_page_url()
            except Exception:
                pass

            programs = await self.store.query(task, context=app_context)
            if programs:
                program = programs[0]
                logger.info(
                    "Found matching program: %s (v%d, %d states)",
                    program.metadata.program_id,
                    program.metadata.version,
                    len(program.states),
                )

        if force_rpa and not program:
            return TaskResult(
                success=False,
                mode="rpa",
                error="No matching program found (force_rpa=True)",
                total_time_ms=(time.monotonic() - start_time) * 1000,
            )

        # ─── Step 2: Execute via RPA or CUA ───────────────────────
        if program and not force_cua:
            # Extract parameters from task if not explicitly provided
            resolved_params = parameters or {}
            if not resolved_params and program.metadata.parameters:
                resolved_params = await self._extract_parameters(
                    task, program.metadata.parameters
                )
            result = await self._execute_with_rpa(
                task, program, resolved_params
            )
        else:
            result = await self._execute_with_cua(task)

        result.total_time_ms = (time.monotonic() - start_time) * 1000
        result.total_input_tokens = self.llm.total_input_tokens
        result.total_output_tokens = self.llm.total_output_tokens

        logger.info(
            "Task %s: mode=%s, time=%.1fms, tokens=%d",
            "succeeded" if result.success else "failed",
            result.mode,
            result.total_time_ms,
            self.llm.total_tokens,
        )

        return result

    async def _execute_with_rpa(
        self,
        task: str,
        program: RPAProgram,
        parameters: dict[str, Any],
    ) -> TaskResult:
        """Execute a task using a compiled RPA program.

        If state verification fails, falls back to CUA and extends the graph.
        """
        result = TaskResult(
            success=False,
            mode="rpa",
            program_id=program.metadata.program_id,
        )

        # Execute the state machine
        exec_result = await self.executor.execute(program, parameters)

        if exec_result.success:
            result.success = True
            result.execution_result = exec_result

            # For information retrieval tasks, extract the answer from screen
            if self._is_info_retrieval_task(task):
                # Wait for page to fully render after RPA replay
                # RPA executes actions back-to-back with no natural delay,
                # so data may not be visible yet when terminal state is reached
                try:
                    await self.env.page.wait_for_load_state(
                        "networkidle", timeout=5000
                    )
                except Exception:
                    pass
                # Additional settle time for dynamic content (Magento tables, etc.)
                import asyncio
                await asyncio.sleep(2)

                answer = await self._extract_answer_from_screen(task)
                if answer:
                    result.cua_result = CUAResult(
                        success=True,
                        actions_taken=0,
                        total_time_ms=0,
                        answer=answer,
                    )

            return result

        # ─── Fallback to CUA ──────────────────────────────────────
        if exec_result.error and (
            exec_result.error.startswith("state_verification_failed:")
            or exec_result.error.startswith("action_failed:")
        ):
            logger.info("RPA failed, falling back to CUA")
            result.mode = "hybrid"

            failed_state = exec_result.error.split(":")[-1]

            # Run CUA from current context
            cua_result = await self.cua.run_from_context(
                task=task,
                failed_context=f"verify state '{failed_state}' in the application",
                record=True,
            )
            result.cua_result = cua_result

            if cua_result.success:
                result.success = True

                # ─── Extend graph with new knowledge ──────────────
                if exec_result.fallback_events:
                    fallback = exec_result.fallback_events[-1]
                    fallback.llm_resolution_trace = cua_result.trace

                    try:
                        program = await refine_graph(
                            program, fallback, self.generator
                        )
                        await self.store.update(
                            program.metadata.program_id, program
                        )
                        result.program_was_extended = True
                        logger.info("Graph extended and saved")
                    except Exception as e:
                        logger.warning("Graph extension failed: %s", e)

            result.execution_result = exec_result
            return result

        # Non-recoverable failure
        result.execution_result = exec_result
        result.error = exec_result.error
        return result

    async def _execute_with_cua(self, task: str) -> TaskResult:
        """Execute a task using the full CUA loop (exploration mode).

        On success, compiles the trace into a new RPA program and stores it.
        """
        result = TaskResult(
            success=False,
            mode="cua",
        )

        cua_result = await self.cua.run(task, record=True)
        result.cua_result = cua_result

        if cua_result.success:
            result.success = True

            # ─── Compile trace into program ───────────────────────
            trace = cua_result.trace
            if trace and len(trace.steps) > 0:
                program = None
                try:
                    logger.info(
                        "Compiling CUA trace into state machine (%d steps)...",
                        len(trace.steps),
                    )
                    program = await self.generator.compile(trace)
                except Exception as e:
                    logger.warning(
                        "LLM compilation failed: %s — trying fallback", e
                    )

                # If LLM compilation failed, use fallback compiler directly
                if program is None:
                    try:
                        program = self.generator._fallback_compile(trace)
                        logger.info(
                            "Fallback compiled: %d states", len(program.states)
                        )
                    except Exception as e2:
                        logger.error(
                            "Fallback compilation also failed: %s", e2
                        )

                if program is not None:
                    try:
                        program_id = await self.store.store(program)
                        result.program_id = program_id
                        result.program_was_new = True
                        logger.info(
                            "New program stored: %s (%d states)",
                            program_id,
                            len(program.states),
                        )
                    except Exception as e:
                        logger.error("Failed to store program: %s", e)
            elif trace:
                logger.warning(
                    "CUA succeeded but trace has no steps — cannot compile"
                )

        result.error = cua_result.error
        return result

    async def _extract_parameters(
        self,
        task: str,
        parameter_names: list[str],
    ) -> dict[str, Any]:
        """Extract parameter values from a task description.

        Uses fast regex extraction first. Falls back to LLM only when
        regex can't find all parameters.
        """
        # Fast path: regex extraction from quoted strings and common patterns
        params = self._extract_parameters_fast(task, parameter_names)
        if params and all(params.get(p) for p in parameter_names):
            logger.info("Fast-extracted parameters: %s", params)
            return params

        # Slow path: LLM extraction
        import json as _json

        param_list = ", ".join(parameter_names)
        prompt = (
            f"Extract the following parameters from this task description.\n\n"
            f"Task: {task}\n\n"
            f"Parameters to extract: {param_list}\n\n"
            f"Return a JSON object with the parameter names as keys and their values "
            f"extracted from the task. If a parameter value cannot be found, use an "
            f"empty string. Return ONLY the JSON object."
        )

        try:
            response = await self.llm.complete(
                messages=[{"role": "user", "content": prompt}]
            )
            text = response.strip()
            if "```json" in text:
                start = text.index("```json") + 7
                closing = text.find("```", start)
                if closing != -1:
                    text = text[start:closing].strip()
            elif "```" in text:
                start = text.index("```") + 3
                closing = text.find("```", start)
                if closing != -1:
                    text = text[start:closing].strip()
            params = _json.loads(text)
            logger.info("LLM-extracted parameters: %s", params)
            return params
        except Exception as e:
            logger.warning("Parameter extraction failed: %s", e)
            return {}

    def _extract_parameters_fast(
        self,
        task: str,
        parameter_names: list[str],
    ) -> dict[str, Any]:
        """Fast regex-based parameter extraction from task descriptions.

        Looks for quoted strings and common patterns like 'name X', 'email X',
        'username X', 'password X' in the task text.
        """
        import re

        params: dict[str, Any] = {}

        # Extract all quoted strings from the task
        quoted = re.findall(r"'([^']+)'", task) + re.findall(r'"([^"]+)"', task)

        # Common parameter-to-pattern mapping
        # Patterns use non-greedy quotes to avoid capturing trailing quotes
        pattern_map = {
            "username": r"username\s+'([^']+)'|username\s+\"([^\"]+)\"|(?:as|username)\s+(\w+)/",
            "password": r"password\s+'([^']+)'|password\s+\"([^\"]+)\"|/(\S+?)(?:\s|,|$)",
            "email": r"email\s+'([^']+)'|email\s+\"([^\"]+)\"",
            "name": r"name\s+'([^']+)'|name\s+\"([^\"]+)\"",
            "customer_name": r"(?:customer\s+)?name\s+'([^']+)'|(?:customer\s+)?name\s+\"([^\"]+)\"",
            "full_name": r"name\s+'([^']+)'|name\s+\"([^\"]+)\"",
            "query": r"(?:search|query)\s+(?:for\s+)?'([^']+)'|(?:search|query)\s+(?:for\s+)?\"([^\"]+)\"",
            "search_query": r"(?:search|query)\s+(?:for\s+)?'([^']+)'|(?:search|query)\s+(?:for\s+)?\"([^\"]+)\"",
            "address": r"address\s+'([^']+)'|address\s+\"([^\"]+)\"",
            "card_number": r"card\s+'?(\d{13,19})'?|card\s+\"?(\d{13,19})\"?",
            "quantity": r"quantity\s+(\d+)",
        }

        for param_name in parameter_names:
            # Try specific pattern first
            if param_name in pattern_map:
                match = re.search(pattern_map[param_name], task, re.IGNORECASE)
                if match:
                    # Get first non-None group
                    val = next((g for g in match.groups() if g is not None), None)
                    if val:
                        params[param_name] = val
                        continue

            # Try matching against quoted strings by position/context
            param_readable = param_name.replace("_", " ")
            # Look for "param_name 'value'" or "param_name: value"
            pattern = rf"{re.escape(param_readable)}\s*[:=]?\s*['\"]([^'\"]+)['\"]"
            match = re.search(pattern, task, re.IGNORECASE)
            if match:
                params[param_name] = match.group(1)
                continue

            # Fall back to using quoted strings in order
            if quoted:
                params[param_name] = quoted.pop(0)

        return params

    async def execute_batch(
        self,
        tasks: list[dict[str, Any]],
    ) -> list[TaskResult]:
        """Execute multiple tasks sequentially.

        Useful for the Learn-Once, Execute-Many pattern.

        Args:
            tasks: List of {"task": str, "parameters": dict} dicts.

        Returns:
            List of TaskResults.
        """
        results = []
        for i, task_spec in enumerate(tasks):
            task = task_spec["task"]
            params = task_spec.get("parameters", {})

            logger.info("Batch task %d/%d: %s", i + 1, len(tasks), task)
            result = await self.execute_task(task, parameters=params)
            results.append(result)

        return results

    @staticmethod
    def _is_info_retrieval_task(task: str) -> bool:
        """Check if task requires extracting information from the screen."""
        lower = task.lower()
        patterns = [
            "what is", "what are", "how many", "how much",
            "tell me", "show me", "list the", "list all",
            "give me", "find the", "which", "who",
            "present", "count", "total", "number of",
        ]
        return any(p in lower for p in patterns)

    async def _extract_answer_from_screen(self, task: str) -> str:
        """Take a screenshot and extract the answer using vision LLM."""
        try:
            screenshot = await self.env.screenshot()
            prompt = (
                f"Task: {task}\n\n"
                f"Look at this screenshot carefully and extract the exact answer to the task.\n\n"
                f"Instructions:\n"
                f"- Return ONLY the answer value — no explanation, no full sentences.\n"
                f"- Read data directly from tables, forms, or page content visible in the screenshot.\n"
                f"- For tables: identify the correct row and column, then read the cell value.\n"
                f"- For names: return the full name as shown (e.g., 'John Doe').\n"
                f"- For amounts: include the currency symbol (e.g., '$36.39').\n"
                f"- For dates: return in the format shown on screen.\n"
                f"- For multiple values: separate with ', ' (e.g., 'John Doe, john@example.com').\n"
                f"- If the data is not visible in the screenshot, say 'N/A'.\n"
                f"- Do NOT guess or make up values. Only return what you can clearly read.\n"
            )
            response = await self.llm.complete_with_vision(
                text_prompt=prompt,
                images=[screenshot],
            )
            answer = response.strip().strip('"').strip("'")
            # Filter out non-answers
            if answer.lower() in (
                "n/a",
                "information not available in the image",
                "not available",
                "cannot determine",
                "unable to determine",
            ):
                logger.warning("Answer extraction returned non-answer: %s", answer)
                return ""
            logger.info("Extracted answer from screen: %s", answer[:100])
            return answer
        except Exception as e:
            logger.warning("Failed to extract answer from screen: %s", e)
            return ""
