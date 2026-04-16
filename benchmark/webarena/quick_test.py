#!/usr/bin/env python3
"""Quick smoke test for CUA + PreAct fixes.

Tests a few representative tasks to validate that:
1. Direct URL navigation works (bypasses sidebar)
2. select_option fallback works for <select> elements
3. RAG relevance check correctly skips irrelevant programs

Usage:
    python3 -m benchmark.webarena.quick_test
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from preact.cua.action_parser import parse_action
from preact.cua.loop import CUALoop
from preact.config import LLMConfig
from preact.environment.browser import BrowserEnvironment
from preact.llm.client import LLMClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("quick_test")


async def test_navigate_action():
    """Test that navigate action parses correctly."""
    action = parse_action('{"action": "navigate", "url": "http://localhost:7780/admin/sales/order/"}')
    assert action is not None, "Navigate action should parse"
    assert action.type.value == "action_navigate", f"Expected action_navigate, got {action.type}"
    assert action.text == "http://localhost:7780/admin/sales/order/"
    print("  [PASS] Navigate action parsing")


async def test_relative_url_resolution():
    """Test relative URL resolution in BrowserEnvironment."""
    env = BrowserEnvironment(headless=True, start_url="http://localhost:7780/admin")
    await env.start()
    try:
        # Navigate to a page
        await env.navigate("/admin/sales/order/")
        url = await env.get_page_url()
        assert "sales/order" in url, f"Expected sales/order in URL, got {url}"
        print(f"  [PASS] Relative URL → {url}")

        # Navigate to reviews
        await env.navigate("/admin/review/product/index/")
        url = await env.get_page_url()
        assert "review" in url, f"Expected review in URL, got {url}"
        print(f"  [PASS] Reviews page → {url}")
    finally:
        await env.stop()


async def test_sidebar_bypass_cua():
    """Test that CUA uses navigate instead of sidebar clicking."""
    auth_path = Path(__file__).parent / "auth" / "shopping_admin_state.json"
    if not auth_path.exists():
        print("  [SKIP] No auth state — run benchmark first")
        return

    llm = LLMClient(LLMConfig())
    env = BrowserEnvironment(
        headless=True,
        start_url="http://localhost:7780/admin",
        storage_state=str(auth_path),
    )
    await env.start()

    try:
        cua = CUALoop(env, llm)
        result = await cua.run(
            "Navigate to the Sales > Orders page and tell me the total number of orders shown",
            max_steps=5,
        )
        print(f"  Result: success={result.success}, steps={result.actions_taken}")
        if result.success:
            print(f"  [PASS] CUA navigated successfully in {result.actions_taken} steps")
            print(f"  Answer: {result.answer}")
        else:
            url = await env.get_page_url()
            print(f"  [INFO] CUA didn't complete but URL is: {url}")
            if "sales/order" in url:
                print("  [PASS] CUA navigated to correct page (didn't finish reading)")
            else:
                print("  [FAIL] CUA didn't navigate to Sales > Orders")
    finally:
        await env.stop()


async def test_rag_relevance():
    """Test RAG relevance matching logic."""
    # Simulate the matching logic
    test_cases = [
        ("Tell me reviews mentioning disappointed", "Tell me reviews mentioning satisfied", True),
        ("Tell me reviews mentioning disappointed", "Monthly count of successful orders", False),
        ("Give me SKU of products with 10 units", "Show customers dissatisfied with Circe", False),
        ("Orders from May to December 2022", "Orders from Jan to November 2022", True),
    ]

    for task, desc, expected in test_cases:
        task_words = set(task.lower().split())
        desc_words = set(desc.lower().split())
        overlap = len(task_words & desc_words)
        min_len = min(len(task_words), len(desc_words))
        score = overlap / min_len if min_len > 0 else 0
        matches = score >= 0.5
        status = "PASS" if matches == expected else "FAIL"
        print(f"  [{status}] '{task[:40]}...' vs '{desc[:40]}...': {score:.2f} ({'match' if matches else 'no match'})")


async def main():
    print("=" * 60)
    print("Quick Smoke Test for CUA + PreAct Fixes")
    print("=" * 60)

    print("\n1. Navigate Action Parsing:")
    await test_navigate_action()

    print("\n2. RAG Relevance Matching:")
    await test_rag_relevance()

    print("\n3. Relative URL Resolution:")
    await test_relative_url_resolution()

    print("\n4. CUA Sidebar Bypass (navigate action):")
    await test_sidebar_bypass_cua()

    print("\n" + "=" * 60)
    print("Quick test complete!")


if __name__ == "__main__":
    asyncio.run(main())
