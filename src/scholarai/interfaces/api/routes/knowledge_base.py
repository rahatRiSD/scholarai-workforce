from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile

from scholarai.application.use_cases.knowledge_base import search_knowledge_base, upload_policy_document
from scholarai.composition import Container
from scholarai.interfaces.api.deps import get_container
from scholarai.interfaces.api.schemas import KnowledgeSearchRequest
from scholarai.interfaces.api.security import RequiresAuth

router = APIRouter(prefix="/knowledge-base", tags=["knowledge-base"])


@router.post("/upload", dependencies=[RequiresAuth])
async def upload_policy(file: UploadFile = File(...), container: Container = Depends(get_container)) -> dict[str, Any]:
    filename = file.filename or "policy.md"
    content = await file.read()
    total_chunks = await upload_policy_document(
        container.settings.knowledge_base_dir, container.vector_store, container.embedder, filename, content
    )
    return {"filename": filename, "total_chunks_indexed": total_chunks}


@router.post("/search", dependencies=[RequiresAuth])
async def search_policy(
    payload: KnowledgeSearchRequest, container: Container = Depends(get_container)
) -> dict[str, Any]:
    results = await search_knowledge_base(container.retriever, payload.query, payload.limit)
    return {"query": payload.query, "results": results}
