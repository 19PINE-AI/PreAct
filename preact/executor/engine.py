"""RPA Executor — state machine traversal engine.

This is the core of PreAct: it directly executes the JSON state machine
by traversing the state transition graph. Each state is verified via
XPath polling before the associated action is executed.

When verification fails, the executor halts and returns a FallbackEvent
so the Agent Core can invoke the CUA loop for recovery.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from preact.executor.actions import execute_action
from preact.executor.context import ExecutionContext
from preact.schemas import (
    ActionType,
    ExecutionResult,
    FallbackEvent,
    HumanIntervention,
    RPAProgram,
    State,
    Transition,
    VerificationType,
)

if TYPE_CHECKING:
    from preact.environment.base import ComputerEnvironment
    from preact.llm.client import LLMClient

logger = logging.getLogger(__name__)


class RPAExecutor:
    """Executes an RPA program by traversing its state transition graph.

    The state machine IS the executable — no code generation needed.
    """

    def __init__(
        self,
        env: ComputerEnvironment,
        llm: LLMClient | None = None,
        max_consecutive_failures: int = 3,
    ):
        self.env = env
        self.llm = llm
        self.max_consecutive_failures = max_consecutive_failures

    async def execute(
        self,
        program: RPAProgram,
        parameters: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """Execute an RPA program by traversing its state machine.

        Args:
            program: The RPA program (JSON state machine) to execute.
            parameters: User-provided parameter values.

        Returns:
            ExecutionResult with success/failure, states visited, fallback events,
            timing, and token usage.
        """
        ctx = ExecutionContext(parameters=parameters)
        start_time = time.monotonic()

        result = ExecutionResult(
            success=False,
            task_description=program.metadata.task_description,
        )

        current_state = program.get_initial_state()
        if not current_state:
            result.error = "Program has no states"
            return result

        consecutive_failures = 0

        while current_state:
            result.states_visited.append(current_state.id)

            # Check for human intervention before this state
            intervention = self._get_intervention(program, current_state.id)
            if intervention:
                await self._handle_intervention(intervention, ctx)

            # ─── Verify current state ─────────────────────────────────
            verified = await self._verify_state(current_state, ctx)

            if not verified:
                logger.warning(
                    "State verification failed: %s", current_state.id
                )
                consecutive_failures += 1

                # Capture fallback event
                screenshot = await self.env.screenshot()
                fallback = FallbackEvent(
                    failed_state_id=current_state.id,
                    failure_reason=f"State verification timeout for {current_state.id}",
                    screenshot_data=screenshot,
                )
                result.fallback_events.append(fallback)

                if consecutive_failures >= self.max_consecutive_failures:
                    result.error = (
                        f"state_verification_failed:{current_state.id}"
                    )
                    break

                # Signal to Agent Core for CUA fallback
                result.error = f"state_verification_failed:{current_state.id}"
                break

            consecutive_failures = 0

            # ─── Check for terminal state ─────────────────────────────
            if current_state.verification.type == VerificationType.TERMINAL_STATE:
                result.success = True
                logger.info("Reached terminal state: %s", current_state.id)
                break

            # ─── Get transitions from current state ───────────────────
            transitions = program.get_transitions_from(current_state.id)

            if not transitions:
                result.error = f"No transitions from state: {current_state.id}"
                break

            # ─── Select and execute transition ────────────────────────
            transition = await self._select_transition(transitions, ctx)

            if not transition:
                result.error = (
                    f"No valid transition from state: {current_state.id}"
                )
                break

            logger.debug(
                "Transition: %s -> %s (action: %s)",
                transition.from_state,
                transition.to_state,
                transition.action.type,
            )

            action_start = time.monotonic()
            try:
                await execute_action(transition.action, self.env, ctx, self.llm)
                result.actions_executed += 1
                result.actions_via_rpa += 1
                ctx.log_step(current_state.id, transition.action.type.value, True)
            except Exception as e:
                logger.error(
                    "Action execution failed at %s: %s",
                    current_state.id,
                    e,
                )
                ctx.log_step(current_state.id, transition.action.type.value, False)

                screenshot = await self.env.screenshot()
                fallback = FallbackEvent(
                    failed_state_id=current_state.id,
                    failure_reason=str(e),
                    screenshot_data=screenshot,
                )
                result.fallback_events.append(fallback)
                result.error = f"action_failed:{current_state.id}:{e}"
                break

            action_time = (time.monotonic() - action_start) * 1000
            result.rpa_time_ms += action_time

            # ─── Move to next state ───────────────────────────────────
            next_state = program.get_state(transition.to_state)
            if not next_state:
                result.error = f"Target state not found: {transition.to_state}"
                break

            current_state = next_state

        # Finalize
        result.total_time_ms = (time.monotonic() - start_time) * 1000

        if self.llm:
            result.total_input_tokens = self.llm.total_input_tokens
            result.total_output_tokens = self.llm.total_output_tokens

        logger.info(
            "Execution %s: %d states, %d actions, %.1fms",
            "succeeded" if result.success else "failed",
            len(result.states_visited),
            result.actions_executed,
            result.total_time_ms,
        )
        return result

    async def _verify_state(
        self, state: State, ctx: ExecutionContext
    ) -> bool:
        """Verify that the current UI matches the expected state."""
        v = state.verification

        if v.type == VerificationType.TERMINAL_STATE:
            return True

        if v.type == VerificationType.EXPECT_ELEMENT:
            if not v.xpath:
                logger.warning("expect_element state has no xpath: %s", state.id)
                return True
            resolved_xpath = ctx.resolve_template(v.xpath)
            return await self.env.element_exists(
                resolved_xpath, timeout_ms=v.timeout_ms
            )

        if v.type == VerificationType.DATA_AVAILABLE:
            if not v.data_key:
                return True
            return ctx.has_data(v.data_key)

        logger.warning("Unknown verification type: %s", v.type)
        return True

    async def _select_transition(
        self,
        transitions: list[Transition],
        ctx: ExecutionContext,
    ) -> Transition | None:
        """Select the appropriate transition, evaluating guards if needed.

        If there's only one transition, use it directly.
        If there are multiple, evaluate each transition's condition/guard
        and take the first one that evaluates to True.
        """
        if len(transitions) == 1:
            t = transitions[0]
            # Single transition may still have a condition
            if t.action.type == ActionType.CONDITIONAL and t.action.condition:
                if ctx.evaluate_expression(t.action.condition):
                    return t
                return None
            return t

        # Multiple transitions: evaluate conditions
        for t in transitions:
            if t.action.type == ActionType.CONDITIONAL and t.action.condition:
                if ctx.evaluate_expression(t.action.condition):
                    return t
            elif t.condition:
                if ctx.evaluate_expression(t.condition):
                    return t
            else:
                # Unconditional transition — use as default
                return t

        return None

    def _get_intervention(
        self, program: RPAProgram, state_id: str
    ) -> HumanIntervention | None:
        """Check if there's a human intervention point before this state."""
        for hi in program.human_interventions:
            if hi.before_state == state_id:
                return hi
        return None

    async def _handle_intervention(
        self,
        intervention: HumanIntervention,
        ctx: ExecutionContext,
    ) -> None:
        """Handle a human intervention point.

        In automated mode (evaluation), auto-continues based on timeout action.
        """
        prompt = ctx.resolve_template(intervention.prompt)
        logger.info("Human intervention: %s", prompt)

        if intervention.on_timeout == "abort":
            raise RuntimeError(f"Human intervention required: {prompt}")
        # Auto-continue for automated execution
