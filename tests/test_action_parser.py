"""Tests for the CUA action parser."""

from preact.cua.action_parser import is_done_action, is_done_success, parse_action
from preact.schemas import ActionType


def test_parse_click():
    action = parse_action('{"action": "click", "xpath": "//button[@id=\'submit\']"}')
    assert action is not None
    assert action.type == ActionType.ACTION_CLICK
    assert action.target == "//button[@id='submit']"


def test_parse_type():
    action = parse_action('{"action": "type", "xpath": "//input", "text": "hello"}')
    assert action is not None
    assert action.type == ActionType.ACTION_TYPE
    assert action.text == "hello"


def test_parse_keypress():
    action = parse_action('{"action": "keypress", "key": "Enter"}')
    assert action is not None
    assert action.type == ActionType.ACTION_KEYPRESS
    assert action.key == "Enter"


def test_parse_scroll():
    action = parse_action('{"action": "scroll", "direction": "down", "amount": 5}')
    assert action is not None
    assert action.type == ActionType.ACTION_SCROLL
    assert action.direction == "down"
    assert action.amount == 5


def test_parse_wait():
    action = parse_action('{"action": "wait", "ms": 2000}')
    assert action is not None
    assert action.type == ActionType.WAIT
    assert action.ms == 2000


def test_parse_done_success():
    action = parse_action('{"action": "done", "success": true, "reason": "Task completed"}')
    assert action is not None
    assert is_done_action(action)
    assert is_done_success(action)


def test_parse_done_failure():
    action = parse_action('{"action": "done", "success": false, "reason": "Stuck"}')
    assert action is not None
    assert is_done_action(action)
    assert not is_done_success(action)


def test_parse_with_markdown_wrapper():
    action = parse_action('```json\n{"action": "click", "xpath": "//a"}\n```')
    assert action is not None
    assert action.type == ActionType.ACTION_CLICK


def test_parse_with_surrounding_text():
    action = parse_action(
        'I will click the button now. {"action": "click", "xpath": "//button"} That should work.'
    )
    assert action is not None
    assert action.type == ActionType.ACTION_CLICK


def test_parse_invalid_json():
    action = parse_action("not json at all")
    assert action is None


def test_parse_unknown_action():
    action = parse_action('{"action": "unknown_action"}')
    assert action is None
