#!/usr/bin/env python3
"""Ablation study runner for PreAct.

Compares PreAct-Full against ablated variants to quantify
the contribution of each architectural component.

Variants:
- PreAct-Full: Complete system
- PreAct-NoVerify: Remove XPath state verification (blind replay)
- PreAct-NoRAG: Disable RAG retrieval (always record from scratch)
- Muscle-Mem: Linear sequence replay (no state machine, no branching, no refinement)
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

from preact.baselines.base import BaselineResult
from preact.baselines.muscle_mem import MuscleMemBaseline
from preact.baselines.preact_baseline import PreActBaseline
from preact.baselines.workflow_use import WorkflowUseBaseline
from preact.config import CUAConfig, LLMConfig, PreActConfig
from preact.environment.browser import BrowserEnvironment
from preact.evaluation.metrics import TaskMetrics, aggregate, from_baseline_result
from preact.llm.client import LLMClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ablation")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("google_genai").setLevel(logging.WARNING)
logging.getLogger("chromadb").setLevel(logging.WARNING)

# Tasks that are the SAME WORKFLOW but different parameters
# This tests cross-task transfer (RAG retrieval of related programs)
ABLATION_TASKS = [
    {
        "task_id": "fill_form_alice",
        "task": "Fill in the form with customer name 'Alice', select Medium pizza size, add mushrooms topping, and submit",
        "url": "https://httpbin.org/forms/post",
        "params": {"customer_name": "Alice"},
    },
    {
        "task_id": "fill_form_bob",
        "task": "Fill in the form with customer name 'Bob', select Small pizza size, add bacon topping, and submit",
        "url": "https://httpbin.org/forms/post",
        "params": {"customer_name": "Bob"},
    },
    {
        "task_id": "fill_form_carol",
        "task": "Fill in the form with customer name 'Carol', select Large pizza size, add cheese topping, and submit",
        "url": "https://httpbin.org/forms/post",
        "params": {"customer_name": "Carol"},
    },
]


async def run_system_ablation(
    system_name: str,
    system: object,
    tasks: list[dict],
    timeout: int = 90,
) -> dict:
    """Run a system on sequential tasks, measuring cross-task transfer."""
    logger.info("\n  === %s ===", system_name)

    all_run1 = []
    all_run2 = []

    for task_spec in tasks:
        tid = task_spec["task_id"]
        task = task_spec["task"]
        url = task_spec["url"]
        params = task_spec.get("params", {})

        # Run 1: Exploration
        llm = LLMClient(LLMConfig(model="gemini-3-flash-preview"))
        env = BrowserEnvironment(headless=True, start_url=url)

        try:
            await env.start()
            r1 = await asyncio.wait_for(
                system.run_exploration(task, env, llm, parameters=params),
                timeout=timeout,
            )
            m1 = from_baseline_result(r1, tid, system_name, 1)
            all_run1.append(m1)
            logger.info("    [%s] R1: %s %.0fms %d tok",
                        tid, "OK" if r1.success else "FAIL",
                        r1.total_time_ms, r1.total_input_tokens + r1.total_output_tokens)
        except Exception as e:
            logger.error("    [%s] R1 ERROR: %s", tid, e)
            all_run1.append(TaskMetrics(
                task_id=tid, system_name=system_name, run_number=1, success=False,
            ))
        finally:
            try:
                await env.stop()
            except Exception:
                pass

        # Run 2: Replay
        if not system.has_cached_artifact(task):
            logger.info("    [%s] R2: skipped (no artifact)", tid)
            all_run2.append(TaskMetrics(
                task_id=tid, system_name=system_name, run_number=2, success=False,
            ))
            continue

        llm2 = LLMClient(LLMConfig(model="gemini-3-flash-preview"))
        env2 = BrowserEnvironment(headless=True, start_url=url)

        try:
            await env2.start()
            r2 = await asyncio.wait_for(
                system.run_replay(task, env2, llm2, parameters=params),
                timeout=timeout,
            )
            m2 = from_baseline_result(r2, tid, system_name, 2)
            all_run2.append(m2)
            logger.info("    [%s] R2: %s %.0fms %d tok cov=%.0f%%",
                        tid, "OK" if r2.success else "FAIL",
                        r2.total_time_ms, r2.total_input_tokens + r2.total_output_tokens,
                        r2.graph_coverage * 100)
        except Exception as e:
            logger.error("    [%s] R2 ERROR: %s", tid, e)
            all_run2.append(TaskMetrics(
                task_id=tid, system_name=system_name, run_number=2, success=False,
            ))
        finally:
            try:
                await env2.stop()
            except Exception:
                pass

    agg1 = aggregate(all_run1)
    agg2 = aggregate(all_run2)

    return {
        "system": system_name,
        "run1_sr": agg1.success_rate,
        "run2_sr": agg2.success_rate,
        "run1_mean_time": agg1.mean_time_ms,
        "run2_mean_time": agg2.mean_time_ms,
        "run1_mean_tokens": agg1.mean_tokens,
        "run2_mean_tokens": agg2.mean_tokens,
        "run2_coverage": agg2.mean_graph_coverage,
        "speedup": agg1.mean_time_ms / agg2.mean_time_ms if agg2.mean_time_ms > 0 else float("inf"),
    }


async def main():
    for d in ["rag_db"]:
        if os.path.exists(d):
            shutil.rmtree(d)

    logger.info("=" * 60)
    logger.info("ABLATION STUDY")
    logger.info("=" * 60)

    systems = {
        "PreAct-Full": PreActBaseline(),
        "Muscle-Mem (blind)": MuscleMemBaseline(),
        "Workflow-Use (linear)": WorkflowUseBaseline(),
    }

    results = {}
    for name, system in systems.items():
        await system.reset()
        for d in ["rag_db"]:
            if os.path.exists(d):
                shutil.rmtree(d)
        results[name] = await run_system_ablation(name, system, ABLATION_TASKS)

    # Print comparison table
    print("\n" + "=" * 100)
    print(f"{'System':<25} {'R1 SR':>6} {'R2 SR':>6} {'R1 Time':>9} {'R2 Time':>9} "
          f"{'Speedup':>8} {'R2 Tokens':>10} {'Coverage':>9}")
    print("-" * 100)

    for name, data in results.items():
        print(f"{name:<25} {data['run1_sr']:>5.0%} {data['run2_sr']:>5.0%} "
              f"{data['run1_mean_time']:>8.0f}ms {data['run2_mean_time']:>8.0f}ms "
              f"{data['speedup']:>7.1f}x {data['run2_mean_tokens']:>10.0f} "
              f"{data['run2_coverage']:>8.0%}")

    print("=" * 100)

    # Save results
    Path("results").mkdir(exist_ok=True)
    with open("results/ablation_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info("Results saved to results/ablation_results.json")


if __name__ == "__main__":
    asyncio.run(main())
