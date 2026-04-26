"""OSWorld CUA backend — thin wrapper around the official AnthropicAgent.

For apples-to-apples SOTA parity, Pre-Act delegates the CUA loop to the
*same* `mm_agents.anthropic.main.AnthropicAgent` used by the official
OSWorld runner `scripts/python/run_multienv_claude.py`. Parameters and
prompts are the official defaults; this file only adapts the call
surface to Pre-Act's `env.desktop_env`/`OSTaskResult` types and tracks
token usage.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import sys
from typing import Any, Optional

from preact.platforms.osworld.environment import OSWorldEnvironment

logger = logging.getLogger(__name__)


# Make the official OSWorld package importable.
_OSWORLD_PATH = os.environ.get("OSWORLD_PATH", os.path.expanduser("~/OSWorld"))
if _OSWORLD_PATH not in sys.path:
    sys.path.insert(0, _OSWORLD_PATH)

from mm_agents.anthropic import main as _mm_main  # noqa: E402
from mm_agents.anthropic.main import AnthropicAgent  # noqa: E402
from mm_agents.anthropic.utils import APIProvider  # noqa: E402


# Token accounting: the official AnthropicAgent does not expose usage,
# so wrap the Anthropic client class it imports and accumulate per-call
# usage into a module-level counter that we reset per run.
_TOKEN_ACCUM = {"input": 0, "output": 0}


def _install_token_tracking():
    """Patch the class-level `beta.messages.create` so every Anthropic
    client (including those returned by `.with_options(...)`) accumulates
    usage tokens into `_TOKEN_ACCUM`."""
    try:
        from anthropic.resources.beta.messages.messages import Messages as _BetaMessages  # type: ignore
    except Exception:
        try:
            from anthropic.resources.beta.messages import Messages as _BetaMessages  # type: ignore
        except Exception:
            logger.warning("Could not locate Anthropic BetaMessages class for token tracking.")
            return

    if getattr(_BetaMessages, "_preact_tokens_wrapped", False):
        return

    orig_create = _BetaMessages.create

    def create_with_tokens(self, *args, **kwargs):
        resp = orig_create(self, *args, **kwargs)
        usage = getattr(resp, "usage", None)
        if usage is not None:
            _TOKEN_ACCUM["input"] += getattr(usage, "input_tokens", 0) or 0
            _TOKEN_ACCUM["output"] += getattr(usage, "output_tokens", 0) or 0
        return resp

    _BetaMessages.create = create_with_tokens  # type: ignore[assignment]
    _BetaMessages._preact_tokens_wrapped = True  # type: ignore[attr-defined]


_install_token_tracking()


DEFAULT_MODEL = "claude-sonnet-4-6"
SCREEN_SIZE = (1920, 1080)


# First pyautogui call in a command string like "pyautogui.click(123, 456)\n..."
_PYAUTOGUI_COORD_RE = re.compile(r"pyautogui\.\w+\((\d+)\s*,\s*(\d+)")


def _semantic_action_string(name: str, input_dict: Optional[dict]) -> str:
    """Render a short action label for the compiler: click(1234,567),
    type(text='hello'), key(text='enter'), etc. format_os_trace truncates
    to 100 chars, so keep it compact."""
    if not isinstance(input_dict, dict):
        return name or ""
    parts = []
    coord = input_dict.get("coordinate")
    if isinstance(coord, (list, tuple)) and len(coord) == 2:
        parts.append(f"{coord[0]},{coord[1]}")
    text = input_dict.get("text")
    if text:
        parts.append(f"text={text!r}")
    direction = input_dict.get("scroll_direction")
    if direction:
        parts.append(f"dir={direction}")
    return f"{name}({', '.join(parts)})" if parts else name


def _element_info_from_action(
    input_dict: Optional[dict], command: str,
    a11y_elements: Optional[list[dict]] = None,
) -> dict:
    """Emit a selector-shaped dict for format_os_trace.

    - x/y come from the pyautogui command (screen-size scale) when present,
      else from the input_dict coordinate (base 1280x720 scale).
    - name/role are looked up from the a11y elements list: the first
      element whose bbox contains (x, y) and that has a non-empty name.
      This is critical for RPA replay — without real a11y name/role,
      the compiler invents selectors that won't match the live tree.
    """
    info: dict = {"name": None, "role": None, "x": None, "y": None}
    if command:
        m = _PYAUTOGUI_COORD_RE.search(command)
        if m:
            info["x"], info["y"] = int(m.group(1)), int(m.group(2))
    if info["x"] is None and isinstance(input_dict, dict):
        coord = input_dict.get("coordinate")
        if isinstance(coord, (list, tuple)) and len(coord) == 2:
            info["x"], info["y"] = coord[0], coord[1]

    if a11y_elements and info["x"] is not None:
        match = _lookup_element_at(a11y_elements, info["x"], info["y"])
        if match:
            name = (match.get("name") or "").strip()
            text = (match.get("text") or "").strip()
            desc = (match.get("description") or "").strip()
            info["name"] = name or text[:80] or desc[:80] or None
            info["role"] = (match.get("role") or "").strip() or None
    return info


def _lookup_element_at(elements: list[dict], x: int, y: int) -> Optional[dict]:
    """Find the smallest on-screen a11y element whose bbox contains (x, y)
    and that has an identifying name/text/description.

    Picks the smallest containing element so leaf nodes (buttons, text
    fields) win over ancestor containers (frames, panels).
    """
    best: Optional[dict] = None
    best_area: int = 1 << 30
    for el in elements:
        ex = el.get("x", 0) or 0
        ey = el.get("y", 0) or 0
        ew = el.get("width", 0) or 0
        eh = el.get("height", 0) or 0
        if ew <= 0 or eh <= 0:
            continue
        if not (ex <= x <= ex + ew and ey <= y <= ey + eh):
            continue
        if not (el.get("name") or el.get("text") or el.get("description")):
            continue
        area = ew * eh
        if area < best_area:
            best = el
            best_area = area
    return best


class ClaudeComputerUseCUA:
    """Wraps the official OSWorld AnthropicAgent with the exact SOTA config.

    Matches `run_multienv_claude.py`: `provider=APIProvider.ANTHROPIC`,
    `action_space="claude_computer_use"`, 10-image history, thinking
    enabled, default system prompt.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        screen_size: tuple[int, int] = SCREEN_SIZE,
        only_n_most_recent_images: int = 10,
        max_tokens: int = 4096,
    ):
        self.model = model
        self.screen_size = screen_size
        self.only_n_most_recent_images = only_n_most_recent_images
        self.max_tokens = max_tokens
        self.total_tokens = 0

    async def run(
        self,
        instruction: str,
        env: OSWorldEnvironment,
        max_steps: int = 15,
    ) -> Any:
        """Run the official CUA loop. Returns OSTaskResult."""
        from preact.platforms.osworld.agent import OSTaskResult

        desktop_env = env.desktop_env
        # Snapshot the global token counter; diff it at the end to get
        # this run's usage only.
        start_input = _TOKEN_ACCUM["input"]
        start_output = _TOKEN_ACCUM["output"]

        # Construct the official agent with identical defaults to
        # run_multienv_claude.py (ANTHROPIC provider, not BEDROCK).
        agent = AnthropicAgent(
            platform="Ubuntu",
            model=self.model,
            provider=APIProvider.ANTHROPIC,
            max_tokens=self.max_tokens,
            only_n_most_recent_images=self.only_n_most_recent_images,
            action_space="claude_computer_use",
            screen_size=self.screen_size,
            no_thinking=False,
            use_isp=False,
            temperature=None,
            top_p=None,
        )
        agent.reset(logger, vm_ip=getattr(desktop_env, "vm_ip", None))

        # Initial observation — env has already been reset by the caller.
        obs = await asyncio.to_thread(desktop_env._get_obs)

        # Pre-fetch a11y elements once per step from the PreAct env wrapper
        # so we can populate element_info.name/role at selector-building
        # time — without real a11y names, the compiler invents role/name
        # pairs that don't match the live tree at replay verification.
        def _fetch_a11y() -> list[dict]:
            try:
                return env._get_a11y_elements() or []
            except Exception as e:
                logger.debug("a11y fetch failed: %s", e)
                return []

        a11y_elements = await asyncio.to_thread(_fetch_a11y)

        step_data: list[dict] = []
        actions_executed = 0
        done = False
        terminal: Optional[str] = None  # "DONE" | "FAIL"

        for step_idx in range(max_steps):
            if done:
                break

            try:
                response, actions = await asyncio.to_thread(
                    agent.predict, instruction, obs
                )
            except Exception as e:
                logger.warning("AnthropicAgent.predict failed: %s", e)
                return OSTaskResult(
                    success=False,
                    mode="cua",
                    actions_executed=actions_executed,
                    actions_via_cua=actions_executed,
                    step_data=step_data,
                    error=f"predict error: {e}",
                )

            if actions is None:
                return OSTaskResult(
                    success=False,
                    mode="cua",
                    actions_executed=actions_executed,
                    actions_via_cua=actions_executed,
                    step_data=step_data,
                    error="Anthropic API failure",
                )

            for action in actions:
                action_type = (
                    action.get("action_type", "") if isinstance(action, dict) else ""
                )
                input_dict = action.get("input") if isinstance(action, dict) else None
                action_name = ""
                if isinstance(input_dict, dict):
                    action_name = input_dict.get("action", "")

                command = action.get("command", "") if isinstance(action, dict) else ""
                semantic = _semantic_action_string(action_name or action_type, input_dict)
                element_info = _element_info_from_action(
                    input_dict, command, a11y_elements=a11y_elements
                )

                step_data.append(
                    {
                        "action": semantic,
                        "command": command,
                        "element_info": element_info,
                    }
                )

                obs, reward, done, info = await asyncio.to_thread(
                    desktop_env.step, action, 0.0
                )

                # Refresh a11y elements after each step so subsequent
                # clicks in this batch (e.g. menu-item after menu-open)
                # resolve against the updated tree.
                a11y_elements = await asyncio.to_thread(_fetch_a11y)

                if action_type not in ("DONE", "FAIL", "WAIT") and action_name not in (
                    "done",
                    "fail",
                    "call_user",
                ):
                    actions_executed += 1

                if action_type == "DONE" or action_name == "done":
                    terminal = "DONE"
                elif action_type == "FAIL" or action_name in ("fail", "call_user"):
                    terminal = "FAIL"

                if done:
                    break

        self.total_tokens = (
            (_TOKEN_ACCUM["input"] - start_input)
            + (_TOKEN_ACCUM["output"] - start_output)
        )

        if terminal == "DONE":
            return OSTaskResult(
                success=True,
                mode="cua",
                actions_executed=actions_executed,
                actions_via_cua=actions_executed,
                step_data=step_data,
            )
        if terminal == "FAIL":
            return OSTaskResult(
                success=False,
                mode="cua",
                actions_executed=actions_executed,
                actions_via_cua=actions_executed,
                step_data=step_data,
                error="Agent emitted FAIL",
            )
        return OSTaskResult(
            success=False,
            mode="cua",
            actions_executed=actions_executed,
            actions_via_cua=actions_executed,
            step_data=step_data,
            error="Max steps reached",
        )
