"""The Policy Agent's retrieval interface: query in, cited chunks out.

Build spec §10: "The Policy Agent must retrieve relevant policy evidence
before making policy-related conclusions... Do not allow the system to claim
a policy exists if it cannot retrieve supporting evidence." An empty result
list is a legitimate, expected outcome here — callers must treat it as "no
evidence," never paper over it with an invented claim.
"""

from __future__ import annotations

from scholarai.domain.ports.vectorstore import Embedder, RetrievedChunk, VectorStore
from scholarai.infrastructure.rag.ingestion import POLICY_COLLECTION


class PolicyRetriever:
    def __init__(self, vector_store: VectorStore, embedder: Embedder) -> None:
        self._vector_store = vector_store
        self._embedder = embedder

    async def retrieve(self, query: str, *, limit: int = 4) -> list[RetrievedChunk]:
        query_embedding = await self._embedder.embed(query)
        return await self._vector_store.search(POLICY_COLLECTION, query_embedding, limit=limit)
