"""HTTP-based Android environment adapter for PreAct.

Connects to AndroidWorld Docker container via HTTP API instead of
direct ADB/gRPC. Implements the same interface as AndroidEnvironment
but uses REST calls to the server.
"""

from __future__ import annotations

import asyncio
import base64
import io
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)


@dataclass
class HTTPUIElement:
    """UI element from the HTTP API response."""
    index: int = 0
    text: Optional[str] = None
    content_description: Optional[str] = None
    class_name: Optional[str] = None
    resource_name: Optional[str] = None
    resource_id: Optional[str] = None
    hint_text: Optional[str] = None
    tooltip: Optional[str] = None
    package_name: Optional[str] = None
    is_clickable: Optional[bool] = None
    is_editable: Optional[bool] = None
    is_scrollable: Optional[bool] = None
    is_checked: Optional[bool] = None
    is_enabled: Optional[bool] = None
    is_focused: Optional[bool] = None
    is_visible: Optional[bool] = None
    center_x: Optional[int] = None
    center_y: Optional[int] = None
    bbox_x_min: Optional[int] = None
    bbox_y_min: Optional[int] = None
    bbox_x_max: Optional[int] = None
    bbox_y_max: Optional[int] = None

    @classmethod
    def from_dict(cls, d: dict) -> HTTPUIElement:
        bbox = d.get("bbox", {})
        return cls(
            index=d.get("index", 0),
            text=d.get("text"),
            content_description=d.get("content_description"),
            class_name=d.get("class_name"),
            resource_name=d.get("resource_name"),
            resource_id=d.get("resource_id"),
            hint_text=d.get("hint_text"),
            tooltip=d.get("tooltip"),
            package_name=d.get("package_name"),
            is_clickable=d.get("is_clickable"),
            is_editable=d.get("is_editable"),
            is_scrollable=d.get("is_scrollable"),
            is_checked=d.get("is_checked"),
            is_enabled=d.get("is_enabled"),
            is_focused=d.get("is_focused"),
            is_visible=d.get("is_visible"),
            center_x=d.get("center_x"),
            center_y=d.get("center_y"),
            bbox_x_min=bbox.get("x_min"),
            bbox_y_min=bbox.get("y_min"),
            bbox_x_max=bbox.get("x_max"),
            bbox_y_max=bbox.get("y_max"),
        )


def _parse_selector(selector: str) -> dict[str, str]:
    """Parse element selector into key-value pairs."""
    parts = selector.split("&&")
    attrs = {}
    for part in parts:
        part = part.strip()
        if "=" in part:
            key, value = part.split("=", 1)
            attrs[key.strip()] = value.strip()
    return attrs


def _element_matches(elem: HTTPUIElement, attrs: dict[str, str]) -> bool:
    """Check if element matches selector attributes."""
    for key, value in attrs.items():
        if key in ("resource_id", "resource_name"):
            elem_val = elem.resource_name or elem.resource_id or ""
            if value not in (elem_val or ""):
                return False
        elif key == "text":
            if value.lower() not in (elem.text or "").lower():
                return False
        elif key == "class":
            if value.lower() not in (elem.class_name or "").lower():
                return False
        elif key == "content_desc":
            if value.lower() not in (elem.content_description or "").lower():
                return False
        elif key == "hint":
            if value.lower() not in (elem.hint_text or "").lower():
                return False
        elif key == "index":
            pass  # handled separately
        elif key == "package":
            if value not in (elem.package_name or ""):
                return False
        elif key == "checked":
            if str(elem.is_checked).lower() != value.lower():
                return False
    return True


def _find_element(elements: list[HTTPUIElement], selector: str) -> Optional[HTTPUIElement]:
    """Find first element matching selector."""
    attrs = _parse_selector(selector)
    if "index" in attrs and len(attrs) == 1:
        idx = int(attrs["index"])
        for e in elements:
            if e.index == idx:
                return e
        return None
    for e in elements:
        if _element_matches(e, attrs):
            return e
    return None


def _elements_to_text(elements: list[HTTPUIElement]) -> str:
    """Format UI elements as text for LLM prompts."""
    lines = []
    for elem in elements:
        parts = [f"[{elem.index}]"]
        if elem.class_name:
            parts.append(elem.class_name.split(".")[-1])
        if elem.text:
            parts.append(f'text="{elem.text}"')
        if elem.content_description:
            parts.append(f'desc="{elem.content_description}"')
        if elem.hint_text:
            parts.append(f'hint="{elem.hint_text}"')
        if elem.resource_name:
            short = elem.resource_name.split("/")[-1] if "/" in (elem.resource_name or "") else elem.resource_name
            parts.append(f"id={short}")
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


class AndroidHTTPEnvironment:
    """PreAct environment adapter that talks to AndroidWorld Docker via HTTP."""

    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url.rstrip("/")
        self._last_elements: list[HTTPUIElement] = []
        self._last_screenshot_b64: Optional[str] = None
        self._screen_width = 1080
        self._screen_height = 2400

    def _get(self, path: str, params: dict = None, timeout: int = 30) -> dict:
        resp = requests.get(f"{self.base_url}{path}", params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, params: dict = None, json_data: dict = None, timeout: int = 30) -> dict:
        resp = requests.post(f"{self.base_url}{path}", params=params, json=json_data, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    def _get_state(self) -> tuple[str, list[HTTPUIElement]]:
        """Get screenshot (base64 PNG) and UI elements from server.

        Tries /state endpoint first (custom build with UI elements).
        Falls back to /screenshot (raw pixels) if /state is unavailable.
        """
        try:
            data = self._get("/state", {"wait_to_stabilize": "false"}, timeout=60)
            self._last_screenshot_b64 = data["screenshot_b64"]
            self._last_elements = [HTTPUIElement.from_dict(e) for e in data.get("ui_elements", [])]
            self._screen_width = data.get("screen_width", 1080)
            self._screen_height = data.get("screen_height", 2400)
            return self._last_screenshot_b64, self._last_elements
        except Exception:
            # Fall back to /screenshot (pre-built image)
            return self._get_screenshot_fallback(), self._last_elements

    def _get_screenshot_fallback(self) -> str:
        """Get screenshot from /screenshot endpoint as base64 PNG."""
        import numpy as np
        from PIL import Image

        data = self._get("/screenshot", {"wait_to_stabilize": "false"}, timeout=60)
        pixels = np.array(data["pixels"], dtype=np.uint8)
        img = Image.fromarray(pixels)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        self._last_screenshot_b64 = b64
        self._screen_width = pixels.shape[1] if len(pixels.shape) >= 2 else 1080
        self._screen_height = pixels.shape[0] if len(pixels.shape) >= 2 else 2400
        return b64

    def wait_for_ready(self, timeout: int = 600):
        """Wait for the Docker server to be ready."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                self._get("/health", timeout=5)
                logger.info("AndroidWorld server is ready")
                return True
            except Exception:
                time.sleep(2)
        raise TimeoutError("AndroidWorld server did not become ready")

    # ─── Lifecycle ────────────────────────────────────────────────────────

    async def start(self) -> None:
        self.wait_for_ready()
        self._get_state()

    async def stop(self) -> None:
        pass

    async def reset(self) -> None:
        self._post("/reset", {"go_home": "true"})
        self._last_elements = []
        self._last_screenshot_b64 = None

    # ─── Observation ──────────────────────────────────────────────────────

    async def screenshot(self) -> bytes:
        """Capture screenshot as PNG bytes."""
        b64, _ = self._get_state()
        return base64.b64decode(b64)

    async def element_exists(self, selector: str, timeout_ms: int = 5000) -> bool:
        """Check if element exists, polling until timeout."""
        deadline = time.time() + timeout_ms / 1000.0
        while True:
            _, elements = self._get_state()
            if _find_element(elements, selector):
                return True
            if time.time() >= deadline:
                return False
            await asyncio.sleep(0.3)

    async def element_text(self, selector: str) -> str:
        elem = _find_element(self._last_elements, selector)
        if elem:
            return elem.text or elem.content_description or ""
        return ""

    async def get_dom_snapshot(self) -> str:
        """Get UI elements as text."""
        if not self._last_elements:
            self._get_state()
        return _elements_to_text(self._last_elements)

    def get_ui_elements_text(self) -> str:
        """Get formatted UI elements for LLM prompts."""
        if not self._last_elements:
            self._get_state()
        return _elements_to_text(self._last_elements)

    def get_ui_elements(self) -> list[HTTPUIElement]:
        """Get current UI elements."""
        if not self._last_elements:
            self._get_state()
        return self._last_elements

    # ─── Actions ──────────────────────────────────────────────────────────

    def _exec_action(self, action_dict: dict) -> None:
        """Execute an action via the HTTP API."""
        # Remove None values
        action_dict = {k: v for k, v in action_dict.items() if v is not None}
        self._post("/execute_action", json_data=action_dict)
        self._last_elements = []
        self._last_screenshot_b64 = None

    async def click(self, selector: str) -> None:
        elem = _find_element(self._last_elements, selector)
        if elem and elem.center_x is not None:
            self._exec_action({"action_type": "click", "x": elem.center_x, "y": elem.center_y})
        else:
            coords = self._parse_coordinates(selector)
            if coords:
                self._exec_action({"action_type": "click", "x": coords[0], "y": coords[1]})
            else:
                logger.warning("click: element not found: %s", selector)
        await asyncio.sleep(0.5)

    async def type_text(self, selector: str, text: str) -> None:
        elem = _find_element(self._last_elements, selector)
        if elem and elem.center_x is not None:
            # Click first to focus
            self._exec_action({"action_type": "click", "x": elem.center_x, "y": elem.center_y})
            await asyncio.sleep(0.3)
        self._exec_action({"action_type": "input_text", "text": text})
        await asyncio.sleep(0.3)

    async def clear_and_type(self, selector: str, text: str) -> None:
        elem = _find_element(self._last_elements, selector)
        if elem and elem.center_x is not None:
            self._exec_action({"action_type": "click", "x": elem.center_x, "y": elem.center_y})
            await asyncio.sleep(0.3)
        self._exec_action({"action_type": "input_text", "text": text, "clear_text": True})
        await asyncio.sleep(0.3)

    async def press_key(self, key: str) -> None:
        key_lower = key.lower()
        if key_lower in ("enter", "return"):
            self._exec_action({"action_type": "keyboard_enter"})
        elif key_lower in ("back", "escape"):
            self._exec_action({"action_type": "navigate_back"})
        elif key_lower in ("home",):
            self._exec_action({"action_type": "navigate_home"})
        else:
            self._exec_action({"action_type": "click", "keycode": f"KEYCODE_{key.upper()}"})
        await asyncio.sleep(0.3)

    async def scroll(self, direction: str = "down", amount: int = 3) -> None:
        for _ in range(amount):
            self._exec_action({"action_type": "scroll", "direction": direction})
            await asyncio.sleep(0.3)

    async def navigate(self, target: str) -> None:
        """Open an app by name."""
        self._exec_action({"action_type": "open_app", "app_name": target})
        await asyncio.sleep(1.0)

    async def go_back(self) -> None:
        self._exec_action({"action_type": "navigate_back"})
        await asyncio.sleep(0.3)

    async def wait_ms(self, ms: int) -> None:
        await asyncio.sleep(ms / 1000.0)

    # ─── Task management ─────────────────────────────────────────────────

    def get_task_list(self) -> list[str]:
        data = self._get("/suite/task_list", {"max_index": -1})
        return data.get("task_list", [])

    def get_task_length(self, task_type: str) -> int:
        data = self._get("/suite/task_length", {"task_type": task_type})
        return data.get("length", 0)

    def get_task_goal(self, task_type: str, task_idx: int) -> str:
        data = self._get("/task/goal", {"task_type": task_type, "task_idx": task_idx})
        return data.get("goal", "")

    def initialize_task(self, task_type: str, task_idx: int) -> None:
        self._post("/task/initialize", {"task_type": task_type, "task_idx": task_idx})

    def get_task_score(self, task_type: str, task_idx: int) -> float:
        data = self._get("/task/score", {"task_type": task_type, "task_idx": task_idx})
        return float(data.get("score", 0.0))

    def tear_down_task(self, task_type: str, task_idx: int) -> None:
        self._post("/task/tear_down", {"task_type": task_type, "task_idx": task_idx})

    def reinitialize_suite(self, n_combinations: int = 2, seed: int = 42) -> None:
        self._get("/suite/reinitialize", {
            "n_task_combinations": n_combinations,
            "seed": seed,
        })

    # ─── Helpers ──────────────────────────────────────────────────────────

    def _parse_coordinates(self, selector: str) -> Optional[tuple[int, int]]:
        match = re.search(r"x=(\d+)&&y=(\d+)", selector)
        if match:
            return int(match.group(1)), int(match.group(2))
        match = re.search(r"coord=(\d+),(\d+)", selector)
        if match:
            return int(match.group(1)), int(match.group(2))
        return None

    def build_selector(self, elem: HTTPUIElement) -> str:
        """Build a stable selector for an element."""
        parts = []
        if elem.resource_name:
            parts.append(f"resource_id={elem.resource_name}")
        if elem.text:
            parts.append(f"text={elem.text}")
        elif elem.content_description:
            parts.append(f"content_desc={elem.content_description}")
        elif elem.hint_text:
            parts.append(f"hint={elem.hint_text}")
        if not parts:
            if elem.class_name:
                parts.append(f"class={elem.class_name}")
            parts.append(f"index={elem.index}")
        return "&&".join(parts)
