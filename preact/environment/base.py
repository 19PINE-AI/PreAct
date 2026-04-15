"""Abstract Computer Environment protocol.

Defines the interface that all environment implementations must satisfy.
The RPA Executor, CUA Loop, and Recorder all interact with the environment
exclusively through this protocol.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ComputerEnvironment(Protocol):
    """Protocol for interacting with a computer environment (browser, VM, etc.)."""

    # ─── Lifecycle ────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Initialize the environment (launch browser, connect to VM, etc.)."""
        ...

    async def stop(self) -> None:
        """Shut down the environment and release resources."""
        ...

    async def reset(self) -> None:
        """Reset the environment to its initial state."""
        ...

    # ─── Observation ──────────────────────────────────────────────────────

    async def screenshot(self) -> bytes:
        """Capture a full-page screenshot as PNG bytes."""
        ...

    async def element_screenshot(self, xpath: str) -> bytes:
        """Capture a screenshot of a specific element identified by XPath."""
        ...

    async def element_exists(self, xpath: str, timeout_ms: int = 5000) -> bool:
        """Check if an element matching the XPath exists within timeout.

        Polls until the element appears or the timeout expires.
        Returns True if found, False on timeout.
        """
        ...

    async def element_text(self, xpath: str) -> str:
        """Extract the text content of an element identified by XPath."""
        ...

    async def element_attribute(self, xpath: str, attribute: str) -> str | None:
        """Get an attribute value of an element identified by XPath."""
        ...

    async def get_page_url(self) -> str:
        """Get the current page URL."""
        ...

    async def get_page_title(self) -> str:
        """Get the current page title."""
        ...

    async def get_dom_snapshot(self) -> str:
        """Get a serialized DOM snapshot (for the recorder)."""
        ...

    # ─── Actions ──────────────────────────────────────────────────────────

    async def click(self, xpath: str) -> None:
        """Click on the element matching the XPath."""
        ...

    async def double_click(self, xpath: str) -> None:
        """Double-click on the element matching the XPath."""
        ...

    async def right_click(self, xpath: str) -> None:
        """Right-click on the element matching the XPath."""
        ...

    async def type_text(self, xpath: str, text: str) -> None:
        """Type text into the element matching the XPath.

        Clicks the element first to focus it, then types.
        """
        ...

    async def clear_and_type(self, xpath: str, text: str) -> None:
        """Clear an input field and type new text."""
        ...

    async def press_key(self, key: str) -> None:
        """Press a keyboard key (e.g., 'Enter', 'Tab', 'Escape')."""
        ...

    async def key_combo(self, keys: str) -> None:
        """Press a key combination (e.g., 'Control+a', 'Meta+c')."""
        ...

    async def scroll(self, direction: str = "down", amount: int = 3) -> None:
        """Scroll the page in the given direction.

        Args:
            direction: 'up', 'down', 'left', 'right'
            amount: Number of scroll units
        """
        ...

    async def scroll_element(
        self, xpath: str, direction: str = "down", amount: int = 3
    ) -> None:
        """Scroll within a specific element."""
        ...

    async def move_to(self, xpath: str) -> None:
        """Move the mouse to the element matching the XPath."""
        ...

    async def drag(self, from_xpath: str, to_xpath: str) -> None:
        """Drag from one element to another."""
        ...

    async def select_option(self, xpath: str, value: str) -> None:
        """Select an option in a dropdown by value."""
        ...

    async def navigate(self, url: str) -> None:
        """Navigate to a URL."""
        ...

    async def go_back(self) -> None:
        """Navigate back in browser history."""
        ...

    async def go_forward(self) -> None:
        """Navigate forward in browser history."""
        ...

    async def refresh(self) -> None:
        """Refresh the current page."""
        ...

    # ─── Advanced ─────────────────────────────────────────────────────────

    async def evaluate_js(self, script: str) -> Any:
        """Execute JavaScript in the page context and return the result."""
        ...

    async def wait_for_navigation(self, timeout_ms: int = 5000) -> None:
        """Wait for a navigation event to complete."""
        ...

    async def wait_ms(self, ms: int) -> None:
        """Wait for a specified duration."""
        ...

    async def find_elements_by_xpath(self, xpath: str) -> list[dict[str, Any]]:
        """Find all elements matching an XPath and return their basic info.

        Returns list of dicts with keys: xpath, tag, text, attributes.
        """
        ...
