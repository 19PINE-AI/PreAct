"""Model Generator — compiles interaction traces into JSON state machines.

Uses Gemini 3 Flash to analyze recorded traces and produce formal
state transition graphs that can be directly executed by the RPA Executor.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from preact.generator.prompts import (
    SYSTEM_PROMPT_COMPILE,
    SYSTEM_PROMPT_EXTEND,
    USER_PROMPT_COMPILE,
    USER_PROMPT_EXTEND,
)
from preact.recorder.trace import trace_to_text
from preact.schemas import (
    FallbackEvent,
    InteractionTrace,
    ProgramMetadata,
    RPAProgram,
    State,
    Transition,
)

if TYPE_CHECKING:
    from preact.llm.client import LLMClient

logger = logging.getLogger(__name__)


class ModelGenerator:
    """Compiles interaction traces into executable JSON state machines.

    This is the "compiler" in PreAct's trajectory compilation pipeline.
    A single LLM call analyzes the full trace and produces a state machine.
    """

    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def compile(self, trace: InteractionTrace) -> RPAProgram:
        """Compile an interaction trace into an RPA program.

        Takes a recorded trace from a successful CUA execution and
        produces a formal state machine that can replay the task
        without LLM invocation (except for inspect actions).

        Args:
            trace: A successful interaction trace from the Recorder.

        Returns:
            An RPAProgram (JSON state machine) ready for execution.
        """
        trace_text = trace_to_text(trace)

        user_prompt = USER_PROMPT_COMPILE.format(trace_text=trace_text)

        response = await self.llm.complete(
            messages=[{"role": "user", "content": user_prompt}],
            system=SYSTEM_PROMPT_COMPILE,
        )

        program = self._parse_program(response, trace)
        logger.info(
            "Compiled trace (%d steps) into program (%d states, %d transitions)",
            len(trace.steps),
            len(program.states),
            len(program.transitions),
        )
        return program

    async def extend_graph(
        self,
        program: RPAProgram,
        fallback: FallbackEvent,
    ) -> RPAProgram:
        """Monotonically extend the state graph after a fallback resolution.

        When a state verification fails and the CUA loop resolves it,
        this method adds new states and transitions to the existing graph
        to handle the new scenario in future executions.

        Args:
            program: The existing RPA program.
            fallback: The fallback event with resolution trace.

        Returns:
            The extended program (same object, modified in place).
        """
        resolution_text = ""
        if fallback.llm_resolution_trace:
            resolution_text = trace_to_text(fallback.llm_resolution_trace)

        existing_states = json.dumps(
            [s.model_dump() for s in program.states], indent=2
        )

        user_prompt = USER_PROMPT_EXTEND.format(
            failed_state_id=fallback.failed_state_id,
            failure_reason=fallback.failure_reason,
            resolution_trace=resolution_text,
            existing_states=existing_states,
        )

        response = await self.llm.complete(
            messages=[{"role": "user", "content": user_prompt}],
            system=SYSTEM_PROMPT_EXTEND,
        )

        new_states, new_transitions = self._parse_extension(response)

        # Monotonic extension: only add, never modify
        for state in new_states:
            program.add_state(state)

        for transition in new_transitions:
            program.add_transition(transition)

        logger.info(
            "Extended graph: +%d states, +%d transitions",
            len(new_states),
            len(new_transitions),
        )
        return program

    def _parse_program(
        self, response: str, trace: InteractionTrace
    ) -> RPAProgram:
        """Parse the LLM response into an RPAProgram."""
        # Extract JSON from response (may have markdown fencing)
        json_str = self._extract_json(response)

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM response as JSON: %s", e)
            logger.debug("Response was: %s", response[:2000])
            # Fall back to constructing a minimal program from the trace
            return self._fallback_compile(trace)

        # Ensure metadata
        if "metadata" not in data:
            data["metadata"] = {}

        metadata = data["metadata"]
        metadata.setdefault("task_description", trace.task_description)
        metadata.setdefault("application_context", trace.application_context)
        metadata["source_trace_id"] = trace.trace_id

        try:
            return RPAProgram.model_validate(data)
        except Exception as e:
            logger.error("Failed to validate program: %s", e)
            return self._fallback_compile(trace)

    def _parse_extension(
        self, response: str
    ) -> tuple[list[State], list[Transition]]:
        """Parse the extension response into new states and transitions."""
        json_str = self._extract_json(response)

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse extension response: %s", e)
            return [], []

        new_states = []
        new_transitions = []

        for s in data.get("new_states", []):
            try:
                new_states.append(State.model_validate(s))
            except Exception as e:
                logger.warning("Invalid state in extension: %s", e)

        for t in data.get("new_transitions", []):
            try:
                new_transitions.append(Transition.model_validate(t))
            except Exception as e:
                logger.warning("Invalid transition in extension: %s", e)

        return new_states, new_transitions

    def _extract_json(self, text: str) -> str:
        """Extract JSON from LLM response, handling markdown code blocks."""
        text = text.strip()

        # Try to find JSON in code blocks
        if "```json" in text:
            start = text.index("```json") + 7
            end = text.index("```", start)
            return text[start:end].strip()
        if "```" in text:
            start = text.index("```") + 3
            end = text.index("```", start)
            return text[start:end].strip()

        # Try to find raw JSON
        for start_char, end_char in [("{", "}"), ("[", "]")]:
            if start_char in text:
                start = text.index(start_char)
                # Find matching closing brace
                depth = 0
                for i in range(start, len(text)):
                    if text[i] == start_char:
                        depth += 1
                    elif text[i] == end_char:
                        depth -= 1
                        if depth == 0:
                            return text[start : i + 1]

        return text

    def _fallback_compile(self, trace: InteractionTrace) -> RPAProgram:
        """Create a minimal program directly from trace steps.

        Used when the LLM fails to produce valid JSON. Constructs a
        linear state machine that replays the trace actions.
        """
        logger.warning("Using fallback compilation (linear replay)")

        from preact.schemas import (
            ActionSpec,
            ActionType,
            ProgramMetadata,
            StateVerification,
            VerificationType,
        )

        states = []
        transitions = []

        for i, step in enumerate(trace.steps):
            state_id = f"step_{i}"
            xpath = step.target_xpath or step.action.target

            if xpath:
                verification = StateVerification(
                    type=VerificationType.EXPECT_ELEMENT,
                    xpath=xpath,
                    timeout_ms=5000,
                )
            else:
                verification = StateVerification(
                    type=VerificationType.EXPECT_ELEMENT,
                    xpath="//body",
                    timeout_ms=2000,
                )

            states.append(
                State(
                    id=state_id,
                    verification=verification,
                    description=f"Step {i}: {step.action.type.value}",
                )
            )

            if i > 0:
                transitions.append(
                    Transition(
                        from_state=f"step_{i - 1}",
                        to_state=state_id,
                        action=step.action,
                    )
                )

        # Terminal state
        terminal_id = "completed"
        states.append(
            State(
                id=terminal_id,
                verification=StateVerification(
                    type=VerificationType.TERMINAL_STATE
                ),
                description="Task completed",
            )
        )
        if trace.steps:
            transitions.append(
                Transition(
                    from_state=f"step_{len(trace.steps) - 1}",
                    to_state=terminal_id,
                    action=ActionSpec(type=ActionType.WAIT, ms=100),
                )
            )

        metadata = ProgramMetadata(
            task_description=trace.task_description,
            application_context=trace.application_context,
            source_trace_id=trace.trace_id,
        )

        return RPAProgram(
            metadata=metadata,
            states=states,
            transitions=transitions,
        )
