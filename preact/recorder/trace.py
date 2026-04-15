"""Trace data structures and utilities.

Helper functions for working with interaction traces, including
serialization, trace analysis, and XPath resolution.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from preact.schemas import InteractionTrace, TraceStep


def save_trace(trace: InteractionTrace, path: str | Path) -> None:
    """Save a trace to disk as JSON (without screenshot bytes)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = trace.model_dump(exclude={"steps": {"__all__": {"screenshot_data"}}})
    path.write_text(json.dumps(data, indent=2, default=str))


def load_trace(path: str | Path) -> InteractionTrace:
    """Load a trace from a JSON file."""
    data = json.loads(Path(path).read_text())
    return InteractionTrace.model_validate(data)


def trace_to_text(trace: InteractionTrace) -> str:
    """Convert a trace to a human-readable text format for LLM processing.

    This is the primary input format for the Model Generator.
    """
    lines = [
        f"Task: {trace.task_description}",
        f"App Context: {trace.application_context}",
        f"Steps: {len(trace.steps)}",
        f"Success: {trace.success}",
        "",
    ]

    for i, step in enumerate(trace.steps, 1):
        lines.append(f"--- Step {i} ---")
        if step.page_url:
            lines.append(f"  URL: {step.page_url}")
        lines.append(f"  Action: {step.action.type.value}")
        if step.action.target:
            lines.append(f"  Target: {step.action.target}")
        if step.action.text:
            lines.append(f"  Text: {step.action.text}")
        if step.action.key:
            lines.append(f"  Key: {step.action.key}")
        if step.target_xpath:
            lines.append(f"  XPath: {step.target_xpath}")
        if step.llm_reasoning:
            lines.append(f"  Reasoning: {step.llm_reasoning}")
        if step.element_info:
            lines.append(f"  Element: {json.dumps(step.element_info)}")
        lines.append(f"  Success: {step.success}")
        lines.append("")

    if trace.parameters_used:
        lines.append("Parameters used:")
        for k, v in trace.parameters_used.items():
            lines.append(f"  {k}: {v}")

    return "\n".join(lines)


def extract_unique_xpaths(trace: InteractionTrace) -> list[str]:
    """Extract all unique XPaths from a trace."""
    xpaths = set()
    for step in trace.steps:
        if step.target_xpath:
            xpaths.add(step.target_xpath)
        if step.action.target:
            xpaths.add(step.action.target)
    return sorted(xpaths)


def estimate_parameters(trace: InteractionTrace) -> dict[str, str]:
    """Identify typed text that likely represents variable input.

    Heuristic: text typed into input fields that looks like user-specific data
    (emails, names, search queries, etc.).
    """
    params: dict[str, str] = {}
    for step in trace.steps:
        if step.action.type.value == "action_type" and step.action.text:
            text = step.action.text
            # Common parameter patterns
            if "@" in text:
                params[f"email_{len(params)}"] = text
            elif len(text) > 3 and not text.isdigit():
                params[f"input_{len(params)}"] = text
    return params
