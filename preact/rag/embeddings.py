"""Embedding generation for RAG-indexed program retrieval.

Uses ChromaDB's default embedding function (all-MiniLM-L6-v2) for
vector representations. Falls back to the LLM client's embed method.
"""

from __future__ import annotations

import hashlib
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from preact.llm.client import LLMClient
    from preact.schemas import RPAProgram

logger = logging.getLogger(__name__)

# Module-level singleton for the embedding function
_default_ef = None


def _get_default_ef():
    """Get or create the default ChromaDB embedding function."""
    global _default_ef
    if _default_ef is None:
        try:
            from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
            _default_ef = DefaultEmbeddingFunction()
        except Exception as e:
            logger.warning("Failed to init default embedding function: %s", e)
    return _default_ef


def program_to_embedding_text(program: RPAProgram) -> str:
    """Convert an RPA program to text suitable for embedding.

    Combines task description, app context, parameters, and state names
    into a single text for vector embedding.
    """
    parts = [
        program.metadata.task_description,
        program.metadata.application_context,
    ]
    if program.metadata.parameters:
        parts.append("Parameters: " + ", ".join(program.metadata.parameters))
    if program.metadata.initial_states:
        parts.append(
            "Initial states: " + ", ".join(program.metadata.initial_states)
        )

    state_names = [s.id.replace("_", " ") for s in program.states[:10]]
    if state_names:
        parts.append("Steps: " + " -> ".join(state_names))

    return " | ".join(parts)


def program_id_hash(program: RPAProgram) -> str:
    """Generate a stable hash for a program based on its content."""
    content = (
        program.metadata.task_description
        + program.metadata.application_context
        + str(sorted(program.metadata.parameters))
    )
    return hashlib.sha256(content.encode()).hexdigest()[:16]


class EmbeddingGenerator:
    """Generates embeddings using ChromaDB's default embedding function.

    Falls back to the LLM client's embed method if the default function
    is unavailable.
    """

    def __init__(self, llm: LLMClient, max_cache_size: int = 500):
        self.llm = llm
        self._cache: dict[str, list[float]] = {}
        self._max_cache_size = max_cache_size
        self._ef = _get_default_ef()

    async def embed_text(self, text: str) -> list[float]:
        """Generate an embedding for a single text."""
        cache_key = hashlib.md5(text.encode()).hexdigest()
        if cache_key in self._cache:
            return self._cache[cache_key]

        embedding = None

        # Primary: use ChromaDB default embedding function (local, fast)
        if self._ef is not None:
            try:
                results = self._ef([text])
                if results:
                    embedding = list(results[0])
            except Exception as e:
                logger.debug("Default embedding failed, using LLM fallback: %s", e)

        # Fallback: use LLM client's embed method
        if embedding is None:
            embeddings = await self.llm.embed([text])
            if embeddings:
                embedding = embeddings[0]

        if embedding:
            if len(self._cache) >= self._max_cache_size:
                oldest = next(iter(self._cache))
                del self._cache[oldest]
            self._cache[cache_key] = embedding
            return embedding
        return []

    async def embed_program(self, program: RPAProgram) -> list[float]:
        """Generate an embedding for an RPA program."""
        text = program_to_embedding_text(program)
        return await self.embed_text(text)

    async def embed_query(self, task: str, context: str = "") -> list[float]:
        """Generate an embedding for a task query."""
        query_text = task
        if context:
            query_text += f" | Context: {context}"
        return await self.embed_text(query_text)
