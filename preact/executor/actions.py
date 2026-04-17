"""Action executors for RPA program steps.

Each action type from the schema maps to a function that takes the
environment, action spec, and execution context, then performs the action.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from preact.schemas import ActionSpec, ActionType

if TYPE_CHECKING:
    from preact.environment.base import ComputerEnvironment
    from preact.executor.context import ExecutionContext
    from preact.llm.client import LLMClient

logger = logging.getLogger(__name__)


async def execute_action(
    action: ActionSpec,
    env: ComputerEnvironment,
    ctx: ExecutionContext,
    llm: LLMClient | None = None,
) -> None:
    """Dispatch and execute a single action."""
    handler = _ACTION_HANDLERS.get(action.type)
    if handler is None:
        raise ValueError(f"Unknown action type: {action.type}")
    await handler(action, env, ctx, llm)


async def _action_click(
    action: ActionSpec,
    env: ComputerEnvironment,
    ctx: ExecutionContext,
    llm: LLMClient | None,
) -> None:
    target = ctx.resolve_template(action.target) if action.target else None
    if not target:
        raise ValueError("action_click requires a target XPath")
    await env.click(target)


async def _action_double_click(
    action: ActionSpec,
    env: ComputerEnvironment,
    ctx: ExecutionContext,
    llm: LLMClient | None,
) -> None:
    target = ctx.resolve_template(action.target) if action.target else None
    if not target:
        raise ValueError("action_double_click requires a target XPath")
    await env.double_click(target)


async def _action_move(
    action: ActionSpec,
    env: ComputerEnvironment,
    ctx: ExecutionContext,
    llm: LLMClient | None,
) -> None:
    target = ctx.resolve_template(action.target) if action.target else None
    if not target:
        raise ValueError("action_move requires a target XPath")
    await env.move_to(target)


async def _action_navigate(
    action: ActionSpec,
    env: ComputerEnvironment,
    ctx: ExecutionContext,
    llm: LLMClient | None,
) -> None:
    url = ctx.resolve_template(action.text) if action.text else None
    if not url:
        raise ValueError("action_navigate requires a URL in text field")
    await env.navigate(url)


async def _action_type(
    action: ActionSpec,
    env: ComputerEnvironment,
    ctx: ExecutionContext,
    llm: LLMClient | None,
) -> None:
    target = ctx.resolve_template(action.target) if action.target else None
    if action.parameter_name:
        text = ctx.resolve_parameter(action.parameter_name)
    elif action.text:
        text = ctx.resolve_template(action.text)
    else:
        raise ValueError("action_type requires either text or parameter_name")

    if target:
        try:
            await env.type_text(target, text)
        except Exception as e:
            # Fallback: element might be a <select> — try select_option
            # Only fall back for element-type errors, not network/timeout
            err_msg = str(e).lower()
            if "fill" in err_msg or "input" in err_msg or "select" in err_msg or "element" in err_msg:
                await env.select_option(target, text)
            else:
                raise
    else:
        # Type without a specific target (assume current focus)
        await env.press_key(text)


async def _action_keypress(
    action: ActionSpec,
    env: ComputerEnvironment,
    ctx: ExecutionContext,
    llm: LLMClient | None,
) -> None:
    key = action.key
    if not key:
        raise ValueError("action_keypress requires a key")
    await env.press_key(key)


async def _action_scroll(
    action: ActionSpec,
    env: ComputerEnvironment,
    ctx: ExecutionContext,
    llm: LLMClient | None,
) -> None:
    direction = action.direction or "down"
    amount = action.amount or 3
    if action.target:
        target = ctx.resolve_template(action.target)
        await env.scroll_element(target, direction, amount)
    else:
        await env.scroll(direction, amount)


async def _action_drag(
    action: ActionSpec,
    env: ComputerEnvironment,
    ctx: ExecutionContext,
    llm: LLMClient | None,
) -> None:
    from_target = action.from_target
    to_target = action.to_target
    if not from_target or not to_target:
        raise ValueError("action_drag requires from_target and to_target")
    await env.drag(
        ctx.resolve_template(from_target),
        ctx.resolve_template(to_target),
    )


async def _action_wait(
    action: ActionSpec,
    env: ComputerEnvironment,
    ctx: ExecutionContext,
    llm: LLMClient | None,
) -> None:
    ms = action.ms or 500
    await asyncio.sleep(ms / 1000.0)


async def _action_inspect_text(
    action: ActionSpec,
    env: ComputerEnvironment,
    ctx: ExecutionContext,
    llm: LLMClient | None,
) -> None:
    """Extract text from an element, capture full screenshot, and process with vision LLM + thinking."""
    if not action.target:
        raise ValueError("inspect_text requires a target XPath")
    if not llm:
        raise ValueError("inspect_text requires an LLM client")

    target = ctx.resolve_template(action.target)
    prompt = ctx.resolve_template(action.prompt or "Analyze this text")

    # Extract element text (may fail if XPath is stale — that's OK, screenshot is primary)
    text = ""
    try:
        text = await env.element_text(target)
    except Exception as e:
        logger.warning("inspect_text: element_text failed for %s: %s", target, e)

    # Capture full page screenshot for visual context
    screenshot = await env.screenshot()

    text_prompt = (
        "You are extracting data from a web page. "
        "Above is a screenshot of the full page as the user sees it.\n\n"
    )
    if text:
        text_prompt += (
            f"Additionally, here is the text content extracted from a specific element:\n\n"
            f"---\n{text}\n---\n\n"
        )
    text_prompt += f"{prompt}"

    response = await llm.complete_with_vision(
        text_prompt=text_prompt,
        images=[screenshot],
        thinking_budget=4096,
    )

    if action.store_result_as:
        ctx.set_data(action.store_result_as, response.strip())


async def _action_inspect_screenshot(
    action: ActionSpec,
    env: ComputerEnvironment,
    ctx: ExecutionContext,
    llm: LLMClient | None,
) -> None:
    """Capture full page screenshot and process with vision LLM + thinking."""
    if not llm:
        raise ValueError("inspect_screenshot requires an LLM client")

    # Always use full page screenshot for maximum context
    screenshot = await env.screenshot()
    prompt = ctx.resolve_template(action.prompt or "Analyze this image")

    response = await llm.complete_with_vision(
        text_prompt=prompt,
        images=[screenshot],
        thinking_budget=4096,
    )

    if action.store_result_as:
        ctx.set_data(action.store_result_as, response.strip())


async def _action_evaluate_condition(
    action: ActionSpec,
    env: ComputerEnvironment,
    ctx: ExecutionContext,
    llm: LLMClient | None,
) -> None:
    """Evaluate a condition expression and store the result."""
    if not action.expression:
        raise ValueError("evaluate_condition requires an expression")

    result = ctx.evaluate_expression(action.expression)
    if action.store_result_as:
        ctx.set_data(action.store_result_as, result)


async def _action_conditional(
    action: ActionSpec,
    env: ComputerEnvironment,
    ctx: ExecutionContext,
    llm: LLMClient | None,
) -> None:
    """Evaluate a condition — the executor handles the branching logic.

    The conditional action itself just evaluates the guard; the executor
    uses this to choose which transition to follow.
    """
    # If there's a side-effect action (then), execute it
    if action.then:
        await execute_action(action.then, env, ctx, llm)


async def _action_compute(
    action: ActionSpec,
    env: ComputerEnvironment,
    ctx: ExecutionContext,
    llm: LLMClient | None,
) -> None:
    """Compute a template expression and store the result."""
    if not action.expression:
        raise ValueError("compute requires an expression")
    result = ctx.resolve_template(action.expression)
    if action.store_result_as:
        ctx.set_data(action.store_result_as, result)


async def _action_human_intervention(
    action: ActionSpec,
    env: ComputerEnvironment,
    ctx: ExecutionContext,
    llm: LLMClient | None,
) -> None:
    """Request human intervention (approval, input, etc.).

    In automated mode, this auto-continues based on on_timeout setting.
    """
    prompt = ctx.resolve_template(action.prompt or "Human intervention needed")
    logger.info("Human intervention requested: %s", prompt)

    # In automated evaluation mode, auto-continue
    timeout = action.timeout_sec or 60
    on_timeout = action.on_timeout

    if on_timeout == "continue":
        logger.info("Auto-continuing (on_timeout=continue)")
        if action.store_result_as:
            ctx.set_data(action.store_result_as, "auto_approved")
    elif on_timeout == "abort":
        raise RuntimeError(
            f"Human intervention required (abort on timeout): {prompt}"
        )
    else:
        # Default: continue
        if action.store_result_as:
            ctx.set_data(action.store_result_as, "auto_approved")


_ACTION_HANDLERS = {
    ActionType.ACTION_CLICK: _action_click,
    ActionType.ACTION_DOUBLE_CLICK: _action_double_click,
    ActionType.ACTION_MOVE: _action_move,
    ActionType.ACTION_TYPE: _action_type,
    ActionType.ACTION_KEYPRESS: _action_keypress,
    ActionType.ACTION_SCROLL: _action_scroll,
    ActionType.ACTION_DRAG: _action_drag,
    ActionType.ACTION_NAVIGATE: _action_navigate,
    ActionType.WAIT: _action_wait,
    ActionType.INSPECT_TEXT: _action_inspect_text,
    ActionType.INSPECT_SCREENSHOT: _action_inspect_screenshot,
    ActionType.EVALUATE_CONDITION: _action_evaluate_condition,
    ActionType.CONDITIONAL: _action_conditional,
    ActionType.COMPUTE: _action_compute,
    ActionType.REQUEST_HUMAN_INTERVENTION: _action_human_intervention,
}
