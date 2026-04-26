"""T3A: Text-only Autonomous Agent for Android — ported to Pre-Act.

This is a faithful port of `android_world.agents.t3a.T3A` (Apache 2.0,
Copyright 2024 The android_world Authors) adapted to Pre-Act's HTTP
Android environment. The prompts (PROMPT_PREFIX, GUIDANCE,
ACTION_SELECTION_PROMPT_TEMPLATE, SUMMARIZATION_PROMPT_TEMPLATE) and the
step control flow (action-select -> execute -> summarize) are copied
VERBATIM from the official source so this agent is an apples-to-apples
SOTA baseline. The only substitutions are:

- `infer.LlmWrapper` -> Pre-Act's `LLMClient` (Claude Sonnet 4.6)
- `interface.AsyncEnv` -> Pre-Act's `AndroidEnvironment` (HTTP)
- `json_action.JSONAction.execute_action` -> equivalent call on Pre-Act env

Do not hand-edit prompts or control flow here; any drift breaks parity
with the official T3A baseline.
"""

from __future__ import annotations

import ast
import asyncio
import json
import logging
import re
from typing import Any, Optional

import os

from preact.platforms.android.environment import AndroidEnvironment

logger = logging.getLogger(__name__)


# CUA provider selection: "anthropic" (Claude) or "gemini" (Google).
# Default "gemini" reflects the 2026-04-23 swap to Gemini 3 Flash as the
# primary Android CUA backend (10× cheaper than Claude Sonnet 4.6 and
# matching-or-exceeding it on public AndroidWorld leaderboards). Set
# PREACT_CUA_PROVIDER=anthropic to reproduce the historical Claude datapoint.
#
# This is intentionally a *separate* env var from PREACT_MODEL (the compile/
# RAG model in preact.config.LLMConfig). Compile/RAG stays on Claude; only
# the CUA step-by-step calls move to Gemini.
_PROVIDER = os.environ.get("PREACT_CUA_PROVIDER", "gemini").lower()

if _PROVIDER == "anthropic":
    _DEFAULT_MODEL_FALLBACK = "claude-sonnet-4-6"
else:
    _DEFAULT_MODEL_FALLBACK = "gemini-3-flash-preview"

DEFAULT_MODEL = os.environ.get("PREACT_CUA_MODEL", _DEFAULT_MODEL_FALLBACK)
DEFAULT_TEMPERATURE = 0.0
DEFAULT_MAX_TOKENS = 1000

# Image-task stall cap: if the goal references image content and the UI does
# not change for this many consecutive actions, the agent is looping on
# zoom/tap gestures with no progress — force `status: infeasible` so the run
# terminates instead of timing out the step budget.
_IMAGE_NOOP_LIMIT = 4
_IMAGE_TASK_KEYWORDS = ("image", "gallery", "photo", "picture")

# Pre-Act runtime guardrails over the verbatim T3A baseline. Default on.
# Set PREACT_GUARDRAILS=off to disable for the vanilla-baseline AB
# experiment (Exp 3 in project_validation_plan_paper_grade.md). Disables:
#   1. Double-tap-before-input_text on populated fields (replace semantics)
#   2. Image-task no-op cap (forced infeasible after _IMAGE_NOOP_LIMIT)
#   3. Scroll-direction exhaustion notes appended to step summaries
_GUARDRAILS_ON = os.environ.get("PREACT_GUARDRAILS", "on").lower() != "off"


def _ui_hash(elements: list) -> str:
    """Cheap identity hash of a UI-element list — text + resource + bbox.
    Two calls that return the same hash describe the same visible screen."""
    parts = []
    for e in elements:
        parts.append((
            getattr(e, 'text', '') or '',
            getattr(e, 'content_description', '') or '',
            getattr(e, 'resource_name', '') or '',
            getattr(e, 'center_x', None),
            getattr(e, 'center_y', None),
        ))
    return str(hash(tuple(parts)))


# ─── Verbatim copy from android_world.agents.t3a ──────────────────────────

PROMPT_PREFIX = (
    'You are an agent who can operate an Android phone on behalf of a user.'
    " Based on user's goal/request, you may\n"
    '- Answer back if the request/goal is a question (or a chat message), like'
    ' user asks "What is my schedule for today?".\n'
    '- Complete some tasks described in the requests/goals by performing'
    ' actions (step by step) on the phone.\n\n'
    'When given a user request, you will try to complete it step by step. At'
    ' each step, a list of descriptions for most UI elements on the'
    ' current screen will be given to you (each element can be specified by an'
    ' index), together with a history of what you have done in previous steps.'
    ' Based on these pieces of information and the goal, you must choose to'
    ' perform one of the action in the following list (action description'
    ' followed by the JSON format) by outputing the action in the correct JSON'
    ' format.\n'
    '- If you think the task has been completed, finish the task by using the'
    ' status action with complete as goal_status:'
    ' `{{"action_type": "status", "goal_status": "complete"}}`\n'
    '- If you think the task is not'
    " feasible (including cases like you don't have enough information or can"
    ' not perform some necessary actions), finish by using the `status` action'
    ' with infeasible as goal_status:'
    ' `{{"action_type": "status", "goal_status": "infeasible"}}`\n'
    "- Answer user's question:"
    ' `{{"action_type": "answer", "text": "<answer_text>"}}`\n'
    '- Click/tap on a UI element (specified by its index) on the screen:'
    ' `{{"action_type": "click", "index": <target_index>}}`.\n'
    '- Long press on a UI element (specified by its index) on the screen:'
    ' `{{"action_type": "long_press", "index": <target_index>}}`.\n'
    '- Type text into an editable text field (specified by its index), this'
    ' action contains clicking the text field, typing in the text and pressing'
    ' the enter, so no need to click on the target field to start:'
    ' `{{"action_type": "input_text", "text": <text_input>, "index":'
    ' <target_index>}}`\n'
    '- Press the Enter key: `{{"action_type": "keyboard_enter"}}`\n'
    '- Navigate to the home screen: `{{"action_type": "navigate_home"}}`\n'
    '- Navigate back: `{{"action_type": "navigate_back"}}`\n'
    '- Scroll the screen or a scrollable UI element in one of the four'
    ' directions, use the same numeric index as above if you want to scroll a'
    ' specific UI element, leave it empty when scroll the whole screen:'
    ' `{{"action_type": "scroll", "direction": <up, down, left, right>,'
    ' "index": <optional_target_index>}}`\n'
    '- Open an app (nothing will happen if the app is not installed):'
    ' `{{"action_type": "open_app", "app_name": <name>}}`\n'
    '- Wait for the screen to update: `{{"action_type": "wait"}}`\n'
)

GUIDANCE = (
    'Here are some useful guidelines you need to follow:\n'
    'General\n'
    '- Usually there will be multiple ways to complete a task, pick the'
    ' easiest one. Also when something does not work as expected (due'
    ' to various reasons), sometimes a simple retry can solve the problem,'
    " but if it doesn't (you can see that from the history), try to"
    ' switch to other solutions.\n'
    '- Sometimes you may need to navigate the phone to gather information'
    ' needed to complete the task, for example if user asks'
    ' "what is my schedule tomorrow", then you may want to open the calendar'
    ' app (using the `open_app` action), look up information there, answer'
    " user's question (using the `answer` action) and finish (using"
    ' the `status` action with complete as goal_status).\n'
    '- For requests that are questions (or chat messages), remember to use'
    ' the `answer` action to reply to user explicitly before finish!'
    ' Merely displaying the answer on the screen is NOT sufficient (unless'
    ' the goal is something like "show me ...").\n'
    '- If the desired state is already achieved (e.g., enabling Wi-Fi when'
    " it's already on), you can just complete the task.\n"
    'Action Related\n'
    '- Use the `open_app` action whenever you want to open an app'
    ' (nothing will happen if the app is not installed), do not use the'
    ' app drawer to open an app unless all other ways have failed.\n'
    '- Use the `input_text` action whenever you want to type'
    ' something (including password) instead of clicking characters on the'
    ' keyboard one by one. Sometimes there is some default text in the text'
    ' field you want to type in, remember to delete them before typing.\n'
    '- For `click`, `long_press` and `input_text`, the index parameter you'
    ' pick must be VISIBLE in the screenshot and also in the UI element'
    ' list given to you (some elements in the list may NOT be visible on'
    ' the screen so you can not interact with them).\n'
    '- Consider exploring the screen by using the `scroll`'
    ' action with different directions to reveal additional content.\n'
    '- The direction parameter for the `scroll` action can be confusing'
    " sometimes as it's opposite to swipe, for example, to view content at the"
    ' bottom, the `scroll` direction should be set to "down". It has been'
    ' observed that you have difficulties in choosing the correct direction, so'
    ' if one does not work, try the opposite as well.\n'
    'Text Related Operations\n'
    '- Normally to select some text on the screen: <i> Enter text selection'
    ' mode by long pressing the area where the text is, then some of the words'
    ' near the long press point will be selected (highlighted with two pointers'
    ' indicating the range) and usually a text selection bar will also appear'
    ' with options like `copy`, `paste`, `select all`, etc.'
    ' <ii> Select the exact text you need. Usually the text selected from the'
    ' previous step is NOT the one you want, you need to adjust the'
    ' range by dragging the two pointers. If you want to select all text in'
    ' the text field, simply click the `select all` button in the bar.\n'
    "- At this point, you don't have the ability to drag something around the"
    ' screen, so in general you can not select arbitrary text.\n'
    '- To delete some text: the most traditional way is to place the cursor'
    ' at the right place and use the backspace button in the keyboard to'
    ' delete the characters one by one (can long press the backspace to'
    ' accelerate if there are many to delete). Another approach is to first'
    ' select the text you want to delete, then click the backspace button'
    ' in the keyboard.\n'
    '- To copy some text: first select the exact text you want to copy, which'
    ' usually also brings up the text selection bar, then click the `copy`'
    ' button in bar.\n'
    '- To paste text into a text box, first long press the'
    ' text box, then usually the text selection bar will appear with a'
    ' `paste` button in it.\n'
    '- When typing into a text field, sometimes an auto-complete dropdown'
    ' list will appear. This usually indicating this is a enum field and you'
    ' should try to select the best match by clicking the corresponding one'
    ' in the list.\n'
)

ACTION_SELECTION_PROMPT_TEMPLATE = (
    PROMPT_PREFIX
    + '\nThe current user goal/request is: {goal}'
    + '\n\nHere is a history of what you have done so far:\n{history}'
    + '\n\nHere is a list of descriptions for some UI elements on the current'
    ' screen:\n{ui_elements_description}\n'
    + GUIDANCE
    + '{additional_guidelines}'
    + '\n\nNow output an action from the above list in the correct JSON format,'
    ' following the reason why you do that. Your answer should look like:\n'
    'Reason: ...\nAction: {{"action_type":...}}\n\n'
    'Your Answer:\n'
)

SUMMARIZATION_PROMPT_TEMPLATE = (
    PROMPT_PREFIX
    + '\nThe (overall) user goal/request is:{goal}\n'
    'Now I want you to summerize the latest step based on the action you'
    ' pick with the reason and descriptions for the before and after (the'
    ' action) screenshots.\n'
    'Here is the description for the before'
    ' screenshot:\n{before_elements}\n'
    'Here is the description for the after screenshot:\n{after_elements}\n'
    'This is the action you picked: {action}\n'
    'Based on the reason: {reason}\n\n'
    '\nBy comparing the descriptions for the two screenshots and the action'
    ' performed, give a brief summary of this step.'
    ' This summary will be added to action history and used in future action'
    ' selection, so try to include essential information you think that will'
    ' be most useful for future action selection like'
    ' what you intended to do, why, if it worked as expected, if not'
    ' what might be the reason (be critical, the action/reason might not be'
    ' correct), what should/should not be done next and so on. Some more'
    ' rules/tips you should follow:\n'
    '- Keep it short and in one line.\n'
    "- Some actions (like `answer`, `wait`) don't involve screen change,"
    ' you can just assume they work as expected.\n'
    '- Given this summary will be added into action history, it can be used as'
    ' memory to include information that needs to be remembered, or shared'
    ' between different apps.\n\n'
    'Summary of this step: '
)


# ─── Verbatim copies of m3a_utils / agent_utils helpers ───────────────────

def _extract_json(s: str) -> Optional[dict[str, Any]]:
    """Verbatim copy of m3a_utils.extract_json."""
    pattern = r'\{.*?\}'
    match = re.search(pattern, s, re.DOTALL)
    if match:
        try:
            return ast.literal_eval(match.group())
        except (SyntaxError, ValueError) as error:
            logger.info('Cannot extract JSON, skipping due to error %s', error)
            return None
    else:
        logger.info('No JSON match in %s', s)
        return None


def _parse_reason_action_output(raw: str) -> tuple[Optional[str], Optional[str]]:
    """Verbatim copy of m3a_utils.parse_reason_action_output."""
    reason_result = re.search(r'Reason:(.*)Action:', raw, flags=re.DOTALL)
    reason = reason_result.group(1).strip() if reason_result else None
    action_result = re.search(r'Action:(.*)', raw, flags=re.DOTALL)
    action = action_result.group(1).strip() if action_result else None
    if action:
        extracted = _extract_json(action)
        if extracted is not None:
            action = json.dumps(extracted)
    return reason, action


# ─── UI element formatting (mirrors representation_utils.UIElement.__str__) ─

def _validate_ui_element(elem, screen_w: int, screen_h: int) -> bool:
    """Match m3a_utils.validate_ui_element semantics on Pre-Act's HTTPUIElement."""
    if elem.is_visible is False:
        return False
    x_min = elem.bbox_x_min
    x_max = elem.bbox_x_max
    y_min = elem.bbox_y_min
    y_max = elem.bbox_y_max
    if None not in (x_min, x_max, y_min, y_max):
        if (
            x_min >= x_max
            or x_min >= screen_w
            or x_max <= 0
            or y_min >= y_max
            or y_max <= 0
        ):
            return False
    return True


def _format_ui_element(elem) -> str:
    """Render an HTTPUIElement as a dataclass-like string (matches
    `str(representation_utils.UIElement)` field order closely enough for
    the LLM to read)."""
    fields = [
        ('text', elem.text),
        ('content_description', elem.content_description),
        ('class_name', elem.class_name),
        ('bbox_pixels',
         None if elem.bbox_x_min is None else
         f"BoundingBox(x_min={elem.bbox_x_min}, x_max={elem.bbox_x_max}, "
         f"y_min={elem.bbox_y_min}, y_max={elem.bbox_y_max})"),
        ('hint_text', elem.hint_text),
        ('is_checked', elem.is_checked),
        ('is_clickable', elem.is_clickable),
        ('is_editable', elem.is_editable),
        ('is_enabled', elem.is_enabled),
        ('is_focused', elem.is_focused),
        ('is_scrollable', elem.is_scrollable),
        ('is_visible', elem.is_visible),
        ('resource_name', elem.resource_name),
        ('tooltip', elem.tooltip),
    ]
    rendered = ', '.join(f'{k}={v!r}' for k, v in fields)
    return f'UIElement({rendered})'


def _generate_ui_elements_description_list_full(
    ui_elements, screen_w: int, screen_h: int
) -> str:
    """Verbatim algorithm of T3A._generate_ui_elements_description_list_full."""
    tree_info = ''
    for index, ui_element in enumerate(ui_elements):
        if _validate_ui_element(ui_element, screen_w, screen_h):
            tree_info += f'UI element {index}: {_format_ui_element(ui_element)}\n'
    return tree_info


def _element_info_from_ui_element(elem) -> dict:
    """Extract selector-friendly fields from an HTTPUIElement for the
    Pre-Act compiler (matches format_trace_for_compilation expectations)."""
    return {
        "resource_name": getattr(elem, "resource_name", None),
        "text": getattr(elem, "text", None),
        "content_description": getattr(elem, "content_description", None),
        "class_name": getattr(elem, "class_name", None),
        "hint_text": getattr(elem, "hint_text", None),
    }


def _action_selection_prompt(
    goal: str,
    history: list[str],
    ui_elements_description: str,
    additional_guidelines: Optional[list[str]] = None,
) -> str:
    """Verbatim copy of T3A._action_selection_prompt."""
    if history:
        history_text = '\n'.join(history)
    else:
        history_text = 'You just started, no action has been performed yet.'

    extra_guidelines = ''
    if additional_guidelines:
        extra_guidelines = 'For The Current Task:\n'
        for guideline in additional_guidelines:
            extra_guidelines += f'- {guideline}\n'

    return ACTION_SELECTION_PROMPT_TEMPLATE.format(
        history=history_text,
        goal=goal,
        ui_elements_description=ui_elements_description
        if ui_elements_description
        else 'Not available',
        additional_guidelines=extra_guidelines,
    )


def _summarize_prompt(
    goal: str,
    action: str,
    reason: str,
    before_elements: str,
    after_elements: str,
) -> str:
    """Verbatim copy of T3A._summarize_prompt."""
    return SUMMARIZATION_PROMPT_TEMPLATE.format(
        goal=goal,
        action=action,
        reason=reason,
        before_elements=before_elements if before_elements else 'Not available',
        after_elements=after_elements if after_elements else 'Not available',
    )


# ─── The agent ────────────────────────────────────────────────────────────

class T3ACUA:
    """Port of the official T3A agent, wired to Pre-Act's env and a
    pluggable LLM (Claude or Gemini).

    `run()` mirrors the outer while-loop of `android_world.run.py` around
    `T3A.step()`: loop up to `max_steps`, stop on an `AgentInteractionResult
    .done=True` (i.e. `status` action)."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        api_key: Optional[str] = None,
        provider: Optional[str] = None,
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.provider = (provider or _PROVIDER).lower()
        self.total_tokens = 0

        if self.provider == "anthropic":
            from anthropic import Anthropic
            self._client = Anthropic(
                api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
            )
        elif self.provider == "gemini":
            from google import genai
            self._client = genai.Client(
                api_key=api_key
                or os.environ.get("GEMINI_API_KEY")
                or os.environ.get("GOOGLE_API_KEY")
            )
        else:
            raise ValueError(f"unsupported PREACT_LLM_PROVIDER: {self.provider}")

    async def _predict(self, prompt: str) -> str:
        """Text-only LLM call. Dispatches by provider — Anthropic messages
        API or Gemini generate_content. Both return concatenated text; the
        T3A prompt already encodes JSON output format."""

        if self.provider == "anthropic":
            return await asyncio.to_thread(self._predict_anthropic, prompt)
        return await asyncio.to_thread(self._predict_gemini, prompt)

    def _predict_anthropic(self, prompt: str) -> str:
        resp = self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        usage = getattr(resp, "usage", None)
        if usage is not None:
            self.total_tokens += getattr(usage, "input_tokens", 0) or 0
            self.total_tokens += getattr(usage, "output_tokens", 0) or 0
        parts = []
        for block in resp.content:
            if getattr(block, "type", None) == "text":
                parts.append(getattr(block, "text", ""))
        return "".join(parts)

    def _predict_gemini(self, prompt: str) -> str:
        from google.genai import types as genai_types
        resp = self._client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                temperature=self.temperature,
                max_output_tokens=self.max_tokens,
            ),
        )
        usage = getattr(resp, "usage_metadata", None)
        if usage is not None:
            self.total_tokens += getattr(usage, "prompt_token_count", 0) or 0
            self.total_tokens += getattr(usage, "candidates_token_count", 0) or 0
        return resp.text or ""

    async def _execute_json_action(
        self, action_dict: dict, ui_elements: list
    ) -> None:
        """Translate a T3A JSONAction dict into the corresponding Pre-Act
        env call. Raises on unknown action types."""
        action_type = action_dict.get('action_type', '')
        idx = action_dict.get('index')

        if action_type == 'click':
            if idx is not None and 0 <= idx < len(ui_elements):
                elem = ui_elements[idx]
                if elem.center_x is not None:
                    self.env._exec_action(
                        {"action_type": "click",
                         "x": elem.center_x, "y": elem.center_y}
                    )
                    await asyncio.sleep(0.5)
                    return
            raise ValueError(f'click: bad index {idx}')

        if action_type == 'long_press':
            if idx is not None and 0 <= idx < len(ui_elements):
                elem = ui_elements[idx]
                self.env._exec_action(
                    {"action_type": "long_press",
                     "x": elem.center_x, "y": elem.center_y}
                )
                await asyncio.sleep(0.5)
                return
            raise ValueError(f'long_press: bad index {idx}')

        if action_type == 'input_text':
            text = action_dict.get('text', '')
            if idx is not None and 0 <= idx < len(ui_elements):
                elem = ui_elements[idx]
                if _GUARDRAILS_ON:
                    # Android's input_text APPENDS by default; tasks like
                    # Markor edit-content and contact-name update require
                    # REPLACEMENT. If the target field already has content,
                    # double-tap to select-word before `text` overwrites.
                    existing = (getattr(elem, 'text', None) or '').strip()
                    self.env._exec_action(
                        {"action_type": "click",
                         "x": elem.center_x, "y": elem.center_y}
                    )
                    await asyncio.sleep(0.3)
                    if existing:
                        for _ in range(2):
                            self.env._exec_action(
                                {"action_type": "click",
                                 "x": elem.center_x, "y": elem.center_y}
                            )
                            await asyncio.sleep(0.08)
                    self.env._exec_action(
                        {"action_type": "input_text", "text": text}
                    )
                    self.env._exec_action({"action_type": "keyboard_enter"})
                    await asyncio.sleep(0.3)
                else:
                    # Vanilla T3A: input_text appends; no clear, no double-tap.
                    self.env._exec_action(
                        {"action_type": "input_text", "text": text,
                         "index": idx}
                    )
                    await asyncio.sleep(0.2)
                return
            raise ValueError(f'input_text: bad index {idx}')

        if action_type == 'keyboard_enter':
            self.env._exec_action({"action_type": "keyboard_enter"})
            await asyncio.sleep(0.2)
            return

        if action_type == 'navigate_home':
            self.env._exec_action({"action_type": "navigate_home"})
            await asyncio.sleep(0.3)
            return

        if action_type == 'navigate_back':
            self.env._exec_action({"action_type": "navigate_back"})
            await asyncio.sleep(0.3)
            return

        if action_type == 'scroll':
            direction = action_dict.get('direction', 'down')
            payload = {"action_type": "scroll", "direction": direction}
            if idx is not None and 0 <= idx < len(ui_elements):
                elem = ui_elements[idx]
                payload["x"] = elem.center_x
                payload["y"] = elem.center_y
            self.env._exec_action(payload)
            await asyncio.sleep(0.5)
            return

        if action_type == 'open_app':
            self.env._exec_action(
                {"action_type": "open_app",
                 "app_name": action_dict.get('app_name', '')}
            )
            await asyncio.sleep(1.0)
            return

        if action_type == 'wait':
            await asyncio.sleep(1.0)
            return

        raise ValueError(f'unsupported action_type: {action_type}')

    async def run(
        self,
        goal: str,
        env: AndroidEnvironment,
        max_steps: int = 15,
        additional_guidelines: Optional[list[str]] = None,
    ) -> dict:
        """Run T3A on `env` for `goal`. Returns a result dict with keys:
        success, answer, step_count, step_data, error."""
        self.env = env
        history: list[dict] = []
        step_data_out: list[dict] = []
        answer: str = ""
        noop_streak = 0
        is_image_task = any(
            kw in goal.lower() for kw in _IMAGE_TASK_KEYWORDS
        )
        exhausted_scroll_dirs: set[str] = set()

        for step_idx in range(max_steps):
            # Fetch fresh screen state.
            _, ui_elements = env._get_state()
            screen_w = getattr(env, '_screen_width', 1080) or 1080
            screen_h = getattr(env, '_screen_height', 2400) or 2400

            before_elements = _generate_ui_elements_description_list_full(
                ui_elements, screen_w, screen_h
            )
            prompt = _action_selection_prompt(
                goal,
                [f'Step {i + 1}: {h["summary"]}' for i, h in enumerate(history)],
                before_elements,
                additional_guidelines,
            )

            try:
                action_output = await self._predict(prompt)
            except Exception as e:
                logger.warning('T3A predict failed: %s', e)
                return {
                    'success': False,
                    'answer': answer,
                    'step_count': step_idx,
                    'step_data': step_data_out,
                    'error': f'predict error: {e}',
                }

            reason, action_str = _parse_reason_action_output(action_output)
            logger.info('T3A step %d reason=%s action=%s', step_idx, (reason or '')[:160], (action_str or '')[:200])

            step_record = {
                'action_prompt': prompt,
                'action_output': action_output,
                'action': {},  # compiler reads this as a dict; filled in below
                'raw_action': action_str,
                'reason': reason,
                'element_info': {},
            }

            if not reason or not action_str:
                summary = (
                    'Output for action selection is not in the correct format, so no'
                    ' action is performed.'
                )
                step_record['summary'] = summary
                history.append(step_record)
                step_data_out.append(step_record)
                continue

            action_dict = _extract_json(action_str)
            if action_dict is None:
                summary = (
                    'Can not parse the output to a valid action. Please make sure to'
                    ' pick the action from the list with the correct json format!'
                )
                step_record['summary'] = summary
                history.append(step_record)
                step_data_out.append(step_record)
                continue

            # Compile-ready: action as dict, element_info from ui_elements[idx].
            step_record['action'] = action_dict
            action_type = action_dict.get('action_type', '')
            idx = action_dict.get('index')
            if (
                action_type in ('click', 'long_press', 'input_text', 'scroll')
                and idx is not None
                and 0 <= idx < len(ui_elements)
            ):
                step_record['element_info'] = _element_info_from_ui_element(
                    ui_elements[idx]
                )

            # Index out-of-range check (matches official T3A).
            if action_type in ('click', 'long_press', 'input_text'):
                if idx is not None and idx >= len(ui_elements):
                    summary = (
                        'The parameter index is out of range. Remember the index must'
                        ' be in the UI element list!'
                    )
                    step_record['summary'] = summary
                    history.append(step_record)
                    step_data_out.append(step_record)
                    continue

            # Terminal: status
            if action_type == 'status':
                step_record['summary'] = 'Agent thinks the request has been completed.'
                history.append(step_record)
                step_data_out.append(step_record)
                return {
                    'success': action_dict.get('goal_status') == 'complete',
                    'answer': answer,
                    'step_count': step_idx + 1,
                    'step_data': step_data_out,
                    'error': None if action_dict.get('goal_status') == 'complete'
                    else 'Agent declared infeasible',
                }

            # Answer: record and continue (NOT terminal by itself per T3A).
            if action_type == 'answer':
                answer = action_dict.get('text', '')

            # Execute the action (skip for answer since it's a no-op on env).
            if action_type != 'answer':
                try:
                    await self._execute_json_action(action_dict, ui_elements)
                except Exception as e:
                    logger.warning('Action execution failed: %s', e)
                    step_record['summary'] = (
                        f'Some error happened executing the action {action_type}'
                    )
                    history.append(step_record)
                    step_data_out.append(step_record)
                    continue

            # Post-transition state + summarization.
            _, after_ui_elements = env._get_state()
            after_elements = _generate_ui_elements_description_list_full(
                after_ui_elements, screen_w, screen_h
            )

            # No-op detection: same UI hash before and after = the action did
            # not change visible state. Three code-level consequences:
            #   (a) Scroll in a direction whose elements are unchanged marks
            #       that direction as exhausted — the LLM is told explicitly
            #       via the step summary so it stops looping.
            #   (b) For image-like goals, N consecutive no-op actions force
            #       `status: infeasible` — galleries without OCR and raster
            #       images in viewers will never expose their text as UI.
            #   (c) `noop_streak` is reset the moment any action produces a
            #       change, so transient stalls don't cause false infeasibles.
            # `answer` is intentionally a no-op on the env (the agent is
            # producing output, not acting). Don't count it toward the
            # image-task no-op cap — otherwise 4 consecutive correct answers
            # on a gallery QA task would force a false `infeasible`.
            noop = (
                action_type != 'answer'
                and _ui_hash(ui_elements) == _ui_hash(after_ui_elements)
            )
            scroll_note = ''
            if noop:
                noop_streak += 1
                if _GUARDRAILS_ON and action_type == 'scroll':
                    direction = action_dict.get('direction', 'down')
                    exhausted_scroll_dirs.add(direction)
                    scroll_note = (
                        f' NOTE: scroll {direction} produced NO change in UI '
                        f'elements — this direction is exhausted. Do NOT repeat '
                        f'scroll {direction}; try a different approach.'
                    )
            elif action_type != 'answer':
                noop_streak = 0

            if _GUARDRAILS_ON and is_image_task and noop_streak >= _IMAGE_NOOP_LIMIT:
                logger.info(
                    'T3A image-task no-op cap hit (%d consecutive) — '
                    'forcing status: infeasible', noop_streak,
                )
                step_record['summary'] = (
                    f'Forced infeasible: {_IMAGE_NOOP_LIMIT} consecutive '
                    'actions produced no UI change on image-content task.'
                )
                history.append(step_record)
                step_data_out.append(step_record)
                return {
                    'success': False,
                    'answer': answer,
                    'step_count': step_idx + 1,
                    'step_data': step_data_out,
                    'error': 'Forced infeasible after image-task no-op cap',
                }

            summary_prompt = _summarize_prompt(
                goal, action_str, reason or '', before_elements, after_elements
            )
            try:
                summary_raw = await self._predict(summary_prompt)
            except Exception as e:
                logger.warning('Summary predict failed: %s', e)
                summary_raw = ''

            step_record['summary'] = (
                f'Action selected: {action_str}. {summary_raw}{scroll_note}'
                if summary_raw
                else f'Error calling LLM in summerization phase.{scroll_note}'
            )
            history.append(step_record)
            step_data_out.append(step_record)

        return {
            'success': False,
            'answer': answer,
            'step_count': max_steps,
            'step_data': step_data_out,
            'error': 'Max steps reached',
        }


# Backwards-compat alias: historical callers imported `T3AClaudeCUA`.
T3AClaudeCUA = T3ACUA
