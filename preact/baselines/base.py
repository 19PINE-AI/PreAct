"""Base interface for all baseline systems.

All baselines implement this protocol for fair comparison in evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class BaselineResult:
    """Standardized result from any baseline system."""

    success: bool
    mode: str  # "exploration", "replay", "hybrid"
    actions_executed: int = 0
    total_time_ms: float = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    actions_via_cache: int = 0  # Actions from cached/compiled artifact
    actions_via_llm: int = 0  # Actions requiring LLM
    fallback_count: int = 0
    error: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def graph_coverage(self) -> float:
        if self.actions_executed == 0:
            return 0.0
        return self.actions_via_cache / self.actions_executed

    @property
    def cost_estimate(self) -> float:
        input_cost = self.total_input_tokens * 0.10 / 1_000_000
        output_cost = self.total_output_tokens * 0.40 / 1_000_000
        return input_cost + output_cost


class BaselineSystem(Protocol):
    """Protocol that all baseline systems must implement."""

    name: str

    async def run_exploration(
        self, task: str, env: Any, llm: Any, **kwargs: Any
    ) -> BaselineResult:
        """Run 1: exploration/recording phase."""
        ...

    async def run_replay(
        self, task: str, env: Any, llm: Any, **kwargs: Any
    ) -> BaselineResult:
        """Run 2: replay from compiled/cached artifact."""
        ...

    async def reset(self) -> None:
        """Reset the system's internal state (cached artifacts, etc.)."""
        ...

    def has_cached_artifact(self, task: str) -> bool:
        """Check if a cached/compiled artifact exists for a task."""
        ...
