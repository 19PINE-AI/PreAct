#!/usr/bin/env python3
"""Cross-task transfer test.

Validates PreAct's RAG retrieval: compile a program for Task A,
then use it to execute a similar Task B without re-exploration.

This tests the "library growth" capability from Section 2.4.
"""

import asyncio
import json
import logging
import os
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from preact.config import LLMConfig, PreActConfig
from preact.core.agent import PreActAgent
from preact.environment.browser import BrowserEnvironment
from preact.llm.client import LLMClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("transfer_test")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("google_genai").setLevel(logging.WARNING)
logging.getLogger("chromadb").setLevel(logging.WARNING)


async def main():
    # Clean RAG DB
    for d in ["rag_db"]:
        if os.path.exists(d):
            shutil.rmtree(d)

    config = PreActConfig()
    llm = LLMClient(LLMConfig(model="gemini-3-flash-preview"))
    url = "https://httpbin.org/forms/post"

    logger.info("=" * 60)
    logger.info("CROSS-TASK TRANSFER TEST")
    logger.info("=" * 60)

    # ─── Phase 1: Learn from Task A ──────────────────────────
    logger.info("\n--- Phase 1: Learn from Task A ---")
    task_a = "Fill in the form with customer name 'Alice', select Medium pizza size, add mushrooms topping, and submit the order"

    env1 = BrowserEnvironment(headless=True, start_url=url)
    await env1.start()
    try:
        agent = PreActAgent(env1, llm, config)
        result_a = await agent.execute_task(task_a, force_cua=True)
        logger.info("Task A: %s (%.0fms, %d tokens)",
                     "SUCCESS" if result_a.success else "FAILED",
                     result_a.total_time_ms,
                     result_a.total_input_tokens + result_a.total_output_tokens)
        logger.info("Program stored: %s", result_a.program_id)
    finally:
        await env1.stop()

    if not result_a.success:
        logger.error("Task A failed, cannot test transfer")
        return

    # ─── Phase 2: Execute Task B using Task A's program ──────
    logger.info("\n--- Phase 2: Execute Task B (different params, same workflow) ---")
    task_b = "Fill in the form with customer name 'Bob', select Large pizza size, add cheese topping, and submit the order"

    llm2 = LLMClient(LLMConfig(model="gemini-3-flash-preview"))
    env2 = BrowserEnvironment(headless=True, start_url=url)
    await env2.start()
    try:
        # Update agent with new env/llm
        agent.env = env2
        agent.llm = llm2
        agent.recorder.env = env2
        agent.executor.env = env2
        agent.executor.llm = llm2
        agent.cua.env = env2
        agent.cua.llm = llm2
        agent.cua.recorder.env = env2

        llm2.reset_usage()
        result_b = await agent.execute_task(task_b)

        logger.info("Task B: %s mode=%s (%.0fms, %d tokens)",
                     "SUCCESS" if result_b.success else "FAILED",
                     result_b.mode,
                     result_b.total_time_ms,
                     result_b.total_input_tokens + result_b.total_output_tokens)

        if result_b.execution_result:
            logger.info("  States visited: %s", result_b.execution_result.states_visited)
            logger.info("  Graph coverage: %.0f%%", result_b.execution_result.graph_coverage * 100)
            logger.info("  Actions via RPA: %d", result_b.execution_result.actions_via_rpa)
            logger.info("  Actions via CUA: %d", result_b.execution_result.actions_via_cua)
    finally:
        await env2.stop()

    # ─── Phase 3: Execute Task C (completely different params) ─
    logger.info("\n--- Phase 3: Execute Task C (yet another variation) ---")
    task_c = "Fill in the pizza order form with customer name 'Carol', select Small size, add bacon, and submit"

    llm3 = LLMClient(LLMConfig(model="gemini-3-flash-preview"))
    env3 = BrowserEnvironment(headless=True, start_url=url)
    await env3.start()
    try:
        agent.env = env3
        agent.llm = llm3
        agent.recorder.env = env3
        agent.executor.env = env3
        agent.executor.llm = llm3
        agent.cua.env = env3
        agent.cua.llm = llm3
        agent.cua.recorder.env = env3

        llm3.reset_usage()
        result_c = await agent.execute_task(task_c)

        logger.info("Task C: %s mode=%s (%.0fms, %d tokens)",
                     "SUCCESS" if result_c.success else "FAILED",
                     result_c.mode,
                     result_c.total_time_ms,
                     result_c.total_input_tokens + result_c.total_output_tokens)

        if result_c.execution_result:
            logger.info("  Graph coverage: %.0f%%", result_c.execution_result.graph_coverage * 100)
    finally:
        await env3.stop()

    # ─── Summary ──────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("CROSS-TASK TRANSFER RESULTS")
    print("-" * 70)
    print(f"Task A (learn):     {result_a.mode:>8} {result_a.total_time_ms:>8.0f}ms "
          f"{result_a.total_input_tokens + result_a.total_output_tokens:>6} tokens")

    if result_b:
        tokens_b = result_b.total_input_tokens + result_b.total_output_tokens
        print(f"Task B (transfer):  {result_b.mode:>8} {result_b.total_time_ms:>8.0f}ms "
              f"{tokens_b:>6} tokens")

    if result_c:
        tokens_c = result_c.total_input_tokens + result_c.total_output_tokens
        print(f"Task C (transfer):  {result_c.mode:>8} {result_c.total_time_ms:>8.0f}ms "
              f"{tokens_c:>6} tokens")

    print("=" * 70)

    if result_b and result_b.mode == "rpa":
        speedup = result_a.total_time_ms / result_b.total_time_ms
        print(f"\nCross-task transfer speedup: {speedup:.1f}x")
        print(f"Token savings: {(1 - tokens_b / (result_a.total_input_tokens + result_a.total_output_tokens)) * 100:.0f}%")


if __name__ == "__main__":
    asyncio.run(main())
