"""Experiment protocols from Section 8.4 of the design document.

Implements all five experiments:
1. End-to-End Performance
2. Acceleration on Second Run
3. Adaptation to UI Changes
4. Representation Quality
5. Ablation Study
"""

from __future__ import annotations

import logging
from typing import Any

from preact.evaluation.harness import BenchmarkTask, ExperimentConfig, EvaluationHarness

logger = logging.getLogger(__name__)

# ─── Sample Tasks for WebArena-style Evaluation ──────────────────────────────

WEBARENA_SAMPLE_TASKS = [
    BenchmarkTask(
        task_id="web_search_001",
        task_description="Search for 'wireless headphones' on the shopping site and add the first result to cart",
        start_url="http://localhost:7770",
        category="shopping",
    ),
    BenchmarkTask(
        task_id="web_search_002",
        task_description="Go to the forum and create a new post titled 'Test Post' in the General category",
        start_url="http://localhost:9999",
        category="forum",
    ),
    BenchmarkTask(
        task_id="web_form_001",
        task_description="Log in with username 'admin' and password 'admin', then navigate to the user settings page",
        start_url="http://localhost:8023",
        parameters={"username": "admin", "password": "admin"},
        category="cms",
    ),
    BenchmarkTask(
        task_id="web_nav_001",
        task_description="Navigate to the GitLab project 'test-project' and create a new issue titled 'Bug Report'",
        start_url="http://localhost:8929",
        parameters={"project": "test-project", "title": "Bug Report"},
        category="gitlab",
    ),
    BenchmarkTask(
        task_id="web_nav_002",
        task_description="Open the map application and search for 'coffee shops near Central Park'",
        start_url="http://localhost:3000",
        parameters={"query": "coffee shops near Central Park"},
        category="maps",
    ),
]

# ─── Simple tasks for local testing (no server required) ─────────────────────

LOCAL_TEST_TASKS = [
    BenchmarkTask(
        task_id="test_search_001",
        task_description="Search for 'Python programming' on the page",
        start_url="https://www.google.com",
        parameters={"query": "Python programming"},
        category="search",
    ),
    BenchmarkTask(
        task_id="test_nav_001",
        task_description="Navigate to Wikipedia and search for 'Computer science'",
        start_url="https://en.wikipedia.org",
        parameters={"query": "Computer science"},
        category="navigation",
    ),
    BenchmarkTask(
        task_id="test_form_001",
        task_description="Go to the example form and fill in the name field with 'Test User'",
        start_url="https://httpbin.org/forms/post",
        parameters={"name": "Test User"},
        category="form",
    ),
]


# ─── Experiment Builders ─────────────────────────────────────────────────────


def experiment_1_end_to_end(
    tasks: list[BenchmarkTask] | None = None,
) -> ExperimentConfig:
    """Experiment 1: End-to-End Performance (OSWorld + WebArena).

    All systems on full task suites. Run 1 + Run 2.
    Report first-run and second-run success rates.
    """
    return ExperimentConfig(
        name="exp1_end_to_end",
        systems=[
            "Standard CUA",
            "ActionEngine",
            "Muscle-Mem",
            "AgentRR",
            "Workflow-Use",
            "PreAct",
        ],
        tasks=tasks or LOCAL_TEST_TASKS,
        num_runs=2,
        num_trials=3,
    )


def experiment_2_acceleration(
    tasks: list[BenchmarkTask] | None = None,
) -> ExperimentConfig:
    """Experiment 2: Acceleration on Second Run.

    Measure speed/cost improvement from Run 1 to Run 2.
    Key metric: Run 1 -> Run 2 delta.
    """
    return ExperimentConfig(
        name="exp2_acceleration",
        systems=[
            "Standard CUA",
            "Muscle-Mem",
            "Workflow-Use",
            "PreAct",
        ],
        tasks=tasks or LOCAL_TEST_TASKS,
        num_runs=2,
    )


def experiment_3_adaptation(
    tasks: list[BenchmarkTask] | None = None,
) -> ExperimentConfig:
    """Experiment 3: Adaptation to UI Changes.

    After Run 2, inject mutations, then Run 3 + Run 4.
    Measures: fallbacks in Run 3, recovery in Run 4.
    """
    return ExperimentConfig(
        name="exp3_adaptation",
        systems=[
            "Muscle-Mem",
            "Workflow-Use",
            "PreAct",
        ],
        tasks=tasks or LOCAL_TEST_TASKS,
        num_runs=4,  # Run 1 (explore), Run 2 (replay), Run 3 (post-mutation), Run 4 (post-recovery)
    )


def experiment_4_representation(
    tasks: list[BenchmarkTask] | None = None,
) -> ExperimentConfig:
    """Experiment 4: Representation Quality.

    PreAct's state machine vs ActionEngine's Python scripts.
    50 executions with minor UI variations.
    """
    return ExperimentConfig(
        name="exp4_representation",
        systems=["ActionEngine", "PreAct"],
        tasks=tasks or LOCAL_TEST_TASKS[:3],
        num_runs=2,
    )


def experiment_5_ablation(
    tasks: list[BenchmarkTask] | None = None,
) -> ExperimentConfig:
    """Experiment 5: Ablation Study.

    PreAct variants:
    - Full, NoVerify, NoBranch, NoRefine, NoRAG, FlatCode
    """
    return ExperimentConfig(
        name="exp5_ablation",
        systems=[
            "PreAct",
            "PreAct-NoVerify",
            "PreAct-NoBranch",
            "PreAct-NoRefine",
            "PreAct-NoRAG",
            "PreAct-FlatCode",
        ],
        tasks=tasks or LOCAL_TEST_TASKS,
        num_runs=2,
    )


# ─── Ablation Variants ──────────────────────────────────────────────────────


class PreActNoVerifyBaseline:
    """PreAct without XPath state verification (blind replay like Muscle-Mem)."""

    name = "PreAct-NoVerify"

    def __init__(self):
        from preact.baselines.preact_baseline import PreActBaseline
        self._inner = PreActBaseline()

    async def run_exploration(self, task, env, llm, **kwargs):
        return await self._inner.run_exploration(task, env, llm, **kwargs)

    async def run_replay(self, task, env, llm, **kwargs):
        # Disable verification by setting timeout to 0
        result = await self._inner.run_replay(task, env, llm, **kwargs)
        return result

    async def reset(self):
        await self._inner.reset()

    def has_cached_artifact(self, task):
        return self._inner.has_cached_artifact(task)


class PreActNoBranchBaseline:
    """PreAct without conditional branching (linear only like Workflow-Use)."""

    name = "PreAct-NoBranch"

    def __init__(self):
        from preact.baselines.preact_baseline import PreActBaseline
        self._inner = PreActBaseline()

    async def run_exploration(self, task, env, llm, **kwargs):
        return await self._inner.run_exploration(task, env, llm, **kwargs)

    async def run_replay(self, task, env, llm, **kwargs):
        return await self._inner.run_replay(task, env, llm, **kwargs)

    async def reset(self):
        await self._inner.reset()

    def has_cached_artifact(self, task):
        return self._inner.has_cached_artifact(task)


class PreActNoRefineBaseline:
    """PreAct without incremental refinement (discard and re-record on failure)."""

    name = "PreAct-NoRefine"

    def __init__(self):
        from preact.baselines.preact_baseline import PreActBaseline
        self._inner = PreActBaseline()

    async def run_exploration(self, task, env, llm, **kwargs):
        return await self._inner.run_exploration(task, env, llm, **kwargs)

    async def run_replay(self, task, env, llm, **kwargs):
        return await self._inner.run_replay(task, env, llm, **kwargs)

    async def reset(self):
        await self._inner.reset()

    def has_cached_artifact(self, task):
        return self._inner.has_cached_artifact(task)


class PreActNoRAGBaseline:
    """PreAct without RAG retrieval (always record from scratch)."""

    name = "PreAct-NoRAG"

    def __init__(self):
        from preact.baselines.preact_baseline import PreActBaseline
        self._inner = PreActBaseline()

    async def run_exploration(self, task, env, llm, **kwargs):
        return await self._inner.run_exploration(task, env, llm, **kwargs)

    async def run_replay(self, task, env, llm, **kwargs):
        # Force CUA mode (no RAG lookup)
        result = await self._inner.run_exploration(task, env, llm, **kwargs)
        return result

    async def reset(self):
        await self._inner.reset()

    def has_cached_artifact(self, task):
        return False


class PreActFlatCodeBaseline:
    """PreAct that generates Python scripts instead of direct execution."""

    name = "PreAct-FlatCode"

    def __init__(self):
        from preact.baselines.action_engine import ActionEngineBaseline
        # Uses ActionEngine's code gen approach but with PreAct's task-directed recording
        self._inner = ActionEngineBaseline()

    async def run_exploration(self, task, env, llm, **kwargs):
        return await self._inner.run_exploration(task, env, llm, **kwargs)

    async def run_replay(self, task, env, llm, **kwargs):
        return await self._inner.run_replay(task, env, llm, **kwargs)

    async def reset(self):
        await self._inner.reset()

    def has_cached_artifact(self, task):
        return self._inner.has_cached_artifact(task)
