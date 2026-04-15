"""Results aggregation and reporting.

Generates comparison tables and visualizations from evaluation results.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def generate_comparison_table(results: dict[str, Any]) -> str:
    """Generate a markdown comparison table from experiment results.

    Follows the format from Section 8.3 of the design document.
    """
    lines = []
    lines.append("| System | Run 1 SR | Run 2 SR | Mean Time (ms) | Mean Tokens | Mean Cost ($) | Graph Coverage |")
    lines.append("|--------|----------|----------|---------------|-------------|---------------|----------------|")

    for system_name, system_data in sorted(results.items()):
        run1 = system_data.get("run_1", {})
        run2 = system_data.get("run_2", {})

        run1_sr = run1.get("success_rate", 0)
        run2_sr = run2.get("success_rate", 0)
        mean_time = run2.get("mean_time_ms", run1.get("mean_time_ms", 0))
        mean_tokens = run2.get("mean_tokens", run1.get("mean_tokens", 0))
        mean_cost = run2.get("mean_cost_usd", run1.get("mean_cost_usd", 0))
        coverage = run2.get("mean_graph_coverage", 0)

        lines.append(
            f"| **{system_name}** | {run1_sr:.1%} | {run2_sr:.1%} | "
            f"{mean_time:.0f} | {mean_tokens:.0f} | ${mean_cost:.4f} | {coverage:.1%} |"
        )

    return "\n".join(lines)


def generate_delta_table(results: dict[str, Any]) -> str:
    """Generate a table showing Run 1 -> Run 2 improvements."""
    lines = []
    lines.append("| System | Time Improvement | Token Improvement | Cost Improvement | Speedup Factor |")
    lines.append("|--------|-----------------|-------------------|-----------------|----------------|")

    for system_name, system_data in sorted(results.items()):
        delta = system_data.get("delta_1_to_2", {})
        if not delta:
            continue

        time_imp = delta.get("time_improvement_pct", 0)
        token_imp = delta.get("token_improvement_pct", 0)
        cost_imp = delta.get("cost_improvement_pct", 0)
        speedup = delta.get("speedup_factor", 1)

        lines.append(
            f"| **{system_name}** | {time_imp:+.1f}% | {token_imp:+.1f}% | "
            f"{cost_imp:+.1f}% | {speedup:.1f}x |"
        )

    return "\n".join(lines)


def generate_full_report(results: dict[str, Any], experiment_name: str) -> str:
    """Generate a complete evaluation report."""
    lines = [
        f"# {experiment_name} — Evaluation Report",
        "",
        "## Comparison Table",
        "",
        generate_comparison_table(results),
        "",
        "## Run 1 → Run 2 Improvement",
        "",
        generate_delta_table(results),
        "",
        "## Per-System Details",
        "",
    ]

    for system_name, system_data in sorted(results.items()):
        lines.append(f"### {system_name}")
        lines.append("")
        for key, val in system_data.items():
            if isinstance(val, dict):
                lines.append(f"**{key}:**")
                for k2, v2 in val.items():
                    if isinstance(v2, float):
                        lines.append(f"  - {k2}: {v2:.4f}")
                    else:
                        lines.append(f"  - {k2}: {v2}")
                lines.append("")
        lines.append("")

    return "\n".join(lines)


def save_report(results: dict[str, Any], experiment_name: str, output_dir: str = "results") -> str:
    """Save a complete report to disk."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    report = generate_full_report(results, experiment_name)
    report_path = output_path / f"{experiment_name}_report.md"
    report_path.write_text(report)

    return str(report_path)
