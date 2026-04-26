"""Durable program store.

Stores compiled RPA programs as JSON documents in ChromaDB's K/V layer.
Retrieval is agentic (see preact.rag.selector) — there is no vector
search, no keyword matching, no rule-based scoring here. The store
just persists programs and exposes a flat listing + direct-by-id load.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import chromadb
from chromadb.config import Settings

from preact.config import RAGConfig
from preact.schemas import RPAProgram


_PARAM_PATTERNS = [
    # ISO-like dates with separators: 2026-04-19, 2026_04_19, optionally
    # followed by _HH:MM:SS / _HH-MM-SS / THH:MM:SS.
    (r"(?<!\d)\d{4}[-_]\d{2}[-_]\d{2}(?:[_T]\d{2}[-_:]\d{2}(?::\d{2})?)?(?!\d)", "TIMESTAMP"),
    # Compact YYYYMMDD with optional _HHMMSS (e.g. 20260419_083930).
    (r"(?<!\d)\d{8}(?:_\d{6})?(?!\d)", "TIMESTAMP"),
    # Compact numeric timestamps (10+ digits — epoch ms etc.).
    (r"(?<!\d)\d{10,}(?!\d)", "TIMESTAMP"),
    # UUID-like.
    (
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        "UUID",
    ),
    # Short hex slugs appended right before a known extension (e.g. "_2c5o.md").
    (r"_[0-9a-z]{4,}(?=\.(?:md|txt|m4a|mp3|mp4|png|jpg|html))", "_SLUG"),
]


def _normalize_for_dedup(text: str) -> str:
    """Strip dynamic bits from a task description for dedup signatures.

    Re-runs of the same AndroidWorld/OSWorld task often generate fresh
    timestamps/slugs in the goal string. Two instances of
    "Create folder_20260419_083930" and "Create folder_20260420_100115"
    describe the *same* program, so we collapse those patterns before
    hashing the signature.
    """
    import re

    normalized = text
    for pattern, tag in _PARAM_PATTERNS:
        normalized = re.sub(pattern, f"<{tag}>", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\s+", " ", normalized).strip().lower()
    return normalized

if TYPE_CHECKING:
    from preact.llm.client import LLMClient

logger = logging.getLogger(__name__)


class ProgramStore:
    """Durable key/value store for RPA programs, keyed by program_id.

    Backed by ChromaDB's persistent collection — we use it purely as a
    JSON document store. No embeddings are computed or queried. All
    program selection is done by an LLM agent that reads program
    descriptions via `list_programs` and picks one via `load_program`
    (see preact.rag.selector.ProgramSelector).
    """

    def __init__(self, llm: "LLMClient" | None = None, config: RAGConfig | None = None):
        self.config = config or RAGConfig()
        # Kept for backward compat with existing callers; unused here.
        self._llm = llm

        # RAG_DB_PATH env var lets parallel benchmarks (e.g. Android + OSWorld
        # multi-seed sweeps running concurrently) point to isolated stores.
        import os as _os
        persist_path = Path(
            _os.environ.get("RAG_DB_PATH") or self.config.persist_dir
        )
        persist_path.mkdir(parents=True, exist_ok=True)

        self._client = chromadb.Client(
            Settings(
                persist_directory=str(persist_path),
                anonymized_telemetry=False,
                is_persistent=True,
            )
        )
        self._collection = self._client.get_or_create_collection(
            name=self.config.collection_name,
        )
        logger.info(
            "Program store initialized: %d programs",
            self._collection.count(),
        )

    async def store(self, program: RPAProgram, platform: str = "") -> str:
        """Persist a compiled RPA program with signature-based dedup.

        The program_id is derived from sha1(platform || normalized
        task_description). Re-storing the same task (possibly with a
        fresher timestamp parameter) upserts the same slot — no bloat.

        Args:
            program: The RPA program to store.
            platform: Platform tag ("osworld" | "android" | "web") —
                scopes the selector so Android never sees OSWorld programs.

        Returns:
            program_id (possibly rewritten for dedup).
        """
        import hashlib

        signature = (platform or "unknown") + "||" + _normalize_for_dedup(
            program.metadata.task_description
        )
        stable_id = hashlib.sha1(signature.encode("utf-8")).hexdigest()[:24]

        existing = self._collection.get(
            ids=[stable_id], include=["metadatas"]
        )
        prior_version = 1
        if existing["ids"]:
            try:
                prior_version = int(existing["metadatas"][0].get("version", 1)) + 1
            except Exception:
                prior_version = 1

        # Rewrite metadata's program_id to match the dedup slot so future
        # selector lookups are self-consistent.
        program.metadata.program_id = stable_id
        program.metadata.version = prior_version
        program_json = program.model_dump_json()

        metadata = {
            "task_description": program.metadata.task_description,
            "application_context": program.metadata.application_context,
            "parameters": json.dumps(program.metadata.parameters),
            "version": prior_version,
            "state_count": len(program.states),
            "transition_count": len(program.transitions),
            "platform": platform or "unknown",
            "dedup_signature": signature,
        }

        self._collection.upsert(
            ids=[stable_id],
            embeddings=[[0.0]],
            documents=[program_json],
            metadatas=[metadata],
        )

        logger.info(
            "Stored program: %s (v%d%s)",
            stable_id,
            prior_version,
            " — upsert" if existing["ids"] else "",
        )
        return stable_id

    def list_programs(self, platform: str = "") -> list[dict[str, Any]]:
        """Return lightweight summaries of all stored programs.

        Used by the selector agent to choose a program. The selector sees
        the task description, application context, and counts — it does
        NOT see the full JSON until it calls `load_program(id)`.
        """
        if self._collection.count() == 0:
            return []
        result = self._collection.get(include=["metadatas"])
        summaries: list[dict[str, Any]] = []
        for i, meta in enumerate(result["metadatas"] or []):
            if platform and meta.get("platform", "") not in (platform, ""):
                continue
            summaries.append(
                {
                    "program_id": result["ids"][i],
                    "task_description": meta.get("task_description", ""),
                    "application_context": meta.get("application_context", ""),
                    "platform": meta.get("platform", ""),
                    "version": meta.get("version", 1),
                    "state_count": meta.get("state_count", 0),
                    "transition_count": meta.get("transition_count", 0),
                }
            )
        return summaries

    async def load_program(self, program_id: str) -> RPAProgram | None:
        """Fetch a stored program by id. Called by the selector."""
        try:
            result = self._collection.get(
                ids=[program_id], include=["documents"]
            )
            if result["documents"] and result["documents"][0]:
                return RPAProgram.model_validate_json(result["documents"][0])
        except Exception as e:
            logger.warning("Failed to load program %s: %s", program_id, e)
        return None

    # Backward-compat alias.
    async def get(self, program_id: str) -> RPAProgram | None:
        return await self.load_program(program_id)

    async def update(self, program_id: str, program: RPAProgram) -> None:
        program.metadata.program_id = program_id
        await self.store(program)

    async def delete(self, program_id: str) -> None:
        try:
            self._collection.delete(ids=[program_id])
            logger.info("Deleted program: %s", program_id)
        except Exception as e:
            logger.warning("Failed to delete program %s: %s", program_id, e)

    def count(self) -> int:
        return self._collection.count()
