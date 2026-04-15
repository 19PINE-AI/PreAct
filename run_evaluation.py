#!/usr/bin/env python3
"""Full evaluation runner for PreAct vs baselines.

Runs all systems on a set of real web tasks and measures:
- Task Success Rate (first run and second run)
- Latency per action
- Token usage and cost
- Graph coverage
- Speedup factor

Usage:
    python run_evaluation.py               # Run all experiments
    python run_evaluation.py --exp 1       # Run experiment 1 only
    python run_evaluation.py --quick       # Quick test with 1 task
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

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from preact.baselines.action_engine import ActionEngineBaseline
from preact.baselines.agent_rr import AgentRRBaseline
from preact.baselines.base import BaselineResult
from preact.baselines.muscle_mem import MuscleMemBaseline
from preact.baselines.preact_baseline import PreActBaseline
from preact.baselines.standard_cua import StandardCUABaseline
from preact.baselines.workflow_use import WorkflowUseBaseline
from preact.config import CUAConfig, LLMConfig, PreActConfig
from preact.environment.browser import BrowserEnvironment
from preact.evaluation.metrics import TaskMetrics, aggregate, compute_delta, from_baseline_result
from preact.evaluation.mutations import MutationSeverity, apply_mutations_by_severity
from preact.evaluation.report import generate_full_report, save_report
from preact.llm.client import LLMClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("evaluation")

# Suppress noisy loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("google_genai").setLevel(logging.WARNING)
logging.getLogger("chromadb").setLevel(logging.WARNING)

# ─── Evaluation Tasks ────────────────────────────────────────────────────────

EVAL_TASKS = [
    {
        "task_id": "form_001",
        "task": "Fill in the form with customer name 'Alice Smith', select Medium pizza size, add mushrooms topping, and submit the order",
        "url": "https://httpbin.org/forms/post",
        "params": {"customer_name": "Alice Smith"},
        "category": "form_filling",
    },
    {
        "task_id": "form_002",
        "task": "Fill in the form with customer name 'Bob Jones', select Large pizza size, add cheese topping, and submit the order",
        "url": "https://httpbin.org/forms/post",
        "params": {"customer_name": "Bob Jones"},
        "category": "form_filling",
    },
    {
        "task_id": "form_003",
        "task": "Fill in the form with customer name 'Carol White', select Small pizza size, add bacon topping, and submit the order",
        "url": "https://httpbin.org/forms/post",
        "params": {"customer_name": "Carol White"},
        "category": "form_filling",
    },
    {
        "task_id": "form_004",
        "task": "Fill in the form with customer name 'Diana Prince', select Large pizza size, add mushrooms and bacon toppings, and submit the order",
        "url": "https://httpbin.org/forms/post",
        "params": {"customer_name": "Diana Prince"},
        "category": "form_filling",
    },
    {
        "task_id": "form_005",
        "task": "Fill in the form with customer name 'Eve Brown', select Small pizza size, add cheese and onion toppings, and submit the order",
        "url": "https://httpbin.org/forms/post",
        "params": {"customer_name": "Eve Brown"},
        "category": "form_filling",
    },
]

QUICK_TASKS = EVAL_TASKS[:2]  # Just form tasks for quick tests


# ─── Evaluation Functions ─────────────────────────────────────────────────────

async def run_single_system(
    system_name: str,
    system: object,
    tasks: list[dict],
    max_steps: int = 10,
    timeout: int = 90,
) -> dict:
    """Run a single system on all tasks with 2-run protocol."""
    logger.info("=" * 60)
    logger.info("SYSTEM: %s", system_name)
    logger.info("=" * 60)

    run1_metrics = []
    run2_metrics = []

    for task_spec in tasks:
        task_id = task_spec["task_id"]
        task = task_spec["task"]
        url = task_spec["url"]
        params = task_spec.get("params", {})

        # ─── Run 1: Exploration ───────────────────────────────
        logger.info("  [%s] Run 1 (exploration): %s", task_id, task[:60])

        llm = LLMClient(LLMConfig(model="gemini-3-flash-preview"))
        env = BrowserEnvironment(headless=True, start_url=url)

        try:
            await env.start()
            start_tokens_in = llm.total_input_tokens
            start_tokens_out = llm.total_output_tokens

            result1 = await asyncio.wait_for(
                system.run_exploration(task, env, llm, parameters=params),
                timeout=timeout,
            )

            m1 = from_baseline_result(result1, task_id, system_name, 1)
            run1_metrics.append(m1)

            status = "PASS" if result1.success else "FAIL"
            logger.info(
                "    %s: %s (%.0fms, %d tokens, %d actions)",
                status, result1.mode, result1.total_time_ms,
                result1.total_input_tokens + result1.total_output_tokens,
                result1.actions_executed,
            )
        except asyncio.TimeoutError:
            logger.warning("    TIMEOUT (%ds)", timeout)
            run1_metrics.append(TaskMetrics(
                task_id=task_id, system_name=system_name, run_number=1,
                success=False, total_time_ms=timeout * 1000,
            ))
        except Exception as e:
            logger.error("    ERROR: %s", e, exc_info=False)
            run1_metrics.append(TaskMetrics(
                task_id=task_id, system_name=system_name, run_number=1,
                success=False, extra={"error": str(e)},
            ))
        finally:
            try:
                await env.stop()
            except Exception:
                pass

        # ─── Run 2: Replay ────────────────────────────────────
        if not system.has_cached_artifact(task):
            logger.info("    [%s] Run 2: No cached artifact — skipping replay", task_id)
            run2_metrics.append(TaskMetrics(
                task_id=task_id, system_name=system_name, run_number=2,
                success=False, extra={"skip": "no_artifact"},
            ))
            continue

        logger.info("  [%s] Run 2 (replay): %s", task_id, task[:60])

        llm2 = LLMClient(LLMConfig(model="gemini-3-flash-preview"))
        env2 = BrowserEnvironment(headless=True, start_url=url)

        try:
            await env2.start()

            result2 = await asyncio.wait_for(
                system.run_replay(task, env2, llm2, parameters=params),
                timeout=timeout,
            )

            m2 = from_baseline_result(result2, task_id, system_name, 2)
            run2_metrics.append(m2)

            status = "PASS" if result2.success else "FAIL"
            logger.info(
                "    %s: %s (%.0fms, %d tokens, %d actions, coverage=%.0f%%)",
                status, result2.mode, result2.total_time_ms,
                result2.total_input_tokens + result2.total_output_tokens,
                result2.actions_executed,
                result2.graph_coverage * 100,
            )
        except asyncio.TimeoutError:
            logger.warning("    TIMEOUT (%ds)", timeout)
            run2_metrics.append(TaskMetrics(
                task_id=task_id, system_name=system_name, run_number=2,
                success=False, total_time_ms=timeout * 1000,
            ))
        except Exception as e:
            logger.error("    ERROR: %s", e, exc_info=False)
            run2_metrics.append(TaskMetrics(
                task_id=task_id, system_name=system_name, run_number=2,
                success=False, extra={"error": str(e)},
            ))
        finally:
            try:
                await env2.stop()
            except Exception:
                pass

    # Aggregate
    agg1 = aggregate(run1_metrics)
    agg2 = aggregate(run2_metrics)
    delta = compute_delta(run1_metrics, run2_metrics) if run1_metrics and run2_metrics else {}

    return {
        "system": system_name,
        "run1": {
            "success_rate": agg1.success_rate,
            "mean_time_ms": agg1.mean_time_ms,
            "mean_tokens": agg1.mean_tokens,
            "mean_cost_usd": agg1.mean_cost_usd,
            "mean_latency_per_action_ms": agg1.mean_latency_per_action_ms,
            "task_count": agg1.task_count,
        },
        "run2": {
            "success_rate": agg2.success_rate,
            "mean_time_ms": agg2.mean_time_ms,
            "mean_tokens": agg2.mean_tokens,
            "mean_cost_usd": agg2.mean_cost_usd,
            "mean_latency_per_action_ms": agg2.mean_latency_per_action_ms,
            "mean_graph_coverage": agg2.mean_graph_coverage,
            "task_count": agg2.task_count,
        },
        "delta": delta,
        "per_task_run1": [
            {"task_id": m.task_id, "success": m.success, "time_ms": m.total_time_ms,
             "tokens": m.total_input_tokens + m.total_output_tokens, "actions": m.actions_executed}
            for m in run1_metrics
        ],
        "per_task_run2": [
            {"task_id": m.task_id, "success": m.success, "time_ms": m.total_time_ms,
             "tokens": m.total_input_tokens + m.total_output_tokens, "actions": m.actions_executed,
             "graph_coverage": m.graph_coverage}
            for m in run2_metrics
        ],
    }


async def run_experiment_1(tasks: list[dict]) -> dict:
    """Experiment 1: End-to-End Performance.

    All systems on all tasks. Run 1 + Run 2.
    """
    logger.info("\n" + "=" * 70)
    logger.info("EXPERIMENT 1: End-to-End Performance")
    logger.info("=" * 70)

    systems = {
        "Standard CUA": StandardCUABaseline(),
        "Muscle-Mem": MuscleMemBaseline(),
        "Workflow-Use": WorkflowUseBaseline(),
        "AgentRR": AgentRRBaseline(),
        "PreAct": PreActBaseline(),
    }

    all_results = {}
    for name, system in systems.items():
        await system.reset()
        result = await run_single_system(name, system, tasks)
        all_results[name] = result

    return all_results


async def run_experiment_2(tasks: list[dict]) -> dict:
    """Experiment 2: Acceleration on Second Run.

    Focus on measuring the speedup from Run 1 to Run 2.
    """
    logger.info("\n" + "=" * 70)
    logger.info("EXPERIMENT 2: Acceleration Measurement")
    logger.info("=" * 70)

    systems = {
        "Standard CUA": StandardCUABaseline(),
        "Muscle-Mem": MuscleMemBaseline(),
        "Workflow-Use": WorkflowUseBaseline(),
        "PreAct": PreActBaseline(),
    }

    all_results = {}
    for name, system in systems.items():
        await system.reset()
        result = await run_single_system(name, system, tasks)
        all_results[name] = result

    return all_results


async def run_experiment_3(tasks: list[dict]) -> dict:
    """Experiment 3: UI Mutation Adaptation.

    Run 1-2 normal, inject mutations, Run 3-4 with mutations.
    """
    logger.info("\n" + "=" * 70)
    logger.info("EXPERIMENT 3: UI Mutation Adaptation")
    logger.info("=" * 70)

    systems = {
        "Muscle-Mem": MuscleMemBaseline(),
        "Workflow-Use": WorkflowUseBaseline(),
        "PreAct": PreActBaseline(),
    }

    all_results = {}

    for name, system in systems.items():
        await system.reset()

        # Normal runs (1 and 2)
        result = await run_single_system(name, system, tasks[:2])

        # Run 3: Post-mutation (with minor mutations)
        logger.info("  Injecting MINOR UI mutations for %s", name)
        run3_metrics = []

        for task_spec in tasks[:2]:
            task_id = task_spec["task_id"]
            task = task_spec["task"]
            url = task_spec["url"]
            params = task_spec.get("params", {})

            llm = LLMClient(LLMConfig(model="gemini-3-flash-preview"))
            env = BrowserEnvironment(headless=True, start_url=url)

            try:
                await env.start()
                # Apply mutations
                await apply_mutations_by_severity(env, MutationSeverity.MINOR)

                result3 = await asyncio.wait_for(
                    system.run_replay(task, env, llm, parameters=params),
                    timeout=90,
                )
                m3 = from_baseline_result(result3, task_id, name, 3)
                run3_metrics.append(m3)

                logger.info(
                    "    [%s] Run 3 (post-mutation): %s (%.0fms, fallbacks=%d)",
                    task_id, "PASS" if result3.success else "FAIL",
                    result3.total_time_ms, result3.fallback_count,
                )
            except Exception as e:
                logger.error("    [%s] Run 3 ERROR: %s", task_id, e)
                run3_metrics.append(TaskMetrics(
                    task_id=task_id, system_name=name, run_number=3, success=False,
                ))
            finally:
                try:
                    await env.stop()
                except Exception:
                    pass

        agg3 = aggregate(run3_metrics)
        result["run3"] = {
            "success_rate": agg3.success_rate,
            "mean_time_ms": agg3.mean_time_ms,
            "mean_tokens": agg3.mean_tokens,
        }

        all_results[name] = result

    return all_results


async def run_experiment_5(tasks: list[dict]) -> dict:
    """Experiment 5: Ablation Study.

    Compare PreAct-Full vs ablated variants.
    """
    logger.info("\n" + "=" * 70)
    logger.info("EXPERIMENT 5: Ablation Study")
    logger.info("=" * 70)

    from preact.evaluation.experiments import (
        PreActFlatCodeBaseline,
        PreActNoBranchBaseline,
        PreActNoRAGBaseline,
        PreActNoRefineBaseline,
        PreActNoVerifyBaseline,
    )

    systems = {
        "PreAct-Full": PreActBaseline(),
        "PreAct-NoVerify": PreActNoVerifyBaseline(),
        "PreAct-NoRAG": PreActNoRAGBaseline(),
    }

    all_results = {}
    for name, system in systems.items():
        await system.reset()
        result = await run_single_system(name, system, tasks[:2])
        all_results[name] = result

    return all_results


def print_comparison_table(results: dict):
    """Print a formatted comparison table."""
    print("\n" + "=" * 110)
    print(f"{'System':<20} {'Run1 SR':>8} {'Run2 SR':>8} {'Run1 Time':>10} {'Run2 Time':>10} "
          f"{'Speedup':>8} {'Run2 Tokens':>12} {'Coverage':>9}")
    print("-" * 110)

    for name, data in sorted(results.items()):
        r1 = data.get("run1", {})
        r2 = data.get("run2", {})
        delta = data.get("delta", {})

        run1_sr = f"{r1.get('success_rate', 0):.0%}"
        run2_sr = f"{r2.get('success_rate', 0):.0%}"
        run1_time = f"{r1.get('mean_time_ms', 0):.0f}ms"
        run2_time = f"{r2.get('mean_time_ms', 0):.0f}ms"
        speedup = f"{delta.get('speedup_factor', 1):.1f}x" if delta else "N/A"
        run2_tokens = f"{r2.get('mean_tokens', 0):.0f}"
        coverage = f"{r2.get('mean_graph_coverage', 0):.0%}"

        print(f"{name:<20} {run1_sr:>8} {run2_sr:>8} {run1_time:>10} {run2_time:>10} "
              f"{speedup:>8} {run2_tokens:>12} {coverage:>9}")

    print("=" * 110)


async def main():
    parser = argparse.ArgumentParser(description="PreAct Evaluation")
    parser.add_argument("--exp", type=int, nargs="*", help="Experiment numbers to run (1,2,3,5)")
    parser.add_argument("--quick", action="store_true", help="Quick test with fewer tasks")
    parser.add_argument("--output", default="results", help="Output directory")
    args = parser.parse_args()

    tasks = QUICK_TASKS if args.quick else EVAL_TASKS
    experiments = args.exp or [1, 2]
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Clean RAG DB between experiments
    for d in ["rag_db", "test_rag_db"]:
        if os.path.exists(d):
            shutil.rmtree(d)

    all_results = {}

    for exp_num in experiments:
        if exp_num == 1:
            results = await run_experiment_1(tasks)
            all_results["experiment_1"] = results
            print("\n\n### EXPERIMENT 1: End-to-End Performance ###")
            print_comparison_table(results)

        elif exp_num == 2:
            results = await run_experiment_2(tasks)
            all_results["experiment_2"] = results
            print("\n\n### EXPERIMENT 2: Acceleration ###")
            print_comparison_table(results)

        elif exp_num == 3:
            results = await run_experiment_3(tasks)
            all_results["experiment_3"] = results
            print("\n\n### EXPERIMENT 3: UI Mutation Adaptation ###")
            print_comparison_table(results)

        elif exp_num == 5:
            results = await run_experiment_5(tasks)
            all_results["experiment_5"] = results
            print("\n\n### EXPERIMENT 5: Ablation Study ###")
            print_comparison_table(results)

    # Save all results
    results_path = output_dir / "evaluation_results.json"
    with open(results_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    logger.info("Results saved to %s", results_path)

    # Generate report
    for exp_name, exp_results in all_results.items():
        report_path = save_report(exp_results, exp_name, str(output_dir))
        logger.info("Report saved: %s", report_path)


if __name__ == "__main__":
    asyncio.run(main())
