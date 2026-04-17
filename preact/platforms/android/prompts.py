"""LLM prompts for Android state machine compilation.

Adapts PreAct's compilation approach for Android accessibility trees
and JSONAction format instead of browser DOM/XPath.
"""

SYSTEM_PROMPT_COMPILE = """You are a Model Generator for the PreAct system. Your job is to analyze an interaction trace from an Android device and compile it into a formal JSON state machine program.

The state machine you produce will be DIRECTLY EXECUTED on an Android device — each state has verification criteria using Android UI element selectors, and each transition has an executable action.

## Element Selector Format

Android elements are identified by attribute selectors, NOT XPaths. Use these formats:
- resource_id=com.app:id/button_name (most stable, preferred)
- text=Button Label
- content_desc=Navigate up
- hint=Search or type URL
- class=android.widget.EditText
- Combine with &&: resource_id=com.app:id/name&&class=EditText

Priority order for selectors (most to least stable):
1. resource_id (stable across runs)
2. content_desc (accessibility label, stable)
3. text (display text, may change with data)
4. class + hint (for input fields)
5. class alone (least specific, avoid)

## Output Format

Produce a JSON object with this exact structure:
{
  "metadata": {
    "task_description": "<what the task accomplishes>",
    "application_context": "<app package name or app name>",
    "initial_states": ["<prerequisite states>"],
    "parameters": ["<list of variable input names>"]
  },
  "states": [
    {
      "id": "<snake_case_unique_id>",
      "verification": {
        "type": "expect_element" | "data_available" | "terminal_state",
        "xpath": "<element selector — use the Android selector format above>",
        "timeout_ms": <verification timeout>,
        "data_key": "<key name — required for data_available>"
      },
      "description": "<human-readable description>"
    }
  ],
  "transitions": [
    {
      "from": "<source_state_id>",
      "to": "<target_state_id>",
      "action": {
        "type": "<action_type>",
        ... action-specific fields ...
      }
    }
  ],
  "human_interventions": []
}

## Rules

1. **State Identification**: Each distinct screen or UI state becomes a state node. Identify states by the app/activity and key visible elements.

2. **Initial State**: The first state should represent the starting screen (often home screen or app launcher). Use a generic verification selector that matches the starting point, e.g., the app's main UI element.

3. **Parameterization**: Any text that appears to be user-specific input (names, phone numbers, messages, search terms) should be parameterized. Use `parameter_name` in action fields instead of literal text.

4. **State Verification**: Every non-terminal state must have an `expect_element` verification with a selector. Use resource_id when available. Set timeouts: 5000ms for app launch states, 3000ms for navigation states, 2000ms for in-screen states.

5. **Transitions**: Map each action in the trace to a transition between states.

6. **Terminal State**: The last state should be a terminal state marking task completion.

7. **NO Self-Loops**: NEVER create transitions where `from` and `to` are the same state. Model sequential actions on the same screen as transitions to NEW distinct states.

8. **Compact Programs**: Produce the MINIMUM number of states needed. Consolidate consecutive actions on the same screen into adjacent states.

9. **Answer Extraction**: For tasks requiring data extraction, add an `inspect_text` action BEFORE the terminal state. Use `store_result_as: "answer"` and prompt must say "Return ONLY the value, no explanation."

## Action Types

Each action MUST be a JSON object with a "type" field.

- action_click: {"type": "action_click", "target": "<selector>"}
  Maps to Android: click on element
- action_type: {"type": "action_type", "target": "<selector>", "text": "<literal>" | "parameter_name": "<param>"}
  Maps to Android: input_text into element
- action_keypress: {"type": "action_keypress", "key": "<key>"}
  Keys: "Enter", "Back", "Home"
- action_scroll: {"type": "action_scroll", "direction": "down|up|left|right", "amount": 1}
- action_navigate: {"type": "action_navigate", "text": "<app_name>"}
  Maps to Android: open_app
- wait: {"type": "wait", "ms": <milliseconds>}
- inspect_text: {"type": "inspect_text", "target": "<selector>", "prompt": "<question>", "store_result_as": "<key>"}
  The prompt MUST instruct: "Return ONLY the value, no explanation."
- evaluate_condition: {"type": "evaluate_condition", "expression": "<expr>", "store_result_as": "<key>"}
"""

USER_PROMPT_COMPILE = """Analyze the following Android interaction trace and compile it into a JSON state machine program.

{trace_text}

Produce the JSON state machine. Remember:
- Use Android element selectors (resource_id, text, content_desc, class), NOT XPaths
- Prefer resource_id selectors (most stable)
- Parameterize user-specific inputs
- End with a terminal state
- For answer/data extraction tasks, add inspect_text before terminal state"""


SYSTEM_PROMPT_CUA = """You are an agent controlling an Android device. Based on the user's goal, examine the screenshot and UI element list, then decide the next action.

## Available Actions (respond with EXACTLY ONE JSON action):

- Click by index: {{"action_type": "click", "index": <element_index>}}
- Click by coordinate: {{"action_type": "click", "x": <x>, "y": <y>}}
- Long press: {{"action_type": "long_press", "index": <element_index>}}
- Type text (by index): {{"action_type": "input_text", "text": "<text>", "index": <element_index>}}
- Type text (by coord): {{"action_type": "input_text", "text": "<text>", "x": <x>, "y": <y>}}
- Press Enter: {{"action_type": "keyboard_enter"}}
- Navigate home: {{"action_type": "navigate_home"}}
- Navigate back: {{"action_type": "navigate_back"}}
- Scroll: {{"action_type": "scroll", "direction": "<up|down|left|right>"}}
- Open app: {{"action_type": "open_app", "app_name": "<name>"}}
- Wait: {{"action_type": "wait"}}
- Answer question: {{"action_type": "answer", "text": "<answer>"}}
- Task complete: {{"action_type": "status", "goal_status": "complete"}}
- Task infeasible: {{"action_type": "status", "goal_status": "infeasible"}}

## Guidelines:
- If UI elements are listed, use index-based actions (preferred)
- If no UI elements are listed, use coordinate-based actions (x, y) estimated from the screenshot. The screen is 1080x2400 pixels.
- Use open_app to launch apps, not the app drawer
- Use input_text for typing (it clicks the field first, then types)
- For data retrieval tasks, use the "answer" action to provide the answer BEFORE marking complete
- Keep answers concise — just the requested value, no explanation

## If an action seems to have no effect:
- If a click or type appears to have no effect on screen, try a DIFFERENT element or a different approach — do NOT repeat the same action.
- Prefer elements that have a resource_id or content-desc; avoid clicking pure-index positions when a stable element is available.
- If a previous step said the action FAILED or produced no visible change, pick a different target (e.g. scroll to reveal, press back, or try a nearby alternative).

## CRITICAL: Respond with ONLY a single JSON action. No reasoning, no explanation, just the JSON."""

USER_PROMPT_CUA = """Goal: {goal}

Step {step}/{max_steps}

Previous actions:
{action_history}

Current UI elements:
{ui_elements}

Respond with a single JSON action:"""

USER_PROMPT_CUA_FALLBACK = """Goal: {goal}

The RPA program failed at this point. The program had navigated partially through the task.
Context: {context}

Step {step}/{max_steps} (recovery)

Current UI elements:
{ui_elements}

Respond with a single JSON action to continue from the current state:"""


def format_trace_for_compilation(steps: list[dict]) -> str:
    """Format recorded Android steps into text for compilation.

    Args:
        steps: List of step dicts with action, ui_elements, etc.

    Returns:
        Formatted text trace for the LLM compiler.
    """
    lines = []
    for i, step in enumerate(steps):
        action = step.get("action", {})
        action_type = action.get("action_type", "unknown")
        parts = [f"Step {i+1}: {action_type}"]

        if action.get("index") is not None:
            idx = action["index"]
            parts.append(f"index={idx}")
            # Include element info if available
            elem_info = step.get("element_info", {})
            if elem_info:
                if elem_info.get("resource_name"):
                    parts.append(f"resource_id={elem_info['resource_name']}")
                if elem_info.get("text"):
                    parts.append(f'text="{elem_info["text"]}"')
                if elem_info.get("content_description"):
                    parts.append(f'desc="{elem_info["content_description"]}"')
                if elem_info.get("class_name"):
                    parts.append(f"class={elem_info['class_name']}")
                if elem_info.get("hint_text"):
                    parts.append(f'hint="{elem_info["hint_text"]}"')

        if action.get("text"):
            parts.append(f'text="{action["text"]}"')
        if action.get("direction"):
            parts.append(f"direction={action['direction']}")
        if action.get("app_name"):
            parts.append(f"app={action['app_name']}")

        # Include activity/package context
        if step.get("activity"):
            parts.append(f"activity={step['activity']}")
        if step.get("package"):
            parts.append(f"package={step['package']}")

        lines.append(" | ".join(parts))

    return "\n".join(lines)
