"""Tool 2 — RAG Search over the university policy knowledge base.

Thin wrapper over ``infrastructure.rag`` so the Policy Agent (and anything
else that needs a policy citation) goes through one traced entry point.
"""

from __future__ import annotations

from scholarai.domain.ports.vectorstore import RetrievedChunk
from scholarai.infrastructure.observability import get_logger
from scholarai.infrastructure.rag.retriever import PolicyRetriever

log = get_logger(__name__)


async def search_policy(
    retriever: PolicyRetriever, query: str, *, application_id: str, limit: int = 4
) -> list[RetrievedChunk]:
    results = await retriever.retrieve(query, limit=limit)
    log.info(
        "tool.rag_search",
        application_id=application_id,
        query=query,
        results=len(results),
        sources=[chunk.source for chunk in results],
    )
    return results
