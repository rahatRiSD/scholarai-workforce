"""Admin operations on the policy knowledge base: upload + search."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scholarai.domain.ports.vectorstore import Embedder, VectorStore
from scholarai.infrastructure.rag.ingestion import ingest_knowledge_base
from scholarai.infrastructure.rag.retriever import PolicyRetriever


async def upload_policy_document(
    knowledge_base_dir: Path,
    vector_store: VectorStore,
    embedder: Embedder,
    filename: str,
    content: bytes,
) -> int:
    knowledge_base_dir.mkdir(parents=True, exist_ok=True)
    target = knowledge_base_dir / filename
    target.write_bytes(content)
    return await ingest_knowledge_base(knowledge_base_dir, vector_store, embedder)


async def search_knowledge_base(retriever: PolicyRetriever, query: str, limit: int = 5) -> list[dict[str, Any]]:
    chunks = await retriever.retrieve(query, limit=limit)
    return [{"source": c.source, "section": c.section, "text": c.text, "score": c.score} for c in chunks]
