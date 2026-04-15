"""Docker container environment for OSWorld-style tasks.

Connects to a running Docker container that exposes a VNC/browser endpoint.
Uses the same Playwright interface but against a containerized browser.
"""

from __future__ import annotations

import logging

from preact.environment.browser import BrowserEnvironment

logger = logging.getLogger(__name__)


class DockerEnvironment(BrowserEnvironment):
    """Environment connecting to a browser inside a Docker container.

    For OSWorld evaluation, the benchmark runs inside Docker containers
    with a web-accessible browser. This environment connects Playwright
    to the container's browser endpoint via CDP (Chrome DevTools Protocol).
    """

    def __init__(
        self,
        cdp_url: str = "http://localhost:9222",
        viewport: dict[str, int] | None = None,
    ):
        super().__init__(headless=True, viewport=viewport)
        self._cdp_url = cdp_url

    async def start(self) -> None:
        """Connect to the Docker container's browser via CDP."""
        from playwright.async_api import async_playwright

        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.connect_over_cdp(self._cdp_url)
        contexts = self._browser.contexts
        if contexts:
            self._context = contexts[0]
            pages = self._context.pages
            self._page = pages[0] if pages else await self._context.new_page()
        else:
            self._context = await self._browser.new_context(
                viewport=self._viewport
            )
            self._page = await self._context.new_page()
        logger.info("Connected to Docker browser at %s", self._cdp_url)
