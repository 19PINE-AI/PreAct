"""Capture Playwright storage state for WebArena pre-authenticated sessions.

WebArena tasks requiring login need pre-authenticated browser sessions.
This module captures and saves Playwright storage state (cookies + localStorage)
for the shopping_admin site.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

AUTH_DIR = Path(__file__).parent / ".auth"

# Default WebArena credentials
ACCOUNTS = {
    "shopping_admin": {
        "username": "admin",
        "password": "admin123",
        "login_url_suffix": "/admin",
    },
    "shopping": {
        "username": "emma.lopez@gmail.com",
        "password": "Password.123",
        "login_url_suffix": "/customer/account/login/",
    },
}


async def capture_shopping_admin_auth(
    hostname: str = "localhost",
    port: int = 7780,
) -> Path:
    """Capture authenticated storage state for shopping_admin.

    Logs into the Magento admin panel and saves the browser state
    (cookies, localStorage) as a Playwright storage state JSON file.

    Returns:
        Path to the saved storage state file.
    """
    AUTH_DIR.mkdir(parents=True, exist_ok=True)
    state_path = AUTH_DIR / "shopping_admin_state.json"

    base_url = f"http://{hostname}:{port}"
    account = ACCOUNTS["shopping_admin"]

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            ignore_https_errors=True,
        )
        page = await context.new_page()

        logger.info("Navigating to %s/admin for login...", base_url)
        await page.goto(f"{base_url}/admin", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        # Fill login form
        logger.info("Logging in as %s...", account["username"])
        await page.fill("#username", account["username"])
        await page.fill("#login", account["password"])
        await page.click(".action-login")

        # Wait for dashboard to load
        await page.wait_for_timeout(5000)

        # Check if login succeeded
        current_url = page.url
        if "/admin/dashboard" in current_url or "/admin" in current_url:
            logger.info("Login successful, saving storage state")
        else:
            logger.warning(
                "Login may have failed, current URL: %s", current_url
            )

        # Dismiss any modal popups (Magento sometimes shows release notes)
        try:
            modal_close = page.locator(".modal-popup .action-close")
            if await modal_close.count() > 0:
                await modal_close.first.click()
                await page.wait_for_timeout(500)
        except Exception:
            pass

        # Save storage state
        await context.storage_state(path=str(state_path))
        await browser.close()

    logger.info("Storage state saved to %s", state_path)
    return state_path


async def capture_shopping_auth(
    hostname: str = "localhost",
    port: int = 7780,
) -> Path:
    """Capture authenticated storage state for shopping (customer-facing).

    Logs into the Magento storefront as a customer and saves the browser state.

    Returns:
        Path to the saved storage state file.
    """
    AUTH_DIR.mkdir(parents=True, exist_ok=True)
    state_path = AUTH_DIR / "shopping_state.json"

    base_url = f"http://{hostname}:{port}"
    account = ACCOUNTS["shopping"]

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            ignore_https_errors=True,
        )
        page = await context.new_page()

        logger.info("Navigating to %s/customer/account/login/ ...", base_url)
        await page.goto(
            f"{base_url}/customer/account/login/",
            wait_until="domcontentloaded",
        )
        await page.wait_for_timeout(2000)

        # Fill login form
        logger.info("Logging in as %s...", account["username"])
        await page.get_by_label("Email", exact=True).fill(account["username"])
        await page.get_by_label("Password", exact=True).fill(account["password"])
        await page.get_by_role("button", name="Sign In").click()

        # Wait for account page to load
        await page.wait_for_timeout(5000)

        current_url = page.url
        if "/customer/account" in current_url:
            logger.info("Shopping login successful, saving storage state")
        else:
            logger.warning(
                "Shopping login may have failed, current URL: %s", current_url
            )

        # Save storage state
        await context.storage_state(path=str(state_path))
        await browser.close()

    logger.info("Shopping storage state saved to %s", state_path)
    return state_path


def get_auth_state_path(site: str = "shopping_admin") -> Path | None:
    """Get the path to a saved auth state file, or None if not captured."""
    state_path = AUTH_DIR / f"{site}_state.json"
    if state_path.exists():
        return state_path
    return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import sys
    hostname = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    site = sys.argv[2] if len(sys.argv) > 2 else "all"
    if site in ("all", "shopping_admin"):
        asyncio.run(capture_shopping_admin_auth(hostname))
    if site in ("all", "shopping"):
        asyncio.run(capture_shopping_auth(hostname))
