from __future__ import annotations

from fastapi import APIRouter

from scholarai.domain.scholarship_presets import PRESETS
from scholarai.interfaces.api.schemas import ScholarshipPresetResponse

router = APIRouter(prefix="/scholarships", tags=["scholarships"])


@router.get("", response_model=list[ScholarshipPresetResponse])
async def list_scholarships() -> list[ScholarshipPresetResponse]:
    return [
        ScholarshipPresetResponse(code=preset.code, name=preset.name, description=preset.description)
        for preset in PRESETS.values()
    ]
