"""Embedding-based selector backend for ablation studies.

Vector retrieval baseline against the agentic Program Selector
(see preact.rag.selector). For each incoming task, encodes the task
description with sentence-transformers/all-MiniLM-L6-v2 and returns
the top-1 stored program by cosine similarity, gated by a similarity
threshold to allow no-pick fallback.

This selector is the implementation of the "embedding-based RAG"
counterfactual referenced in the paper's design rationale (\S3.4).
The agentic selector deliberately avoids embedding retrieval because
the discrimination problem is reasoning, not similarity. This module
exists to test that claim empirically.

Selected via PREACT_SELECTOR_MODE=embedding. Default behavior remains
the agentic selector; this is opt-in for ablation runs only.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from preact.schemas import RPAProgram

if TYPE_CHECKING:
    from preact.llm.client import LLMClient
    from preact.rag.store import ProgramStore

logger = logging.getLogger(__name__)

_MODEL = None  # lazily loaded
_TOKENIZER = None


def _get_model():
    """Load all-MiniLM-L6-v2 via transformers directly (sentence-transformers
    pulls in torchcodec which is broken on this system)."""
    global _MODEL, _TOKENIZER
    if _MODEL is None:
        from transformers import AutoTokenizer, AutoModel
        _TOKENIZER = AutoTokenizer.from_pretrained(
            "sentence-transformers/all-MiniLM-L6-v2"
        )
        _MODEL = AutoModel.from_pretrained(
            "sentence-transformers/all-MiniLM-L6-v2"
        )
        _MODEL.eval()
    return _MODEL, _TOKENIZER


def _encode(texts):
    """Mean-pool BERT outputs to get sentence embeddings."""
    import torch
    model, tokenizer = _get_model()
    enc = tokenizer(texts, padding=True, truncation=True, return_tensors="pt")
    with torch.no_grad():
        out = model(**enc)
    # Mean pooling over token dimension, masking out padding.
    mask = enc["attention_mask"].unsqueeze(-1).float()
    summed = (out.last_hidden_state * mask).sum(1)
    counts = mask.sum(1).clamp(min=1e-9)
    return (summed / counts).numpy()


class EmbeddingSelector:
    """Top-1 cosine retrieval over stored task_descriptions.

    Same .select() interface as ProgramSelector. Threshold defaults
    to 0.5 (cosine similarity); below threshold the selector returns
    None ("no candidate"), mirroring the agentic selector's no-match
    fallback.
    """

    def __init__(
        self,
        llm: "LLMClient",
        store: "ProgramStore",
        threshold: float = 0.5,
    ):
        # llm kept for interface compatibility; not used.
        self.llm = llm
        self.store = store
        self.threshold = threshold

    async def select(
        self,
        task: str,
        platform: str,
        application_context: str = "",
        max_iters: int = 3,  # ignored; kept for interface compat
    ) -> RPAProgram | None:
        if self.store.count() == 0:
            return None

        candidates = self.store.list_programs(platform=platform)
        if not candidates:
            logger.info("EmbeddingSelector: no %s programs in store", platform)
            return None

        # Encode incoming task + all candidate descriptions.
        # For a 100-program corpus this is sub-second on CPU.
        descs = [c["task_description"] for c in candidates]
        embs = _encode([task] + descs)

        import numpy as np

        query = embs[0]
        cand = embs[1:]

        # Cosine similarity (embeddings are L2-normalized by the model).
        sims = (cand @ query) / (
            (np.linalg.norm(cand, axis=1) + 1e-9) * (np.linalg.norm(query) + 1e-9)
        )
        best_idx = int(np.argmax(sims))
        best_sim = float(sims[best_idx])
        best_id = candidates[best_idx]["program_id"]

        logger.info(
            "EmbeddingSelector: best=%s sim=%.3f (threshold=%.2f)",
            best_id[:8], best_sim, self.threshold,
        )

        if best_sim < self.threshold:
            return None
        return await self.store.load_program(best_id)
