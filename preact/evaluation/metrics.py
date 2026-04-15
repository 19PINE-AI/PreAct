"""Metrics collection and computation for evaluation.

Implements all metrics from Section 8.3 of the design document:
- Task Success Rate (SR), First-Run SR, Second-Run SR
- Latency per Action
- Total LLM Tokens, Cost per Task
- Adaptation Cycles, Graph Coverage, Compilation Overhead
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any

from preact.baselines.base import BaselineResult


@dataclass
class TaskMetrics:
    """Metrics for a single task execution."""

    task_id: str
    system_name: str
    run_number: int  # 1 = exploration, 2 = replay, 3+ = mutation runs
    success: bool
    total_time_ms: float = 0
    latency_per_action_ms: float = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    cost_usd: float = 0
    actions_executed: int = 0
    actions_via_cache: int = 0
    actions_via_llm: int = 0
    graph_coverage: float = 0
    adaptation_cycles: int = 0
    fallback_count: int = 0
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class AggregateMetrics:
    """Aggregate metrics across multiple tasks."""

    system_name: str
    run_number: int
    task_count: int = 0
    success_rate: float = 0
    mean_time_ms: float = 0
    median_time_ms: float = 0
    mean_latency_per_action_ms: float = 0
    mean_tokens: float = 0
    mean_cost_usd: float = 0
    mean_graph_coverage: float = 0
    mean_adaptation_cycles: float = 0
    ci_95_success: tuple[float, float] = (0, 0)
    ci_95_time: tuple[float, float] = (0, 0)


def from_baseline_result(
    result: BaselineResult,
    task_id: str,
    system_name: str,
    run_number: int,
) -> TaskMetrics:
    """Convert a BaselineResult into TaskMetrics."""
    latency_per_action = 0
    if result.actions_executed > 0:
        latency_per_action = result.total_time_ms / result.actions_executed

    cost = (
        result.total_input_tokens * 0.10 / 1_000_000
        + result.total_output_tokens * 0.40 / 1_000_000
    )

    return TaskMetrics(
        task_id=task_id,
        system_name=system_name,
        run_number=run_number,
        success=result.success,
        total_time_ms=result.total_time_ms,
        latency_per_action_ms=latency_per_action,
        total_input_tokens=result.total_input_tokens,
        total_output_tokens=result.total_output_tokens,
        cost_usd=cost,
        actions_executed=result.actions_executed,
        actions_via_cache=result.actions_via_cache,
        actions_via_llm=result.actions_via_llm,
        graph_coverage=result.graph_coverage,
        fallback_count=result.fallback_count,
        extra=result.extra,
    )


def aggregate(metrics_list: list[TaskMetrics]) -> AggregateMetrics:
    """Compute aggregate statistics from a list of task metrics."""
    if not metrics_list:
        return AggregateMetrics(system_name="", run_number=0)

    system = metrics_list[0].system_name
    run = metrics_list[0].run_number
    n = len(metrics_list)

    successes = [m.success for m in metrics_list]
    times = [m.total_time_ms for m in metrics_list]
    tokens = [m.total_input_tokens + m.total_output_tokens for m in metrics_list]
    costs = [m.cost_usd for m in metrics_list]
    coverages = [m.graph_coverage for m in metrics_list]
    latencies = [m.latency_per_action_ms for m in metrics_list if m.latency_per_action_ms > 0]
    adaptations = [m.adaptation_cycles for m in metrics_list]

    success_rate = sum(successes) / n if n > 0 else 0
    mean_time = statistics.mean(times) if times else 0
    median_time = statistics.median(times) if times else 0

    # 95% CI for success rate (Wilson score interval approximation)
    ci_success = _wilson_ci(sum(successes), n)

    # 95% CI for time (t-distribution)
    ci_time = _mean_ci(times) if len(times) >= 2 else (mean_time, mean_time)

    return AggregateMetrics(
        system_name=system,
        run_number=run,
        task_count=n,
        success_rate=success_rate,
        mean_time_ms=mean_time,
        median_time_ms=median_time,
        mean_latency_per_action_ms=statistics.mean(latencies) if latencies else 0,
        mean_tokens=statistics.mean(tokens) if tokens else 0,
        mean_cost_usd=statistics.mean(costs) if costs else 0,
        mean_graph_coverage=statistics.mean(coverages) if coverages else 0,
        mean_adaptation_cycles=statistics.mean(adaptations) if adaptations else 0,
        ci_95_success=ci_success,
        ci_95_time=ci_time,
    )


def compute_delta(
    run1_metrics: list[TaskMetrics],
    run2_metrics: list[TaskMetrics],
) -> dict[str, Any]:
    """Compute the improvement from Run 1 to Run 2.

    Used for Experiment 2 (acceleration measurement).
    """
    agg1 = aggregate(run1_metrics)
    agg2 = aggregate(run2_metrics)

    time_improvement = (
        (agg1.mean_time_ms - agg2.mean_time_ms) / agg1.mean_time_ms * 100
        if agg1.mean_time_ms > 0
        else 0
    )
    token_improvement = (
        (agg1.mean_tokens - agg2.mean_tokens) / agg1.mean_tokens * 100
        if agg1.mean_tokens > 0
        else 0
    )
    cost_improvement = (
        (agg1.mean_cost_usd - agg2.mean_cost_usd) / agg1.mean_cost_usd * 100
        if agg1.mean_cost_usd > 0
        else 0
    )

    return {
        "time_improvement_pct": time_improvement,
        "token_improvement_pct": token_improvement,
        "cost_improvement_pct": cost_improvement,
        "run1_sr": agg1.success_rate,
        "run2_sr": agg2.success_rate,
        "run1_mean_time_ms": agg1.mean_time_ms,
        "run2_mean_time_ms": agg2.mean_time_ms,
        "run1_mean_tokens": agg1.mean_tokens,
        "run2_mean_tokens": agg2.mean_tokens,
        "speedup_factor": agg1.mean_time_ms / agg2.mean_time_ms
        if agg2.mean_time_ms > 0
        else float("inf"),
    }


def _wilson_ci(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score confidence interval for proportions."""
    if n == 0:
        return (0, 0)
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    spread = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / denom
    return (max(0, center - spread), min(1, center + spread))


def _mean_ci(values: list[float], z: float = 1.96) -> tuple[float, float]:
    """Confidence interval for mean using normal approximation."""
    if len(values) < 2:
        m = values[0] if values else 0
        return (m, m)
    m = statistics.mean(values)
    se = statistics.stdev(values) / (len(values) ** 0.5)
    return (m - z * se, m + z * se)
