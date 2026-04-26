"""Agentic program selector — no RAG, no rules.

The selector calls Claude with two tools (`list_programs`, `finalize_selection`)
and lets the model decide autonomously whether any stored program matches
the incoming task. There is no vector search, no keyword overlap, no
threshold. The final decision is forced through a dedicated tool so the
parser never has to scrape JSON out of freeform text.

Why this design beats keyword/embedding matching:
- The compiled task descriptions are natural language; a capable model
  disambiguates "record audio" vs "record audio with filename X" by
  reading both, not by lexical overlap.
- Short-circuits (empty store / empty platform) skip the LLM call
  entirely so cold runs don't pay selector cost.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from preact.schemas import RPAProgram

if TYPE_CHECKING:
    from preact.llm.client import LLMClient
    from preact.rag.store import ProgramStore

logger = logging.getLogger(__name__)


_SELECTOR_SYSTEM = """You are the Program Selector for the PreAct system. Given an incoming task, decide whether any stored RPA program can solve it AS-IS.

Tools:
1. list_programs(platform) — returns available programs with their original task descriptions, application context, state counts, and short action summaries.
2. finalize_selection(program_id, reasoning) — commit your decision. program_id is the chosen id, or the literal string "none" if no stored program matches.

Decision rules:
- Match ONLY when the incoming task has the SAME GOAL and SAME PARAMETERIZATION as a stored program.
  Good match:  "Take one photo"                               ↔ stored "Take a photo".
  Bad match:   "Record audio saved as X.m4a"                  ↔ stored "Record an audio clip"  (new filename parameter)
  Bad match:   "Create a new note named X with text Y"        ↔ stored "Create a new folder named Z"  (different verb)
  Bad match:   "Open task.html and draw a line"               ↔ stored "Open task.html and solve the maze"  (different goal)
- Prefer no-match over wrong-match — the caller falls back to CUA, which is safe.
- Always end by calling finalize_selection. Do not answer in prose."""


class ProgramSelector:
    """LLM-driven selector that replaces vector/keyword RAG matching."""

    def __init__(self, llm: "LLMClient", store: "ProgramStore"):
        self.llm = llm
        self.store = store

    def _tool_schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "list_programs",
                "description": (
                    "List all stored RPA programs available for the given platform. "
                    "Returns [{program_id, task_description, application_context, "
                    "parameters, state_count, transition_count, action_summary}]. "
                    "action_summary is a natural-language outline of what the program "
                    "does, which you should read to judge match quality."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "platform": {
                            "type": "string",
                            "description": "Platform scope: 'osworld' | 'android' | 'web'",
                        }
                    },
                    "required": ["platform"],
                },
            },
            {
                "name": "finalize_selection",
                "description": (
                    "Commit your decision. Pass program_id of the chosen program, or "
                    "the literal string 'none' if no stored program matches."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "program_id": {
                            "type": "string",
                            "description": "program_id of the chosen program, or 'none'",
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "one-sentence rationale (logged for debugging)",
                        },
                    },
                    "required": ["program_id"],
                },
            },
        ]

    def _build_action_summary(self, program_id: str, summaries: list[dict[str, Any]]) -> str:
        """Caller's side: enrich summary with per-transition action descriptions
        so the selector doesn't need to call load_program."""
        # Empty stub — real enrichment happens in _run_tool when we actually
        # fetch the full program. We keep this here as a placeholder for
        # future tuning (e.g. truncation policies).
        return ""

    async def _run_tool(
        self, name: str, tool_input: dict[str, Any], platform: str
    ) -> str:
        if name == "list_programs":
            p = tool_input.get("platform") or platform
            summaries = self.store.list_programs(platform=p)
            # Enrich each summary with a one-line action outline so the
            # selector has enough context without a second tool hop.
            enriched: list[dict[str, Any]] = []
            for s in summaries:
                program = await self.store.load_program(s["program_id"])
                action_summary = ""
                if program:
                    parts = [
                        (t.action.description or t.action.type.value)
                        for t in program.transitions
                    ]
                    action_summary = " → ".join(parts[:8])
                    if len(program.transitions) > 8:
                        action_summary += f" → … ({len(program.transitions)} total)"
                enriched.append({
                    "program_id": s["program_id"],
                    "task_description": s["task_description"],
                    "application_context": s.get("application_context", ""),
                    "parameters": list(program.metadata.parameters) if program else [],
                    "state_count": s.get("state_count", 0),
                    "transition_count": s.get("transition_count", 0),
                    "action_summary": action_summary,
                })
            return json.dumps(enriched, ensure_ascii=False)

        if name == "finalize_selection":
            return json.dumps({"ok": True})

        return json.dumps({"error": f"unknown tool {name}"})

    async def select(
        self,
        task: str,
        platform: str,
        application_context: str = "",
        max_iters: int = 3,
    ) -> RPAProgram | None:
        """Ask the model to pick a matching program, or None."""
        # Short-circuits: no LLM call when the store has nothing relevant.
        if self.store.count() == 0:
            return None
        if not self.store.list_programs(platform=platform):
            logger.info("Selector: no %s programs in store — skipping", platform)
            return None

        user_prompt = (
            f"Incoming task: {task}\n"
            f"Platform: {platform}\n"
            f"Application context: {application_context or 'unknown'}\n\n"
            "Decide which stored program (if any) matches this task. "
            "Call list_programs first, then finalize_selection."
        )

        messages: list[dict[str, Any]] = [
            {"role": "user", "content": user_prompt}
        ]
        tools = self._tool_schemas()

        chosen_id: str | None = None

        for iteration in range(max_iters):
            # On the final iteration, force a tool call so we never fall
            # through to freeform text.
            tool_choice: dict[str, Any] | None = None
            if iteration == max_iters - 1:
                tool_choice = {"type": "tool", "name": "finalize_selection"}

            resp = await self.llm.complete_with_tools(
                messages=messages,
                tools=tools,
                system=_SELECTOR_SYSTEM,
                tool_choice=tool_choice,
            )
            messages.append({"role": "assistant", "content": resp["assistant_blocks"]})

            if not resp["tool_uses"]:
                logger.info("Selector produced no tool call — treating as no-match")
                return None

            tool_results: list[dict[str, Any]] = []
            for tu in resp["tool_uses"]:
                if tu["name"] == "finalize_selection":
                    chosen_id = (tu["input"] or {}).get("program_id", "none")
                    reasoning = (tu["input"] or {}).get("reasoning", "")
                    logger.info(
                        "Selector finalized: %s — %s",
                        (chosen_id[:8] if chosen_id and chosen_id != "none" else "none"),
                        reasoning[:120],
                    )
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tu["id"],
                        "content": json.dumps({"ok": True}),
                    })
                else:
                    serialized = await self._run_tool(
                        tu["name"], tu["input"] or {}, platform
                    )
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tu["id"],
                        "content": serialized,
                    })

            if chosen_id is not None:
                break

            messages.append({"role": "user", "content": tool_results})

        if not chosen_id or chosen_id.lower() == "none":
            return None
        return await self.store.load_program(chosen_id)
