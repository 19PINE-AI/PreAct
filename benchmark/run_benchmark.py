#!/usr/bin/env python3
"""Benchmark runner for PreAct vs baselines on WebArena-style tasks.

Runs all systems on the TestShop benchmark (10 multi-page e-commerce tasks)
using the two-run protocol:
  Run 1: Exploration (CUA + record)
  Run 2: Replay from compiled artifact

For each system, measures:
  - Task Success Rate (scored by evaluator)
  - Execution time
  - Token usage
  - Speedup factor (Run 1 -> Run 2)

Usage:
    python -m benchmark.run_benchmark                  # Full benchmark
    python -m benchmark.run_benchmark --tasks 3        # First 3 tasks only
    python -m benchmark.run_benchmark --systems preact  # PreAct only
"""

import argparse
import asyncio
import json
import logging
import os
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmark.evaluator import evaluate_string_match_async, evaluate_task
from benchmark.testsite.app import start_background
from preact.baselines.base import BaselineResult
from preact.baselines.muscle_mem import MuscleMemBaseline
from preact.baselines.preact_baseline import PreActBaseline
from preact.baselines.standard_cua import StandardCUABaseline
from preact.baselines.workflow_use import WorkflowUseBaseline
from preact.baselines.agent_rr import AgentRRBaseline
from preact.config import LLMConfig
from preact.environment.browser import BrowserEnvironment
from preact.evaluation.metrics import TaskMetrics, aggregate, from_baseline_result
from preact.llm.client import LLMClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("benchmark")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("google_genai").setLevel(logging.WARNING)
logging.getLogger("chromadb").setLevel(logging.WARNING)


AVAILABLE_SYSTEMS = {
    "standard_cua": ("Standard CUA", StandardCUABaseline),
    "muscle_mem": ("Muscle-Mem", MuscleMemBaseline),
    "workflow_use": ("Workflow-Use", WorkflowUseBaseline),
    "agent_rr": ("AgentRR", AgentRRBaseline),
    "preact": ("PreAct", PreActBaseline),
}


async def run_task_with_eval(
    system: object,
    task: dict,
    run_type: str,  # "exploration" or "replay"
    timeout: int = 120,
) -> dict:
    """Run a single task and evaluate the result."""
    task_id = task["task_id"]
    url = task["start_url"]

    llm = LLMClient(LLMConfig(model="gemini-3-flash-preview"))
    env = BrowserEnvironment(headless=True, start_url=url)

    result = {
        "task_id": task_id,
        "run_type": run_type,
        "success": False,
        "score": 0,
        "time_ms": 0,
        "tokens": 0,
        "actions": 0,
        "coverage": 0,
        "error": None,
    }

    try:
        await env.start()

        if run_type == "exploration":
            baseline_result = await asyncio.wait_for(
                system.run_exploration(task["intent"], env, llm),
                timeout=timeout,
            )
        else:
            baseline_result = await asyncio.wait_for(
                system.run_replay(task["intent"], env, llm),
                timeout=timeout,
            )

        result["success"] = baseline_result.success
        result["time_ms"] = baseline_result.total_time_ms
        result["tokens"] = baseline_result.total_input_tokens + baseline_result.total_output_tokens
        result["actions"] = baseline_result.actions_executed
        result["coverage"] = baseline_result.graph_coverage
        result["error"] = baseline_result.error

        # Evaluate using benchmark evaluator
        if baseline_result.success:
            eval_result = await evaluate_task(task, env, agent_answer="")
            # Also check page content for string_match tasks
            if task.get("eval", {}).get("eval_types") == ["string_match"]:
                ref = task["eval"].get("reference_answers", {})
                string_pass = await evaluate_string_match_async(env, ref)
                eval_result["score"] = 1 if string_pass else 0
                eval_result["details"]["string_match_page"] = string_pass

            result["score"] = eval_result["score"]
            result["eval_details"] = eval_result["details"]

    except asyncio.TimeoutError:
        result["error"] = f"timeout_{timeout}s"
        result["time_ms"] = timeout * 1000
    except Exception as e:
        result["error"] = str(e)
        logger.error("  Error: %s", e)
    finally:
        try:
            await env.stop()
        except Exception:
            pass

    return result


async def run_system_benchmark(
    system_name: str,
    system: object,
    tasks: list[dict],
    timeout: int = 120,
) -> dict:
    """Run a full benchmark for one system."""
    logger.info("=" * 70)
    logger.info("SYSTEM: %s (%d tasks)", system_name, len(tasks))
    logger.info("=" * 70)

    run1_results = []
    run2_results = []

    for task in tasks:
        tid = task["task_id"]
        difficulty = task.get("difficulty", "?")

        # ─── Run 1: Exploration ─────────────────
        logger.info("  [%s] Run 1 (%s, %s steps): %s",
                     tid, difficulty, task.get("num_steps", "?"),
                     task["intent"][:70])

        r1 = await run_task_with_eval(system, task, "exploration", timeout)
        run1_results.append(r1)

        status = "PASS" if r1["score"] else ("EXEC" if r1["success"] else "FAIL")
        logger.info("    %s: %.0fms, %d tok, %d actions, score=%d",
                     status, r1["time_ms"], r1["tokens"], r1["actions"], r1["score"])

        # ─── Run 2: Replay ──────────────────────
        if not system.has_cached_artifact(task["intent"]):
            logger.info("  [%s] Run 2: No artifact — skip", tid)
            run2_results.append({
                "task_id": tid, "run_type": "replay",
                "success": False, "score": 0, "time_ms": 0,
                "tokens": 0, "actions": 0, "coverage": 0,
                "error": "no_artifact",
            })
            continue

        logger.info("  [%s] Run 2 (replay):", tid)
        r2 = await run_task_with_eval(system, task, "replay", timeout)
        run2_results.append(r2)

        status = "PASS" if r2["score"] else ("EXEC" if r2["success"] else "FAIL")
        logger.info("    %s: %.0fms, %d tok, %d actions, score=%d, cov=%.0f%%",
                     status, r2["time_ms"], r2["tokens"], r2["actions"],
                     r2["score"], r2["coverage"] * 100)

    # Aggregate
    def avg(lst, key):
        vals = [x[key] for x in lst if x.get(key) is not None]
        return sum(vals) / len(vals) if vals else 0

    r1_sr = sum(1 for r in run1_results if r["score"]) / len(run1_results) if run1_results else 0
    r2_sr = sum(1 for r in run2_results if r["score"]) / len(run2_results) if run2_results else 0
    r1_exec_sr = sum(1 for r in run1_results if r["success"]) / len(run1_results) if run1_results else 0
    r2_exec_sr = sum(1 for r in run2_results if r["success"]) / len(run2_results) if run2_results else 0

    # Only compute speedup on tasks that succeeded in both runs
    speedups = []
    for r1, r2 in zip(run1_results, run2_results):
        if r1["success"] and r2["success"] and r2["time_ms"] > 0:
            speedups.append(r1["time_ms"] / r2["time_ms"])

    return {
        "system": system_name,
        "task_count": len(tasks),
        "run1": {
            "eval_sr": r1_sr,
            "exec_sr": r1_exec_sr,
            "mean_time_ms": avg(run1_results, "time_ms"),
            "mean_tokens": avg(run1_results, "tokens"),
            "per_task": run1_results,
        },
        "run2": {
            "eval_sr": r2_sr,
            "exec_sr": r2_exec_sr,
            "mean_time_ms": avg(run2_results, "time_ms"),
            "mean_tokens": avg(run2_results, "tokens"),
            "mean_coverage": avg(run2_results, "coverage"),
            "per_task": run2_results,
        },
        "mean_speedup": sum(speedups) / len(speedups) if speedups else 0,
        "speedups": speedups,
    }


def print_results_table(all_results: dict):
    """Print a formatted comparison table."""
    print("\n" + "=" * 120)
    print(f"{'System':<18} {'R1 Eval SR':>10} {'R1 Exec SR':>11} {'R2 Eval SR':>10} {'R2 Exec SR':>11} "
          f"{'R1 Time':>9} {'R2 Time':>9} {'Speedup':>8} {'R2 Tok':>8} {'R2 Cov':>7}")
    print("-" * 120)

    for name, data in sorted(all_results.items()):
        r1 = data["run1"]
        r2 = data["run2"]
        print(f"{name:<18} {r1['eval_sr']:>9.0%} {r1['exec_sr']:>10.0%} "
              f"{r2['eval_sr']:>9.0%} {r2['exec_sr']:>10.0%} "
              f"{r1['mean_time_ms']:>8.0f}ms {r2['mean_time_ms']:>8.0f}ms "
              f"{data['mean_speedup']:>7.1f}x {r2['mean_tokens']:>8.0f} "
              f"{r2['mean_coverage']:>6.0%}")

    print("=" * 120)

    # Per-task breakdown for successful replay systems
    print("\nPer-Task Run 2 Breakdown (replay):")
    print(f"{'Task':<20}", end="")
    for name in sorted(all_results.keys()):
        print(f" {name:>15}", end="")
    print()
    print("-" * (20 + 16 * len(all_results)))

    # Get task list from first system
    first_sys = next(iter(all_results.values()))
    for i, r2 in enumerate(first_sys["run2"]["per_task"]):
        tid = r2["task_id"]
        print(f"{tid:<20}", end="")
        for name in sorted(all_results.keys()):
            r = all_results[name]["run2"]["per_task"][i]
            if r["score"]:
                print(f" {r['time_ms']:>10.0f}ms ✓", end="")
            elif r["success"]:
                print(f" {r['time_ms']:>10.0f}ms ~", end="")
            elif r["error"] == "no_artifact":
                print(f"       {'skip':>8}", end="")
            else:
                print(f"       {'FAIL':>8}", end="")
        print()


async def main():
    parser = argparse.ArgumentParser(description="PreAct Benchmark")
    parser.add_argument("--tasks", type=int, default=None, help="Number of tasks to run")
    parser.add_argument("--systems", nargs="*", default=None, help="Systems to evaluate")
    parser.add_argument("--timeout", type=int, default=120, help="Per-task timeout (seconds)")
    parser.add_argument("--output", default="benchmark/results", help="Output directory")
    args = parser.parse_args()

    # Load tasks
    tasks_path = Path(__file__).parent / "tasks.json"
    with open(tasks_path) as f:
        all_tasks = json.load(f)

    if args.tasks:
        all_tasks = all_tasks[:args.tasks]

    # Select systems
    if args.systems:
        systems = {k: v for k, v in AVAILABLE_SYSTEMS.items() if k in args.systems}
    else:
        systems = AVAILABLE_SYSTEMS

    # Clean RAG state
    for d in ["rag_db"]:
        if os.path.exists(d):
            shutil.rmtree(d)

    # Start test shop server
    logger.info("Starting TestShop server on port 8080...")
    start_background(8080)

    # Verify server is running
    env_test = BrowserEnvironment(headless=True, start_url="http://localhost:8080")
    await env_test.start()
    title = await env_test.get_page_title()
    logger.info("TestShop verified: %s", title)
    await env_test.stop()

    # Run benchmark
    all_results = {}
    for key, (display_name, SystemClass) in systems.items():
        system = SystemClass()
        await system.reset()
        # Clean RAG for each system
        for d in ["rag_db"]:
            if os.path.exists(d):
                shutil.rmtree(d)

        result = await run_system_benchmark(display_name, system, all_tasks, args.timeout)
        all_results[display_name] = result

    # Print comparison table
    print_results_table(all_results)

    # Save results
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    results_path = output_dir / "benchmark_results.json"
    with open(results_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    logger.info("\nResults saved to %s", results_path)


if __name__ == "__main__":
    asyncio.run(main())
