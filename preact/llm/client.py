"""LLM client wrapping Claude Sonnet via Anthropic SDK."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from typing import Any

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from preact.config import LLMConfig

logger = logging.getLogger(__name__)


class LLMClient:
    """Async wrapper around Claude Sonnet for all PreAct LLM calls.

    Tracks token usage for cost analysis across all invocations.
    """

    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig()
        self._client = anthropic.AsyncAnthropic(api_key=self.config.api_key)
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self._call_count: int = 0

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def complete(
        self,
        messages: list[dict[str, Any]],
        system: str | None = None,
        response_format: dict | None = None,
    ) -> str:
        """Send a text completion request to Claude.

        Args:
            messages: List of {"role": "user"|"assistant", "content": str} dicts.
            system: Optional system instruction.
            response_format: If provided, hint for JSON output (via prompt).

        Returns:
            The model's text response.
        """
        # Normalize roles: convert "model" to "assistant" for Anthropic
        normalized = []
        for msg in messages:
            role = msg.get("role", "user")
            if role == "model":
                role = "assistant"
            normalized.append({"role": role, "content": msg.get("content", "")})

        # Anthropic requires alternating user/assistant messages
        # Merge consecutive same-role messages
        merged = self._merge_consecutive_messages(normalized)

        # Ensure conversation starts with a user message
        if merged and merged[0]["role"] != "user":
            merged.insert(0, {"role": "user", "content": "Begin."})

        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "max_tokens": self.config.max_output_tokens,
            "messages": merged,
            "temperature": self.config.temperature,
        }
        if system:
            # If response_format is requested, add JSON instruction to system
            if response_format:
                system += "\n\nYou MUST respond with valid JSON only. No markdown, no explanation."
            kwargs["system"] = system
        elif response_format:
            kwargs["system"] = "You MUST respond with valid JSON only. No markdown, no explanation."

        response = await self._client.messages.create(**kwargs)

        self._track_usage(response)
        return self._extract_text(response)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def complete_with_vision(
        self,
        text_prompt: str,
        images: list[bytes],
        system: str | None = None,
        response_format: dict | None = None,
        max_tokens: int | None = None,
        thinking_budget: int | None = None,
    ) -> str:
        """Send a vision request with images to Claude.

        Args:
            text_prompt: The text portion of the prompt.
            images: List of image bytes (PNG/JPEG).
            system: Optional system instruction.
            response_format: If provided, hint for JSON output.
            max_tokens: Override max_output_tokens for this call.
            thinking_budget: If set, enable extended thinking with this
                token budget.  Temperature is forced to 1 as required
                by the API when thinking is enabled.

        Returns:
            The model's text response.
        """
        content: list[dict[str, Any]] = []

        for img in images:
            img_b64 = base64.standard_b64encode(img).decode("utf-8")
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": img_b64,
                },
            })

        content.append({"type": "text", "text": text_prompt})

        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "max_tokens": max_tokens or self.config.max_output_tokens,
            "messages": [{"role": "user", "content": content}],
        }

        if thinking_budget:
            kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": thinking_budget,
            }
            # Temperature must be 1 when thinking is enabled
            kwargs["temperature"] = 1
            # Ensure max_tokens > thinking budget
            if kwargs["max_tokens"] <= thinking_budget:
                kwargs["max_tokens"] = thinking_budget + 4096
        else:
            kwargs["temperature"] = self.config.temperature

        if system:
            if response_format:
                system += "\n\nYou MUST respond with valid JSON only. No markdown, no explanation."
            kwargs["system"] = system
        elif response_format:
            kwargs["system"] = "You MUST respond with valid JSON only. No markdown, no explanation."

        response = await self._client.messages.create(**kwargs)

        self._track_usage(response)
        return self._extract_text(response)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts.

        Uses a lightweight local approach since Anthropic doesn't provide
        an embedding API. Falls back to simple hash-based vectors.
        This is only used as a fallback — the primary matching uses
        text overlap, not embeddings.
        """
        try:
            from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
            ef = DefaultEmbeddingFunction()
            return ef(texts)
        except Exception:
            # Fallback: simple character-frequency vectors (768 dims)
            # This is a last-resort — text matching handles most cases
            embeddings = []
            for text in texts:
                vec = [0.0] * 768
                for i, ch in enumerate(text.lower()):
                    idx = ord(ch) % 768
                    vec[idx] += 1.0 / (1 + i * 0.01)
                # Normalize
                norm = sum(v * v for v in vec) ** 0.5
                if norm > 0:
                    vec = [v / norm for v in vec]
                embeddings.append(vec)
            return embeddings

    def _extract_text(self, response: Any) -> str:
        """Extract text from an Anthropic response."""
        for block in response.content:
            if block.type == "text":
                return block.text
        return ""

    def _merge_consecutive_messages(
        self, messages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Merge consecutive messages with the same role.

        Anthropic API requires strict alternation of user/assistant roles.
        """
        if not messages:
            return []

        merged = [messages[0].copy()]
        for msg in messages[1:]:
            if msg["role"] == merged[-1]["role"]:
                merged[-1]["content"] += "\n\n" + msg["content"]
            else:
                merged.append(msg.copy())
        return merged

    def _track_usage(self, response: Any) -> None:
        """Track token usage from response metadata."""
        self._call_count += 1
        if hasattr(response, "usage") and response.usage:
            input_tokens = getattr(response.usage, "input_tokens", 0) or 0
            output_tokens = getattr(response.usage, "output_tokens", 0) or 0
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            logger.debug(
                "LLM call #%d: %d input, %d output tokens",
                self._call_count,
                input_tokens,
                output_tokens,
            )

    def reset_usage(self) -> None:
        """Reset token counters."""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self._call_count = 0

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    @property
    def cost_estimate(self) -> float:
        """Estimated cost in USD (Claude Sonnet pricing)."""
        input_cost = self.total_input_tokens * 3.00 / 1_000_000
        output_cost = self.total_output_tokens * 15.00 / 1_000_000
        return input_cost + output_cost
