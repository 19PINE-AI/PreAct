"""Parse LLM action output into executable ActionSpec.

Handles the JSON action format from the CUA Loop's LLM responses
and converts them to ActionSpec objects for execution.
"""

from __future__ import annotations

import json
import logging
import re

from preact.schemas import ActionSpec, ActionType

logger = logging.getLogger(__name__)


def parse_action(llm_output: str) -> ActionSpec | None:
    """Parse an LLM action output string into an ActionSpec.

    Handles various LLM output formats:
    - Clean JSON
    - JSON in markdown code blocks
    - JSON with surrounding text
    """
    text = llm_output.strip()

    # Extract JSON from markdown code blocks
    if "```json" in text:
        match = re.search(r"```json\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()
    elif "```" in text:
        match = re.search(r"```\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()

    # Extract the first JSON object from text
    match = re.search(r"\{[^{}]*\}", text)
    if match:
        text = match.group(0)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning("Failed to parse action JSON: %s — %s", e, text[:200])
        return None

    action_name = data.get("action", "").lower()

    if action_name == "click":
        return ActionSpec(
            type=ActionType.ACTION_CLICK,
            target=data.get("xpath"),
        )
    elif action_name == "double_click":
        return ActionSpec(
            type=ActionType.ACTION_DOUBLE_CLICK,
            target=data.get("xpath"),
        )
    elif action_name == "triple_click":
        # Triple-click selects all text — treat as click (clear_and_type handles it)
        return ActionSpec(
            type=ActionType.ACTION_CLICK,
            target=data.get("xpath"),
        )
    elif action_name == "clear":
        # Clear field — treat as type with empty text to trigger clear_and_type
        return ActionSpec(
            type=ActionType.ACTION_TYPE,
            target=data.get("xpath"),
            text="",
        )
    elif action_name == "type":
        return ActionSpec(
            type=ActionType.ACTION_TYPE,
            target=data.get("xpath"),
            text=data.get("text", ""),
        )
    elif action_name == "keypress":
        return ActionSpec(
            type=ActionType.ACTION_KEYPRESS,
            key=data.get("key"),
        )
    elif action_name == "hover":
        return ActionSpec(
            type=ActionType.ACTION_MOVE,
            target=data.get("xpath"),
        )
    elif action_name == "scroll":
        return ActionSpec(
            type=ActionType.ACTION_SCROLL,
            direction=data.get("direction", "down"),
            amount=data.get("amount", 3),
        )
    elif action_name == "wait":
        return ActionSpec(
            type=ActionType.WAIT,
            ms=data.get("ms", 1000),
        )
    elif action_name == "select":
        return ActionSpec(
            type=ActionType.ACTION_TYPE,
            target=data.get("xpath"),
            text=data.get("value", ""),
        )
    elif action_name == "navigate":
        return ActionSpec(
            type=ActionType.ACTION_NAVIGATE,
            text=data.get("url"),
        )
    elif action_name == "done":
        # Special sentinel — not a real action
        # Capture answer for information retrieval tasks
        answer = data.get("answer", "")
        reason = data.get("reason", "")
        return ActionSpec(
            type=ActionType.WAIT,
            ms=0,
            description=f"done:{'success' if data.get('success') else 'failure'}:"
            f"{reason}",
            text=answer if answer else None,
        )
    else:
        logger.warning("Unknown action type: %s", action_name)
        return None


def is_done_action(action: ActionSpec) -> bool:
    """Check if an action is a 'done' sentinel."""
    return (
        action.description is not None
        and action.description.startswith("done:")
    )


def is_done_success(action: ActionSpec) -> bool:
    """Check if a 'done' action indicates success."""
    return (
        action.description is not None
        and action.description.startswith("done:success")
    )


def get_done_answer(action: ActionSpec) -> str:
    """Extract the answer from a 'done' action (for info retrieval tasks).

    First checks the explicit answer field (action.text).
    Falls back to extracting from the reason/description if no answer
    field was provided.
    """
    if action.text:
        return action.text

    # Fallback: try to extract answer from the reason field
    if action.description and "done:success:" in action.description:
        reason = action.description.split("done:success:", 1)[1]
        if reason:
            return reason.strip()

    return ""
