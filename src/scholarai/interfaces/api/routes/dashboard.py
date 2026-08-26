from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from scholarai.application.use_cases.dashboard_summary import get_dashboard_summary
from scholarai.composition import Container
from scholarai.interfaces.api.deps import get_container
from scholarai.interfaces.api.security import RequiresAuth

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", dependencies=[RequiresAuth])
async def dashboard_summary(container: Container = Depends(get_container)) -> dict[str, Any]:
    return await get_dashboard_summary(container.application_store, container.episode_repository)
