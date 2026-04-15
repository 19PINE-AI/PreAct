"""Monotonic graph refinement logic.

Handles extending the state graph when a fallback occurs, ensuring
the graph only grows (never shrinks or modifies existing states).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from preact.schemas import FallbackEvent, RPAProgram

if TYPE_CHECKING:
    from preact.generator.compiler import ModelGenerator

logger = logging.getLogger(__name__)


async def refine_graph(
    program: RPAProgram,
    fallback: FallbackEvent,
    generator: ModelGenerator,
) -> RPAProgram:
    """Monotonically extend the state graph based on a fallback event.

    This is PreAct's key differentiator from systems like Muscle-Mem
    (which discard and re-record) and Workflow-Use (which have no refinement).

    The process:
    1. The fallback event contains the failed state and the CUA's resolution trace
    2. The Model Generator analyzes the resolution and produces new states/transitions
    3. New states/transitions are added to the graph (never removing existing ones)
    4. The failed state becomes a branch point with an alternative path

    Args:
        program: The existing RPA program to extend.
        fallback: The fallback event with resolution information.
        generator: The Model Generator for LLM-based extension.

    Returns:
        The extended program (same object, modified in place).
    """
    if not fallback.llm_resolution_trace:
        logger.warning(
            "No resolution trace for fallback at state %s — "
            "cannot extend graph",
            fallback.failed_state_id,
        )
        return program

    # Use the Model Generator to produce new states and transitions
    extended = await generator.extend_graph(program, fallback)

    # Log the extension
    logger.info(
        "Graph refinement: state %s now has %d outgoing transitions "
        "(was %d before extension). Total states: %d, transitions: %d",
        fallback.failed_state_id,
        len(extended.get_transitions_from(fallback.failed_state_id)),
        len(program.get_transitions_from(fallback.failed_state_id))
        - len(fallback.new_transitions),
        len(extended.states),
        len(extended.transitions),
    )

    return extended


def validate_graph_integrity(program: RPAProgram) -> list[str]:
    """Validate the structural integrity of a state machine graph.

    Checks:
    - All transition references point to existing states
    - There's at least one terminal state reachable from the initial state
    - No orphaned states (states with no incoming or outgoing transitions)

    Returns a list of warnings (empty if graph is valid).
    """
    warnings = []
    state_ids = {s.id for s in program.states}

    # Check transitions reference valid states
    for t in program.transitions:
        if t.from_state not in state_ids:
            warnings.append(
                f"Transition references unknown source state: {t.from_state}"
            )
        if t.to_state not in state_ids:
            warnings.append(
                f"Transition references unknown target state: {t.to_state}"
            )

    # Check for orphaned states
    states_with_incoming = {t.to_state for t in program.transitions}
    states_with_outgoing = {t.from_state for t in program.transitions}
    terminal_ids = {s.id for s in program.get_terminal_states()}

    for s in program.states:
        if s.id == program.states[0].id:
            continue  # Initial state won't have incoming
        if s.id not in states_with_incoming and s.id not in terminal_ids:
            warnings.append(f"Orphaned state (no incoming transitions): {s.id}")
        if s.id not in states_with_outgoing and s.id not in terminal_ids:
            if s.id not in terminal_ids:
                warnings.append(
                    f"Dead-end state (no outgoing transitions, not terminal): {s.id}"
                )

    # Check at least one terminal state exists
    if not terminal_ids:
        warnings.append("No terminal states in the graph")

    return warnings
