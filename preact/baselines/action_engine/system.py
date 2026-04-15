"""ActionEngine complete baseline system.

Combines crawling, code generation, and execution into a single
baseline that implements the BaselineSystem protocol.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from preact.baselines.action_engine.codegen import generate_script
from preact.baselines.action_engine.crawler import AppCrawler, CrawlGraph
from preact.baselines.action_engine.executor import execute_script
from preact.baselines.base import BaselineResult

logger = logging.getLogger(__name__)


class ActionEngineBaseline:
    """ActionEngine baseline (Zhong et al., 2026).

    Phase 1 (Exploration): Crawl the app to build state-machine graph,
    then generate a Python script for the task.
    Phase 2 (Replay): Execute the generated Python script.
    Fallback: Re-crawl changed sections and regenerate.
    """

    name = "ActionEngine"

    def __init__(self):
        self._graphs: dict[str, CrawlGraph] = {}
        self._scripts: dict[str, str] = {}

    async def run_exploration(
        self, task: str, env: Any, llm: Any, **kwargs: Any
    ) -> BaselineResult:
        """Phase 1: Crawl app + generate script + execute."""
        start = time.monotonic()
        start_tokens_in = llm.total_input_tokens
        start_tokens_out = llm.total_output_tokens

        # Step 1: Crawl the application (untargeted)
        crawler = AppCrawler(env, max_states=15)
        graph = await crawler.crawl()
        self._graphs[task] = graph

        crawl_time = (time.monotonic() - start) * 1000

        # Step 2: Generate Python script from graph
        script = await generate_script(graph, task, llm)
        self._scripts[task] = script

        # Step 3: Also run CUA to actually complete the task
        # (ActionEngine uses the script, but we also need CUA for fair comparison)
        from preact.cua.loop import CUALoop

        cua = CUALoop(env, llm)
        cua_result = await cua.run(task, record=False)

        total_time = (time.monotonic() - start) * 1000
        return BaselineResult(
            success=cua_result.success,
            mode="exploration",
            actions_executed=cua_result.actions_taken,
            total_time_ms=total_time,
            total_input_tokens=llm.total_input_tokens - start_tokens_in,
            total_output_tokens=llm.total_output_tokens - start_tokens_out,
            actions_via_cache=0,
            actions_via_llm=cua_result.actions_taken,
            error=cua_result.error,
            extra={
                "crawl_time_ms": crawl_time,
                "graph_states": graph.state_count,
                "graph_transitions": graph.transition_count,
                "script_lines": script.count("\n") + 1,
            },
        )

    async def run_replay(
        self, task: str, env: Any, llm: Any, **kwargs: Any
    ) -> BaselineResult:
        """Phase 2: Execute the generated Python script."""
        start = time.monotonic()
        start_tokens_in = llm.total_input_tokens
        start_tokens_out = llm.total_output_tokens

        script = self._scripts.get(task)
        if not script:
            return BaselineResult(
                success=False,
                mode="replay",
                error="No script available (exploration not run)",
            )

        result = await execute_script(script, env, kwargs.get("parameters"))
        total_time = (time.monotonic() - start) * 1000

        if not result["success"]:
            # Fallback: regenerate script
            logger.info("Script failed, regenerating...")
            graph = self._graphs.get(task)
            if graph:
                script = await generate_script(graph, task, llm)
                self._scripts[task] = script
                result = await execute_script(script, env, kwargs.get("parameters"))

        return BaselineResult(
            success=result["success"],
            mode="replay",
            actions_executed=1,  # Script counts as single execution unit
            total_time_ms=total_time,
            total_input_tokens=llm.total_input_tokens - start_tokens_in,
            total_output_tokens=llm.total_output_tokens - start_tokens_out,
            actions_via_cache=1 if result["success"] else 0,
            actions_via_llm=0 if result["success"] else 1,
            error=result.get("error"),
        )

    async def reset(self) -> None:
        self._graphs.clear()
        self._scripts.clear()

    def has_cached_artifact(self, task: str) -> bool:
        return task in self._scripts
