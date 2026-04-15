"""AgentRR multi-level experience store.

Implements the three-level experience hierarchy from the AgentRR paper:
- High-level: task decomposition and strategy
- Mid-level: sub-task procedures
- Low-level: precise operational descriptions
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LowLevelExperience:
    """Precise operational description for a single action."""

    step_number: int
    description: str  # NL description of what to do
    action_type: str
    target_description: str  # NL description of target element
    target_xpath: str | None = None  # Optional XPath (less reliable in AgentRR)
    check_function: str | None = None  # Verification condition


@dataclass
class MidLevelExperience:
    """Sub-task procedure — a sequence of low-level experiences."""

    sub_task: str
    steps: list[LowLevelExperience] = field(default_factory=list)


@dataclass
class HighLevelExperience:
    """Task-level strategy and decomposition."""

    task_description: str
    strategy: str  # NL description of overall approach
    sub_tasks: list[MidLevelExperience] = field(default_factory=list)
    app_context: str = ""


@dataclass
class ExperienceStore:
    """Store of multi-level experiences indexed by task."""

    experiences: dict[str, HighLevelExperience] = field(default_factory=dict)

    def store(self, task: str, experience: HighLevelExperience) -> None:
        self.experiences[task] = experience

    def retrieve(self, task: str) -> HighLevelExperience | None:
        # Simple exact match — AgentRR uses more sophisticated retrieval
        return self.experiences.get(task)

    def has_experience(self, task: str) -> bool:
        return task in self.experiences

    def clear(self) -> None:
        self.experiences.clear()
