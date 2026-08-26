from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from scholarai.application.use_cases.get_memory import find_similar_cases, get_student_history
from scholarai.composition import Container
from scholarai.interfaces.api.deps import get_container
from scholarai.interfaces.api.schemas import MemorySearchRequest
from scholarai.interfaces.api.security import RequiresAuth

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/{student_id}", dependencies=[RequiresAuth])
async def student_history(student_id: str, container: Container = Depends(get_container)) -> dict[str, Any]:
    episodes = await get_student_history(container.episode_repository, student_id)
    return {"student_id": student_id, "episodes": episodes}


@router.post("/search", dependencies=[RequiresAuth])
async def similar_cases(payload: MemorySearchRequest, container: Container = Depends(get_container)) -> dict[str, Any]:
    results = await find_similar_cases(container.semantic_memory, payload.query, payload.limit)
    return {"query": payload.query, "results": results}
