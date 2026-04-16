"""Global configuration for PreAct."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class LLMConfig:
    """Configuration for LLM clients."""

    model: str = "claude-sonnet-4-6"
    api_key: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", ""))
    temperature: float = 0.0
    max_output_tokens: int = 8192
    timeout_sec: float = 60.0


@dataclass
class ExecutorConfig:
    """Configuration for the RPA Executor."""

    default_state_timeout_ms: int = 5000
    poll_interval_ms: int = 100
    max_consecutive_failures: int = 3
    screenshot_dir: str = "screenshots"


@dataclass
class RecorderConfig:
    """Configuration for the Interaction Recorder."""

    save_screenshots: bool = True
    screenshot_dir: str = "traces"
    log_dom_snapshots: bool = False


@dataclass
class RAGConfig:
    """Configuration for the RAG Database."""

    persist_dir: str = "rag_db"
    collection_name: str = "rpa_programs"
    embedding_model: str = "default"
    top_k: int = 3
    similarity_threshold: float = 0.7


@dataclass
class CUAConfig:
    """Configuration for the Standard CUA Loop."""

    max_steps: int = 30
    screenshot_delay_ms: int = 500
    action_delay_ms: int = 200


@dataclass
class PreActConfig:
    """Top-level configuration."""

    llm: LLMConfig = field(default_factory=LLMConfig)
    executor: ExecutorConfig = field(default_factory=ExecutorConfig)
    recorder: RecorderConfig = field(default_factory=RecorderConfig)
    rag: RAGConfig = field(default_factory=RAGConfig)
    cua: CUAConfig = field(default_factory=CUAConfig)
    data_dir: str = "preact_data"
