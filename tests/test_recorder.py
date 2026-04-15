"""Tests for the Interaction Recorder."""

import pytest
from unittest.mock import AsyncMock

from preact.recorder.recorder import InteractionRecorder
from preact.recorder.trace import trace_to_text, extract_unique_xpaths
from preact.schemas import ActionSpec, ActionType


@pytest.fixture
def mock_env():
    env = AsyncMock()
    env.screenshot = AsyncMock(return_value=b"fake_screenshot")
    env.get_page_url = AsyncMock(return_value="https://test.com")
    env.get_dom_snapshot = AsyncMock(return_value="<html></html>")
    return env


@pytest.mark.asyncio
async def test_recorder_lifecycle(mock_env):
    recorder = InteractionRecorder(mock_env)

    assert not recorder.is_recording

    recorder.start_recording("Test task", "test.com")
    assert recorder.is_recording

    await recorder.record_step(
        action=ActionSpec(type=ActionType.ACTION_CLICK, target="//button"),
        target_xpath="//button[@id='test']",
    )

    trace = recorder.stop_recording(success=True)
    assert not recorder.is_recording
    assert trace.success is True
    assert len(trace.steps) == 1
    assert trace.task_description == "Test task"


@pytest.mark.asyncio
async def test_recorder_multiple_steps(mock_env):
    recorder = InteractionRecorder(mock_env)
    recorder.start_recording("Multi step test")

    for i in range(5):
        await recorder.record_step(
            action=ActionSpec(type=ActionType.ACTION_CLICK, target=f"//button[{i}]"),
        )

    trace = recorder.stop_recording()
    assert len(trace.steps) == 5


@pytest.mark.asyncio
async def test_recorder_parameter_tracking(mock_env):
    recorder = InteractionRecorder(mock_env)
    recorder.start_recording("Param test")
    recorder.record_parameter("email", "test@example.com")
    trace = recorder.stop_recording()
    assert trace.parameters_used["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_recorder_discard(mock_env):
    recorder = InteractionRecorder(mock_env)
    recorder.start_recording("Discard test")
    recorder.discard_recording()
    assert not recorder.is_recording


def test_recorder_stop_without_start():
    mock_env = AsyncMock()
    recorder = InteractionRecorder(mock_env)
    with pytest.raises(RuntimeError, match="No recording in progress"):
        recorder.stop_recording()


def test_trace_to_text():
    from preact.schemas import InteractionTrace, TraceStep

    trace = InteractionTrace(
        task_description="Test task",
        application_context="test.com",
    )
    trace.steps.append(
        TraceStep(
            action=ActionSpec(type=ActionType.ACTION_CLICK, target="//button"),
            target_xpath="//button[@id='submit']",
            page_url="https://test.com",
        )
    )
    text = trace_to_text(trace)
    assert "Test task" in text
    assert "action_click" in text
    assert "//button[@id='submit']" in text


def test_extract_unique_xpaths():
    from preact.schemas import InteractionTrace, TraceStep

    trace = InteractionTrace(task_description="Test")
    trace.steps.extend([
        TraceStep(
            action=ActionSpec(type=ActionType.ACTION_CLICK, target="//button[1]"),
            target_xpath="//button[@id='a']",
        ),
        TraceStep(
            action=ActionSpec(type=ActionType.ACTION_CLICK, target="//button[2]"),
            target_xpath="//button[@id='a']",  # Duplicate
        ),
        TraceStep(
            action=ActionSpec(type=ActionType.ACTION_TYPE, target="//input"),
            target_xpath="//input[@name='email']",
        ),
    ])
    xpaths = extract_unique_xpaths(trace)
    assert len(xpaths) >= 3  # All unique xpaths
