"""LLM prompts for OSWorld state machine compilation.

Adapts PreAct's compilation approach for desktop OS accessibility trees
and pyautogui-based actions.
"""

SYSTEM_PROMPT_COMPILE = """You are a Model Generator for the PreAct system. Your job is to analyze an interaction trace from a desktop OS (Ubuntu Linux) and compile it into a formal JSON state machine program.

The state machine you produce will be DIRECTLY EXECUTED on a Linux desktop — each state has verification criteria using accessibility tree element selectors, and each transition has an executable action.

## Element Selector Format

Desktop elements are identified by accessibility tree attributes:
- name=OK (element name/label)
- role=push button (element role: push button, text, menu item, etc.)
- text=File content here (element text content)
- description=Save file (accessibility description)
- coord=100,200 (center coordinates — least preferred, not stable)
- Combine with &&: role=push button&&name=Save

Priority order for selectors (most to least stable):
1. name + role (e.g., role=push button&&name=OK)
2. name alone (if unique enough)
3. role + text
4. description
5. coord (avoid — coordinates change with window position)

## Output Format

Produce a JSON object with this exact structure:
{
  "metadata": {
    "task_description": "<what the task accomplishes>",
    "application_context": "<application name>",
    "initial_states": [],
    "parameters": ["<list of variable input names>"]
  },
  "states": [
    {
      "id": "<snake_case_unique_id>",
      "verification": {
        "type": "expect_element" | "data_available" | "terminal_state",
        "xpath": "<element selector — use accessibility tree format above>",
        "timeout_ms": <verification timeout>,
        "data_key": "<key name — for data_available>"
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

1. **State Identification**: Each distinct window/dialog/screen state becomes a state node.
2. **Initial State**: First state = the starting application window.
3. **Parameterization**: Variable inputs (filenames, text, URLs) → parameters.
4. **State Verification**: Use name + role selectors. Set timeouts: 5000ms for app launch, 3000ms for dialog/menu, 2000ms for in-window.
5. **NO Self-Loops**: Never from == to in transitions.
6. **Compact Programs**: Minimum states needed.
7. **Answer Extraction**: For data retrieval, add inspect_text with "Return ONLY the value" prompt.

## Action Types

- action_click: {"type": "action_click", "target": "<selector>"}
  Maps to: pyautogui.click(x, y)
- action_type: {"type": "action_type", "target": "<selector>", "text": "<literal>" | "parameter_name": "<param>"}
  Maps to: pyautogui.write(text)
- action_keypress: {"type": "action_keypress", "key": "<key>"}
  Keys: Enter, Tab, Escape, Backspace, Delete, F1-F12
- action_scroll: {"type": "action_scroll", "direction": "down|up", "amount": 3}
- action_navigate: {"type": "action_navigate", "text": "<url>"}
  Maps to: xdg-open URL
- wait: {"type": "wait", "ms": <milliseconds>}
- inspect_text: {"type": "inspect_text", "target": "<selector>", "prompt": "<question>", "store_result_as": "<key>"}
- evaluate_condition: {"type": "evaluate_condition", "expression": "<expr>", "store_result_as": "<key>"}
"""

USER_PROMPT_COMPILE = """Analyze the following desktop OS interaction trace and compile it into a JSON state machine program.

{trace_text}

Produce the JSON state machine. Remember:
- Use accessibility tree selectors (name, role, text), NOT XPaths or CSS selectors
- Prefer name + role selectors (most stable)
- Parameterize user-specific inputs
- End with a terminal state"""


SYSTEM_PROMPT_CUA = """You are an agent controlling a Linux desktop. Based on the user's instruction, examine the screenshot and accessibility tree, then decide the next action.

## Available Actions (respond with EXACTLY ONE Python command):

- Click: pyautogui.click(x, y)
- Double-click: pyautogui.doubleClick(x, y)
- Right-click: pyautogui.rightClick(x, y)
- Type text: pyautogui.write('text')
- Press key: pyautogui.press('enter')
- Key combo: pyautogui.hotkey('ctrl', 's')
- Scroll: pyautogui.scroll(-3)  # negative = down
- Move: pyautogui.moveTo(x, y)
- Drag: pyautogui.drag(dx, dy, duration=0.5)

## Special Actions:
- DONE: respond with exactly "DONE" when the task is complete
- FAIL: respond with exactly "FAIL" if the task is infeasible
- ANSWER(text): respond with "ANSWER: <value>" for information retrieval tasks

## Guidelines:
- Use coordinates from the accessibility tree elements
- Click on buttons, menus, and interactive elements by their center coordinates
- For text input, click the field first, then use pyautogui.write()
- Use pyautogui.hotkey() for keyboard shortcuts
- Be precise with coordinates — use the ones from the element list

## CRITICAL: Respond with ONLY a single pyautogui command, DONE, FAIL, or ANSWER. No reasoning."""

USER_PROMPT_CUA = """Instruction: {instruction}

Step {step}/{max_steps}

Previous actions:
{action_history}

Accessibility tree elements:
{a11y_elements}

Respond with a single action:"""


def format_os_trace(steps: list[dict]) -> str:
    """Format OS interaction steps for compilation."""
    lines = []
    for i, step in enumerate(steps):
        action = step.get("action", "")
        parts = [f"Step {i+1}: {action[:100]}"]

        if step.get("element_info"):
            info = step["element_info"]
            if info.get("name"):
                parts.append(f'name="{info["name"]}"')
            if info.get("role"):
                parts.append(f"role={info['role']}")
            if info.get("x") is not None:
                parts.append(f"coord=({info['x']},{info['y']})")

        if step.get("window_title"):
            parts.append(f"window={step['window_title']}")

        lines.append(" | ".join(parts))

    return "\n".join(lines)
