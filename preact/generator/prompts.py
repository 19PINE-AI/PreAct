"""LLM prompts for the Model Generator.

Contains the system and user prompts used to compile interaction traces
into JSON state machine programs.
"""

SYSTEM_PROMPT_COMPILE = """You are a Model Generator for the PreAct system. Your job is to analyze an interaction trace (a sequence of CUA agent actions on a GUI) and compile it into a formal JSON state machine program.

The state machine you produce will be DIRECTLY EXECUTED — it is not code, it is a graph that an executor traverses. Each state must have verification criteria, and each transition must have an executable action.

## Output Format

Produce a JSON object with this exact structure:
{
  "metadata": {
    "task_description": "<what the task accomplishes>",
    "application_context": "<URL pattern or app identifier>",
    "initial_states": ["<prerequisite states>"],
    "parameters": ["<list of variable input names>"]
  },
  "states": [
    {
      "id": "<snake_case_unique_id>",
      "verification": {
        "type": "expect_element" | "data_available" | "terminal_state",
        "xpath": "<XPath to verify state — required for expect_element>",
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

1. **State Identification**: Each distinct UI state in the trace becomes a state node. Identify states by the presence of key UI elements (buttons, inputs, dialogs, etc.). Use the XPaths from the trace for verification.

2. **Initial State**: The FIRST state must represent the starting page (e.g., admin dashboard). Use a GENERIC verification xpath that matches any admin page, such as `//body[contains(@class,'adminhtml')]` or `//body`. The first transition should be the navigation action that goes to the target page. Do NOT use page-specific xpaths (like `//input[@name='detail']`) for the initial state — those elements don't exist on the starting page.

3. **Parameterization**: Any text that was typed and appears to be user-specific input (emails, names, search terms, messages) should be parameterized. Use `parameter_name` in action_type actions instead of literal text. Do NOT parameterize admin credentials (username/password) — they are handled by the browser auth system.

4. **State Verification**: Every non-terminal state must have an `expect_element` verification with a robust XPath. Use the XPaths observed in the trace. Set timeouts: 5000ms for the initial state, 3000ms for states after navigation or filter actions, 2000ms for states where elements are already present on the page.

5. **Transitions**: Map each action in the trace to a transition between states. Include wait actions where the trace shows page loads or UI transitions.

6. **Branching**: If the trace shows decision points (content inspection, conditional navigation), model them as branching transitions with conditions.

7. **Terminal State**: The last state should be a terminal state marking task completion.

8. **Robustness**: Prefer XPaths using id, name, aria-label, role, or data-testid attributes over positional selectors. Avoid fragile index-based XPaths like //input[1] when more specific alternatives exist (e.g., //input[@name='custname']). For radio buttons and checkboxes, use @value: //input[@value='medium']. For buttons, use text: //button[contains(text(), 'Submit')].

9. **NO Self-Loops**: NEVER create transitions where `from` and `to` are the same state. If multiple sequential actions happen on the same page, model each as a transition to a NEW distinct state (e.g., `page_username_entered`, `page_password_entered`). Self-loops cause the executor to get stuck in infinite loops.

10. **Compact Programs**: Produce the MINIMUM number of states needed. A good program for a 4-step trace should have ~5-6 states. Consolidate consecutive actions on the same page into adjacent states. Do NOT add unnecessary wait states — the executor handles page stabilization automatically.

11. **Skip Login/Auth**: Ignore any login or authentication steps in the trace (username, password, "Sign in" button clicks). The browser is pre-authenticated. Start the program from the first post-login action.

12. **Answer Extraction (CRITICAL)**: If the task asks a question or requests any value from the page (e.g., "what is…", "how many…", "find…", "which…", "name of…", "top 5", "list", "most recent", "compare", "identify", "view", "display", "report"), you MUST include exactly one `inspect_screenshot` (preferred) or `inspect_text` action as the transition INTO or immediately before the terminal state, with `store_result_as: "answer"`. Without this, the program cannot produce an answer during replay and the task will fail. The prompt MUST say "Return ONLY the raw value — no explanation, no full sentences." Do NOT wrap this behind an `evaluate_condition`. Do NOT add an `evaluate_condition` after the inspect action. Prefer `inspect_screenshot` (it sees the whole page) over `inspect_text` (element-scoped).

## Action Types

Each action MUST be a JSON object with a "type" field. NEVER use a string — always use the full object format.

- action_click: {"type": "action_click", "target": "<xpath>"}
- action_type: {"type": "action_type", "target": "<xpath>", "text": "<literal>" | "parameter_name": "<param>"}
- action_keypress: {"type": "action_keypress", "key": "<key>"}
- action_scroll: {"type": "action_scroll", "direction": "down|up", "amount": 3}
- action_navigate: {"type": "action_navigate", "text": "<url>"}
- wait: {"type": "wait", "ms": <milliseconds>}
- inspect_text: {"type": "inspect_text", "target": "<xpath>", "prompt": "<question>", "store_result_as": "<key>"} — The prompt MUST instruct: "Return ONLY the value, no explanation." Example: "What is the grand total? Return ONLY the dollar amount."
- inspect_screenshot: {"type": "inspect_screenshot", "target": "<xpath>", "prompt": "<question>", "store_result_as": "<key>"} — Same rule: prompt must request ONLY the raw value.
- evaluate_condition: {"type": "evaluate_condition", "expression": "<expr>", "store_result_as": "<key>"}
- conditional: {"type": "conditional", "condition": "<guard>"} — for branching transitions
"""

USER_PROMPT_COMPILE = """Analyze the following interaction trace and compile it into a JSON state machine program.

{trace_text}

Produce the JSON state machine. Remember:
- Every state needs verification criteria
- Parameterize user-specific inputs
- Use XPaths from the trace for verification and action targets
- Include wait transitions for page loads
- End with a terminal state"""

SYSTEM_PROMPT_EXTEND = """You are updating an existing JSON state machine program. A state verification failed during execution, and the CUA loop resolved the situation by performing additional actions. You must extend the existing state machine with new states and transitions to handle this scenario.

## Rules

1. **Monotonic Extension**: Only ADD new states and transitions. Never modify or remove existing ones.
2. **Branch Point**: The failed state becomes a branch point. Add a new path from it.
3. **Reconnection**: The new path should reconnect to an existing state in the graph when possible.
4. **Verification**: All new states need verification criteria.

## Output Format

Return a JSON object with:
{
  "new_states": [<list of new State objects>],
  "new_transitions": [<list of new Transition objects>]
}
"""

USER_PROMPT_EXTEND = """The state machine execution failed at state "{failed_state_id}" because: {failure_reason}

The CUA loop resolved it with these actions:
{resolution_trace}

Existing program states: {existing_states}

Produce the new states and transitions to add to the graph (monotonic extension only — do not modify existing states/transitions)."""
