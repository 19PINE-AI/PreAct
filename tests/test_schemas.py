"""Tests for PreAct schema validation and serialization."""

import json

from preact.schemas import (
    ActionSpec,
    ActionType,
    ExecutionResult,
    HumanIntervention,
    InteractionTrace,
    ProgramMetadata,
    RPAProgram,
    State,
    StateVerification,
    TraceStep,
    Transition,
    VerificationType,
)


def test_state_verification_expect_element():
    sv = StateVerification(
        type=VerificationType.EXPECT_ELEMENT,
        xpath="//div[@id='test']",
        timeout_ms=3000,
    )
    assert sv.type == VerificationType.EXPECT_ELEMENT
    assert sv.xpath == "//div[@id='test']"
    assert sv.timeout_ms == 3000


def test_state_verification_terminal():
    sv = StateVerification(type=VerificationType.TERMINAL_STATE)
    assert sv.type == VerificationType.TERMINAL_STATE


def test_action_spec_click():
    action = ActionSpec(
        type=ActionType.ACTION_CLICK,
        target="//button[@id='submit']",
    )
    assert action.type == ActionType.ACTION_CLICK
    assert action.target == "//button[@id='submit']"


def test_action_spec_type_with_parameter():
    action = ActionSpec(
        type=ActionType.ACTION_TYPE,
        target="//input[@name='email']",
        parameter_name="recipient_email",
    )
    assert action.parameter_name == "recipient_email"


def test_transition_model():
    t = Transition(
        from_state="state_a",
        to_state="state_b",
        action=ActionSpec(type=ActionType.ACTION_CLICK, target="//button"),
    )
    # Using alias
    assert t.from_state == "state_a"
    assert t.to_state == "state_b"


def test_rpa_program_creation():
    program = RPAProgram(
        metadata=ProgramMetadata(
            task_description="Test task",
            application_context="test.com",
            parameters=["email"],
        ),
        states=[
            State(
                id="initial",
                verification=StateVerification(
                    type=VerificationType.EXPECT_ELEMENT,
                    xpath="//body",
                    timeout_ms=5000,
                ),
            ),
            State(
                id="completed",
                verification=StateVerification(
                    type=VerificationType.TERMINAL_STATE,
                ),
            ),
        ],
        transitions=[
            Transition(
                from_state="initial",
                to_state="completed",
                action=ActionSpec(type=ActionType.WAIT, ms=100),
            ),
        ],
    )
    assert len(program.states) == 2
    assert len(program.transitions) == 1
    assert program.get_state("initial") is not None
    assert program.get_state("nonexistent") is None
    assert len(program.get_transitions_from("initial")) == 1
    assert len(program.get_terminal_states()) == 1


def test_rpa_program_serialization():
    program = RPAProgram(
        metadata=ProgramMetadata(
            task_description="Test",
            program_id="test_id",
        ),
        states=[
            State(
                id="s1",
                verification=StateVerification(
                    type=VerificationType.EXPECT_ELEMENT,
                    xpath="//div",
                ),
            ),
        ],
        transitions=[],
    )
    json_str = program.model_dump_json()
    restored = RPAProgram.model_validate_json(json_str)
    assert restored.metadata.program_id == "test_id"
    assert len(restored.states) == 1


def test_rpa_program_add_state_and_transition():
    program = RPAProgram(
        metadata=ProgramMetadata(task_description="Test"),
        states=[
            State(
                id="s1",
                verification=StateVerification(type=VerificationType.TERMINAL_STATE),
            ),
        ],
        transitions=[],
    )
    program.add_state(
        State(
            id="s2",
            verification=StateVerification(type=VerificationType.TERMINAL_STATE),
        )
    )
    assert len(program.states) == 2

    # Adding duplicate should not increase count
    program.add_state(
        State(
            id="s2",
            verification=StateVerification(type=VerificationType.TERMINAL_STATE),
        )
    )
    assert len(program.states) == 2


def test_interaction_trace():
    trace = InteractionTrace(
        task_description="Test task",
        application_context="test.com",
    )
    trace.steps.append(
        TraceStep(
            action=ActionSpec(type=ActionType.ACTION_CLICK, target="//button"),
            target_xpath="//button[@id='test']",
        )
    )
    assert len(trace.steps) == 1
    assert trace.steps[0].target_xpath == "//button[@id='test']"


def test_execution_result_graph_coverage():
    result = ExecutionResult(
        success=True,
        actions_executed=10,
        actions_via_rpa=8,
        actions_via_cua=2,
    )
    assert result.graph_coverage == 0.8


def test_execution_result_cost():
    result = ExecutionResult(
        success=True,
        total_input_tokens=1000,
        total_output_tokens=500,
    )
    assert result.cost_estimate > 0


def test_gmail_example_from_design_doc():
    """Validate the Gmail example from DESIGN.md Section 5.1."""
    gmail_json = {
        "metadata": {
            "program_id": "gmail_send_basic_email_v1",
            "task_description": "Compose and send a basic email in Gmail",
            "application_context": "mail.google.com",
            "initial_states": ["logged_in_to_gmail", "inbox_view"],
            "parameters": ["recipient_email", "subject_line", "message_body"],
        },
        "states": [
            {"id": "initial", "verification": {"type": "expect_element", "xpath": "//div[text()='Compose']", "timeout_ms": 5000}},
            {"id": "compose_button_clicked", "verification": {"type": "expect_element", "xpath": "//div[@aria-label='New Message']", "timeout_ms": 5000}},
            {"id": "message_sent", "verification": {"type": "terminal_state"}},
        ],
        "transitions": [
            {"from": "initial", "to": "compose_button_clicked", "action": {"type": "action_click", "target": "//div[text()='Compose']"}},
            {"from": "compose_button_clicked", "to": "message_sent", "action": {"type": "wait", "ms": 500}},
        ],
    }
    program = RPAProgram.model_validate(gmail_json)
    assert program.metadata.program_id == "gmail_send_basic_email_v1"
    assert len(program.states) == 3
    assert len(program.transitions) == 2
    assert program.get_initial_state().id == "initial"
    assert len(program.get_terminal_states()) == 1
