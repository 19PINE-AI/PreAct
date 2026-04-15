"""PreAct CLI — command-line interface for running tasks."""

from __future__ import annotations

import asyncio
import json
import logging
import sys

import click

from preact.config import PreActConfig


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def main(verbose: bool):
    """PreAct: Predictive Actions for High-Performance Computer Using Agents."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )


@main.command()
@click.argument("task")
@click.option("--url", "-u", help="Starting URL for the browser")
@click.option("--param", "-p", multiple=True, help="Parameters as key=value")
@click.option("--headless/--no-headless", default=True)
@click.option("--force-cua", is_flag=True, help="Force CUA mode (skip RAG)")
@click.option("--force-rpa", is_flag=True, help="Force RPA mode")
def run(task: str, url: str, param: tuple, headless: bool, force_cua: bool, force_rpa: bool):
    """Execute a task with PreAct."""
    parameters = {}
    for p in param:
        key, _, value = p.partition("=")
        parameters[key] = value

    asyncio.run(
        _run_task(task, url, parameters, headless, force_cua, force_rpa)
    )


async def _run_task(
    task: str,
    url: str | None,
    parameters: dict,
    headless: bool,
    force_cua: bool,
    force_rpa: bool,
):
    from preact.core.agent import PreActAgent
    from preact.environment.browser import BrowserEnvironment
    from preact.llm.client import LLMClient

    config = PreActConfig()
    llm = LLMClient(config.llm)
    env = BrowserEnvironment(headless=headless, start_url=url)

    await env.start()
    try:
        agent = PreActAgent(env, llm, config)
        result = await agent.execute_task(
            task, parameters=parameters, force_cua=force_cua, force_rpa=force_rpa
        )
        click.echo(f"\nResult: {'SUCCESS' if result.success else 'FAILED'}")
        click.echo(f"Mode: {result.mode}")
        click.echo(f"Time: {result.total_time_ms:.0f}ms")
        click.echo(f"Tokens: {result.total_input_tokens + result.total_output_tokens}")
        if result.program_id:
            click.echo(f"Program: {result.program_id}")
        if result.error:
            click.echo(f"Error: {result.error}")
    finally:
        await env.stop()


@main.command()
@click.argument("task")
@click.option("--url", "-u", help="Starting URL")
@click.option("--headless/--no-headless", default=True)
@click.option("--max-steps", default=30, help="Max CUA steps")
def record(task: str, url: str, headless: bool, max_steps: int):
    """Record a CUA interaction trace."""
    asyncio.run(_record_task(task, url, headless, max_steps))


async def _record_task(task: str, url: str | None, headless: bool, max_steps: int):
    from preact.cua.loop import CUALoop
    from preact.environment.browser import BrowserEnvironment
    from preact.llm.client import LLMClient
    from preact.recorder.recorder import InteractionRecorder
    from preact.recorder.trace import save_trace

    config = PreActConfig()
    llm = LLMClient(config.llm)
    env = BrowserEnvironment(headless=headless, start_url=url)

    await env.start()
    try:
        recorder = InteractionRecorder(env, config.recorder)
        cua = CUALoop(env, llm, recorder, config.cua)
        result = await cua.run(task, max_steps=max_steps, record=True)

        click.echo(f"\nCUA Result: {'SUCCESS' if result.success else 'FAILED'}")
        click.echo(f"Actions: {result.actions_taken}")
        click.echo(f"Time: {result.total_time_ms:.0f}ms")

        if result.trace:
            trace_path = f"traces/{result.trace.trace_id}.json"
            save_trace(result.trace, trace_path)
            click.echo(f"Trace saved: {trace_path}")
    finally:
        await env.stop()


@main.command()
@click.argument("trace_path")
def compile(trace_path: str):
    """Compile a trace into an RPA program."""
    asyncio.run(_compile_trace(trace_path))


async def _compile_trace(trace_path: str):
    from preact.generator.compiler import ModelGenerator
    from preact.llm.client import LLMClient
    from preact.recorder.trace import load_trace

    config = PreActConfig()
    llm = LLMClient(config.llm)
    generator = ModelGenerator(llm)

    trace = load_trace(trace_path)
    program = await generator.compile(trace)

    output_path = trace_path.replace(".json", "_program.json")
    with open(output_path, "w") as f:
        f.write(program.model_dump_json(indent=2))

    click.echo(f"Program compiled: {len(program.states)} states, {len(program.transitions)} transitions")
    click.echo(f"Saved to: {output_path}")


@main.command()
@click.argument("program_path")
@click.option("--url", "-u", help="Starting URL")
@click.option("--param", "-p", multiple=True, help="Parameters as key=value")
@click.option("--headless/--no-headless", default=True)
def replay(program_path: str, url: str, param: tuple, headless: bool):
    """Replay an RPA program."""
    parameters = {}
    for p in param:
        key, _, value = p.partition("=")
        parameters[key] = value

    asyncio.run(_replay_program(program_path, url, parameters, headless))


async def _replay_program(
    program_path: str, url: str | None, parameters: dict, headless: bool
):
    from preact.environment.browser import BrowserEnvironment
    from preact.executor.engine import RPAExecutor
    from preact.llm.client import LLMClient
    from preact.schemas import RPAProgram

    config = PreActConfig()
    llm = LLMClient(config.llm)
    env = BrowserEnvironment(headless=headless, start_url=url)

    with open(program_path) as f:
        program = RPAProgram.model_validate_json(f.read())

    await env.start()
    try:
        executor = RPAExecutor(env, llm)
        result = await executor.execute(program, parameters)

        click.echo(f"\nReplay: {'SUCCESS' if result.success else 'FAILED'}")
        click.echo(f"States visited: {len(result.states_visited)}")
        click.echo(f"Actions: {result.actions_executed}")
        click.echo(f"RPA time: {result.rpa_time_ms:.0f}ms")
        click.echo(f"Graph coverage: {result.graph_coverage:.1%}")
        if result.error:
            click.echo(f"Error: {result.error}")
    finally:
        await env.stop()


@main.command()
def store_list():
    """List all programs in the RAG store."""
    asyncio.run(_list_programs())


async def _list_programs():
    from preact.llm.client import LLMClient
    from preact.rag.store import ProgramStore

    config = PreActConfig()
    llm = LLMClient(config.llm)
    store = ProgramStore(llm, config.rag)

    programs = await store.list_all()
    if not programs:
        click.echo("No programs stored.")
        return

    for p in programs:
        click.echo(
            f"  {p['program_id'][:12]}  v{p['version']}  "
            f"{p['state_count']} states  {p['task_description'][:60]}"
        )


if __name__ == "__main__":
    main()
