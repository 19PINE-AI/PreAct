"""Pydantic models for all PreAct data structures.

These schemas define the JSON state machine format, interaction traces,
execution results, and all intermediate data structures.
"""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ─── Enums ────────────────────────────────────────────────────────────────────


class VerificationType(str, Enum):
    EXPECT_ELEMENT = "expect_element"
    DATA_AVAILABLE = "data_available"
    TERMINAL_STATE = "terminal_state"


class ActionType(str, Enum):
    ACTION_CLICK = "action_click"
    ACTION_DOUBLE_CLICK = "action_double_click"
    ACTION_MOVE = "action_move"
    ACTION_TYPE = "action_type"
    ACTION_KEYPRESS = "action_keypress"
    ACTION_SCROLL = "action_scroll"
    ACTION_DRAG = "action_drag"
    ACTION_NAVIGATE = "action_navigate"
    WAIT = "wait"
    INSPECT_TEXT = "inspect_text"
    INSPECT_SCREENSHOT = "inspect_screenshot"
    EVALUATE_CONDITION = "evaluate_condition"
    CONDITIONAL = "conditional"
    COMPUTE = "compute"
    REQUEST_HUMAN_INTERVENTION = "request_human_intervention"


class InterventionType(str, Enum):
    APPROVAL = "approval"
    INPUT = "input"
    SELECTION = "selection"
    VERIFICATION = "verification"


class TimeoutAction(str, Enum):
    CONTINUE = "continue"
    RETRY = "retry"
    ABORT = "abort"


# ─── State Machine Schema ────────────────────────────────────────────────────


class StateVerification(BaseModel):
    """Verification criteria for a state in the state machine."""

    type: VerificationType
    xpath: str | None = None
    timeout_ms: int = 5000
    data_key: str | None = None


class State(BaseModel):
    """A node in the state transition graph."""

    id: str
    verification: StateVerification
    description: str = ""


class ActionSpec(BaseModel):
    """Specification for an action that triggers a state transition."""

    type: ActionType
    target: str | None = None  # XPath target
    text: str | None = None  # Literal text for type actions
    parameter_name: str | None = None  # Parameter reference for type actions
    key: str | None = None  # For keypress actions
    ms: int | None = None  # For wait actions
    direction: str | None = None  # For scroll actions
    amount: int | None = None  # For scroll actions
    prompt: str | None = None  # For inspect actions
    store_result_as: str | None = None  # Variable name for inspect results
    return_to_api: bool = False  # For inspect_screenshot
    description: str | None = None  # Human-readable description
    expression: str | None = None  # For evaluate_condition / conditional
    condition: str | None = None  # For conditional transitions
    then: ActionSpec | None = None  # For conditional with side effect
    true_steps: list[ActionSpec] | None = None  # For condition branching
    false_steps: list[ActionSpec] | None = None  # For condition branching
    from_target: str | None = None  # For drag
    to_target: str | None = None  # For drag
    # Raw command fallback — verbatim pyautogui string captured during CUA
    # recording. Replayed when the semantic action (click/type/scroll)
    # fails or drops low-level detail (e.g. keystroke combos the compiler
    # collapses into a single semantic step). Platform-specific: unused on
    # Android since JSONAction is already low-level.
    raw_command: str | None = None
    # Human intervention fields
    intervention_type: InterventionType | None = None
    timeout_sec: int | None = None
    ui_elements: list[str] | None = None
    on_timeout: TimeoutAction | None = None
    xpath_highlight: str | None = None


class Transition(BaseModel):
    """An edge in the state transition graph."""

    from_state: str = Field(alias="from")
    to_state: str = Field(alias="to")
    action: ActionSpec
    condition: str | None = None  # Guard condition for branching

    model_config = {"populate_by_name": True}


class ProgramMetadata(BaseModel):
    """Metadata for an RPA program, used for RAG indexing."""

    program_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_description: str
    application_context: str = ""
    initial_states: list[str] = Field(default_factory=list)
    parameters: list[str] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    version: int = 1
    source_trace_id: str | None = None


class HumanIntervention(BaseModel):
    """A human intervention point embedded in the state machine."""

    before_state: str
    prompt: str
    intervention_type: InterventionType = InterventionType.APPROVAL
    timeout_sec: int = 60
    ui_elements: list[str] = Field(default_factory=list)
    on_timeout: TimeoutAction = TimeoutAction.ABORT


class RPAProgram(BaseModel):
    """Complete RPA program — a JSON state machine.

    This is both the representation and the directly executable artifact.
    The RPA Executor traverses this graph at runtime.
    """

    metadata: ProgramMetadata
    states: list[State]
    transitions: list[Transition]
    human_interventions: list[HumanIntervention] = Field(default_factory=list)

    def get_state(self, state_id: str) -> State | None:
        for s in self.states:
            if s.id == state_id:
                return s
        return None

    def get_transitions_from(self, state_id: str) -> list[Transition]:
        return [t for t in self.transitions if t.from_state == state_id]

    def get_initial_state(self) -> State | None:
        if self.states:
            return self.states[0]
        return None

    def get_terminal_states(self) -> list[State]:
        return [
            s
            for s in self.states
            if s.verification.type == VerificationType.TERMINAL_STATE
        ]

    def add_state(self, state: State) -> None:
        if not self.get_state(state.id):
            self.states.append(state)

    def add_transition(self, transition: Transition) -> None:
        self.transitions.append(transition)
        self.metadata.updated_at = time.time()
        self.metadata.version += 1


# ─── Interaction Trace Schema ────────────────────────────────────────────────


class TraceStep(BaseModel):
    """A single step in a recorded interaction trace."""

    timestamp: float = Field(default_factory=time.time)
    screenshot_path: str | None = None
    screenshot_data: bytes | None = None
    action: ActionSpec
    target_xpath: str | None = None  # Resolved XPath for the action target
    element_info: dict[str, Any] = Field(default_factory=dict)
    llm_reasoning: str | None = None
    page_url: str | None = None
    dom_snapshot: str | None = None
    success: bool = True
    error: str | None = None

    model_config = {"arbitrary_types_allowed": True}


class InteractionTrace(BaseModel):
    """Complete trace of a CUA interaction session."""

    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_description: str
    application_context: str = ""
    steps: list[TraceStep] = Field(default_factory=list)
    start_time: float = Field(default_factory=time.time)
    end_time: float | None = None
    success: bool = False
    parameters_used: dict[str, str] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}


# ─── Execution Result Schema ─────────────────────────────────────────────────


class FallbackEvent(BaseModel):
    """Records a single fallback from RPA execution to CUA loop."""

    failed_state_id: str
    failure_reason: str
    screenshot_data: bytes | None = None
    llm_resolution_trace: InteractionTrace | None = None
    new_states: list[State] = Field(default_factory=list)
    new_transitions: list[Transition] = Field(default_factory=list)
    resolution_time_ms: float = 0

    model_config = {"arbitrary_types_allowed": True}


class ExecutionResult(BaseModel):
    """Result of executing an RPA program or CUA task."""

    success: bool
    task_description: str = ""
    states_visited: list[str] = Field(default_factory=list)
    fallback_events: list[FallbackEvent] = Field(default_factory=list)
    total_time_ms: float = 0
    rpa_time_ms: float = 0  # Time spent in RPA execution
    cua_time_ms: float = 0  # Time spent in CUA fallback
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    actions_executed: int = 0
    actions_via_rpa: int = 0
    actions_via_cua: int = 0
    data: dict[str, Any] = Field(default_factory=dict)  # Data from inspect_text/inspect_screenshot
    error: str | None = None

    model_config = {"arbitrary_types_allowed": True}

    @property
    def graph_coverage(self) -> float:
        """Fraction of actions executed via RPA vs total."""
        if self.actions_executed == 0:
            return 0.0
        return self.actions_via_rpa / self.actions_executed

    @property
    def cost_estimate(self) -> float:
        """Estimated cost in USD (Gemini 3 Flash pricing)."""
        input_cost = self.total_input_tokens * 0.10 / 1_000_000
        output_cost = self.total_output_tokens * 0.40 / 1_000_000
        return input_cost + output_cost
