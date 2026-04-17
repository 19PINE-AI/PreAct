"""OSWorld benchmark runner for PreAct.

Runs PreAct CUA on OSWorld tasks. Uses synchronous outer loop
to avoid Playwright sync API conflict with asyncio.

Usage:
  python -m benchmark.osworld.run_osworld \
    --task-set test_small \
    --systems preact \
    --provider docker
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Optional

# Add OSWorld to path
sys.path.insert(0, os.path.expanduser("~/OSWorld"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("osworld")


@dataclass
class TaskResult:
    """Result of a single task evaluation."""
    task_id: str
    domain: str
    system: str
    success: bool
    score: float
    mode: str = ""
    time_ms: float = 0
    tokens: int = 0
    actions: int = 0
    actions_rpa: int = 0
    graph_coverage: float = 0.0
    error: Optional[str] = None


@dataclass
class BenchmarkResults:
    """Aggregated benchmark results."""
    results: list[TaskResult] = field(default_factory=list)
    start_time: float = 0
    end_time: float = 0

    def summary(self) -> dict:
        by_system = {}
        for r in self.results:
            if r.system not in by_system:
                by_system[r.system] = {"total": 0, "success": 0, "tokens": 0, "time": 0}
            by_system[r.system]["total"] += 1
            by_system[r.system]["success"] += int(r.success)
            by_system[r.system]["tokens"] += r.tokens
            by_system[r.system]["time"] += r.time_ms

        summary = {}
        for system, stats in by_system.items():
            total = stats["total"]
            summary[system] = {
                "total": total,
                "success": stats["success"],
                "success_rate": stats["success"] / total if total > 0 else 0,
                "avg_tokens": stats["tokens"] / total if total > 0 else 0,
                "avg_time_ms": stats["time"] / total if total > 0 else 0,
            }
        return summary


def _run_async(coro):
    """Run an async coroutine from synchronous code."""
    return asyncio.get_event_loop().run_until_complete(coro)


def run_preact_task(
    desktop_env,
    agent,
    instruction: str,
    max_steps: int,
) -> TaskResult:
    """Run a task using PreAct agent (sync wrapper)."""
    start = time.time()

    try:
        result = _run_async(agent.execute_task(instruction))
        elapsed_ms = (time.time() - start) * 1000

        # Evaluate using OSWorld evaluator
        time.sleep(20)  # Wait for system to settle
        score = desktop_env.evaluate()

        success = score >= 1.0

        # Compile if CUA succeeded
        if result.mode == "cua" and result.success and result.step_data:
            try:
                _run_async(agent.compile_and_store(instruction, result.step_data))
            except Exception as e:
                logger.warning("Compilation failed: %s", e)

        return TaskResult(
            task_id="",
            domain="",
            system="preact",
            success=success,
            score=score,
            mode=result.mode,
            time_ms=elapsed_ms,
            tokens=result.total_tokens,
            actions=result.actions_executed,
            actions_rpa=result.actions_via_rpa,
            graph_coverage=result.graph_coverage,
        )

    except Exception as e:
        logger.error("PreAct task failed: %s", e)
        return TaskResult(
            task_id="",
            domain="",
            system="preact",
            success=False,
            score=0.0,
            error=str(e),
            time_ms=(time.time() - start) * 1000,
        )


def run_benchmark(args):
    """Run the full OSWorld benchmark (synchronous)."""
    from desktop_env.desktop_env import DesktopEnv

    # Load task definitions
    task_set_file = os.path.join(
        os.path.expanduser("~/OSWorld"),
        "evaluation_examples",
        f"{args.task_set}.json",
    )

    if not os.path.exists(task_set_file):
        logger.error("Task set not found: %s", task_set_file)
        return

    with open(task_set_file) as f:
        task_set = json.load(f)

    # Flatten tasks
    all_tasks = []
    for domain, task_ids in task_set.items():
        for task_id in task_ids:
            task_file = os.path.join(
                os.path.expanduser("~/OSWorld"),
                "evaluation_examples",
                "examples",
                domain,
                f"{task_id}.json",
            )
            if os.path.exists(task_file):
                with open(task_file) as f:
                    task_data = json.load(f)
                task_data["domain"] = domain
                all_tasks.append(task_data)

    if args.max_tasks:
        all_tasks = all_tasks[: args.max_tasks]

    logger.info("Loaded %d tasks from %s", len(all_tasks), args.task_set)

    # Initialize environment
    logger.info("Setting up OSWorld environment...")
    desktop_env = DesktopEnv(
        provider_name=args.provider,
        path_to_vm=args.vm_path,
        action_space="pyautogui",
        screen_size=(1920, 1080),
        headless=args.headless,
        os_type="Ubuntu",
        require_a11y_tree=True,
    )

    # Create a persistent event loop for async PreAct operations
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Initialize agents
    preact_agent = None

    if "preact" in args.systems:
        from preact.llm.client import LLMClient
        from preact.platforms.osworld.environment import OSWorldEnvironment
        from preact.platforms.osworld.agent import PreActOSAgent
        from preact.rag.store import ProgramStore

        llm = LLMClient()
        os_env = OSWorldEnvironment(desktop_env)
        store = ProgramStore(llm)
        preact_agent = PreActOSAgent(
            env=os_env,
            llm=llm,
            store=store,
            max_cua_steps=args.max_steps,
        )

    # Run benchmark
    results = BenchmarkResults(start_time=time.time())

    for task_idx, task_data in enumerate(all_tasks):
        task_id = task_data.get("id", f"task_{task_idx}")
        domain = task_data.get("domain", "unknown")
        instruction = task_data.get("instruction", "")

        logger.info(
            "\n[%d/%d] %s/%s: %s",
            task_idx + 1,
            len(all_tasks),
            domain,
            task_id[:8],
            instruction[:60],
        )

        for system_name in args.systems:
            # Reset environment with task config (synchronous — uses Playwright)
            try:
                desktop_env.reset(task_config=task_data)
                time.sleep(60)  # Wait for env readiness
            except Exception as e:
                logger.error("Env reset failed: %s", e)
                continue

            if system_name == "preact" and preact_agent:
                os_env_wrapper = OSWorldEnvironment(desktop_env)
                preact_agent.env = os_env_wrapper
                result = run_preact_task(
                    desktop_env, preact_agent, instruction, args.max_steps
                )
            else:
                continue

            result.task_id = task_id
            result.domain = domain
            results.results.append(result)

            status = "PASS" if result.success else "FAIL"
            logger.info(
                "  %s [%s]: score=%.1f, %dms, %d tok, %d actions, cov=%.0f%%",
                system_name,
                status,
                result.score,
                result.time_ms,
                result.tokens,
                result.actions,
                result.graph_coverage * 100,
            )

    results.end_time = time.time()
    loop.close()

    # Clean up
    try:
        desktop_env.close()
    except Exception:
        pass

    # Save results
    os.makedirs("benchmark/osworld/results", exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    results_file = f"benchmark/osworld/results/results_{timestamp}.json"

    results_data = {
        "timestamp": timestamp,
        "args": vars(args),
        "summary": results.summary(),
        "results": [
            {
                "task_id": r.task_id,
                "domain": r.domain,
                "system": r.system,
                "success": r.success,
                "score": r.score,
                "mode": r.mode,
                "time_ms": r.time_ms,
                "tokens": r.tokens,
                "actions": r.actions,
                "actions_rpa": r.actions_rpa,
                "graph_coverage": r.graph_coverage,
                "error": r.error,
            }
            for r in results.results
        ],
    }

    with open(results_file, "w") as f:
        json.dump(results_data, f, indent=2)
    logger.info("\nResults saved: %s", results_file)

    # Print summary
    total_time = results.end_time - results.start_time
    print(f"\n{'='*60}")
    print("OSWORLD BENCHMARK RESULTS")
    print(f"Total time: {total_time:.0f}s")
    print("=" * 60)
    summary = results.summary()
    for system, stats in summary.items():
        print(f"\n{system}:")
        print(f"  Success: {stats['success']}/{stats['total']} ({stats['success_rate']:.1%})")
        print(f"  Avg Tokens: {stats['avg_tokens']:.0f}")
        print(f"  Avg Time: {stats['avg_time_ms']:.0f}ms")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="OSWorld benchmark for PreAct")
    parser.add_argument("--task-set", default="test_small", help="Task set name")
    parser.add_argument("--max-tasks", type=int, default=None, help="Max tasks to run")
    parser.add_argument(
        "--systems",
        nargs="+",
        default=["preact"],
    )
    parser.add_argument("--max-steps", type=int, default=15)
    parser.add_argument("--model", default="claude-sonnet-4-6")
    parser.add_argument("--provider", default="docker")
    parser.add_argument("--vm-path", default=os.path.expanduser("~/OSWorld/docker_vm_data/Ubuntu.qcow2"))
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    run_benchmark(args)


if __name__ == "__main__":
    main()
