"""Tests for the RPA Executor and ExecutionContext."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from preact.executor.context import ExecutionContext
from preact.executor.engine import RPAExecutor
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


# ─── ExecutionContext Tests ───────────────────────────────────────────────────


def test_context_parameters():
    ctx = ExecutionContext(parameters={"email": "test@example.com"})
    assert ctx.resolve_parameter("email") == "test@example.com"


def test_context_parameter_missing():
    ctx = ExecutionContext(parameters={})
    with pytest.raises(ValueError, match="Parameter 'email' not provided"):
        ctx.resolve_parameter("email")


def test_context_data():
    ctx = ExecutionContext()
    ctx.set_data("price", "29.99")
    assert ctx.get_data("price") == "29.99"
    assert ctx.has_data("price")
    assert not ctx.has_data("nonexistent")


def test_context_template_resolution():
    ctx = ExecutionContext(parameters={"name": "Alice"})
    ctx.set_data("greeting", "Hello")
    assert ctx.resolve_template("${name}") == "Alice"
    assert ctx.resolve_template("${parameters.name}") == "Alice"
    assert ctx.resolve_template("${data.greeting}") == "Hello"
    assert ctx.resolve_template("${data.greeting}, ${name}!") == "Hello, Alice!"


def test_context_expression_evaluation():
    ctx = ExecutionContext(parameters={"threshold": "50"})
    ctx.set_data("price", 30)
    assert ctx.evaluate_expression("data.price < 50") is True
    assert ctx.evaluate_expression("data.price > 100") is False


def test_context_log_step():
    ctx = ExecutionContext()
    ctx.log_step("state_1", "click", True)
    ctx.log_step("state_2", "type", True)
    assert ctx.step_count == 2
    assert len(ctx.execution_log) == 2


# ─── RPAExecutor Tests ────────────────────────────────────────────────────────


def _make_simple_program() -> RPAProgram:
    """Create a minimal two-state program for testing."""
    return RPAProgram(
        metadata=ProgramMetadata(task_description="Test"),
        states=[
            State(
                id="start",
                verification=StateVerification(
                    type=VerificationType.EXPECT_ELEMENT,
                    xpath="//button[@id='start']",
                    timeout_ms=1000,
                ),
            ),
            State(
                id="done",
                verification=StateVerification(type=VerificationType.TERMINAL_STATE),
            ),
        ],
        transitions=[
            Transition(
                from_state="start",
                to_state="done",
                action=ActionSpec(type=ActionType.WAIT, ms=10),
            ),
        ],
    )


@pytest.fixture
def mock_env():
    env = AsyncMock()
    env.element_exists = AsyncMock(return_value=True)
    env.screenshot = AsyncMock(return_value=b"fake_screenshot")
    return env


@pytest.mark.asyncio
async def test_executor_simple_success(mock_env):
    executor = RPAExecutor(mock_env, llm=None)
    program = _make_simple_program()
    result = await executor.execute(program)

    assert result.success is True
    assert "start" in result.states_visited
    assert "done" in result.states_visited
    assert result.actions_executed == 1
    assert result.actions_via_rpa == 1


@pytest.mark.asyncio
async def test_executor_state_verification_failure(mock_env):
    mock_env.element_exists = AsyncMock(return_value=False)

    executor = RPAExecutor(mock_env, llm=None, max_consecutive_failures=1)
    program = _make_simple_program()
    result = await executor.execute(program)

    assert result.success is False
    assert len(result.fallback_events) >= 1
    assert "state_verification_failed" in (result.error or "")


@pytest.mark.asyncio
async def test_executor_with_parameters(mock_env):
    program = RPAProgram(
        metadata=ProgramMetadata(
            task_description="Test with params",
            parameters=["name"],
        ),
        states=[
            State(
                id="input",
                verification=StateVerification(
                    type=VerificationType.EXPECT_ELEMENT,
                    xpath="//input",
                    timeout_ms=1000,
                ),
            ),
            State(
                id="done",
                verification=StateVerification(type=VerificationType.TERMINAL_STATE),
            ),
        ],
        transitions=[
            Transition(
                from_state="input",
                to_state="done",
                action=ActionSpec(
                    type=ActionType.ACTION_TYPE,
                    target="//input",
                    parameter_name="name",
                ),
            ),
        ],
    )

    executor = RPAExecutor(mock_env, llm=None)
    result = await executor.execute(program, parameters={"name": "Alice"})

    assert result.success is True
    mock_env.type_text.assert_called_once()


@pytest.mark.asyncio
async def test_executor_no_states():
    env = AsyncMock()
    executor = RPAExecutor(env, llm=None)
    program = RPAProgram(
        metadata=ProgramMetadata(task_description="Empty"),
        states=[],
        transitions=[],
    )
    result = await executor.execute(program)
    assert result.success is False
    assert result.error == "Program has no states"


@pytest.mark.asyncio
async def test_executor_data_available_verification(mock_env):
    """Test data_available verification type."""
    program = RPAProgram(
        metadata=ProgramMetadata(task_description="Data test"),
        states=[
            State(
                id="start",
                verification=StateVerification(
                    type=VerificationType.EXPECT_ELEMENT,
                    xpath="//body",
                    timeout_ms=1000,
                ),
            ),
            State(
                id="data_ready",
                verification=StateVerification(
                    type=VerificationType.DATA_AVAILABLE,
                    data_key="result",
                ),
            ),
            State(
                id="done",
                verification=StateVerification(type=VerificationType.TERMINAL_STATE),
            ),
        ],
        transitions=[
            Transition(
                from_state="start",
                to_state="data_ready",
                action=ActionSpec(
                    type=ActionType.EVALUATE_CONDITION,
                    expression="True",
                    store_result_as="result",
                ),
            ),
            Transition(
                from_state="data_ready",
                to_state="done",
                action=ActionSpec(type=ActionType.WAIT, ms=10),
            ),
        ],
    )

    executor = RPAExecutor(mock_env, llm=None)
    result = await executor.execute(program)
    assert result.success is True
