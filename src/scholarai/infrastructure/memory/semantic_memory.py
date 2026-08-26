"""Semantic recall over past evaluation episodes ("have similar cases been reviewed before?").

Layered on top of the SQL episode store: every saved episode is also
embedded (a short, non-sensitive summary — never the raw documents) and
upserted into its own Qdrant collection, so free-text queries like "strong
academic case with financial hardship" can surface comparable prior
applications by meaning, not just by student ID.
"""

from __future__ import annotations

from scholarai.domain.ports.vectorstore import Embedder, RetrievedChunk, VectorStore

EPISODE_COLLECTION = "scholarai_episodes"


def _summarize(record: dict) -> str:
    """A short, PII-minimal text used only for semantic indexing — never the raw docs."""
    evaluation = record.get("evaluation", {}) or {}
    return (
        f"scholarship={record.get('scholarship_code')} "
        f"status={record.get('status')} "
        f"overall_score={evaluation.get('overall_score')} "
        f"recommendation={evaluation.get('recommendation')} "
        f"review_reasons={', '.join(evaluation.get('review_reasons', []))}"
    )


class EpisodicSemanticMemory:
    def __init__(self, vector_store: VectorStore, embedder: Embedder) -> None:
        self._vector_store = vector_store
        self._embedder = embedder

    async def index_episode(self, application_id: str, record: dict) -> None:
        summary = _summarize(record)
        embedding = await self._embedder.embed(summary)
        await self._vector_store.upsert(
            EPISODE_COLLECTION,
            application_id,
            summary,
            embedding,
            metadata={
                "source": application_id,
                "student_id": record.get("student_id") or "",
                "scholarship_code": record.get("scholarship_code", ""),
            },
        )

    async def find_similar(self, query: str, *, limit: int = 5) -> list[RetrievedChunk]:
        embedding = await self._embedder.embed(query)
        return await self._vector_store.search(EPISODE_COLLECTION, embedding, limit=limit)
