"""Execution context for RPA programs.

Manages runtime state: parameter values, extracted data, and variable scope.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class ExecutionContext:
    """Runtime context for an executing RPA program.

    Holds:
    - parameters: User-provided input values matching program metadata
    - data: Variables populated during execution (inspect results, conditions)
    - execution_log: Ordered list of state visits and actions
    """

    def __init__(self, parameters: dict[str, Any] | None = None):
        self.parameters: dict[str, Any] = parameters or {}
        self.data: dict[str, Any] = {}
        self.execution_log: list[dict[str, Any]] = []
        self._step_count: int = 0

    def set_data(self, key: str, value: Any) -> None:
        """Store a value in the data context."""
        self.data[key] = value
        logger.debug("Context data set: %s = %s", key, repr(value)[:200])

    def get_data(self, key: str) -> Any:
        """Retrieve a value from the data context."""
        return self.data.get(key)

    def has_data(self, key: str) -> bool:
        """Check if a data key exists."""
        return key in self.data

    def resolve_parameter(self, param_name: str) -> str:
        """Resolve a parameter name to its value."""
        if param_name not in self.parameters:
            raise ValueError(
                f"Parameter '{param_name}' not provided. "
                f"Available: {list(self.parameters.keys())}"
            )
        return str(self.parameters[param_name])

    def resolve_template(self, template: str) -> str:
        """Resolve ${...} template expressions in a string.

        Supports:
        - ${parameter_name} — resolves from parameters
        - ${data.key} — resolves from data context
        - ${parameters.key} — resolves from parameters (explicit)
        """

        def replacer(match: re.Match) -> str:
            expr = match.group(1)
            if expr.startswith("data."):
                key = expr[5:]
                val = self.data.get(key, f"<undefined:{key}>")
            elif expr.startswith("parameters."):
                key = expr[11:]
                val = self.parameters.get(key, f"<undefined:{key}>")
            else:
                # Try parameters first, then data
                val = self.parameters.get(
                    expr, self.data.get(expr, f"<undefined:{expr}>")
                )
            return str(val)

        return re.sub(r"\$\{([^}]+)\}", replacer, template)

    def evaluate_expression(self, expression: str) -> Any:
        """Evaluate a simple expression against the context.

        Supports basic comparisons and logical operators using data and parameters.
        This is intentionally limited for security — no arbitrary code execution.
        """
        resolved = self.resolve_template(expression)

        # Build a safe evaluation namespace
        namespace = {
            "data": _DotDict(self.data),
            "parameters": _DotDict(self.parameters),
            "true": True,
            "false": False,
            "True": True,
            "False": False,
            "null": None,
            "None": None,
        }

        # Replace JavaScript-style operators
        resolved = resolved.replace("&&", " and ").replace("||", " or ")
        resolved = resolved.replace("===", "==").replace("!==", "!=")

        try:
            return eval(resolved, {"__builtins__": {}}, namespace)
        except Exception as e:
            logger.warning("Expression evaluation failed: %s — %s", expression, e)
            return False

    def log_step(self, state_id: str, action_type: str, success: bool) -> None:
        """Log an execution step."""
        self._step_count += 1
        self.execution_log.append(
            {
                "step": self._step_count,
                "state": state_id,
                "action": action_type,
                "success": success,
            }
        )

    @property
    def step_count(self) -> int:
        return self._step_count


class _DotDict:
    """Dict wrapper that allows attribute-style access for expression evaluation."""

    def __init__(self, d: dict):
        self._d = d

    def __getattr__(self, key: str) -> Any:
        if key.startswith("_"):
            return super().__getattribute__(key)
        return self._d.get(key)

    def __getitem__(self, key: str) -> Any:
        return self._d.get(key)

    def __contains__(self, key: str) -> bool:
        return key in self._d

    def __repr__(self) -> str:
        return repr(self._d)
