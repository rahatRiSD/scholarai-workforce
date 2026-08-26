"""Qdrant adapter for the ``VectorStore`` port.

Defaults to an in-process, in-memory Qdrant instance
(``QdrantClient(location=":memory:")``) when ``SCHOLARAI_VECTORSTORE__URL``
is unset — a real Qdrant server needs zero setup to try the project on a
laptop, per build spec §3 ("prefer Qdrant but provide a lightweight local
development fallback if practical"). Pointing at ``docker-compose``'s Qdrant
service is a single environment variable.
"""

from __future__ import annotations

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels

from scholarai.domain.ports.vectorstore import RetrievedChunk


class QdrantVectorStore:
    def __init__(self, url: str | None) -> None:
        self._client = AsyncQdrantClient(url=url) if url else AsyncQdrantClient(location=":memory:")
        self._known_collections: set[str] = set()

    async def ensure_collection(self, collection: str, vector_size: int) -> None:
        if collection in self._known_collections:
            return
        exists = await self._client.collection_exists(collection)
        if not exists:
            await self._client.create_collection(
                collection_name=collection,
                vectors_config=qmodels.VectorParams(size=vector_size, distance=qmodels.Distance.COSINE),
            )
        self._known_collections.add(collection)

    async def upsert(
        self,
        collection: str,
        chunk_id: str,
        text: str,
        embedding: list[float],
        metadata: dict[str, str],
    ) -> None:
        await self.ensure_collection(collection, len(embedding))
        point_id = _stable_point_id(chunk_id)
        await self._client.upsert(
            collection_name=collection,
            points=[
                qmodels.PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={"text": text, "chunk_id": chunk_id, **metadata},
                )
            ],
        )

    async def search(self, collection: str, query_embedding: list[float], *, limit: int = 5) -> list[RetrievedChunk]:
        if not await self._client.collection_exists(collection):
            return []
        results = await self._client.query_points(collection_name=collection, query=query_embedding, limit=limit)
        chunks: list[RetrievedChunk] = []
        for point in results.points:
            payload = point.payload or {}
            chunks.append(
                RetrievedChunk(
                    text=payload.get("text", ""),
                    source=payload.get("source", "unknown"),
                    section=payload.get("section"),
                    score=float(point.score),
                    metadata={k: str(v) for k, v in payload.items() if k not in ("text",)},
                )
            )
        return chunks


def _stable_point_id(chunk_id: str) -> int:
    import hashlib

    digest = hashlib.blake2b(chunk_id.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big") % (2**63)


def build_vector_store(url: str | None) -> QdrantVectorStore:
    return QdrantVectorStore(url)
