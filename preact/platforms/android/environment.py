"""Android environment adapter for PreAct.

Implements the ComputerEnvironment protocol using AndroidWorld's AsyncEnv,
translating element selectors from PreAct's format to Android accessibility
tree lookups.

Selector Format:
  resource_id=com.app:id/name
  text=Settings
  class=android.widget.Button
  content_desc=Navigate up
  hint=Search
  Multiple: class=EditText&&hint=Name
  Index: index=5
"""

from __future__ import annotations

import asyncio
import io
import logging
import re
import time
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)


def _parse_selector(selector: str) -> dict[str, str]:
    """Parse a PreAct element selector into attribute key-value pairs.

    Supports formats:
      resource_id=com.app:id/name
      text=OK&&class=Button
      index=5
    """
    parts = selector.split("&&")
    attrs = {}
    for part in parts:
        part = part.strip()
        if "=" in part:
            key, value = part.split("=", 1)
            attrs[key.strip()] = value.strip()
    return attrs


def _element_matches(element, attrs: dict[str, str]) -> bool:
    """Check if a UIElement matches the given selector attributes."""
    for key, value in attrs.items():
        if key == "resource_id" or key == "resource_name":
            elem_val = element.resource_name or element.resource_id or ""
            if value not in (elem_val or ""):
                return False
        elif key == "text":
            elem_text = element.text or ""
            if value.lower() not in elem_text.lower():
                return False
        elif key == "class":
            elem_class = element.class_name or ""
            # Allow partial match (e.g., "EditText" matches "android.widget.EditText")
            if value.lower() not in elem_class.lower():
                return False
        elif key == "content_desc":
            elem_desc = element.content_description or ""
            if value.lower() not in elem_desc.lower():
                return False
        elif key == "hint":
            elem_hint = element.hint_text or ""
            if value.lower() not in elem_hint.lower():
                return False
        elif key == "index":
            # Index-based match handled separately
            pass
        elif key == "package":
            elem_pkg = element.package_name or ""
            if value not in elem_pkg:
                return False
        elif key == "checked":
            if str(element.is_checked).lower() != value.lower():
                return False
        else:
            # Unknown attribute, skip
            pass
    return True


def _find_element_index(
    ui_elements: list,
    selector: str,
) -> Optional[int]:
    """Find the index of the first UI element matching the selector."""
    attrs = _parse_selector(selector)

    # Direct index reference
    if "index" in attrs and len(attrs) == 1:
        idx = int(attrs["index"])
        if 0 <= idx < len(ui_elements):
            return idx
        return None

    for i, elem in enumerate(ui_elements):
        if _element_matches(elem, attrs):
            return i

    return None


def _find_all_element_indices(
    ui_elements: list,
    selector: str,
) -> list[int]:
    """Find all UI element indices matching the selector."""
    attrs = _parse_selector(selector)
    indices = []
    for i, elem in enumerate(ui_elements):
        if _element_matches(elem, attrs):
            indices.append(i)
    return indices


def _element_to_dict(element, index: int) -> dict[str, Any]:
    """Convert a UIElement to a dictionary for PreAct compatibility."""
    d = {
        "index": index,
        "text": element.text or "",
        "content_description": element.content_description or "",
        "class_name": element.class_name or "",
        "resource_name": element.resource_name or "",
        "hint_text": element.hint_text or "",
        "is_clickable": element.is_clickable,
        "is_editable": element.is_editable,
        "is_scrollable": element.is_scrollable,
        "is_enabled": element.is_enabled,
        "is_visible": element.is_visible,
        "package_name": element.package_name or "",
    }
    if element.bbox_pixels:
        d["bounds"] = {
            "left": element.bbox_pixels.x_min,
            "right": element.bbox_pixels.x_max,
            "top": element.bbox_pixels.y_min,
            "bottom": element.bbox_pixels.y_max,
        }
    return d


def _ui_elements_to_text(ui_elements: list) -> str:
    """Convert UI elements list to a text description for the LLM."""
    lines = []
    for i, elem in enumerate(ui_elements):
        parts = [f"[{i}]"]
        if elem.class_name:
            short_class = elem.class_name.split(".")[-1]
            parts.append(short_class)
        if elem.text:
            parts.append(f'text="{elem.text}"')
        if elem.content_description:
            parts.append(f'desc="{elem.content_description}"')
        if elem.hint_text:
            parts.append(f'hint="{elem.hint_text}"')
        if elem.resource_name:
            # Shorten resource ID
            short_res = elem.resource_name.split("/")[-1] if "/" in (elem.resource_name or "") else elem.resource_name
            parts.append(f"id={short_res}")
        flags = []
        if elem.is_clickable:
            flags.append("clickable")
        if elem.is_editable:
            flags.append("editable")
        if elem.is_scrollable:
            flags.append("scrollable")
        if elem.is_checked:
            flags.append("checked")
        if flags:
            parts.append(f"[{','.join(flags)}]")
        lines.append(" ".join(parts))
    return "\n".join(lines)


class AndroidEnvironment:
    """PreAct ComputerEnvironment adapter for AndroidWorld.

    Wraps AndroidWorld's AsyncEnv to implement the interface needed by
    PreAct's executor, CUA loop, and recorder.
    """

    def __init__(self, android_env):
        """Initialize with an AndroidWorld AsyncEnv instance.

        Args:
            android_env: An instance of android_world.env.interface.AsyncEnv
        """
        self._env = android_env
        self._last_state = None
        self._last_screenshot_bytes = None

    @property
    def android_env(self):
        """Access the underlying AndroidWorld environment."""
        return self._env

    def _get_state(self, wait_stable: bool = False):
        """Get current Android state (screenshot + UI elements)."""
        state = self._env.get_state(wait_to_stabilize=wait_stable)
        self._last_state = state
        return state

    def _get_ui_elements(self) -> list:
        """Get current UI elements from accessibility tree."""
        if self._last_state is None:
            self._get_state()
        return self._last_state.ui_elements

    def _pixels_to_png(self, pixels: np.ndarray) -> bytes:
        """Convert numpy pixel array to PNG bytes."""
        try:
            from PIL import Image
            img = Image.fromarray(pixels)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
        except ImportError:
            # Fallback using cv2
            import cv2
            success, encoded = cv2.imencode(".png", cv2.cvtColor(pixels, cv2.COLOR_RGB2BGR))
            return encoded.tobytes() if success else b""

    # ─── Lifecycle ────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Initialize (env is already started by AndroidWorld)."""
        self._get_state(wait_stable=True)

    async def stop(self) -> None:
        """Stop the environment."""
        pass  # Lifecycle managed by AndroidWorld

    async def reset(self) -> None:
        """Reset to home screen."""
        self._env.reset(go_home=True)
        self._last_state = None
        self._last_screenshot_bytes = None

    # ─── Observation ──────────────────────────────────────────────────────

    async def screenshot(self) -> bytes:
        """Capture screenshot as PNG bytes."""
        state = self._get_state()
        png_bytes = self._pixels_to_png(state.pixels)
        self._last_screenshot_bytes = png_bytes
        return png_bytes

    async def element_screenshot(self, selector: str) -> bytes:
        """Capture screenshot of element area."""
        # For Android, we crop the full screenshot to the element bounds
        state = self._get_state()
        idx = _find_element_index(state.ui_elements, selector)
        if idx is None:
            return await self.screenshot()
        elem = state.ui_elements[idx]
        if elem.bbox_pixels is None:
            return await self.screenshot()

        pixels = state.pixels
        top = max(0, int(elem.bbox_pixels.y_min))
        bottom = min(pixels.shape[0], int(elem.bbox_pixels.y_max))
        left = max(0, int(elem.bbox_pixels.x_min))
        right = min(pixels.shape[1], int(elem.bbox_pixels.x_max))
        cropped = pixels[top:bottom, left:right]
        return self._pixels_to_png(cropped)

    async def element_exists(self, selector: str, timeout_ms: int = 5000) -> bool:
        """Check if element matching selector exists in accessibility tree."""
        deadline = time.time() + timeout_ms / 1000.0
        poll_interval = 0.3

        while True:
            state = self._get_state()
            idx = _find_element_index(state.ui_elements, selector)
            if idx is not None:
                return True
            if time.time() >= deadline:
                return False
            await asyncio.sleep(poll_interval)

    async def element_text(self, selector: str) -> str:
        """Get text content of element."""
        state = self._get_state()
        idx = _find_element_index(state.ui_elements, selector)
        if idx is None:
            return ""
        elem = state.ui_elements[idx]
        return elem.text or elem.content_description or ""

    async def element_attribute(self, selector: str, attribute: str) -> Optional[str]:
        """Get attribute of element."""
        state = self._get_state()
        idx = _find_element_index(state.ui_elements, selector)
        if idx is None:
            return None
        elem = state.ui_elements[idx]
        return getattr(elem, attribute, None)

    async def get_page_url(self) -> str:
        """Get current activity name (Android equivalent of URL)."""
        return self._env.foreground_activity_name

    async def get_page_title(self) -> str:
        """Get current activity name."""
        return self._env.foreground_activity_name

    async def get_dom_snapshot(self) -> str:
        """Get UI element list as text (Android equivalent of DOM)."""
        state = self._get_state()
        return _ui_elements_to_text(state.ui_elements)

    # ─── Actions ──────────────────────────────────────────────────────────

    async def click(self, selector: str) -> None:
        """Click on element matching selector.

        Raises ValueError if neither an element match nor parseable coords
        can be derived from the selector — silent no-ops mislead the CUA loop.
        """
        from android_world.env.json_action import JSONAction
        state = self._get_state()
        idx = _find_element_index(state.ui_elements, selector)
        if idx is not None:
            action = JSONAction(action_type="click", index=idx)
        else:
            # Fallback: try coordinate-based click
            coords = self._parse_coordinates(selector)
            if coords:
                action = JSONAction(action_type="click", x=coords[0], y=coords[1])
            else:
                raise ValueError(
                    f"click: element not found and no parseable coords: {selector}"
                )
        self._env.execute_action(action)
        await asyncio.sleep(0.5)
        self._last_state = None

    async def double_click(self, selector: str) -> None:
        """Double tap on element."""
        from android_world.env.json_action import JSONAction
        state = self._get_state()
        idx = _find_element_index(state.ui_elements, selector)
        if idx is not None:
            action = JSONAction(action_type="double_tap", index=idx)
            self._env.execute_action(action)
            await asyncio.sleep(0.5)
            self._last_state = None

    async def right_click(self, selector: str) -> None:
        """Long press (Android equivalent of right-click)."""
        from android_world.env.json_action import JSONAction
        state = self._get_state()
        idx = _find_element_index(state.ui_elements, selector)
        if idx is not None:
            action = JSONAction(action_type="long_press", index=idx)
            self._env.execute_action(action)
            await asyncio.sleep(0.5)
            self._last_state = None

    async def type_text(self, selector: str, text: str) -> None:
        """Type text into element.

        If the selector is empty, types into the currently focused field
        (legacy behaviour). Otherwise requires either an element match or
        parseable coords — raises if neither is available.
        """
        from android_world.env.json_action import JSONAction
        state = self._get_state()
        idx = _find_element_index(state.ui_elements, selector)
        if idx is not None:
            action = JSONAction(action_type="input_text", index=idx, text=text)
            self._env.execute_action(action)
            await asyncio.sleep(0.5)
            self._last_state = None
            return

        coords = self._parse_coordinates(selector)
        if coords:
            self._env.execute_action(
                JSONAction(action_type="click", x=coords[0], y=coords[1])
            )
            await asyncio.sleep(0.3)
            self._env.execute_action(
                JSONAction(action_type="input_text", text=text)
            )
            await asyncio.sleep(0.3)
            self._last_state = None
            return

        if selector == "":
            # Type into currently focused field
            self._env.execute_action(JSONAction(action_type="input_text", text=text))
            await asyncio.sleep(0.3)
            self._last_state = None
            return

        raise ValueError(
            f"type_text: element not found and no parseable coords: {selector}"
        )

    async def clear_and_type(self, selector: str, text: str) -> None:
        """Clear field and type new text."""
        from android_world.env.json_action import JSONAction
        state = self._get_state()
        idx = _find_element_index(state.ui_elements, selector)
        if idx is not None:
            action = JSONAction(
                action_type="input_text", index=idx, text=text, clear_text=True
            )
            self._env.execute_action(action)
            await asyncio.sleep(0.5)
            self._last_state = None

    async def press_key(self, key: str) -> None:
        """Press a key."""
        from android_world.env.json_action import JSONAction
        key_lower = key.lower()
        if key_lower in ("enter", "return"):
            action = JSONAction(action_type="keyboard_enter")
        elif key_lower in ("back", "escape"):
            action = JSONAction(action_type="navigate_back")
        elif key_lower in ("home",):
            action = JSONAction(action_type="navigate_home")
        else:
            # Map to Android keycode
            keycode = f"KEYCODE_{key.upper()}"
            action = JSONAction(action_type="click", keycode=keycode)
        self._env.execute_action(action)
        await asyncio.sleep(0.3)
        self._last_state = None

    async def key_combo(self, keys: str) -> None:
        """Press key combination (limited on Android)."""
        # Android doesn't support arbitrary key combos; press each key
        for key in keys.split("+"):
            await self.press_key(key.strip())

    async def scroll(self, direction: str = "down", amount: int = 3) -> None:
        """Scroll the screen."""
        from android_world.env.json_action import JSONAction
        action = JSONAction(action_type="scroll", direction=direction)
        for _ in range(amount):
            self._env.execute_action(action)
            await asyncio.sleep(0.3)
        self._last_state = None

    async def scroll_element(
        self, selector: str, direction: str = "down", amount: int = 3
    ) -> None:
        """Scroll within a specific element."""
        from android_world.env.json_action import JSONAction
        state = self._get_state()
        idx = _find_element_index(state.ui_elements, selector)
        if idx is not None:
            action = JSONAction(action_type="scroll", direction=direction, index=idx)
            for _ in range(amount):
                self._env.execute_action(action)
                await asyncio.sleep(0.3)
        self._last_state = None

    async def move_to(self, selector: str) -> None:
        """No-op on Android (no mouse cursor)."""
        pass

    async def drag(self, from_selector: str, to_selector: str) -> None:
        """Drag from one element to another (not commonly used)."""
        pass

    async def select_option(self, selector: str, value: str) -> None:
        """Select option - click element then click matching option."""
        await self.click(selector)
        await asyncio.sleep(0.5)
        # Try to find and click the option text
        state = self._get_state()
        for i, elem in enumerate(state.ui_elements):
            if elem.text and value.lower() in elem.text.lower():
                from android_world.env.json_action import JSONAction
                action = JSONAction(action_type="click", index=i)
                self._env.execute_action(action)
                await asyncio.sleep(0.3)
                self._last_state = None
                return

    async def navigate(self, target: str) -> None:
        """Navigate - open app by name."""
        from android_world.env.json_action import JSONAction
        action = JSONAction(action_type="open_app", app_name=target)
        self._env.execute_action(action)
        await asyncio.sleep(1.0)
        self._last_state = None

    async def go_back(self) -> None:
        """Press back button."""
        from android_world.env.json_action import JSONAction
        action = JSONAction(action_type="navigate_back")
        self._env.execute_action(action)
        await asyncio.sleep(0.3)
        self._last_state = None

    async def go_forward(self) -> None:
        """No forward on Android."""
        pass

    async def refresh(self) -> None:
        """Refresh = go home then back to app."""
        pass

    # ─── Advanced ─────────────────────────────────────────────────────────

    async def evaluate_js(self, script: str) -> Any:
        """Not applicable on Android."""
        return None

    async def wait_for_navigation(self, timeout_ms: int = 5000) -> None:
        """Wait for UI to stabilize."""
        self._get_state(wait_stable=True)

    async def wait_ms(self, ms: int) -> None:
        """Wait for specified duration."""
        await asyncio.sleep(ms / 1000.0)

    async def find_elements_by_xpath(self, selector: str) -> list[dict[str, Any]]:
        """Find all elements matching selector."""
        state = self._get_state()
        indices = _find_all_element_indices(state.ui_elements, selector)
        return [_element_to_dict(state.ui_elements[i], i) for i in indices]

    # ─── Android-specific helpers ─────────────────────────────────────────

    def get_ui_elements_text(self) -> str:
        """Get formatted text of current UI elements for LLM prompts."""
        state = self._get_state()
        return _ui_elements_to_text(state.ui_elements)

    def get_current_state(self):
        """Get the raw Android state object."""
        return self._get_state()

    def execute_android_action(self, action) -> None:
        """Execute a raw AndroidWorld JSONAction."""
        self._env.execute_action(action)
        self._last_state = None

    def _parse_coordinates(self, selector: str) -> Optional[tuple[int, int]]:
        """Try to parse x,y coordinates from selector."""
        match = re.search(r"x=(\d+)&&y=(\d+)", selector)
        if match:
            return int(match.group(1)), int(match.group(2))
        match = re.search(r"coord=(\d+),(\d+)", selector)
        if match:
            return int(match.group(1)), int(match.group(2))
        return None

    def build_selector(self, element, index: int) -> str:
        """Build a stable selector string for a UIElement.

        Prefers resource_id (most stable), then text, then content_desc,
        falling back to class + index.
        """
        parts = []
        if element.resource_name:
            # Resource IDs are most stable across runs
            parts.append(f"resource_id={element.resource_name}")
        if element.text:
            parts.append(f"text={element.text}")
        elif element.content_description:
            parts.append(f"content_desc={element.content_description}")
        elif element.hint_text:
            parts.append(f"hint={element.hint_text}")

        if not parts:
            # Fallback to class name
            if element.class_name:
                parts.append(f"class={element.class_name}")
            parts.append(f"index={index}")

        return "&&".join(parts)
