#!/usr/bin/env python3
"""WebArena benchmark runner for PreAct.

Runs PreAct and baselines on the WebArena shopping_admin task subset
(182 tasks on a Magento admin panel).

Usage:
    python -m benchmark.webarena.run_webarena                        # Full run
    python -m benchmark.webarena.run_webarena --tasks 20             # First 20 tasks
    python -m benchmark.webarena.run_webarena --systems preact       # PreAct only
    python -m benchmark.webarena.run_webarena --task-ids 0 1 5 10    # Specific tasks
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

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from benchmark.webarena.auth import (
    capture_shopping_admin_auth,
    capture_shopping_auth,
    get_auth_state_path,
)
from benchmark.webarena.evaluator import evaluate_webarena_task
from benchmark.webarena.setup import generate_task_configs, start_shopping_admin
from preact.baselines.base import BaselineResult
from preact.baselines.muscle_mem import MuscleMemBaseline
from preact.baselines.preact_baseline import PreActBaseline
from preact.baselines.standard_cua import StandardCUABaseline
from preact.baselines.workflow_use import WorkflowUseBaseline
from preact.config import LLMConfig
from preact.environment.browser import BrowserEnvironment
from preact.llm.client import LLMClient

import sys

# Force unbuffered logging output
_handler = logging.StreamHandler(sys.stderr)
_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
))
_handler.flush = lambda: sys.stderr.flush()
logging.basicConfig(
    level=logging.INFO,
    handlers=[_handler],
)
logger = logging.getLogger("webarena")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("anthropic").setLevel(logging.WARNING)
logging.getLogger("chromadb").setLevel(logging.WARNING)
logging.getLogger("playwright").setLevel(logging.WARNING)


AVAILABLE_SYSTEMS = {
    "standard_cua": ("Standard CUA", StandardCUABaseline),
    "muscle_mem": ("Muscle-Mem", MuscleMemBaseline),
    "workflow_use": ("Workflow-Use", WorkflowUseBaseline),
    "preact": ("PreAct", PreActBaseline),
}

HOSTNAME = "localhost"
SHOPPING_ADMIN_PORT = 7780


def load_webarena_tasks(
    config_dir: Path | None = None,
    task_ids: list[int] | None = None,
    max_tasks: int | None = None,
) -> list[dict]:
    """Load WebArena task configs from generated JSON files.

    Falls back to generating from raw if no configs exist.
    """
    config_dir = config_dir or Path(__file__).parent / "configs"

    if not config_dir.exists() or not list(config_dir.glob("*.json")):
        logger.info("No task configs found, generating from raw...")
        generate_task_configs(
            HOSTNAME, ["shopping_admin", "shopping"], str(config_dir)
        )

    tasks = []
    for config_path in sorted(config_dir.glob("*.json")):
        with open(config_path) as f:
            task = json.load(f)
        tasks.append(task)

    # Filter by task IDs if specified
    if task_ids is not None:
        tasks = [t for t in tasks if t["task_id"] in task_ids]

    # Sort by task_id for reproducibility
    tasks.sort(key=lambda t: t["task_id"])

    if max_tasks:
        tasks = tasks[:max_tasks]

    return tasks


async def run_task_with_eval(
    system: object,
    task: dict,
    run_type: str,
    auth_states: dict[str, str | None] | None = None,
    timeout: int = 180,
) -> dict:
    """Run a single WebArena task and evaluate the result."""
    task_id = task["task_id"]
    start_url = task["start_url"]

    # Pick correct auth state based on task's storage_state field
    auth_state = None
    if auth_states:
        task_storage = task.get("storage_state", "")
        if "shopping_admin" in task_storage:
            auth_state = auth_states.get("shopping_admin")
        elif "shopping" in task_storage:
            auth_state = auth_states.get("shopping")

    llm = LLMClient(LLMConfig())
    env = BrowserEnvironment(
        headless=True,
        start_url=start_url,
        storage_state=auth_state,
    )

    result = {
        "task_id": task_id,
        "run_type": run_type,
        "intent": task["intent"],
        "success": False,
        "score": 0.0,
        "time_ms": 0,
        "tokens": 0,
        "actions": 0,
        "coverage": 0,
        "answer": "",
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
        result["tokens"] = (
            baseline_result.total_input_tokens
            + baseline_result.total_output_tokens
        )
        result["actions"] = baseline_result.actions_executed
        result["coverage"] = baseline_result.graph_coverage
        result["error"] = baseline_result.error

        # Extract agent answer from the baseline result
        agent_answer = baseline_result.extra.get("answer", "")
        result["answer"] = agent_answer

        # Evaluate using WebArena evaluator
        eval_result = await evaluate_webarena_task(
            config=task,
            env=env,
            agent_answer=agent_answer,
            hostname=HOSTNAME,
        )
        result["score"] = eval_result["score"]
        result["eval_details"] = eval_result["details"]

    except asyncio.TimeoutError:
        result["error"] = f"timeout_{timeout}s"
        result["time_ms"] = timeout * 1000
        # Capture partial token usage from the LLM client
        result["tokens"] = llm.total_input_tokens + llm.total_output_tokens
    except Exception as e:
        result["error"] = str(e)
        logger.error("  Error on task %s: %s", task_id, e)
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
    auth_states: dict[str, str | None] | None = None,
    timeout: int = 180,
) -> dict:
    """Run full benchmark for one system on WebArena tasks."""
    logger.info("=" * 70)
    logger.info("SYSTEM: %s (%d tasks)", system_name, len(tasks))
    logger.info("=" * 70)

    run1_results = []
    run2_results = []

    for i, task in enumerate(tasks):
        tid = task["task_id"]
        intent = task["intent"][:80]

        # Snapshot corpus state before Run 1 so we can identify
        # any program newly added by Run 1's compile path.
        pre_run1_pids: set[str] = set()
        if getattr(system, '_agent', None) and system._agent.store:
            try:
                pre_run1_pids = {
                    s["program_id"] for s in system._agent.store.list_programs()
                }
            except Exception:
                pre_run1_pids = set()

        # ---- Run 1: Exploration ----
        logger.info(
            "  [%d/%d] Task %s Run 1: %s",
            i + 1, len(tasks), tid, intent,
        )

        r1 = await run_task_with_eval(
            system, task, "exploration", auth_states, timeout
        )
        run1_results.append(r1)

        status = "PASS" if r1["score"] else (
            "EXEC" if r1["success"] else "FAIL"
        )
        logger.info(
            "    %s: %.0fms, %d tok, %d actions, score=%.1f",
            status, r1["time_ms"], r1["tokens"], r1["actions"], r1["score"],
        )
        sys.stderr.flush()

        # ---- Verify-before-store gate (Tier-3 #1 AB) ----
        # Mirrors the Android/OSWorld double-gate semantics: if Run 1's
        # compile path stored a NEW program, run a fresh-state verify-replay
        # and require score >= 1.0 to keep the new program. On failure,
        # delete *only* the newly-stored program(s); pre-existing verified
        # programs in the corpus are unaffected.
        import os as _os
        _gate_on = _os.environ.get('PREACT_VERIFY_BEFORE_STORE', 'on').lower() != 'off'
        new_pids: set[str] = set()
        if _gate_on and getattr(system, '_agent', None) and system._agent.store:
            try:
                post_run1_pids = {
                    s["program_id"] for s in system._agent.store.list_programs()
                }
                new_pids = post_run1_pids - pre_run1_pids
            except Exception:
                new_pids = set()
        if _gate_on and new_pids:
            verify = await run_task_with_eval(
                system, task, "replay", auth_states, timeout
            )
            if verify["score"] < 1.0:
                logger.info(
                    "    [verify-gate] Δreplay-fail: replay_score=%.1f, cov=%.0f%% — deleting %d new program(s)",
                    verify["score"], verify.get("coverage", 0) * 100, len(new_pids),
                )
                for pid in new_pids:
                    try:
                        await system._agent.store.delete(pid)
                    except Exception as e:
                        logger.warning("    [verify-gate] delete failed for %s: %s", pid, e)
            else:
                logger.info(
                    "    [verify-gate] replay-verified: replay_score=%.1f (kept %d new program(s))",
                    verify["score"], len(new_pids),
                )

        # ---- Run 2: Replay ----
        if not system.has_cached_artifact(task["intent"]):
            logger.info("  [%s] Run 2: No artifact — skip", tid)
            run2_results.append({
                "task_id": tid,
                "run_type": "replay",
                "intent": task["intent"],
                "success": False,
                "score": 0.0,
                "time_ms": 0,
                "tokens": 0,
                "actions": 0,
                "coverage": 0,
                "answer": "",
                "error": "no_artifact",
            })
            continue

        logger.info("  [%s] Run 2 (replay):", tid)
        r2 = await run_task_with_eval(
            system, task, "replay", auth_states, timeout
        )
        run2_results.append(r2)

        status = "PASS" if r2["score"] else (
            "EXEC" if r2["success"] else "FAIL"
        )
        logger.info(
            "    %s: %.0fms, %d tok, %d actions, score=%.1f, cov=%.0f%%",
            status, r2["time_ms"], r2["tokens"], r2["actions"],
            r2["score"], r2["coverage"] * 100,
        )

    return _aggregate_results(system_name, tasks, run1_results, run2_results)


def _aggregate_results(
    system_name: str,
    tasks: list[dict],
    run1_results: list[dict],
    run2_results: list[dict],
) -> dict:
    """Aggregate per-task results into summary statistics."""
    def avg(lst, key):
        vals = [x[key] for x in lst if x.get(key) is not None]
        return sum(vals) / len(vals) if vals else 0

    n1 = len(run1_results) or 1
    n2 = len(run2_results) or 1

    r1_sr = sum(1 for r in run1_results if r["score"] > 0) / n1
    r2_sr = sum(1 for r in run2_results if r["score"] > 0) / n2
    r1_exec_sr = sum(1 for r in run1_results if r["success"]) / n1
    r2_exec_sr = sum(1 for r in run2_results if r["success"]) / n2

    # Speedups for tasks that succeeded in both runs
    speedups = []
    for r1, r2 in zip(run1_results, run2_results):
        if r1["success"] and r2["success"] and r2["time_ms"] > 0:
            speedups.append(r1["time_ms"] / r2["time_ms"])

    # Per-eval-type breakdown
    eval_type_results = {}
    for r1 in run1_results:
        task = next(
            (t for t in tasks if t["task_id"] == r1["task_id"]), None
        )
        if not task:
            continue
        for et in task["eval"]["eval_types"]:
            if et not in eval_type_results:
                eval_type_results[et] = {"pass": 0, "total": 0}
            eval_type_results[et]["total"] += 1
            if r1["score"] > 0:
                eval_type_results[et]["pass"] += 1

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
        "mean_speedup": (
            sum(speedups) / len(speedups) if speedups else 0
        ),
        "speedups": speedups,
        "eval_type_breakdown": eval_type_results,
    }


def print_results_table(all_results: dict):
    """Print comparison table across all systems."""
    print("\n" + "=" * 130)
    print(
        f"{'System':<18} {'R1 Eval SR':>10} {'R1 Exec SR':>11} "
        f"{'R2 Eval SR':>10} {'R2 Exec SR':>11} "
        f"{'R1 Time':>9} {'R2 Time':>9} {'Speedup':>8} "
        f"{'R2 Tok':>8} {'R2 Cov':>7}"
    )
    print("-" * 130)

    for name, data in sorted(all_results.items()):
        r1 = data["run1"]
        r2 = data["run2"]
        print(
            f"{name:<18} {r1['eval_sr']:>9.0%} {r1['exec_sr']:>10.0%} "
            f"{r2['eval_sr']:>9.0%} {r2['exec_sr']:>10.0%} "
            f"{r1['mean_time_ms']:>8.0f}ms {r2['mean_time_ms']:>8.0f}ms "
            f"{data['mean_speedup']:>7.1f}x {r2['mean_tokens']:>8.0f} "
            f"{r2['mean_coverage']:>6.0%}"
        )

    print("=" * 130)

    # Per eval-type breakdown
    print("\nPer Eval-Type Breakdown (Run 1):")
    for name, data in sorted(all_results.items()):
        breakdown = data.get("eval_type_breakdown", {})
        if breakdown:
            parts = []
            for et, counts in sorted(breakdown.items()):
                pct = counts["pass"] / counts["total"] if counts["total"] else 0
                parts.append(
                    f"{et}: {counts['pass']}/{counts['total']} ({pct:.0%})"
                )
            print(f"  {name}: {', '.join(parts)}")


async def main():
    parser = argparse.ArgumentParser(
        description="WebArena Benchmark for PreAct"
    )
    parser.add_argument(
        "--tasks", type=int, default=None,
        help="Max number of tasks to run",
    )
    parser.add_argument(
        "--task-ids", nargs="*", type=int, default=None,
        help="Specific task IDs to run",
    )
    parser.add_argument(
        "--systems", nargs="*", default=None,
        help="Systems to evaluate (default: all)",
    )
    parser.add_argument(
        "--timeout", type=int, default=180,
        help="Per-task timeout in seconds",
    )
    parser.add_argument(
        "--hostname", default="localhost",
        help="Server hostname",
    )
    parser.add_argument(
        "--output", default="benchmark/webarena/results",
        help="Output directory",
    )
    parser.add_argument(
        "--skip-setup", action="store_true",
        help="Skip Docker container setup",
    )
    parser.add_argument(
        "--eval-types", nargs="*", default=None,
        help="Filter tasks by eval type (string_match, url_match, program_html)",
    )
    args = parser.parse_args()

    global HOSTNAME
    HOSTNAME = args.hostname

    # ---- Setup Docker ----
    if not args.skip_setup:
        logger.info("Setting up WebArena shopping_admin container...")
        if not start_shopping_admin(HOSTNAME):
            logger.error("Failed to start shopping_admin container")
            sys.exit(1)

    # ---- Capture auth states ----
    auth_states: dict[str, str | None] = {}

    # Shopping admin auth
    admin_state = get_auth_state_path("shopping_admin")
    if not admin_state:
        logger.info("Capturing auth state for shopping_admin...")
        admin_state = await capture_shopping_admin_auth(
            HOSTNAME, SHOPPING_ADMIN_PORT
        )
    auth_states["shopping_admin"] = str(admin_state) if admin_state else None

    # Shopping customer auth
    shopping_state = get_auth_state_path("shopping")
    if not shopping_state:
        logger.info("Capturing auth state for shopping...")
        shopping_state = await capture_shopping_auth(HOSTNAME, SHOPPING_ADMIN_PORT)
    auth_states["shopping"] = str(shopping_state) if shopping_state else None

    logger.info("Auth states: %s", auth_states)

    # ---- Generate task configs ----
    config_dir = Path(__file__).parent / "configs"
    if not config_dir.exists() or not list(config_dir.glob("*.json")):
        generate_task_configs(
            HOSTNAME, ["shopping_admin", "shopping"], str(config_dir)
        )

    # ---- Load tasks ----
    tasks = load_webarena_tasks(
        config_dir=config_dir,
        task_ids=args.task_ids,
        max_tasks=args.tasks,
    )

    # Filter by eval type if specified
    if args.eval_types:
        eval_type_set = set(args.eval_types)
        tasks = [
            t for t in tasks
            if eval_type_set.intersection(t["eval"]["eval_types"])
        ]

    logger.info("Loaded %d WebArena tasks", len(tasks))
    if not tasks:
        logger.error("No tasks found!")
        sys.exit(1)

    # ---- Select systems ----
    if args.systems:
        systems = {
            k: v for k, v in AVAILABLE_SYSTEMS.items() if k in args.systems
        }
    else:
        systems = AVAILABLE_SYSTEMS

    # ---- Run benchmark ----
    all_results = {}
    for key, (display_name, SystemClass) in systems.items():
        system = SystemClass()
        await system.reset()

        # Clean RAG state between systems
        for d in ["rag_db"]:
            if os.path.exists(d):
                shutil.rmtree(d)

        result = await run_system_benchmark(
            display_name, system, tasks, auth_states, args.timeout
        )
        all_results[display_name] = result

    # ---- Print results ----
    print_results_table(all_results)

    # ---- Save results ----
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    results_path = output_dir / f"webarena_results_{timestamp}.json"
    with open(results_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    logger.info("Results saved to %s", results_path)

    # Also save a "latest" symlink
    latest_path = output_dir / "latest.json"
    if latest_path.exists():
        latest_path.unlink()
    latest_path.symlink_to(results_path.name)


if __name__ == "__main__":
    asyncio.run(main())
