"""Integration tests for the PreAct pipeline.

Tests the full flow: record → compile → replay → fallback → refine
using a mock environment and mock LLM.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from preact.config import PreActConfig
from preact.core.agent import PreActAgent
from preact.cua.loop import CUALoop
from preact.executor.engine import RPAExecutor
from preact.generator.compiler import ModelGenerator
from preact.llm.client import LLMClient
from preact.recorder.recorder import InteractionRecorder
from preact.schemas import (
    ActionSpec,
    ActionType,
    InteractionTrace,
    ProgramMetadata,
    RPAProgram,
    State,
    StateVerification,
    TraceStep,
    Transition,
    VerificationType,
)


@pytest.fixture
def mock_env():
    """Mock environment that simulates a simple web page."""
    env = AsyncMock()
    env.element_exists = AsyncMock(return_value=True)
    env.click = AsyncMock()
    env.type_text = AsyncMock()
    env.press_key = AsyncMock()
    env.scroll = AsyncMock()
    env.screenshot = AsyncMock(return_value=b"fake_png_data")
    env.element_screenshot = AsyncMock(return_value=b"fake_element_png")
    env.element_text = AsyncMock(return_value="Sample text content")
    env.get_page_url = AsyncMock(return_value="https://test.com")
    env.get_page_title = AsyncMock(return_value="Test Page")
    env.get_dom_snapshot = AsyncMock(return_value="<html><body>test</body></html>")
    env.evaluate_js = AsyncMock(return_value=[])
    env.start = AsyncMock()
    env.stop = AsyncMock()
    env.go_back = AsyncMock()
    return env


@pytest.fixture
def mock_llm():
    """Mock LLM that returns predefined responses."""
    llm = AsyncMock(spec=LLMClient)
    llm.total_input_tokens = 0
    llm.total_output_tokens = 0
    llm.total_tokens = 0
    llm.reset_usage = MagicMock()
    llm.embed = AsyncMock(return_value=[[0.1] * 768])
    return llm


def _make_test_program() -> RPAProgram:
    """Create a test program with 3 states."""
    return RPAProgram(
        metadata=ProgramMetadata(
            task_description="Click a button and type text",
            application_context="test.com",
            parameters=["name"],
        ),
        states=[
            State(
                id="page_loaded",
                verification=StateVerification(
                    type=VerificationType.EXPECT_ELEMENT,
                    xpath="//div[@id='content']",
                    timeout_ms=3000,
                ),
            ),
            State(
                id="button_clicked",
                verification=StateVerification(
                    type=VerificationType.EXPECT_ELEMENT,
                    xpath="//input[@id='name']",
                    timeout_ms=2000,
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
                from_state="page_loaded",
                to_state="button_clicked",
                action=ActionSpec(
                    type=ActionType.ACTION_CLICK,
                    target="//button[@id='start']",
                ),
            ),
            Transition(
                from_state="button_clicked",
                to_state="completed",
                action=ActionSpec(
                    type=ActionType.ACTION_TYPE,
                    target="//input[@id='name']",
                    parameter_name="name",
                ),
            ),
        ],
    )


@pytest.mark.asyncio
async def test_executor_full_pipeline(mock_env):
    """Test executing a complete RPA program."""
    executor = RPAExecutor(mock_env, llm=None)
    program = _make_test_program()
    result = await executor.execute(program, parameters={"name": "Alice"})

    assert result.success is True
    assert result.actions_executed == 2
    assert result.actions_via_rpa == 2
    assert result.actions_via_cua == 0
    assert result.graph_coverage == 1.0


@pytest.mark.asyncio
async def test_executor_fallback_on_verification_failure(mock_env):
    """Test that executor signals fallback when state verification fails."""
    # First call succeeds, second fails
    mock_env.element_exists = AsyncMock(
        side_effect=[True, False]
    )

    executor = RPAExecutor(mock_env, llm=None, max_consecutive_failures=1)
    program = _make_test_program()
    result = await executor.execute(program, parameters={"name": "Bob"})

    assert result.success is False
    assert len(result.fallback_events) == 1
    assert result.fallback_events[0].failed_state_id == "button_clicked"


@pytest.mark.asyncio
async def test_recorder_captures_trace(mock_env):
    """Test that the recorder captures a complete trace."""
    recorder = InteractionRecorder(mock_env)
    recorder.start_recording("Test recording", "test.com")

    await recorder.record_step(
        action=ActionSpec(type=ActionType.ACTION_CLICK, target="//button"),
        target_xpath="//button[@id='test']",
        llm_reasoning="Clicking the test button",
    )

    await recorder.record_step(
        action=ActionSpec(
            type=ActionType.ACTION_TYPE, target="//input", text="hello"
        ),
        target_xpath="//input[@name='field']",
    )

    trace = recorder.stop_recording(success=True)

    assert trace.success is True
    assert len(trace.steps) == 2
    assert trace.steps[0].llm_reasoning == "Clicking the test button"
    assert trace.application_context == "test.com"


@pytest.mark.asyncio
async def test_model_generator_compilation(mock_llm):
    """Test compiling an interaction trace into an RPA program."""
    # Mock LLM to return a valid program JSON
    program_json = json.dumps({
        "metadata": {
            "task_description": "Test task",
            "application_context": "test.com",
            "parameters": ["name"],
        },
        "states": [
            {"id": "start", "verification": {"type": "expect_element", "xpath": "//body", "timeout_ms": 3000}},
            {"id": "done", "verification": {"type": "terminal_state"}},
        ],
        "transitions": [
            {"from": "start", "to": "done", "action": {"type": "wait", "ms": 100}},
        ],
    })
    mock_llm.complete = AsyncMock(return_value=program_json)

    generator = ModelGenerator(mock_llm)

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

    program = await generator.compile(trace)

    assert program.metadata.task_description == "Test task"
    assert len(program.states) == 2
    assert len(program.transitions) == 1


@pytest.mark.asyncio
async def test_model_generator_fallback_compilation(mock_llm):
    """Test fallback compilation when LLM returns invalid JSON."""
    mock_llm.complete = AsyncMock(return_value="This is not valid JSON")

    generator = ModelGenerator(mock_llm)

    trace = InteractionTrace(
        task_description="Fallback test",
    )
    trace.steps.append(
        TraceStep(
            action=ActionSpec(type=ActionType.ACTION_CLICK, target="//button"),
            target_xpath="//button[@id='x']",
        )
    )

    program = await generator.compile(trace)

    # Should produce a fallback linear program
    assert program is not None
    assert len(program.states) >= 2  # At least one step + terminal
    assert len(program.transitions) >= 1


@pytest.mark.asyncio
async def test_model_generator_graph_extension(mock_llm):
    """Test monotonic graph extension after a fallback."""
    extension_json = json.dumps({
        "new_states": [
            {"id": "recovery_state", "verification": {"type": "expect_element", "xpath": "//div[@id='new']", "timeout_ms": 3000}},
        ],
        "new_transitions": [
            {"from": "button_clicked", "to": "recovery_state", "action": {"type": "action_click", "target": "//a[@id='alt']"}},
            {"from": "recovery_state", "to": "completed", "action": {"type": "wait", "ms": 100}},
        ],
    })
    mock_llm.complete = AsyncMock(return_value=extension_json)

    generator = ModelGenerator(mock_llm)
    program = _make_test_program()
    original_state_count = len(program.states)

    from preact.schemas import FallbackEvent

    fallback = FallbackEvent(
        failed_state_id="button_clicked",
        failure_reason="Element not found",
        llm_resolution_trace=InteractionTrace(
            task_description="Recovery",
            steps=[
                TraceStep(
                    action=ActionSpec(type=ActionType.ACTION_CLICK, target="//a[@id='alt']"),
                )
            ],
        ),
    )

    extended = await generator.extend_graph(program, fallback)

    # Monotonic: only additions
    assert len(extended.states) == original_state_count + 1
    assert extended.get_state("recovery_state") is not None


@pytest.mark.asyncio
async def test_cua_loop_with_done_action(mock_env, mock_llm):
    """Test CUA loop terminates on 'done' action."""
    mock_llm.complete_with_vision = AsyncMock(
        return_value='{"action": "done", "success": true, "reason": "Task complete"}'
    )

    recorder = InteractionRecorder(mock_env)
    cua = CUALoop(mock_env, mock_llm, recorder)
    result = await cua.run("Test task", max_steps=5, record=False)

    assert result.success is True
    assert result.actions_taken == 0  # Done immediately


@pytest.mark.asyncio
async def test_cua_loop_executes_actions(mock_env, mock_llm):
    """Test CUA loop executes actions then completes."""
    responses = [
        '{"action": "click", "xpath": "//button"}',
        '{"action": "type", "xpath": "//input", "text": "hello"}',
        '{"action": "done", "success": true, "reason": "Done"}',
    ]
    mock_llm.complete_with_vision = AsyncMock(side_effect=responses)

    cua = CUALoop(mock_env, mock_llm)
    result = await cua.run("Test task", max_steps=10, record=False)

    assert result.success is True
    assert result.actions_taken == 2


@pytest.mark.asyncio
async def test_full_record_compile_replay_cycle(mock_env, mock_llm):
    """Test the complete PreAct cycle: record → compile → replay."""
    # Phase 1: CUA exploration (returns actions then done)
    mock_llm.complete_with_vision = AsyncMock(
        side_effect=[
            '{"action": "click", "xpath": "//button[@id=\'start\']"}',
            '{"action": "type", "xpath": "//input[@id=\'name\']", "text": "Alice"}',
            '{"action": "done", "success": true, "reason": "Completed"}',
        ]
    )

    recorder = InteractionRecorder(mock_env)
    cua = CUALoop(mock_env, mock_llm, recorder)
    cua_result = await cua.run("Fill form", max_steps=10, record=True)

    assert cua_result.success is True
    assert cua_result.trace is not None
    assert len(cua_result.trace.steps) == 2

    # Phase 2: Compile trace to program
    compiled_json = json.dumps({
        "metadata": {
            "task_description": "Fill form",
            "parameters": ["name"],
        },
        "states": [
            {"id": "form_page", "verification": {"type": "expect_element", "xpath": "//button[@id='start']", "timeout_ms": 3000}},
            {"id": "form_filled", "verification": {"type": "expect_element", "xpath": "//input[@id='name']", "timeout_ms": 2000}},
            {"id": "done", "verification": {"type": "terminal_state"}},
        ],
        "transitions": [
            {"from": "form_page", "to": "form_filled", "action": {"type": "action_click", "target": "//button[@id='start']"}},
            {"from": "form_filled", "to": "done", "action": {"type": "action_type", "target": "//input[@id='name']", "parameter_name": "name"}},
        ],
    })
    mock_llm.complete = AsyncMock(return_value=compiled_json)

    generator = ModelGenerator(mock_llm)
    program = await generator.compile(cua_result.trace)

    assert len(program.states) == 3
    assert len(program.transitions) == 2

    # Phase 3: Replay from compiled program
    executor = RPAExecutor(mock_env, llm=None)
    result = await executor.execute(program, parameters={"name": "Bob"})

    assert result.success is True
    assert result.actions_via_rpa == 2
    assert result.graph_coverage == 1.0
