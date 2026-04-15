"""Benchmark execution harness.

Runs evaluation experiments across all systems and tasks,
collecting metrics for comparison.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from preact.baselines.base import BaselineResult
from preact.evaluation.metrics import TaskMetrics, aggregate, compute_delta, from_baseline_result

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkTask:
    """A single benchmark task to evaluate."""

    task_id: str
    task_description: str
    start_url: str
    parameters: dict[str, Any] = field(default_factory=dict)
    expected_outcome: str = ""  # For validation
    category: str = ""  # e.g., "web_navigation", "form_filling"


@dataclass
class ExperimentConfig:
    """Configuration for a single experiment run."""

    name: str
    systems: list[str]  # System names to evaluate
    tasks: list[BenchmarkTask]
    num_runs: int = 2  # Runs per task (1=exploration, 2=replay, etc.)
    num_trials: int = 3  # Independent trials for CI computation
    output_dir: str = "results"
    headless: bool = True
    timeout_per_task_sec: int = 120


class EvaluationHarness:
    """Orchestrates evaluation experiments."""

    def __init__(self, output_dir: str = "results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._systems: dict[str, Any] = {}
        self._all_metrics: list[TaskMetrics] = []

    def register_system(self, name: str, system: Any) -> None:
        """Register a baseline system for evaluation."""
        self._systems[name] = system

    async def run_experiment(
        self,
        config: ExperimentConfig,
        env_factory: Any = None,
        llm_factory: Any = None,
    ) -> dict[str, Any]:
        """Run a complete experiment and return results.

        Args:
            config: Experiment configuration.
            env_factory: Callable that creates a new environment.
            llm_factory: Callable that creates a new LLM client.

        Returns:
            Dict with per-system, per-run aggregate metrics.
        """
        logger.info(
            "Starting experiment: %s (%d systems, %d tasks, %d runs)",
            config.name,
            len(config.systems),
            len(config.tasks),
            config.num_runs,
        )

        results = {}
        for system_name in config.systems:
            if system_name not in self._systems:
                logger.warning("System not registered: %s", system_name)
                continue

            system = self._systems[system_name]
            system_results = await self._run_system(
                system_name, system, config, env_factory, llm_factory
            )
            results[system_name] = system_results

        # Save results
        output_path = self.output_dir / f"{config.name}_results.json"
        self._save_results(results, output_path)

        logger.info("Experiment complete: %s", config.name)
        return results

    async def _run_system(
        self,
        system_name: str,
        system: Any,
        config: ExperimentConfig,
        env_factory: Any,
        llm_factory: Any,
    ) -> dict[str, Any]:
        """Run all tasks for a single system."""
        logger.info("Evaluating system: %s", system_name)

        run_metrics: dict[int, list[TaskMetrics]] = {}

        for run_num in range(1, config.num_runs + 1):
            run_metrics[run_num] = []

            for task in config.tasks:
                logger.info(
                    "  Task %s, Run %d: %s",
                    task.task_id,
                    run_num,
                    task.task_description[:50],
                )

                # Create fresh environment and LLM for each task
                env = env_factory(task.start_url) if env_factory else None
                llm = llm_factory() if llm_factory else None

                if not env or not llm:
                    logger.warning("No env/llm factory — skipping")
                    continue

                try:
                    await env.start()

                    # Reset system between runs if needed
                    if run_num == 1:
                        await system.reset()

                    # Execute
                    if run_num == 1:
                        result = await asyncio.wait_for(
                            system.run_exploration(
                                task.task_description,
                                env,
                                llm,
                                parameters=task.parameters,
                            ),
                            timeout=config.timeout_per_task_sec,
                        )
                    else:
                        result = await asyncio.wait_for(
                            system.run_replay(
                                task.task_description,
                                env,
                                llm,
                                parameters=task.parameters,
                            ),
                            timeout=config.timeout_per_task_sec,
                        )

                    metrics = from_baseline_result(
                        result, task.task_id, system_name, run_num
                    )
                    run_metrics[run_num].append(metrics)
                    self._all_metrics.append(metrics)

                    logger.info(
                        "    %s: %s (%.0fms, %d tokens)",
                        "PASS" if result.success else "FAIL",
                        result.mode,
                        result.total_time_ms,
                        result.total_input_tokens + result.total_output_tokens,
                    )

                except asyncio.TimeoutError:
                    logger.warning("    TIMEOUT (%ds)", config.timeout_per_task_sec)
                    metrics = TaskMetrics(
                        task_id=task.task_id,
                        system_name=system_name,
                        run_number=run_num,
                        success=False,
                        total_time_ms=config.timeout_per_task_sec * 1000,
                    )
                    run_metrics[run_num].append(metrics)

                except Exception as e:
                    logger.error("    ERROR: %s", e)
                    metrics = TaskMetrics(
                        task_id=task.task_id,
                        system_name=system_name,
                        run_number=run_num,
                        success=False,
                        extra={"error": str(e)},
                    )
                    run_metrics[run_num].append(metrics)

                finally:
                    try:
                        await env.stop()
                    except Exception:
                        pass

        # Aggregate
        aggregated = {}
        for run_num, metrics_list in run_metrics.items():
            agg = aggregate(metrics_list)
            aggregated[f"run_{run_num}"] = {
                "success_rate": agg.success_rate,
                "mean_time_ms": agg.mean_time_ms,
                "median_time_ms": agg.median_time_ms,
                "mean_latency_per_action_ms": agg.mean_latency_per_action_ms,
                "mean_tokens": agg.mean_tokens,
                "mean_cost_usd": agg.mean_cost_usd,
                "mean_graph_coverage": agg.mean_graph_coverage,
                "ci_95_success": agg.ci_95_success,
                "task_count": agg.task_count,
            }

        # Run 1 -> Run 2 delta
        if 1 in run_metrics and 2 in run_metrics:
            aggregated["delta_1_to_2"] = compute_delta(
                run_metrics[1], run_metrics[2]
            )

        return aggregated

    def _save_results(
        self, results: dict[str, Any], path: Path
    ) -> None:
        """Save results to a JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        logger.info("Results saved: %s", path)

    def get_all_metrics(self) -> list[TaskMetrics]:
        """Return all collected metrics."""
        return self._all_metrics
