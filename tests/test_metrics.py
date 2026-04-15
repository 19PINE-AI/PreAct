"""Tests for the evaluation metrics."""

from preact.baselines.base import BaselineResult
from preact.evaluation.metrics import (
    TaskMetrics,
    aggregate,
    compute_delta,
    from_baseline_result,
)


def test_from_baseline_result():
    result = BaselineResult(
        success=True,
        mode="exploration",
        actions_executed=10,
        total_time_ms=5000,
        total_input_tokens=1000,
        total_output_tokens=500,
        actions_via_cache=8,
        actions_via_llm=2,
    )
    metrics = from_baseline_result(result, "task_1", "PreAct", 1)
    assert metrics.success is True
    assert metrics.task_id == "task_1"
    assert metrics.system_name == "PreAct"
    assert metrics.latency_per_action_ms == 500.0
    assert metrics.cost_usd > 0


def test_aggregate_metrics():
    metrics = [
        TaskMetrics(
            task_id=f"task_{i}",
            system_name="PreAct",
            run_number=1,
            success=i < 7,
            total_time_ms=1000 + i * 100,
            total_input_tokens=500,
            total_output_tokens=200,
            cost_usd=0.01,
            graph_coverage=0.8,
        )
        for i in range(10)
    ]
    agg = aggregate(metrics)
    assert agg.task_count == 10
    assert agg.success_rate == 0.7
    assert agg.mean_time_ms > 0
    assert 0 < agg.ci_95_success[0] < agg.ci_95_success[1] < 1


def test_compute_delta():
    run1 = [
        TaskMetrics(
            task_id="task_1",
            system_name="PreAct",
            run_number=1,
            success=True,
            total_time_ms=5000,
            total_input_tokens=1000,
            total_output_tokens=500,
            cost_usd=0.05,
        ),
    ]
    run2 = [
        TaskMetrics(
            task_id="task_1",
            system_name="PreAct",
            run_number=2,
            success=True,
            total_time_ms=500,
            total_input_tokens=100,
            total_output_tokens=50,
            cost_usd=0.005,
        ),
    ]
    delta = compute_delta(run1, run2)
    assert delta["time_improvement_pct"] == 90.0  # 5000 -> 500 = 90% reduction
    assert delta["speedup_factor"] == 10.0


def test_aggregate_empty():
    agg = aggregate([])
    assert agg.task_count == 0
    assert agg.success_rate == 0
