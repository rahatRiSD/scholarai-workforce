"""Shared dependencies every agent node receives — assembled once in ``composition.py``.

Keeping this as one small container (rather than each agent importing
infrastructure directly) is what makes agents testable with fakes and keeps
``application`` free of concrete infrastructure imports.
"""

from __future__ import annotations

from dataclasses import dataclass

from scholarai.domain.ports.documents import DocumentReader
from scholarai.domain.ports.llm import LLMClient
from scholarai.domain.ports.web_search import WebSearchClient
from scholarai.infrastructure.rag.retriever import PolicyRetriever


@dataclass
class AgentDeps:
    llm: LLMClient
    retriever: PolicyRetriever
    document_reader: DocumentReader
    web_search: WebSearchClient | None
