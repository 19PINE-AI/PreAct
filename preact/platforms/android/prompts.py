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
        "description": "<ONE-SENTENCE natural-language summary of what this action does — required, human-readable, no code>",
        ... action-specific fields ...
      }
    }
  ],
  "human_interventions": []
}

## Natural-language descriptions (REQUIRED)

Every state MUST have a `description` field that reads like a caption
("audio recorder main screen", "save-confirmation dialog"). Every transition
action MUST have a `description` field that reads like a caption
("tap the record button to start recording", "enter the filename in the
save-as field"). These descriptions are consumed by a downstream selector
agent that picks which compiled program to replay based on the task goal,
so make them precise and parameter-aware — e.g. "type the filename (parameter
`filename`)", not "type text".

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


SYSTEM_PROMPT_CUA = """You are an agent that operates an Android device on behalf of a user. At each step you are given TWO images of the current screen:
  1. The raw screenshot (unobscured).
  2. The same screenshot with GREEN bounding boxes and WHITE numeric index labels drawn on every interactable element. The numeric label in the top-left corner of a box IS that element's index (and matches the index in the UI element list).

You also receive a list of the numbered UI elements and a history of what you have already done.

## Action list (you will emit EXACTLY ONE action as JSON):

- Click: {{"action_type": "click", "index": <index>}}
- Click by coordinate (fallback): {{"action_type": "click", "x": <x>, "y": <y>}}
- Long press: {{"action_type": "long_press", "index": <index>}}
- Type text: {{"action_type": "input_text", "text": "<text>", "index": <index>}}  (auto-focuses field first)
- Press Enter: {{"action_type": "keyboard_enter"}}
- Home: {{"action_type": "navigate_home"}}
- Back: {{"action_type": "navigate_back"}}
- Scroll: {{"action_type": "scroll", "direction": "<up|down|left|right>"}}
- Open app: {{"action_type": "open_app", "app_name": "<name>"}}
- Wait: {{"action_type": "wait"}}
- Answer: {{"action_type": "answer", "text": "<answer>"}}
- Complete: {{"action_type": "status", "goal_status": "complete"}}
- Infeasible: {{"action_type": "status", "goal_status": "infeasible"}}

## Guidelines
- Prefer index-based actions; use coordinates only if no element list is available.
- Use open_app rather than the app drawer.
- input_text clicks the field and types — do not click the field first.
- For question-answering tasks, emit an `answer` action with the value BEFORE `status complete`.
- If an action produced NO visible change, do NOT repeat it — pick a different element or approach (scroll, back, alternate target).
- The UI-elements list already includes the FULL `text` attribute of every TextView/EditText — you do NOT need to scroll to "see more text" inside an editor/viewer. If you have already opened a document and its element has a long `text`, extract the info you need from that element and move on. Scrolling repeatedly inside the same document is a failure mode.
- Track phases explicitly in `Reason:` for multi-step tasks (e.g. "Phase 1: read source file DONE, now Phase 2: enter data in target app").
- **Replacing field content**: `input_text` appends — it does NOT clear the field. If the target field already has any text and the task requires replacement (not appending), you MUST first clear it: `long_press` the field, then click the "Select all" menu item, then emit `input_text` with the new value. Never emit `input_text` into a non-empty field unless you intend to append.
- **Scroll boundaries**: A horizontal or vertical list has an end. If you scroll in a direction and the UI-elements list is unchanged from before the scroll, that direction is exhausted — do NOT keep scrolling the same way. Try the opposite direction once; if that is also exhausted, the target item is not in this list — conclude `infeasible` or pick a different entry point rather than looping.
- **Image content**: If a task requires reading text from an image and manual zoom/tap does not surface the text in UI elements, do not loop on zoom gestures. Try one alternate viewer (e.g. Google Lens) once; if that fails, emit `status infeasible` — repeated zoom/tap in a gallery is a guaranteed timeout.

## OUTPUT FORMAT (REQUIRED)

Respond in EXACTLY this two-line format:

Reason: <one sentence explaining which element you picked and why>
Action: {{"action_type": "...", ...}}

Nothing else. Do not prefix with code fences.
"""

USER_PROMPT_CUA = """Goal: {goal}

Step {step}/{max_steps}

Previous actions:
{action_history}

Current UI elements:
{ui_elements}

Respond with a single JSON action:"""

SYSTEM_PROMPT_SUMMARY = """You are summarizing the latest step of an agent operating an Android device. Your summary will be appended to the agent's action history and used to guide future action selection."""


USER_PROMPT_SUMMARY = """The (overall) user goal/request is: {goal}

You are given the screenshot BEFORE the action (labeled "before") and AFTER the action (labeled "after"), together with the UI element lists for each.

UI elements BEFORE:
{before_elements}

UI elements AFTER:
{after_elements}

Action picked: {action}
Reason given: {reason}

Compare the two screenshots and UI element lists. In <=50 words on ONE single line, summarize:
- what was intended,
- whether it worked (be critical — the action/reason might be wrong),
- what should or should not be done next.

Rules:
- Keep it to a single line, <=50 words.
- For `answer` and `wait` actions you may assume they worked as expected.
- Include any information worth remembering across steps (e.g. values read from the screen).

Summary of this step:"""


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
