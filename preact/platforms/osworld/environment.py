"""OSWorld environment adapter for PreAct.

Implements the ComputerEnvironment protocol using OSWorld's DesktopEnv,
translating element selectors to accessibility tree lookups and
actions to pyautogui commands.

Selector Format (using a11y tree attributes):
  name=OK
  role=push button
  text=File name
  coord=100,200
  Multiple: role=push button&&name=OK
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
import xml.etree.ElementTree as ET
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _parse_selector(selector: str) -> dict[str, str]:
    """Parse a PreAct element selector into attribute key-value pairs."""
    parts = selector.split("&&")
    attrs = {}
    for part in parts:
        part = part.strip()
        if "=" in part:
            key, value = part.split("=", 1)
            attrs[key.strip()] = value.strip()
    return attrs


def _parse_a11y_tree(tree_xml: str) -> list[dict[str, Any]]:
    """Parse OSWorld accessibility tree XML into element dicts.

    Returns a list of elements with their attributes and coordinates.
    """
    if not tree_xml or not tree_xml.strip():
        return []

    elements = []
    try:
        # OSWorld returns accessibility tree as XML or TSV
        # Try XML first
        if tree_xml.strip().startswith("<"):
            root = ET.fromstring(tree_xml)
            _extract_elements_xml(root, elements)
        else:
            # TSV format from linearized tree
            _extract_elements_tsv(tree_xml, elements)
    except ET.ParseError:
        # Try TSV format
        _extract_elements_tsv(tree_xml, elements)

    return elements


def _extract_elements_xml(node, elements: list, depth: int = 0):
    """Extract elements from XML accessibility tree."""
    elem = {
        "tag": node.tag,
        "name": node.get("name", ""),
        "text": node.get("text", node.text or ""),
        "role": node.get("class", node.tag),
        "description": node.get("description", ""),
        "x": 0,
        "y": 0,
        "width": 0,
        "height": 0,
        "visible": True,
        "enabled": True,
        "depth": depth,
    }

    # Parse coordinates from various formats
    screencoord = node.get("screencoord", "")
    if screencoord:
        try:
            parts = screencoord.strip("()").split(",")
            elem["x"] = int(float(parts[0].strip()))
            elem["y"] = int(float(parts[1].strip()))
        except (ValueError, IndexError):
            pass

    size = node.get("size", "")
    if size:
        try:
            parts = size.strip("()").split(",")
            elem["width"] = int(float(parts[0].strip()))
            elem["height"] = int(float(parts[1].strip()))
        except (ValueError, IndexError):
            pass

    # Check state attributes (with namespace handling)
    for attr_name, attr_val in node.attrib.items():
        if "showing" in attr_name:
            elem["visible"] = attr_val.lower() == "true"
        if "enabled" in attr_name:
            elem["enabled"] = attr_val.lower() == "true"
        if "visible" in attr_name:
            elem["visible"] = attr_val.lower() == "true"

    # Only add elements that are visible and have some identifying info
    if elem["visible"] and (elem["name"] or elem["text"] or elem["description"]):
        elements.append(elem)

    for child in node:
        _extract_elements_xml(child, elements, depth + 1)


def _extract_elements_tsv(tsv_text: str, elements: list):
    """Extract elements from TSV-format accessibility tree."""
    lines = tsv_text.strip().split("\n")
    if len(lines) < 2:
        return

    # Parse header
    header = lines[0].split("\t")
    col_map = {h.strip().lower(): i for i, h in enumerate(header)}

    for line in lines[1:]:
        cols = line.split("\t")
        if len(cols) < len(header):
            continue

        elem = {
            "tag": cols[col_map.get("tag", 0)] if "tag" in col_map else "",
            "name": cols[col_map.get("name", 1)] if "name" in col_map else "",
            "text": cols[col_map.get("text", 2)] if "text" in col_map else "",
            "role": cols[col_map.get("class", 3)] if "class" in col_map else "",
            "description": cols[col_map.get("description", 4)] if "description" in col_map else "",
            "x": 0,
            "y": 0,
            "width": 0,
            "height": 0,
            "visible": True,
            "enabled": True,
        }

        # Parse position
        if "position (top-left x&y)" in col_map:
            pos_str = cols[col_map["position (top-left x&y)"]]
            match = re.search(r"(\d+)\D+(\d+)", pos_str)
            if match:
                elem["x"] = int(match.group(1))
                elem["y"] = int(match.group(2))

        # Parse size
        if "size (w&h)" in col_map:
            size_str = cols[col_map["size (w&h)"]]
            match = re.search(r"(\d+)\D+(\d+)", size_str)
            if match:
                elem["width"] = int(match.group(1))
                elem["height"] = int(match.group(2))

        if elem["name"] or elem["text"] or elem["description"]:
            elements.append(elem)


def _element_matches(element: dict, attrs: dict[str, str]) -> bool:
    """Check if an a11y tree element matches selector attributes."""
    for key, value in attrs.items():
        if key == "name":
            if value.lower() not in (element.get("name", "") or "").lower():
                return False
        elif key == "text":
            if value.lower() not in (element.get("text", "") or "").lower():
                return False
        elif key == "role" or key == "class":
            if value.lower() not in (element.get("role", "") or "").lower():
                return False
        elif key == "description" or key == "desc":
            if value.lower() not in (element.get("description", "") or "").lower():
                return False
        elif key == "tag":
            if value.lower() not in (element.get("tag", "") or "").lower():
                return False
        elif key == "coord":
            # Coordinate matching (approximate)
            try:
                cx, cy = map(int, value.split(","))
                ex, ey = element.get("x", 0), element.get("y", 0)
                ew, eh = element.get("width", 50), element.get("height", 50)
                if not (ex <= cx <= ex + ew and ey <= cy <= ey + eh):
                    return False
            except (ValueError, TypeError):
                return False
    return True


def _find_element(elements: list[dict], selector: str) -> Optional[dict]:
    """Find first element matching selector."""
    attrs = _parse_selector(selector)
    for elem in elements:
        if _element_matches(elem, attrs):
            return elem
    return None


def _elements_to_text(elements: list[dict]) -> str:
    """Format elements list for LLM prompts.

    Bug 4 fix: dense line-per-element format
        [idx] role "name" (cx,cy)
    Indices start at 0 and align with _get_a11y_elements() so the LLM
    can reference `click(id=N)` which the agent then maps to coordinates.
    Falls back to text/description if name is absent.
    """
    lines = []
    for i, elem in enumerate(elements):
        role = elem.get("role") or "element"
        label = (
            elem.get("name")
            or (elem.get("text") or "")[:60]
            or (elem.get("description") or "")[:60]
            or ""
        )
        cx = elem.get("x", 0) + elem.get("width", 0) // 2
        cy = elem.get("y", 0) + elem.get("height", 0) // 2
        label = label.replace('"', "'")
        lines.append(f'[{i}] {role} "{label}" ({cx},{cy})')
    return "\n".join(lines)


class OSWorldEnvironment:
    """PreAct ComputerEnvironment adapter for OSWorld.

    Wraps OSWorld's DesktopEnv to implement the interface needed by
    PreAct's executor, CUA loop, and recorder.
    """

    def __init__(self, desktop_env):
        """Initialize with an OSWorld DesktopEnv instance."""
        self._env = desktop_env
        self._last_screenshot = None
        self._last_a11y_tree = None
        self._last_elements = None

    @property
    def desktop_env(self):
        """Access the underlying OSWorld environment."""
        return self._env

    def _get_observation(self) -> dict:
        """Get current observation."""
        return self._env._get_obs()

    def _get_a11y_elements(self) -> list[dict]:
        """Get parsed accessibility tree elements.

        Bug 1 fix: never silently swallow errors. Log raw XML at DEBUG,
        count at INFO, and any exception + raw XML at WARNING. Also warn
        when the tree parses but returns zero elements — that indicates
        the controller (not our parser) is returning nothing.
        """
        tree_xml = ""
        try:
            tree_xml = self._env.controller.get_accessibility_tree()
            if isinstance(tree_xml, dict):
                tree_xml = tree_xml.get("AT", "")
            tree_xml = tree_xml or ""
            self._last_a11y_tree = tree_xml

            logger.debug("a11y raw (first 500): %r", tree_xml[:500])

            elements = _parse_a11y_tree(tree_xml)
            self._last_elements = elements
            logger.info("a11y tree parsed: %d elements (raw length=%d)",
                        len(elements), len(tree_xml))
            if not elements:
                logger.warning(
                    "a11y tree returned zero elements — check controller. "
                    "Raw length=%d, raw head=%r",
                    len(tree_xml), tree_xml[:500],
                )
            return elements
        except Exception as e:
            logger.warning(
                "Failed to parse a11y tree: %r — raw (first 500): %r",
                e, tree_xml[:500] if isinstance(tree_xml, str) else tree_xml,
            )
            return self._last_elements or []

    def a11y_tree_is_empty(self) -> bool:
        """Return True if last a11y fetch returned no elements.

        Used by the agent to inject a warning into the LLM context.
        """
        return not bool(self._last_elements)

    # ─── Lifecycle ────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Environment already started by OSWorld."""
        pass

    async def stop(self) -> None:
        """Environment lifecycle managed by OSWorld."""
        pass

    async def reset(self) -> None:
        """Reset handled by OSWorld task initialization."""
        self._last_screenshot = None
        self._last_a11y_tree = None
        self._last_elements = None

    # ─── Observation ──────────────────────────────────────────────────────

    async def screenshot(self) -> bytes:
        """Capture screenshot as PNG bytes.

        Bug 7 fix: give the display compositor a short grace period before
        grabbing the frame so that pyautogui-driven UI changes have time to
        propagate (menus open, windows focus, text appears). 100ms is short
        enough to be invisible in the total step budget but long enough to
        avoid "screenshot taken before the UI updated" stale captures.
        """
        await asyncio.sleep(0.1)
        try:
            png_bytes = self._env.controller.get_screenshot()
            self._last_screenshot = png_bytes
            return png_bytes
        except Exception as e:
            logger.warning("Screenshot failed: %s", e)
            return self._last_screenshot or b""

    async def element_screenshot(self, selector: str) -> bytes:
        """Capture full screenshot (element-level cropping not easily supported)."""
        return await self.screenshot()

    async def element_exists(self, selector: str, timeout_ms: int = 5000) -> bool:
        """Check if element exists in accessibility tree."""
        deadline = time.time() + timeout_ms / 1000.0
        poll_interval = 0.5

        while True:
            elements = self._get_a11y_elements()
            elem = _find_element(elements, selector)
            if elem is not None:
                return True
            if time.time() >= deadline:
                return False
            await asyncio.sleep(poll_interval)

    async def element_text(self, selector: str) -> str:
        """Get text of element."""
        elements = self._get_a11y_elements()
        elem = _find_element(elements, selector)
        if elem:
            return elem.get("text", "") or elem.get("name", "")
        return ""

    async def element_attribute(self, selector: str, attribute: str) -> Optional[str]:
        """Get attribute of element."""
        elements = self._get_a11y_elements()
        elem = _find_element(elements, selector)
        if elem:
            return str(elem.get(attribute, ""))
        return None

    async def get_page_url(self) -> str:
        """Not applicable for OS."""
        return ""

    async def get_page_title(self) -> str:
        """Return window title if available."""
        return ""

    async def get_dom_snapshot(self) -> str:
        """Get accessibility tree as text."""
        elements = self._get_a11y_elements()
        return _elements_to_text(elements)

    # ─── Actions ──────────────────────────────────────────────────────────

    def _exec_pyautogui(self, command: str) -> None:
        """Execute a pyautogui command on the VM."""
        try:
            self._env.controller.execute_python_command(command)
        except Exception as e:
            logger.warning("pyautogui command failed: %s — %s", command[:100], e)

    def _get_element_center(self, selector: str) -> Optional[tuple[int, int]]:
        """Get center coordinates of element."""
        # Check for direct coordinates
        attrs = _parse_selector(selector)
        if "coord" in attrs:
            try:
                parts = attrs["coord"].split(",")
                return int(parts[0]), int(parts[1])
            except (ValueError, IndexError):
                pass

        elements = self._get_a11y_elements()
        elem = _find_element(elements, selector)
        if elem:
            x = elem.get("x", 0) + elem.get("width", 0) // 2
            y = elem.get("y", 0) + elem.get("height", 0) // 2
            return x, y
        return None

    async def click(self, selector: str) -> None:
        """Click on element. Raises ValueError if selector does not resolve."""
        center = self._get_element_center(selector)
        if not center:
            raise ValueError(f"click: element not found: {selector}")
        self._exec_pyautogui(f"import pyautogui; pyautogui.click({center[0]}, {center[1]})")
        await asyncio.sleep(0.5)

    async def double_click(self, selector: str) -> None:
        """Double-click on element. Raises ValueError if selector does not resolve."""
        center = self._get_element_center(selector)
        if not center:
            raise ValueError(f"double_click: element not found: {selector}")
        self._exec_pyautogui(
            f"import pyautogui; pyautogui.doubleClick({center[0]}, {center[1]})"
        )
        await asyncio.sleep(0.5)

    async def right_click(self, selector: str) -> None:
        """Right-click on element. Raises ValueError if selector does not resolve."""
        center = self._get_element_center(selector)
        if not center:
            raise ValueError(f"right_click: element not found: {selector}")
        self._exec_pyautogui(
            f"import pyautogui; pyautogui.rightClick({center[0]}, {center[1]})"
        )
        await asyncio.sleep(0.5)

    async def type_text(self, selector: str, text: str) -> None:
        """Click element then type text. Raises ValueError on missing selector."""
        center = self._get_element_center(selector)
        if not center:
            raise ValueError(f"type_text: element not found: {selector}")
        self._exec_pyautogui(f"import pyautogui; pyautogui.click({center[0]}, {center[1]})")
        await asyncio.sleep(0.3)

        # Use write for unicode, typewrite for ASCII
        escaped = text.replace("\\", "\\\\").replace("'", "\\'")
        self._exec_pyautogui(f"import pyautogui; pyautogui.write('{escaped}')")
        await asyncio.sleep(0.3)

    async def clear_and_type(self, selector: str, text: str) -> None:
        """Select all, then type. Raises ValueError on missing selector."""
        center = self._get_element_center(selector)
        if not center:
            raise ValueError(f"clear_and_type: element not found: {selector}")
        self._exec_pyautogui(f"import pyautogui; pyautogui.click({center[0]}, {center[1]})")
        await asyncio.sleep(0.2)

        self._exec_pyautogui("import pyautogui; pyautogui.hotkey('ctrl', 'a')")
        await asyncio.sleep(0.1)
        escaped = text.replace("\\", "\\\\").replace("'", "\\'")
        self._exec_pyautogui(f"import pyautogui; pyautogui.write('{escaped}')")
        await asyncio.sleep(0.3)

    async def press_key(self, key: str) -> None:
        """Press a keyboard key."""
        key_map = {
            "Enter": "enter",
            "Return": "enter",
            "Tab": "tab",
            "Escape": "escape",
            "Backspace": "backspace",
            "Delete": "delete",
            "Space": "space",
        }
        key_name = key_map.get(key, key.lower())
        self._exec_pyautogui(f"import pyautogui; pyautogui.press('{key_name}')")
        await asyncio.sleep(0.3)

    async def key_combo(self, keys: str) -> None:
        """Press key combination."""
        key_list = [k.strip().lower() for k in keys.split("+")]
        key_args = ", ".join(f"'{k}'" for k in key_list)
        self._exec_pyautogui(f"import pyautogui; pyautogui.hotkey({key_args})")
        await asyncio.sleep(0.3)

    async def scroll(self, direction: str = "down", amount: int = 3) -> None:
        """Scroll the screen."""
        if direction in ("down", "left"):
            scroll_amount = -amount
        else:
            scroll_amount = amount
        self._exec_pyautogui(f"import pyautogui; pyautogui.scroll({scroll_amount})")
        await asyncio.sleep(0.3)

    async def scroll_element(
        self, selector: str, direction: str = "down", amount: int = 3
    ) -> None:
        """Scroll at element position. Raises ValueError on missing selector."""
        center = self._get_element_center(selector)
        if not center:
            raise ValueError(f"scroll_element: element not found: {selector}")
        self._exec_pyautogui(
            f"import pyautogui; pyautogui.moveTo({center[0]}, {center[1]})"
        )
        await asyncio.sleep(0.1)
        await self.scroll(direction, amount)

    async def move_to(self, selector: str) -> None:
        """Move cursor to element. Raises ValueError on missing selector."""
        center = self._get_element_center(selector)
        if not center:
            raise ValueError(f"move_to: element not found: {selector}")
        self._exec_pyautogui(
            f"import pyautogui; pyautogui.moveTo({center[0]}, {center[1]})"
        )

    async def drag(self, from_selector: str, to_selector: str) -> None:
        """Drag from one element to another. Raises ValueError on missing selector."""
        from_center = self._get_element_center(from_selector)
        to_center = self._get_element_center(to_selector)
        if not from_center:
            raise ValueError(f"drag: element not found (from): {from_selector}")
        if not to_center:
            raise ValueError(f"drag: element not found (to): {to_selector}")
        dx = to_center[0] - from_center[0]
        dy = to_center[1] - from_center[1]
        self._exec_pyautogui(
            f"import pyautogui; pyautogui.moveTo({from_center[0]}, {from_center[1]}); "
            f"pyautogui.drag({dx}, {dy}, duration=0.5)"
        )

    async def select_option(self, selector: str, value: str) -> None:
        """Click element, then type value."""
        await self.click(selector)
        await asyncio.sleep(0.3)
        escaped = value.replace("\\", "\\\\").replace("'", "\\'")
        self._exec_pyautogui(f"import pyautogui; pyautogui.write('{escaped}')")

    async def navigate(self, url: str) -> None:
        """Open URL in browser or run command."""
        if url.startswith("http"):
            escaped = url.replace("'", "\\'")
            self._exec_pyautogui(
                f"import subprocess; subprocess.Popen(['xdg-open', '{escaped}'])"
            )
        await asyncio.sleep(1.0)

    async def go_back(self) -> None:
        """Alt+Left to go back."""
        self._exec_pyautogui("import pyautogui; pyautogui.hotkey('alt', 'left')")

    async def go_forward(self) -> None:
        """Alt+Right to go forward."""
        self._exec_pyautogui("import pyautogui; pyautogui.hotkey('alt', 'right')")

    async def refresh(self) -> None:
        """F5 to refresh."""
        self._exec_pyautogui("import pyautogui; pyautogui.press('f5')")

    # ─── Advanced ─────────────────────────────────────────────────────────

    async def evaluate_js(self, script: str) -> Any:
        """Not applicable for OS."""
        return None

    async def wait_for_navigation(self, timeout_ms: int = 5000) -> None:
        """Wait for UI to settle."""
        await asyncio.sleep(timeout_ms / 1000.0)

    async def wait_ms(self, ms: int) -> None:
        """Wait for specified duration."""
        await asyncio.sleep(ms / 1000.0)

    async def find_elements_by_xpath(self, selector: str) -> list[dict[str, Any]]:
        """Find all elements matching selector."""
        elements = self._get_a11y_elements()
        attrs = _parse_selector(selector)
        return [e for e in elements if _element_matches(e, attrs)]

    # ─── OS-specific helpers ──────────────────────────────────────────────

    def get_a11y_elements_text(self) -> str:
        """Get formatted accessibility tree for LLM prompts."""
        elements = self._get_a11y_elements()
        return _elements_to_text(elements)

    def build_selector(self, element: dict) -> str:
        """Build a stable selector string for an a11y element."""
        parts = []
        if element.get("name"):
            parts.append(f"name={element['name']}")
        if element.get("role"):
            parts.append(f"role={element['role']}")
        if not parts:
            if element.get("text"):
                parts.append(f"text={element['text']}")
            elif element.get("x") and element.get("y"):
                cx = element["x"] + element.get("width", 0) // 2
                cy = element["y"] + element.get("height", 0) // 2
                parts.append(f"coord={cx},{cy}")
        return "&&".join(parts) if parts else ""
