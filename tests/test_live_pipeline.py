"""Live integration test for the full PreAct pipeline.

Tests the complete cycle:
1. CUA exploration → record trace → compile to state machine
2. Store in RAG
3. Retrieve from RAG → RPA replay

Requires network access and Gemini API key.
Mark with @pytest.mark.live to skip in CI.
"""

import asyncio
import os
import shutil

import pytest

# Skip if no API key
pytestmark = pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set",
)


@pytest.fixture
def clean_data_dirs():
    """Clean up test data directories."""
    dirs = ["test_rag_db", "test_traces"]
    yield
    for d in dirs:
        if os.path.exists(d):
            shutil.rmtree(d)


@pytest.mark.asyncio
@pytest.mark.timeout(120)
async def test_full_pipeline_live(clean_data_dirs):
    """Test the complete PreAct pipeline against a real website."""
    from preact.config import CUAConfig, LLMConfig, PreActConfig, RAGConfig
    from preact.core.agent import PreActAgent
    from preact.environment.browser import BrowserEnvironment
    from preact.llm.client import LLMClient

    config = PreActConfig(
        llm=LLMConfig(model="gemini-3-flash-preview"),
        cua=CUAConfig(max_steps=8, screenshot_delay_ms=300),
        rag=RAGConfig(persist_dir="test_rag_db"),
    )

    llm = LLMClient(config.llm)
    env = BrowserEnvironment(
        headless=True, start_url="https://httpbin.org/forms/post"
    )

    await env.start()
    try:
        agent = PreActAgent(env, llm, config)

        # ─── Run 1: CUA exploration ─────────────────────────────
        result1 = await agent.execute_task(
            "Fill the form with customer name 'Alice', select Small size, add bacon topping, and submit",
            force_cua=True,
        )

        assert result1.success, f"Run 1 failed: {result1.error}"
        assert result1.mode == "cua"
        run1_time = result1.total_time_ms
        run1_tokens = result1.total_input_tokens + result1.total_output_tokens

    finally:
        await env.stop()

    # ─── Run 2: RPA replay ──────────────────────────────────
    # New environment, same agent (has RAG store)
    env2 = BrowserEnvironment(
        headless=True, start_url="https://httpbin.org/forms/post"
    )
    await env2.start()
    try:
        # Re-create agent with same config (RAG store persists)
        agent2 = PreActAgent(env2, llm, config)
        llm.reset_usage()

        result2 = await agent2.execute_task(
            "Fill the form with customer name 'Bob', select Small size, add bacon topping, and submit",
        )

        run2_time = result2.total_time_ms
        run2_tokens = result2.total_input_tokens + result2.total_output_tokens

        print(f"\n═══ Results ═══")
        print(f"Run 1: {run1_time:.0f}ms, {run1_tokens} tokens")
        print(f"Run 2: {run2_time:.0f}ms, {run2_tokens} tokens")
        if run2_time > 0:
            print(f"Speedup: {run1_time / run2_time:.1f}x")

    finally:
        await env2.stop()
