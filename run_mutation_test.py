#!/usr/bin/env python3
"""UI Mutation Adaptation Test (Experiment 3).

Tests resilience to UI changes:
1. Run 1: Normal exploration → compile
2. Run 2: Normal replay (verify compiled program works)
3. Inject UI mutations
4. Run 3: Post-mutation replay (measure fallbacks)
5. Run 4: Second post-mutation replay (measure recovery)
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
from preact.config import LLMConfig
from preact.environment.browser import BrowserEnvironment
from preact.evaluation.metrics import TaskMetrics, aggregate, from_baseline_result
from preact.evaluation.mutations import MutationSeverity, apply_mutations_by_severity
from preact.llm.client import LLMClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("mutation_test")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("google_genai").setLevel(logging.WARNING)
logging.getLogger("chromadb").setLevel(logging.WARNING)

TASK = {
    "task_id": "mutation_form",
    "task": "Fill in the form with customer name 'Test User', select Medium pizza size, add mushrooms topping, and submit",
    "url": "https://httpbin.org/forms/post",
    "params": {"customer_name": "Test User"},
}


async def run_mutation_experiment(
    system_name: str,
    system: object,
    timeout: int = 90,
) -> dict:
    """Run the 4-run mutation protocol for a single system."""
    logger.info("\n  === %s ===", system_name)
    results = {}

    task = TASK["task"]
    url = TASK["url"]
    params = TASK.get("params", {})

    # ─── Run 1: Normal exploration ────────────────────────
    logger.info("  Run 1: Normal exploration")
    llm = LLMClient(LLMConfig(model="gemini-3-flash-preview"))
    env = BrowserEnvironment(headless=True, start_url=url)
    try:
        await env.start()
        r1 = await asyncio.wait_for(
            system.run_exploration(task, env, llm, parameters=params),
            timeout=timeout,
        )
        results["run1"] = {
            "success": r1.success, "time_ms": r1.total_time_ms,
            "tokens": r1.total_input_tokens + r1.total_output_tokens,
        }
        logger.info("    R1: %s %.0fms", "OK" if r1.success else "FAIL", r1.total_time_ms)
    except Exception as e:
        logger.error("    R1 ERROR: %s", e)
        results["run1"] = {"success": False, "error": str(e)}
    finally:
        try:
            await env.stop()
        except Exception:
            pass

    # ─── Run 2: Normal replay ─────────────────────────────
    logger.info("  Run 2: Normal replay")
    if system.has_cached_artifact(task):
        llm2 = LLMClient(LLMConfig(model="gemini-3-flash-preview"))
        env2 = BrowserEnvironment(headless=True, start_url=url)
        try:
            await env2.start()
            r2 = await asyncio.wait_for(
                system.run_replay(task, env2, llm2, parameters=params),
                timeout=timeout,
            )
            results["run2"] = {
                "success": r2.success, "time_ms": r2.total_time_ms,
                "tokens": r2.total_input_tokens + r2.total_output_tokens,
                "coverage": r2.graph_coverage,
            }
            logger.info("    R2: %s %.0fms cov=%.0f%%",
                        "OK" if r2.success else "FAIL", r2.total_time_ms, r2.graph_coverage * 100)
        except Exception as e:
            logger.error("    R2 ERROR: %s", e)
            results["run2"] = {"success": False, "error": str(e)}
        finally:
            try:
                await env2.stop()
            except Exception:
                pass
    else:
        results["run2"] = {"success": False, "skip": "no_artifact"}

    # ─── Run 3: Post-mutation replay ──────────────────────
    logger.info("  Run 3: Post-mutation replay (MINOR mutations)")
    if system.has_cached_artifact(task):
        llm3 = LLMClient(LLMConfig(model="gemini-3-flash-preview"))
        env3 = BrowserEnvironment(headless=True, start_url=url)
        try:
            await env3.start()
            # Inject mutations
            mutations = await apply_mutations_by_severity(env3, MutationSeverity.MINOR)
            logger.info("    Injected %d mutations", len(mutations))

            r3 = await asyncio.wait_for(
                system.run_replay(task, env3, llm3, parameters=params),
                timeout=timeout,
            )
            results["run3_minor"] = {
                "success": r3.success, "time_ms": r3.total_time_ms,
                "tokens": r3.total_input_tokens + r3.total_output_tokens,
                "fallback_count": r3.fallback_count,
                "coverage": r3.graph_coverage,
            }
            logger.info("    R3: %s %.0fms fallbacks=%d",
                        "OK" if r3.success else "FAIL", r3.total_time_ms, r3.fallback_count)
        except Exception as e:
            logger.error("    R3 ERROR: %s", e)
            results["run3_minor"] = {"success": False, "error": str(e)}
        finally:
            try:
                await env3.stop()
            except Exception:
                pass
    else:
        results["run3_minor"] = {"success": False, "skip": "no_artifact"}

    # ─── Run 3b: Moderate mutations ───────────────────────
    logger.info("  Run 3b: Post-mutation replay (MODERATE mutations)")
    if system.has_cached_artifact(task):
        llm3b = LLMClient(LLMConfig(model="gemini-3-flash-preview"))
        env3b = BrowserEnvironment(headless=True, start_url=url)
        try:
            await env3b.start()
            mutations = await apply_mutations_by_severity(env3b, MutationSeverity.MODERATE)
            logger.info("    Injected %d mutations", len(mutations))

            r3b = await asyncio.wait_for(
                system.run_replay(task, env3b, llm3b, parameters=params),
                timeout=timeout,
            )
            results["run3_moderate"] = {
                "success": r3b.success, "time_ms": r3b.total_time_ms,
                "tokens": r3b.total_input_tokens + r3b.total_output_tokens,
                "fallback_count": r3b.fallback_count,
            }
            logger.info("    R3b: %s %.0fms fallbacks=%d",
                        "OK" if r3b.success else "FAIL", r3b.total_time_ms, r3b.fallback_count)
        except Exception as e:
            logger.error("    R3b ERROR: %s", e)
            results["run3_moderate"] = {"success": False, "error": str(e)}
        finally:
            try:
                await env3b.stop()
            except Exception:
                pass
    else:
        results["run3_moderate"] = {"success": False, "skip": "no_artifact"}

    return results


async def main():
    for d in ["rag_db"]:
        if os.path.exists(d):
            shutil.rmtree(d)

    logger.info("=" * 60)
    logger.info("EXPERIMENT 3: UI Mutation Adaptation")
    logger.info("=" * 60)

    systems = {
        "PreAct": PreActBaseline(),
        "Muscle-Mem": MuscleMemBaseline(),
        "Workflow-Use": WorkflowUseBaseline(),
    }

    all_results = {}
    for name, system in systems.items():
        await system.reset()
        for d in ["rag_db"]:
            if os.path.exists(d):
                shutil.rmtree(d)
        all_results[name] = await run_mutation_experiment(name, system)

    # Print summary
    print("\n" + "=" * 90)
    print("UI Mutation Adaptation Results")
    print("-" * 90)
    print(f"{'System':<20} {'R1 OK?':>6} {'R2 OK?':>6} {'R2 Time':>9} "
          f"{'R3-Minor':>9} {'R3-Mod':>9} {'Fallbacks':>10}")
    print("-" * 90)

    for name, data in all_results.items():
        r1_ok = "Y" if data.get("run1", {}).get("success") else "N"
        r2_ok = "Y" if data.get("run2", {}).get("success") else "N"
        r2_time = f"{data.get('run2', {}).get('time_ms', 0):.0f}ms"
        r3_minor = "Y" if data.get("run3_minor", {}).get("success") else "N"
        r3_mod = "Y" if data.get("run3_moderate", {}).get("success") else "N"
        fb_minor = data.get("run3_minor", {}).get("fallback_count", "?")
        fb_mod = data.get("run3_moderate", {}).get("fallback_count", "?")
        print(f"{name:<20} {r1_ok:>6} {r2_ok:>6} {r2_time:>9} "
              f"{r3_minor:>9} {r3_mod:>9} {fb_minor}/{fb_mod}")

    print("=" * 90)

    # Save results
    Path("results").mkdir(exist_ok=True)
    with open("results/mutation_results.json", "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    logger.info("Results saved to results/mutation_results.json")


if __name__ == "__main__":
    asyncio.run(main())
