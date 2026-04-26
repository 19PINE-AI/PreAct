"""AndroidWorld benchmark runner for PreAct.

Runs PreAct vs Standard CUA (M3A/T3A) on AndroidWorld tasks,
comparing success rates, speed, and token usage.

Usage:
  python -m benchmark.androidworld.run_androidworld \
    --tasks ContactsAddContact ContactsDeleteContact \
    --systems standard_cua preact \
    --n-instances 3
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

# Add android_world to path
sys.path.insert(0, os.path.expanduser("~/android_world"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("androidworld")


@dataclass
class TaskResult:
    """Result of a single task evaluation."""
    task_name: str
    instance_id: int
    system: str
    success: bool
    score: float
    answer: str = ""
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
        """Generate summary statistics."""
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


async def run_preact_task(
    env,
    task,
    agent,
    goal: str,
    max_steps: int,
) -> TaskResult:
    """Run a task using PreAct agent."""
    from preact.platforms.android.agent import AndroidTaskResult

    start = time.time()

    try:
        result = await agent.execute_task(goal)

        elapsed_ms = (time.time() - start) * 1000

        # Check task success via AndroidWorld evaluation
        task_successful = task.is_successful(env) == 1.0
        agent_done = result.success

        success = task_successful and agent_done

        # Try to compile and store if CUA succeeded
        if result.mode == "cua" and result.success and result.step_data:
            try:
                app_context = env.foreground_activity_name
                await agent.compile_and_store(goal, result.step_data, app_context)
            except Exception as e:
                logger.warning("Compilation failed: %s", e)

        return TaskResult(
            task_name=task.__class__.__name__,
            instance_id=0,
            system="preact",
            success=success,
            score=1.0 if success else 0.0,
            answer=result.answer,
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
            task_name=task.__class__.__name__,
            instance_id=0,
            system="preact",
            success=False,
            score=0.0,
            error=str(e),
            time_ms=(time.time() - start) * 1000,
        )


async def run_standard_cua_task(
    env,
    task,
    agent,
    goal: str,
    max_steps: int,
) -> TaskResult:
    """Run a task using standard M3A/T3A agent."""
    from android_world.agents.base_agent import AgentInteractionResult

    start = time.time()
    total_steps = 0

    try:
        agent.reset()

        for step in range(max_steps):
            result = agent.step(goal)
            total_steps += 1

            if result.done:
                break

        elapsed_ms = (time.time() - start) * 1000

        # Evaluate
        task_successful = task.is_successful(env) == 1.0
        agent_done = result.done

        success = task_successful and agent_done

        return TaskResult(
            task_name=task.__class__.__name__,
            instance_id=0,
            system="standard_cua",
            success=success,
            score=1.0 if success else 0.0,
            mode="cua",
            time_ms=elapsed_ms,
            actions=total_steps,
        )

    except Exception as e:
        logger.error("Standard CUA task failed: %s", e)
        return TaskResult(
            task_name=task.__class__.__name__,
            instance_id=0,
            system="standard_cua",
            success=False,
            score=0.0,
            error=str(e),
            time_ms=(time.time() - start) * 1000,
        )


async def run_benchmark(args):
    """Run the full benchmark."""
    from android_world.env import env_launcher
    from android_world.env import interface as android_interface
    from android_world import registry
    from android_world import suite_utils

    logger.info("Setting up Android environment...")
    env = env_launcher.load_and_setup_env(
        console_port=args.console_port,
        emulator_setup=args.emulator_setup,
        adb_path=args.adb_path,
        grpc_port=args.grpc_port,
    )
    env.reset(go_home=True)

    # Get task registry
    task_registry = registry.TaskRegistry()
    aw_registry = task_registry.get_registry(
        task_registry.ANDROID_WORLD_FAMILY
    )

    # Filter tasks
    if args.tasks:
        task_names = args.tasks
    else:
        # Default: simple single-app tasks
        task_names = list(aw_registry.keys())[:20]

    logger.info("Running %d task types with %d instances each", len(task_names), args.n_instances)

    # Initialize systems
    preact_agent = None
    standard_agent = None

    if "preact" in args.systems:
        from preact.llm.client import LLMClient
        from preact.platforms.android.environment import AndroidEnvironment
        from preact.platforms.android.agent import PreActAndroidAgent
        from preact.rag.store import ProgramStore

        llm = LLMClient()
        android_env = AndroidEnvironment(env)
        store = ProgramStore(llm)
        preact_agent = PreActAndroidAgent(
            env=android_env,
            llm=llm,
            store=store,
            max_cua_steps=args.max_steps,
        )

    if "standard_cua" in args.systems:
        from android_world.agents import infer
        from android_world.agents import t3a

        # Use Claude Sonnet via compatible wrapper
        llm_wrapper = _create_llm_wrapper(args.model)
        standard_agent = t3a.T3A(env, llm_wrapper)

    # Run benchmark
    results = BenchmarkResults(start_time=time.time())

    for task_name in task_names:
        if task_name not in aw_registry:
            logger.warning("Task not found: %s", task_name)
            continue

        task_type = aw_registry[task_name]

        for instance_i in range(args.n_instances):
            # Generate task parameters
            params = task_type.generate_random_params()
            task = task_type(params)

            logger.info(
                "\n[%s] Instance %d: %s",
                task_name,
                instance_i,
                task.goal[:80],
            )

            for system_name in args.systems:
                # Reset environment
                env.reset(go_home=True)

                # Initialize task
                try:
                    task.initialize_task(env)
                except Exception as e:
                    logger.error("Task init failed: %s", e)
                    continue

                max_steps = min(int(8 * task.complexity), 30)

                if system_name == "preact" and preact_agent:
                    result = await run_preact_task(
                        env, task, preact_agent, task.goal, max_steps
                    )
                elif system_name == "standard_cua" and standard_agent:
                    result = await run_standard_cua_task(
                        env, task, standard_agent, task.goal, max_steps
                    )
                else:
                    continue

                result.instance_id = instance_i
                results.results.append(result)

                status = "PASS" if result.success else "FAIL"
                logger.info(
                    "  %s [%s]: %s | %dms, %d tok, %d actions, cov=%.0f%%",
                    system_name,
                    status,
                    result.mode,
                    result.time_ms,
                    result.tokens,
                    result.actions,
                    result.graph_coverage * 100,
                )

    results.end_time = time.time()

    # Save results
    os.makedirs("benchmark/androidworld/results", exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    results_file = f"benchmark/androidworld/results/results_{timestamp}.json"

    results_data = {
        "timestamp": timestamp,
        "args": vars(args),
        "summary": results.summary(),
        "results": [
            {
                "task_name": r.task_name,
                "instance_id": r.instance_id,
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
    logger.info("\nResults saved to: %s", results_file)

    # Print summary
    print("\n" + "=" * 60)
    print("BENCHMARK RESULTS")
    print("=" * 60)
    summary = results.summary()
    for system, stats in summary.items():
        print(f"\n{system}:")
        print(f"  Success Rate: {stats['success']}/{stats['total']} ({stats['success_rate']:.1%})")
        print(f"  Avg Tokens: {stats['avg_tokens']:.0f}")
        print(f"  Avg Time: {stats['avg_time_ms']:.0f}ms")
    print("=" * 60)


def _create_llm_wrapper(model: str):
    """Create an LLM wrapper compatible with AndroidWorld's infer interface."""
    # This would need to adapt Claude/Gemini API to AndroidWorld's infer.Wrapper
    # For now, return a placeholder
    logger.warning("Standard CUA agent requires model wrapper implementation")
    return None


def main():
    parser = argparse.ArgumentParser(description="AndroidWorld benchmark for PreAct")
    parser.add_argument("--tasks", nargs="+", help="Task names to evaluate")
    parser.add_argument(
        "--systems",
        nargs="+",
        default=["standard_cua", "preact"],
        help="Systems to evaluate",
    )
    parser.add_argument("--n-instances", type=int, default=3, help="Instances per task")
    parser.add_argument("--max-steps", type=int, default=15, help="Max CUA steps")
    parser.add_argument("--model", default="claude-sonnet-4-6", help="LLM model")
    parser.add_argument("--console-port", type=int, default=5554)
    parser.add_argument("--grpc-port", type=int, default=8554)
    parser.add_argument("--adb-path", default="~/Android/Sdk/platform-tools/adb")
    parser.add_argument("--emulator-setup", action="store_true")
    args = parser.parse_args()

    asyncio.run(run_benchmark(args))


if __name__ == "__main__":
    main()
