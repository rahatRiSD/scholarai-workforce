"""Port for the RAG vector store used by the Policy Agent and episodic memory."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RetrievedChunk:
    text: str
    source: str
    section: str | None
    score: float
    metadata: dict[str, str]


class VectorStore(Protocol):
    """A named-collection vector store: upsert chunks, search by embedding."""

    async def upsert(
        self,
        collection: str,
        chunk_id: str,
        text: str,
        embedding: list[float],
        metadata: dict[str, str],
    ) -> None: ...

    async def search(
        self,
        collection: str,
        query_embedding: list[float],
        *,
        limit: int = 5,
    ) -> list[RetrievedChunk]: ...

    async def ensure_collection(self, collection: str, vector_size: int) -> None: ...


class Embedder(Protocol):
    """Turns text into a fixed-size embedding vector."""

    dimensions: int

    async def embed(self, text: str) -> list[float]: ...

    async def embed_many(self, texts: list[str]) -> list[list[float]]: ...
