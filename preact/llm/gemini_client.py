"""Gemini-backed LLMClient shim for the compile path.

The standard preact.llm.LLMClient is Anthropic-only. For the compile
ablation (PREACT_COMPILE_PROVIDER=gemini), we drop in this thin
adapter that exposes the same .complete(messages=, system=) interface
backed by the Gemini SDK.

Only the methods used by ModelGenerator (compile path) are implemented;
calling other LLMClient methods on this object will fail.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class GeminiCompileClient:
    """Drop-in for LLMClient.complete() backed by Gemini."""

    def __init__(self, model: str = "gemini-3-flash-preview"):
        from google import genai
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get(
            "GOOGLE_API_KEY"
        )
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY (or GOOGLE_API_KEY) must be set for "
                "PREACT_COMPILE_PROVIDER=gemini"
            )
        self._client = genai.Client(api_key=api_key)
        self.model = model
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    async def complete(
        self,
        messages: list[dict[str, Any]],
        system: str | None = None,
        max_tokens: int | None = None,
        temperature: float = 0.0,
    ) -> str:
        # Compose Gemini prompt: system + user message text.
        # Compiler messages are always single-user-text; we don't need
        # role-by-role translation.
        user_text = ""
        for m in messages:
            if m.get("role") == "user":
                content = m.get("content", "")
                if isinstance(content, str):
                    user_text += content
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            user_text += block.get("text", "")
        prompt = (system + "\n\n" + user_text) if system else user_text

        return await asyncio.to_thread(self._sync_complete, prompt, max_tokens, temperature)

    def _sync_complete(self, prompt: str, max_tokens: int | None, temperature: float) -> str:
        from google.genai import types as genai_types
        resp = self._client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens or 8192,
            ),
        )
        usage = getattr(resp, "usage_metadata", None)
        if usage is not None:
            self.total_input_tokens += getattr(usage, "prompt_token_count", 0) or 0
            self.total_output_tokens += getattr(usage, "candidates_token_count", 0) or 0
        return resp.text or ""
