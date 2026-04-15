"""ActionEngine script executor — runs generated Python scripts.

Executes the flat Python scripts generated from crawl graphs.
This demonstrates the limitation: scripts can't be incrementally patched.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


async def execute_script(
    script: str,
    env: Any,
    parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute a generated Python script against the environment.

    Uses the environment's page object directly (Playwright page).

    Returns:
        Dict with success, time_ms, error keys.
    """
    start = time.monotonic()
    parameters = parameters or {}

    # Create execution namespace with the page object
    namespace = {
        "page": env.page,
        "asyncio": asyncio,
        "params": parameters,
    }

    try:
        # Compile and execute the script
        exec(compile(script, "<generated>", "exec"), namespace)

        # Call the execute_task function
        if "execute_task" in namespace:
            result = namespace["execute_task"](env.page, **parameters)
            if asyncio.iscoroutine(result):
                result = await result
            success = bool(result)
        else:
            success = False
            logger.warning("Generated script has no execute_task function")

        return {
            "success": success,
            "time_ms": (time.monotonic() - start) * 1000,
            "error": None,
        }

    except Exception as e:
        logger.error("Script execution failed: %s", e)
        return {
            "success": False,
            "time_ms": (time.monotonic() - start) * 1000,
            "error": str(e),
        }
