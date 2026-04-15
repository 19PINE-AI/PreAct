"""LLM client wrapping Gemini 3 Flash via google-genai SDK."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

from preact.config import LLMConfig

logger = logging.getLogger(__name__)


class LLMClient:
    """Async wrapper around Gemini 3 Flash for all PreAct LLM calls.

    Tracks token usage for cost analysis across all invocations.
    """

    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig()
        self._client = genai.Client(api_key=self.config.api_key)
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
        """Send a text completion request to Gemini.

        Args:
            messages: List of {"role": "user"|"model", "content": str} dicts.
            system: Optional system instruction.
            response_format: If provided, request JSON output with this schema.

        Returns:
            The model's text response.
        """
        contents = self._build_contents(messages)

        config = types.GenerateContentConfig(
            temperature=self.config.temperature,
            max_output_tokens=self.config.max_output_tokens,
        )
        if system:
            config.system_instruction = system

        if response_format:
            config.response_mime_type = "application/json"
            config.response_schema = response_format

        response = await asyncio.to_thread(
            self._client.models.generate_content,
            model=self.config.model,
            contents=contents,
            config=config,
        )

        self._track_usage(response)
        return response.text or ""

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
    ) -> str:
        """Send a vision request with images to Gemini.

        Args:
            text_prompt: The text portion of the prompt.
            images: List of image bytes (PNG/JPEG).
            system: Optional system instruction.
            response_format: If provided, request JSON output.

        Returns:
            The model's text response.
        """
        parts = []
        for img in images:
            parts.append(
                types.Part.from_bytes(data=img, mime_type="image/png")
            )
        parts.append(types.Part.from_text(text=text_prompt))

        contents = [types.Content(role="user", parts=parts)]

        config = types.GenerateContentConfig(
            temperature=self.config.temperature,
            max_output_tokens=self.config.max_output_tokens,
        )
        if system:
            config.system_instruction = system

        if response_format:
            config.response_mime_type = "application/json"
            config.response_schema = response_format

        response = await asyncio.to_thread(
            self._client.models.generate_content,
            model=self.config.model,
            contents=contents,
            config=config,
        )

        self._track_usage(response)
        return response.text or ""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts.

        Uses the same Gemini model's embedding endpoint.
        """
        result = await asyncio.to_thread(
            self._client.models.embed_content,
            model="gemini-embedding-001",
            contents=texts,
        )
        return [e.values for e in result.embeddings]

    def _build_contents(
        self, messages: list[dict[str, Any]]
    ) -> list[types.Content]:
        """Convert message dicts to Gemini Content objects."""
        contents = []
        for msg in messages:
            role = msg.get("role", "user")
            if role == "assistant":
                role = "model"
            text = msg.get("content", "")
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=text)],
                )
            )
        return contents

    def _track_usage(self, response: Any) -> None:
        """Track token usage from response metadata."""
        self._call_count += 1
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            meta = response.usage_metadata
            input_tokens = getattr(meta, "prompt_token_count", 0) or 0
            output_tokens = getattr(meta, "candidates_token_count", 0) or 0
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
        """Estimated cost in USD (Gemini 3 Flash pricing)."""
        input_cost = self.total_input_tokens * 0.10 / 1_000_000
        output_cost = self.total_output_tokens * 0.40 / 1_000_000
        return input_cost + output_cost
