from __future__ import annotations

from fastapi import APIRouter, Depends

from scholarai.composition import Container
from scholarai.interfaces.api.deps import get_container
from scholarai.interfaces.api.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(container: Container = Depends(get_container)) -> HealthResponse:
    return HealthResponse(llm_provider=container.llm.provider_name, environment=container.settings.environment.value)
