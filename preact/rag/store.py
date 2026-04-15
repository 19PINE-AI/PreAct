"""RAG-indexed program store using ChromaDB.

Stores compiled RPA programs with vector embeddings for semantic retrieval.
Programs are indexed by task description, app context, and parameters.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import chromadb
from chromadb.config import Settings

from preact.config import RAGConfig
from preact.rag.embeddings import EmbeddingGenerator, program_to_embedding_text
from preact.schemas import RPAProgram

if TYPE_CHECKING:
    from preact.llm.client import LLMClient

logger = logging.getLogger(__name__)


class ProgramStore:
    """ChromaDB-backed store for RPA programs with semantic retrieval.

    Programs are stored as JSON documents with vector embeddings
    derived from their task descriptions and metadata.
    """

    def __init__(self, llm: LLMClient, config: RAGConfig | None = None):
        self.config = config or RAGConfig()
        self.embedder = EmbeddingGenerator(llm)

        persist_path = Path(self.config.persist_dir)
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
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "Program store initialized: %d programs",
            self._collection.count(),
        )

    async def store(self, program: RPAProgram) -> str:
        """Store a compiled RPA program.

        Args:
            program: The RPA program to store.

        Returns:
            The program_id.
        """
        program_id = program.metadata.program_id
        embedding = await self.embedder.embed_program(program)
        program_json = program.model_dump_json()

        metadata = {
            "task_description": program.metadata.task_description,
            "application_context": program.metadata.application_context,
            "parameters": json.dumps(program.metadata.parameters),
            "version": program.metadata.version,
            "state_count": len(program.states),
            "transition_count": len(program.transitions),
        }

        # Upsert to handle updates
        self._collection.upsert(
            ids=[program_id],
            embeddings=[embedding],
            documents=[program_json],
            metadatas=[metadata],
        )

        logger.info("Stored program: %s", program_id)
        return program_id

    async def query(
        self,
        task: str,
        context: str = "",
        k: int | None = None,
    ) -> list[RPAProgram]:
        """Query for matching programs by task description.

        Uses fast text-matching first (no API call). Falls back to
        semantic embedding search only when text matching fails.

        Args:
            task: The task description to search for.
            context: Optional application context (URL, app name).
            k: Number of results to return.

        Returns:
            List of matching RPAPrograms, sorted by relevance.
        """
        k = k or self.config.top_k

        if self._collection.count() == 0:
            return []

        # Fast path: text-based matching (no API call)
        fast_results = await self._query_by_text(task, context, k)
        if fast_results:
            logger.info("Fast text match found %d programs", len(fast_results))
            return fast_results

        # Slow path: semantic embedding search
        embedding = await self.embedder.embed_query(task, context)

        # Build where filter for app context if provided
        where = None
        if context:
            where = {"application_context": {"$eq": context}}

        try:
            results = self._collection.query(
                query_embeddings=[embedding],
                n_results=min(k, self._collection.count()),
                where=where,
                include=["documents", "distances"],
            )
        except Exception:
            # Retry without where filter if context filter fails
            results = self._collection.query(
                query_embeddings=[embedding],
                n_results=min(k, self._collection.count()),
                include=["documents", "distances"],
            )

        programs = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                distance = results["distances"][0][i] if results["distances"] else 1.0
                similarity = 1 - distance
                if similarity < self.config.similarity_threshold:
                    continue
                try:
                    program = RPAProgram.model_validate_json(doc)
                    programs.append(program)
                except Exception as e:
                    logger.warning("Failed to deserialize program: %s", e)

        logger.info(
            "Query '%s': %d results (from %d candidates)",
            task[:50],
            len(programs),
            self._collection.count(),
        )
        return programs

    async def _query_by_text(
        self,
        task: str,
        context: str,
        k: int,
    ) -> list[RPAProgram]:
        """Fast text-based matching using keyword overlap.

        Avoids the embedding API call by computing word overlap between
        the query task and stored program descriptions.
        """
        result = self._collection.get(include=["metadatas", "documents"])
        if not result["documents"]:
            return []

        task_words = set(task.lower().split())
        scored = []

        for i, meta in enumerate(result["metadatas"] or []):
            desc = meta.get("task_description", "").lower()
            desc_words = set(desc.split())
            if not desc_words:
                continue

            # Weighted overlap: intersection / min(len) — favors shorter descriptions
            # that are fully contained in the query
            overlap = len(task_words & desc_words)
            min_len = min(len(task_words), len(desc_words))
            score = overlap / min_len if min_len > 0 else 0

            # Boost for matching app context
            app_ctx = meta.get("application_context", "")
            if context and context in app_ctx:
                score += 0.1

            if score >= 0.4:  # Minimum threshold
                scored.append((score, i))

        if not scored:
            return []

        scored.sort(reverse=True)
        programs = []
        for score, idx in scored[:k]:
            try:
                doc = result["documents"][idx]
                program = RPAProgram.model_validate_json(doc)
                programs.append(program)
            except Exception as e:
                logger.warning("Failed to deserialize program: %s", e)

        return programs

    async def update(self, program_id: str, program: RPAProgram) -> None:
        """Update an existing program in the store.

        Used after monotonic graph extension to persist the updated program.
        """
        program.metadata.program_id = program_id
        await self.store(program)

    async def delete(self, program_id: str) -> None:
        """Delete a program from the store."""
        try:
            self._collection.delete(ids=[program_id])
            logger.info("Deleted program: %s", program_id)
        except Exception as e:
            logger.warning("Failed to delete program %s: %s", program_id, e)

    async def get(self, program_id: str) -> RPAProgram | None:
        """Retrieve a specific program by ID."""
        try:
            result = self._collection.get(
                ids=[program_id], include=["documents"]
            )
            if result["documents"] and result["documents"][0]:
                return RPAProgram.model_validate_json(result["documents"][0])
        except Exception as e:
            logger.warning("Failed to get program %s: %s", program_id, e)
        return None

    def count(self) -> int:
        """Return the number of stored programs."""
        return self._collection.count()

    async def list_all(self) -> list[dict[str, Any]]:
        """List all stored programs with basic metadata."""
        if self._collection.count() == 0:
            return []
        result = self._collection.get(include=["metadatas"])
        summaries = []
        for i, meta in enumerate(result["metadatas"] or []):
            summaries.append(
                {
                    "program_id": result["ids"][i],
                    "task_description": meta.get("task_description", ""),
                    "application_context": meta.get("application_context", ""),
                    "version": meta.get("version", 1),
                    "state_count": meta.get("state_count", 0),
                }
            )
        return summaries
