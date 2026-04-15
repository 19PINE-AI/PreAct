"""Workflow-Use baseline — linear script compilation with agent fallback.

Workflow-Use (browser-use, 2025) records browser interactions and converts
them into deterministic linear scripts with variables.

Key differences from PreAct:
1. Generates linear scripts, not state graphs
2. No conditional branching in compiled artifacts
3. No incremental refinement
4. Browser-only
"""

from preact.baselines.workflow_use.system import WorkflowUseBaseline

__all__ = ["WorkflowUseBaseline"]
