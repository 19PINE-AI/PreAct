"""Playwright-based browser environment implementation."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

logger = logging.getLogger(__name__)


class BrowserEnvironment:
    """Browser environment using Playwright.

    Implements the ComputerEnvironment protocol for web-based interactions.
    Supports Chromium, Firefox, and WebKit.
    """

    def __init__(
        self,
        headless: bool = True,
        browser_type: str = "chromium",
        viewport: dict[str, int] | None = None,
        start_url: str | None = None,
        slow_mo: int = 0,
        storage_state: str | None = None,
    ):
        self._headless = headless
        self._browser_type = browser_type
        self._viewport = viewport or {"width": 1280, "height": 720}
        self._start_url = start_url
        self._slow_mo = slow_mo
        self._storage_state = storage_state

        self._pw: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("Environment not started. Call start() first.")
        return self._page

    # ─── Lifecycle ────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Launch browser and create initial page."""
        self._pw = await async_playwright().start()
        launcher = getattr(self._pw, self._browser_type)
        self._browser = await launcher.launch(
            headless=self._headless,
            slow_mo=self._slow_mo,
        )
        ctx_kwargs: dict = {
            "viewport": self._viewport,
            "ignore_https_errors": True,
        }
        if self._storage_state:
            ctx_kwargs["storage_state"] = self._storage_state
        self._context = await self._browser.new_context(**ctx_kwargs)
        self._page = await self._context.new_page()
        if self._start_url:
            await self._page.goto(self._start_url, wait_until="domcontentloaded")
        logger.info("Browser environment started (%s)", self._browser_type)

    async def stop(self) -> None:
        """Close browser and cleanup."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()
        self._page = None
        self._context = None
        self._browser = None
        self._pw = None
        logger.info("Browser environment stopped")

    async def reset(self) -> None:
        """Reset by clearing cookies/storage and navigating to start URL."""
        if self._context:
            await self._context.clear_cookies()
        if self._start_url and self._page:
            await self._page.goto(
                self._start_url, wait_until="domcontentloaded"
            )

    # ─── Observation ──────────────────────────────────────────────────────

    async def screenshot(self) -> bytes:
        """Capture full page screenshot as PNG bytes."""
        return await self.page.screenshot(type="png", full_page=False)

    async def element_screenshot(self, xpath: str) -> bytes:
        """Capture screenshot of a specific element."""
        locator = self.page.locator(f"xpath={xpath}").first
        return await locator.screenshot(type="png")

    async def element_exists(
        self, xpath: str, timeout_ms: int = 5000
    ) -> bool:
        """Poll for element existence within timeout."""
        try:
            locator = self.page.locator(f"xpath={xpath}").first
            await locator.wait_for(state="visible", timeout=timeout_ms)
            return True
        except Exception:
            # Fallback: check if element is in DOM but hidden (e.g. collapsed sidebar)
            try:
                locator = self.page.locator(f"xpath={xpath}").first
                fallback_timeout = min(timeout_ms, 1000)
                await locator.wait_for(state="attached", timeout=fallback_timeout)
                return True
            except Exception:
                return False

    async def element_text(self, xpath: str) -> str:
        """Extract text content of an element."""
        locator = self.page.locator(f"xpath={xpath}").first
        return await locator.inner_text()

    async def element_attribute(
        self, xpath: str, attribute: str
    ) -> str | None:
        """Get an attribute value of an element."""
        locator = self.page.locator(f"xpath={xpath}").first
        return await locator.get_attribute(attribute)

    async def get_page_url(self) -> str:
        return self.page.url

    async def get_page_title(self) -> str:
        return await self.page.title()

    async def get_dom_snapshot(self) -> str:
        """Get simplified DOM snapshot for recording.

        Returns a compact representation focusing on interactive elements.
        """
        return await self.page.evaluate("""() => {
            function serializeNode(node, depth = 0) {
                if (depth > 6) return '';
                if (node.nodeType === Node.TEXT_NODE) {
                    const text = node.textContent.trim();
                    return text ? text.slice(0, 100) : '';
                }
                if (node.nodeType !== Node.ELEMENT_NODE) return '';

                const tag = node.tagName.toLowerCase();
                const skip = new Set(['script', 'style', 'noscript', 'svg', 'path']);
                if (skip.has(tag)) return '';

                const attrs = [];
                for (const attr of ['id', 'class', 'name', 'type', 'href', 'role',
                                     'aria-label', 'placeholder', 'value', 'data-testid']) {
                    const val = node.getAttribute(attr);
                    if (val) attrs.push(`${attr}="${val.slice(0, 80)}"`);
                }
                const attrStr = attrs.length ? ' ' + attrs.join(' ') : '';

                const children = Array.from(node.childNodes)
                    .map(c => serializeNode(c, depth + 1))
                    .filter(Boolean)
                    .join('');

                return `<${tag}${attrStr}>${children}</${tag}>`;
            }
            return serializeNode(document.body);
        }""")

    # ─── Actions ──────────────────────────────────────────────────────────

    async def click(self, xpath: str) -> None:
        locator = self.page.locator(f"xpath={xpath}").first
        try:
            await locator.click(timeout=5000)
        except Exception as e:
            if "not visible" in str(e).lower():
                # Fallback: JS click for hidden elements (e.g. collapsed sidebar menus)
                logger.warning("Element not visible, trying JS click: %s", xpath)
                await locator.evaluate("el => el.click()")
            else:
                raise

    async def double_click(self, xpath: str) -> None:
        locator = self.page.locator(f"xpath={xpath}").first
        await locator.dblclick(timeout=5000)

    async def right_click(self, xpath: str) -> None:
        locator = self.page.locator(f"xpath={xpath}").first
        await locator.click(button="right", timeout=5000)

    async def type_text(self, xpath: str, text: str) -> None:
        locator = self.page.locator(f"xpath={xpath}").first
        await locator.click()
        await locator.fill(text)

    async def clear_and_type(self, xpath: str, text: str) -> None:
        locator = self.page.locator(f"xpath={xpath}").first
        await locator.click(click_count=3)
        await locator.fill(text)

    async def press_key(self, key: str) -> None:
        await self.page.keyboard.press(key)

    async def key_combo(self, keys: str) -> None:
        await self.page.keyboard.press(keys)

    async def scroll(
        self, direction: str = "down", amount: int = 3
    ) -> None:
        delta_map = {
            "down": (0, 100 * amount),
            "up": (0, -100 * amount),
            "right": (100 * amount, 0),
            "left": (-100 * amount, 0),
        }
        dx, dy = delta_map.get(direction, (0, 100 * amount))
        await self.page.mouse.wheel(dx, dy)

    async def scroll_element(
        self, xpath: str, direction: str = "down", amount: int = 3
    ) -> None:
        locator = self.page.locator(f"xpath={xpath}").first
        box = await locator.bounding_box()
        if box:
            cx = box["x"] + box["width"] / 2
            cy = box["y"] + box["height"] / 2
            await self.page.mouse.move(cx, cy)
            delta = 100 * amount * (1 if direction in ("down", "right") else -1)
            if direction in ("up", "down"):
                await self.page.mouse.wheel(0, delta)
            else:
                await self.page.mouse.wheel(delta, 0)

    async def move_to(self, xpath: str) -> None:
        locator = self.page.locator(f"xpath={xpath}").first
        await locator.hover()

    async def drag(self, from_xpath: str, to_xpath: str) -> None:
        src = self.page.locator(f"xpath={from_xpath}").first
        dst = self.page.locator(f"xpath={to_xpath}").first
        await src.drag_to(dst)

    async def select_option(self, xpath: str, value: str) -> None:
        locator = self.page.locator(f"xpath={xpath}").first
        await locator.select_option(value)

    async def navigate(self, url: str) -> None:
        # Handle relative URLs by resolving against current page
        if url.startswith("/") and self._page:
            current = self._page.url
            from urllib.parse import urlparse
            parsed = urlparse(current)
            url = f"{parsed.scheme}://{parsed.netloc}{url}"
        await self.page.goto(url, wait_until="domcontentloaded")

    async def go_back(self) -> None:
        await self.page.go_back()

    async def go_forward(self) -> None:
        await self.page.go_forward()

    async def refresh(self) -> None:
        await self.page.reload()

    # ─── Advanced ─────────────────────────────────────────────────────────

    async def evaluate_js(self, script: str) -> Any:
        return await self.page.evaluate(script)

    async def wait_for_navigation(self, timeout_ms: int = 5000) -> None:
        try:
            await self.page.wait_for_load_state(
                "domcontentloaded", timeout=timeout_ms
            )
        except Exception:
            pass

    async def wait_ms(self, ms: int) -> None:
        await asyncio.sleep(ms / 1000.0)

    async def find_elements_by_xpath(
        self, xpath: str
    ) -> list[dict[str, Any]]:
        """Find all elements matching an XPath and return basic info."""
        elements = self.page.locator(f"xpath={xpath}")
        count = await elements.count()
        results = []
        for i in range(min(count, 50)):
            el = elements.nth(i)
            tag = await el.evaluate("el => el.tagName.toLowerCase()")
            text = await el.evaluate(
                "el => (el.textContent || '').trim().slice(0, 200)"
            )
            results.append({"index": i, "tag": tag, "text": text})
        return results

    # ─── XPath Resolution ─────────────────────────────────────────────────

    async def resolve_element_xpath(self, x: int, y: int) -> str | None:
        """Given coordinates, resolve the element at that position to an XPath.

        Used by the Interaction Recorder to get stable selectors.
        """
        return await self.page.evaluate(
            """([x, y]) => {
            const el = document.elementFromPoint(x, y);
            if (!el) return null;
            function getXPath(element) {
                if (element.id) return `//*[@id="${element.id}"]`;
                if (element === document.body) return '//body';
                const parent = element.parentElement;
                if (!parent) return '/' + element.tagName.toLowerCase();
                const siblings = Array.from(parent.children)
                    .filter(c => c.tagName === element.tagName);
                const idx = siblings.indexOf(element) + 1;
                const suffix = siblings.length > 1 ? `[${idx}]` : '';
                return getXPath(parent) + '/' + element.tagName.toLowerCase() + suffix;
            }
            return getXPath(el);
        }""",
            [x, y],
        )
