"""Post-compile hygiene: force dynamic-looking literals into parameters.

Programs compiled by the LLM sometimes embed task-instance data (random
timestamps, generated filenames, short hex slugs) as literal strings in
action.text. That breaks verification and warm replay when the same task
class is re-initialized with a fresh parameter value.

This pass walks each transition's action and rewrites any match of
timestamp/uuid/slug patterns in `text` to `parameter_name`, registering
the parameter on the program metadata. Purely mechanical — no matching,
no retrieval.
"""

from __future__ import annotations

import logging
import re

from preact.schemas import RPAProgram

logger = logging.getLogger(__name__)

_DYNAMIC_PATTERNS = [
    # ISO dates with separators: 2026-04-19, 2026_04_19, optional time.
    re.compile(r"(?<!\d)\d{4}[-_]\d{2}[-_]\d{2}(?:[_T]\d{2}[-_:]\d{2}(?::\d{2})?)?(?!\d)"),
    # Compact YYYYMMDD with optional _HHMMSS (e.g. 20260419_083930).
    re.compile(r"(?<!\d)\d{8}(?:_\d{6})?(?!\d)"),
    # 10+ digit compact numeric (epoch/timestamp).
    re.compile(r"(?<!\d)\d{10,}(?!\d)"),
    # UUID.
    re.compile(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        re.IGNORECASE,
    ),
    # Short hex slug immediately before a known extension (e.g. "_2c5o.md").
    re.compile(r"_[0-9a-z]{4,}(?=\.(?:md|txt|m4a|mp3|mp4|png|jpg|html))"),
]


def _contains_dynamic(text: str) -> bool:
    return any(p.search(text) for p in _DYNAMIC_PATTERNS)


def _next_param_name(existing: set[str], base: str = "param") -> str:
    i = 1
    while f"{base}_{i}" in existing:
        i += 1
    return f"{base}_{i}"


def sanitize_literals(program: RPAProgram, goal: str) -> RPAProgram:
    """Rewrite dynamic-looking literals in action text fields as parameters.

    Effects program in place *and* returns it. Idempotent: already
    parameterized actions are left alone.
    """
    params = set(program.metadata.parameters)
    rewrites = 0

    for transition in program.transitions:
        action = transition.action
        text = action.text
        if not text or not isinstance(text, str):
            continue
        if not _contains_dynamic(text):
            continue
        # Only rewrite when the dynamic blob also appears in the user's
        # goal — i.e. it's a task parameter, not e.g. a version string
        # hard-coded by the application.
        if not any(p.search(text) and p.search(goal or "") for p in _DYNAMIC_PATTERNS):
            continue

        name = _next_param_name(params, base="dynamic_value")
        params.add(name)
        action.parameter_name = name
        action.text = None
        rewrites += 1
        logger.info(
            "sanitize_literals: rewrote action text '%s' → parameter %s",
            text[:40],
            name,
        )

    if rewrites:
        program.metadata.parameters = list(params)
        logger.info(
            "sanitize_literals: %d literals parameterized (total params: %d)",
            rewrites,
            len(params),
        )
    return program
