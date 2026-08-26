"""Builds the configured ``LLMClient`` — the single place provider choice is decided.

Agents and use cases never instantiate a provider client directly; they
receive an ``LLMClient`` from ``composition.py``, which calls this factory
once at startup.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from scholarai.domain.ports.llm import LLMClient
from scholarai.infrastructure.config.settings import LLMProvider
from scholarai.infrastructure.llm.offline_client import OfflineLLMClient

if TYPE_CHECKING:
    from scholarai.infrastructure.config.settings import LLMSettings

log = structlog.get_logger()


def build_llm_client(settings: LLMSettings) -> LLMClient:
    provider = settings.effective_provider
    log.info("llm.provider_selected", provider=provider.value)

    if provider is LLMProvider.OPENAI:
        from scholarai.infrastructure.llm.openai_client import OpenAILLMClient

        return OpenAILLMClient(settings)
    if provider is LLMProvider.ANTHROPIC:
        from scholarai.infrastructure.llm.anthropic_client import AnthropicLLMClient

        return AnthropicLLMClient(settings)
    if provider is LLMProvider.OLLAMA:
        from scholarai.infrastructure.llm.ollama_client import OllamaLLMClient

        return OllamaLLMClient(settings)
    return OfflineLLMClient()
