"""Main evaluation runner.

Orchestrates all experiments and generates the final report.
Can be run standalone or through the CLI.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import Any

from preact.baselines.action_engine import ActionEngineBaseline
from preact.baselines.agent_rr import AgentRRBaseline
from preact.baselines.muscle_mem import MuscleMemBaseline
from preact.baselines.preact_baseline import PreActBaseline
from preact.baselines.standard_cua import StandardCUABaseline
from preact.baselines.workflow_use import WorkflowUseBaseline
from preact.config import PreActConfig
from preact.environment.browser import BrowserEnvironment
from preact.evaluation.experiments import (
    LOCAL_TEST_TASKS,
    PreActFlatCodeBaseline,
    PreActNoBranchBaseline,
    PreActNoRAGBaseline,
    PreActNoRefineBaseline,
    PreActNoVerifyBaseline,
    experiment_1_end_to_end,
    experiment_2_acceleration,
    experiment_3_adaptation,
    experiment_4_representation,
    experiment_5_ablation,
)
from preact.evaluation.harness import EvaluationHarness
from preact.evaluation.report import generate_full_report, save_report
from preact.llm.client import LLMClient

logger = logging.getLogger(__name__)


def create_env_factory(headless: bool = True):
    """Create a factory for browser environments."""

    def factory(start_url: str) -> BrowserEnvironment:
        return BrowserEnvironment(
            headless=headless,
            start_url=start_url,
        )

    return factory


def create_llm_factory():
    """Create a factory for LLM clients."""
    config = PreActConfig()

    def factory() -> LLMClient:
        return LLMClient(config.llm)

    return factory


async def run_all_experiments(
    headless: bool = True,
    output_dir: str = "results",
    experiments: list[str] | None = None,
) -> dict[str, Any]:
    """Run all evaluation experiments.

    Args:
        headless: Whether to run browsers in headless mode.
        output_dir: Directory for results output.
        experiments: Optional list of experiment names to run.
                     If None, runs all experiments.

    Returns:
        Dict mapping experiment names to their results.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    env_factory = create_env_factory(headless)
    llm_factory = create_llm_factory()

    harness = EvaluationHarness(output_dir)

    # Register all systems
    harness.register_system("Standard CUA", StandardCUABaseline())
    harness.register_system("ActionEngine", ActionEngineBaseline())
    harness.register_system("Muscle-Mem", MuscleMemBaseline())
    harness.register_system("AgentRR", AgentRRBaseline())
    harness.register_system("Workflow-Use", WorkflowUseBaseline())
    harness.register_system("PreAct", PreActBaseline())

    # Ablation variants
    harness.register_system("PreAct-NoVerify", PreActNoVerifyBaseline())
    harness.register_system("PreAct-NoBranch", PreActNoBranchBaseline())
    harness.register_system("PreAct-NoRefine", PreActNoRefineBaseline())
    harness.register_system("PreAct-NoRAG", PreActNoRAGBaseline())
    harness.register_system("PreAct-FlatCode", PreActFlatCodeBaseline())

    all_experiments = {
        "exp1": experiment_1_end_to_end,
        "exp2": experiment_2_acceleration,
        "exp3": experiment_3_adaptation,
        "exp4": experiment_4_representation,
        "exp5": experiment_5_ablation,
    }

    selected = experiments or list(all_experiments.keys())
    all_results = {}

    for exp_name in selected:
        if exp_name not in all_experiments:
            logger.warning("Unknown experiment: %s", exp_name)
            continue

        config = all_experiments[exp_name]()
        logger.info("=" * 60)
        logger.info("Running %s: %s", exp_name, config.name)
        logger.info("=" * 60)

        try:
            results = await harness.run_experiment(
                config, env_factory, llm_factory
            )
            all_results[config.name] = results

            # Generate report for this experiment
            report_path = save_report(results, config.name, output_dir)
            logger.info("Report saved: %s", report_path)

        except Exception as e:
            logger.error("Experiment %s failed: %s", exp_name, e, exc_info=True)
            all_results[config.name] = {"error": str(e)}

    return all_results


async def run_quick_test(headless: bool = False) -> dict[str, Any]:
    """Run a quick test with a single task to verify the system works."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    from preact.evaluation.harness import BenchmarkTask, ExperimentConfig

    task = BenchmarkTask(
        task_id="quick_test",
        task_description="Search for 'hello world' on Google",
        start_url="https://www.google.com",
        parameters={"query": "hello world"},
    )

    config = ExperimentConfig(
        name="quick_test",
        systems=["Standard CUA", "PreAct"],
        tasks=[task],
        num_runs=1,
        headless=headless,
    )

    env_factory = create_env_factory(headless)
    llm_factory = create_llm_factory()

    harness = EvaluationHarness("results")
    harness.register_system("Standard CUA", StandardCUABaseline())
    harness.register_system("PreAct", PreActBaseline())

    results = await harness.run_experiment(config, env_factory, llm_factory)
    return results


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "quick"
    if mode == "quick":
        asyncio.run(run_quick_test(headless=False))
    elif mode == "all":
        asyncio.run(run_all_experiments(headless=True))
    else:
        asyncio.run(
            run_all_experiments(headless=True, experiments=mode.split(","))
        )
