"""AndroidWorld benchmark runner for PreAct (Docker-based).

Connects to AndroidWorld Docker container via HTTP API.
Runs PreAct CUA-compile-replay pipeline on AndroidWorld tasks.

Usage:
  # Start the Docker container first:
  sudo docker run --privileged -p 5000:5000 -it android_world:latest

  # Then run:
  python -m benchmark.androidworld.run_docker \
    --tasks ContactsAddContact ContactsDeleteContact \
    --n-instances 2 \
    --max-steps 15
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Optional

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
        by_system: dict[str, dict] = {}
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
    agent,
    goal: str,
    task_name: str,
    task_idx: int,
    max_steps: int,
) -> TaskResult:
    """Run a task using PreAct agent."""
    start = time.time()

    try:
        result = await agent.execute_task(goal)
        elapsed_ms = (time.time() - start) * 1000

        # Evaluate via server
        score = env.get_task_score(task_name, task_idx)
        success = score >= 1.0 and result.success

        # Compile if CUA succeeded
        if result.mode == "cua" and result.success and result.step_data:
            try:
                await agent.compile_and_store(goal, result.step_data)
            except Exception as e:
                logger.warning("Compilation failed: %s", e)

        return TaskResult(
            task_name=task_name,
            instance_id=task_idx,
            system="preact",
            success=success,
            score=score,
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
            task_name=task_name,
            instance_id=task_idx,
            system="preact",
            success=False,
            score=0.0,
            error=str(e),
            time_ms=(time.time() - start) * 1000,
        )


async def run_standard_cua_task(
    env,
    llm,
    goal: str,
    task_name: str,
    task_idx: int,
    max_steps: int,
) -> TaskResult:
    """Run a task using standard CUA (LLM + screenshots, no RPA)."""
    from preact.platforms.android.prompts import SYSTEM_PROMPT_CUA, USER_PROMPT_CUA

    start = time.time()
    total_tokens = 0
    action_history = []

    try:
        for step in range(max_steps):
            # Get state
            screenshot_bytes = await env.screenshot()
            elements_text = env.get_ui_elements_text()

            history_text = "\n".join(action_history[-5:]) if action_history else "None"

            prompt = USER_PROMPT_CUA.format(
                instruction=goal,
                step=step + 1,
                max_steps=max_steps,
                action_history=history_text,
                ui_elements=elements_text[:4000],
            )

            response = await llm.complete_with_vision(
                prompt, [screenshot_bytes], system=SYSTEM_PROMPT_CUA
            )
            total_tokens += llm.last_usage.get("total_tokens", 0)
            response = response.strip()

            # Terminal
            if "STATUS:COMPLETE" in response.upper() or response.upper() == "DONE":
                break
            if "STATUS:IMPOSSIBLE" in response.upper() or response.upper() == "FAIL":
                break

            # Parse and execute action
            action_dict = _parse_cua_action(response, env.get_ui_elements())
            if action_dict:
                env._exec_action(action_dict)
                await asyncio.sleep(0.5)
                action_history.append(f"Step {step+1}: {action_dict.get('action_type', '?')}")
            else:
                action_history.append(f"Step {step+1}: PARSE_ERROR")

        elapsed_ms = (time.time() - start) * 1000
        score = env.get_task_score(task_name, task_idx)

        return TaskResult(
            task_name=task_name,
            instance_id=task_idx,
            system="standard_cua",
            success=score >= 1.0,
            score=score,
            mode="cua",
            time_ms=elapsed_ms,
            tokens=total_tokens,
            actions=step + 1,
        )

    except Exception as e:
        logger.error("Standard CUA failed: %s", e)
        return TaskResult(
            task_name=task_name,
            instance_id=task_idx,
            system="standard_cua",
            success=False,
            score=0.0,
            error=str(e),
            time_ms=(time.time() - start) * 1000,
        )


def _parse_cua_action(response: str, elements: list) -> Optional[dict]:
    """Parse LLM response into an action dict for the HTTP API."""
    response = response.strip()

    # click(index)
    import re
    m = re.search(r"click\s*\(\s*(\d+)\s*\)", response, re.IGNORECASE)
    if m:
        idx = int(m.group(1))
        elem = next((e for e in elements if e.index == idx), None)
        if elem and elem.center_x is not None:
            return {"action_type": "click", "x": elem.center_x, "y": elem.center_y}
        return {"action_type": "click", "index": idx}

    # input_text("text") or type("text")
    m = re.search(r"(?:input_text|type)\s*\(\s*['\"](.+?)['\"]\s*\)", response, re.IGNORECASE)
    if m:
        return {"action_type": "input_text", "text": m.group(1)}

    # scroll(direction)
    m = re.search(r"scroll\s*\(\s*['\"]?(\w+)['\"]?\s*\)", response, re.IGNORECASE)
    if m:
        return {"action_type": "scroll", "direction": m.group(1)}

    # open_app("name")
    m = re.search(r"open_app\s*\(\s*['\"](.+?)['\"]\s*\)", response, re.IGNORECASE)
    if m:
        return {"action_type": "open_app", "app_name": m.group(1)}

    # navigate_back
    if "navigate_back" in response.lower() or "go_back" in response.lower():
        return {"action_type": "navigate_back"}

    # navigate_home
    if "navigate_home" in response.lower() or "go_home" in response.lower():
        return {"action_type": "navigate_home"}

    # enter / keyboard_enter
    if "keyboard_enter" in response.lower() or "press_enter" in response.lower():
        return {"action_type": "keyboard_enter"}

    # long_press(index)
    m = re.search(r"long_press\s*\(\s*(\d+)\s*\)", response, re.IGNORECASE)
    if m:
        idx = int(m.group(1))
        elem = next((e for e in elements if e.index == idx), None)
        if elem and elem.center_x is not None:
            return {"action_type": "long_press", "x": elem.center_x, "y": elem.center_y}

    # answer("text")
    m = re.search(r"answer\s*\(\s*['\"](.+?)['\"]\s*\)", response, re.IGNORECASE)
    if m:
        return {"action_type": "answer", "text": m.group(1)}

    # wait
    if "wait" in response.lower():
        return {"action_type": "wait"}

    return None


async def run_benchmark(args):
    """Run the full benchmark via Docker HTTP API."""
    from preact.platforms.android.http_environment import AndroidHTTPEnvironment

    env = AndroidHTTPEnvironment(base_url=f"http://localhost:{args.port}")

    logger.info("Waiting for AndroidWorld server...")
    env.wait_for_ready(timeout=600)
    logger.info("Server ready!")

    # Reset environment
    await env.reset()

    # Get task list
    all_tasks = env.get_task_list()
    logger.info("Available tasks: %d", len(all_tasks))

    # Filter tasks
    if args.tasks:
        task_names = [t for t in args.tasks if t in all_tasks]
        missing = [t for t in args.tasks if t not in all_tasks]
        if missing:
            logger.warning("Tasks not found: %s", missing)
    else:
        # Default: first N simple tasks
        task_names = all_tasks[:args.max_tasks] if args.max_tasks else all_tasks[:20]

    # Reinitialize suite
    env.reinitialize_suite(n_combinations=args.n_instances, seed=args.seed)

    logger.info("Running %d task types x %d instances", len(task_names), args.n_instances)

    # Initialize agents
    preact_agent = None
    llm = None

    if "preact" in args.systems:
        from preact.llm.client import LLMClient
        from preact.platforms.android.agent import PreActAndroidAgent
        from preact.rag.store import ProgramStore

        llm = LLMClient()
        store = ProgramStore(llm)
        preact_agent = PreActAndroidAgent(
            env=env,
            llm=llm,
            store=store,
            max_cua_steps=args.max_steps,
        )

    if "standard_cua" in args.systems and llm is None:
        from preact.llm.client import LLMClient
        llm = LLMClient()

    # Run benchmark
    results = BenchmarkResults(start_time=time.time())

    for task_name in task_names:
        n_instances = env.get_task_length(task_name)

        for task_idx in range(min(n_instances, args.n_instances)):
            goal = env.get_task_goal(task_name, task_idx)
            logger.info("\n[%s] Instance %d: %s", task_name, task_idx, goal[:80])

            for system_name in args.systems:
                # Reset and initialize task
                await env.reset()
                try:
                    env.initialize_task(task_name, task_idx)
                    await asyncio.sleep(3)  # Wait for task setup
                except Exception as e:
                    logger.error("Task init failed: %s", e)
                    continue

                if system_name == "preact" and preact_agent:
                    result = await run_preact_task(
                        env, preact_agent, goal, task_name, task_idx, args.max_steps
                    )
                elif system_name == "standard_cua" and llm:
                    result = await run_standard_cua_task(
                        env, llm, goal, task_name, task_idx, args.max_steps
                    )
                else:
                    continue

                results.results.append(result)

                status = "PASS" if result.success else "FAIL"
                logger.info(
                    "  %s [%s]: %s | %.0fms, %d tok, %d actions, cov=%.0f%%",
                    system_name, status, result.mode,
                    result.time_ms, result.tokens, result.actions,
                    result.graph_coverage * 100,
                )

                # Tear down task
                try:
                    env.tear_down_task(task_name, task_idx)
                except Exception:
                    pass

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
    logger.info("\nResults saved: %s", results_file)

    # Print summary
    total_time = results.end_time - results.start_time
    print(f"\n{'='*60}")
    print("ANDROIDWORLD BENCHMARK RESULTS")
    print(f"Total time: {total_time:.0f}s")
    print(f"{'='*60}")
    summary = results.summary()
    for system, stats in summary.items():
        print(f"\n{system}:")
        print(f"  Success: {stats['success']}/{stats['total']} ({stats['success_rate']:.1%})")
        print(f"  Avg Tokens: {stats['avg_tokens']:.0f}")
        print(f"  Avg Time: {stats['avg_time_ms']:.0f}ms")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="AndroidWorld Docker benchmark for PreAct")
    parser.add_argument("--tasks", nargs="+", help="Task type names to evaluate")
    parser.add_argument("--max-tasks", type=int, default=20, help="Max task types if --tasks not set")
    parser.add_argument("--systems", nargs="+", default=["preact"], help="Systems: preact, standard_cua")
    parser.add_argument("--n-instances", type=int, default=2, help="Instances per task type")
    parser.add_argument("--max-steps", type=int, default=15, help="Max CUA steps")
    parser.add_argument("--port", type=int, default=5000, help="Docker server port")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for task params")
    args = parser.parse_args()

    asyncio.run(run_benchmark(args))


if __name__ == "__main__":
    main()
