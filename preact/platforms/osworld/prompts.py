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


SYSTEM_PROMPT_CUA = """You are an agent controlling a Linux desktop. Based on the user's instruction, the screenshot, and the accessibility tree, decide the NEXT single action.

## PREFERRED ACTION FORMAT (semantic — use this whenever possible)

The accessibility tree is shown to you as a numbered list. Each line is:
    [idx] role "name" (cx,cy)
where idx is the element index, role is e.g. "push button" or "text", name
is the visible label, and (cx,cy) is the center coordinate.

Refer to elements by their INDEX. Emit exactly ONE of:

- click(id=N)                        — left-click element N
- double_click(id=N)                 — double-click element N
- right_click(id=N)                  — right-click element N
- type(id=N, text="...")             — click N, then type text
- type(text="...")                   — type into the currently-focused widget
- key(name)                          — press a single key: enter, tab, escape, backspace, delete, space, f1..f12
- hotkey(ctrl+s)                     — key combo; use `+` between modifiers
- scroll(direction=down, amount=3)   — direction is up|down|left|right
- drag(from=N, to=M)                 — drag element N onto element M
- wait(ms=500)                       — small wait

## FALLBACK: raw coordinates (only when NOTHING in the a11y list matches)

- raw_click(x, y)                    — click absolute pixel coords
- raw_double_click(x, y)
- raw_right_click(x, y)
- raw_move(x, y)

Prefer id=N always. raw_click is a last resort (e.g. empty a11y tree).

## SPECIAL RESPONSES
- DONE          — the task is complete
- FAIL          — the task is infeasible
- ANSWER: ...   — information-retrieval answer

## RULES
- Output EXACTLY ONE action on ONE line. No code fences, no reasoning.
- Do NOT repeat the same action. If the screen did not change after your last
  action, that action did not work — try a DIFFERENT element or approach
  (scroll, a keyboard shortcut, a different click target, Escape, etc.).
- Only use raw_click / raw_coordinates when the a11y tree is empty or does
  not contain the element you need.

## WORKED EXAMPLE

Instruction: "Open the Settings application from the launcher."

Accessibility tree (excerpt):
    [0] frame "Activities" (40,20)
    [3] push button "Files" (800,67)
    [5] push button "Settings" (1200,67)
    [7] push button "Terminal" (1400,67)

Correct output:
    click(id=5)

(Do NOT write `pyautogui.click(1200, 67)` — use the semantic form.)
"""

USER_PROMPT_CUA = """Instruction: {instruction}

Step {step}/{max_steps}

Previous actions:
{action_history}

Accessibility tree elements (index → coord):
{a11y_elements}

Respond with a single action line (click(id=N), type(id=N, text="..."), hotkey(...), DONE, FAIL, ANSWER: ...):"""


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
