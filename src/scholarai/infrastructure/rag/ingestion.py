"""Loads the policy knowledge base directory into the vector store."""

from __future__ import annotations

from pathlib import Path

from scholarai.domain.ports.vectorstore import Embedder, VectorStore
from scholarai.infrastructure.observability import get_logger
from scholarai.infrastructure.rag.chunking import chunk_document

log = get_logger(__name__)

POLICY_COLLECTION = "scholarai_policy"
_SUPPORTED_SUFFIXES = (".md", ".txt")


async def ingest_knowledge_base(directory: Path, vector_store: VectorStore, embedder: Embedder) -> int:
    """Ingest every ``.md``/``.txt`` file under ``directory``. Returns chunk count."""
    if not directory.exists():
        log.warning("rag.ingestion.missing_directory", directory=str(directory))
        return 0

    total_chunks = 0
    for path in sorted(directory.iterdir()):
        if path.suffix.lower() not in _SUPPORTED_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        chunks = chunk_document(text)
        if not chunks:
            continue
        embeddings = await embedder.embed_many([chunk.text for chunk in chunks])
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            chunk_id = f"{path.name}::{chunk.index}"
            await vector_store.upsert(
                POLICY_COLLECTION,
                chunk_id,
                chunk.text,
                embedding,
                metadata={"source": path.stem.replace("_", " ").title(), "section": chunk.section or ""},
            )
        total_chunks += len(chunks)
        log.info("rag.ingestion.file", file=path.name, chunks=len(chunks))

    log.info("rag.ingestion.complete", directory=str(directory), total_chunks=total_chunks)
    return total_chunks
