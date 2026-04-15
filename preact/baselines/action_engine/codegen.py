"""ActionEngine code generation — state machine to Python script.

Reimplements ActionEngine's approach of converting a crawled state machine
into a flat Python script. This is the lossy transformation that PreAct avoids.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from preact.baselines.action_engine.crawler import CrawlGraph

if TYPE_CHECKING:
    from preact.llm.client import LLMClient

logger = logging.getLogger(__name__)

CODEGEN_PROMPT = """You are generating a Python script from a state-machine graph of a web application.

The graph has {state_count} states and {transition_count} transitions.

States and their elements:
{states_description}

Transitions:
{transitions_description}

Task to accomplish: {task}

Generate a Python function called `execute_task(page, **params)` that uses Playwright's `page` object to accomplish the task. The function should:
1. Navigate through the states using click/type actions
2. Wait for elements before interacting
3. Handle basic errors with try/except
4. Return True on success, False on failure

Output ONLY the Python code, no explanations."""


async def generate_script(
    graph: CrawlGraph,
    task: str,
    llm: LLMClient,
) -> str:
    """Generate a Python script from a crawl graph for a specific task.

    This is ActionEngine's approach: the state machine is used to
    inform code generation, but the output is a flat Python script,
    not the state machine itself.
    """
    states_desc = []
    for state_id, state in graph.states.items():
        elements = [
            f"  - {e.get('tag', '?')}: {e.get('text', '?')[:50]} ({e.get('xpath', '')})"
            for e in state.interactive_elements[:5]
        ]
        states_desc.append(
            f"State '{state_id}' (URL: {state.url}):\n" + "\n".join(elements)
        )

    transitions_desc = []
    for t in graph.transitions:
        transitions_desc.append(
            f"  {t.from_state} --[{t.action} on '{t.element_text[:30]}']"
            f"--> {t.to_state}"
        )

    prompt = CODEGEN_PROMPT.format(
        state_count=graph.state_count,
        transition_count=graph.transition_count,
        states_description="\n\n".join(states_desc),
        transitions_description="\n".join(transitions_desc),
        task=task,
    )

    response = await llm.complete(
        messages=[{"role": "user", "content": prompt}]
    )

    # Extract Python code from response
    code = _extract_python(response)
    logger.info("Generated script: %d lines", code.count("\n") + 1)
    return code


def _extract_python(text: str) -> str:
    """Extract Python code from LLM response."""
    if "```python" in text:
        start = text.index("```python") + 9
        end = text.index("```", start)
        return text[start:end].strip()
    if "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        return text[start:end].strip()
    return text.strip()
