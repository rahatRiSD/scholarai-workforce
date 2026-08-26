"""Embedding adapters implementing ``domain.ports.vectorstore.Embedder``."""

from __future__ import annotations

from scholarai.domain.ports.vectorstore import Embedder
from scholarai.infrastructure.config.settings import LLMSettings


def build_embedder(llm_settings: LLMSettings) -> Embedder:
    """Uses OpenAI embeddings when an OpenAI key is configured, else the offline hasher."""
    if llm_settings.openai_api_key:
        from scholarai.infrastructure.embeddings.openai_embeddings import OpenAIEmbedder

        return OpenAIEmbedder(llm_settings.openai_api_key.get_secret_value())
    from scholarai.infrastructure.embeddings.hashing import HashingEmbedder

    return HashingEmbedder()
