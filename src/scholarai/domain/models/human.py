"""Human-in-the-loop decisions. The AI never awards a scholarship by itself."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class HumanAction(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_REVIEW = "request_review"
    REQUEST_MORE_INFORMATION = "request_more_information"


class HumanDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    application_id: str
    action: HumanAction
    reviewer: str = "reviewer"
    notes: str = ""
    decided_at: datetime = Field(default_factory=datetime.utcnow)
