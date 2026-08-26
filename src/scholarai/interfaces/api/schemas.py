"""HTTP request/response contracts. Kept separate from domain models so the
wire format can evolve independently of the domain (build spec §19)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from scholarai.domain.models.human import HumanAction


class ApplicationCreateResponse(BaseModel):
    application_id: str
    scholarship_code: str
    status: str
    documents_received: int


class HumanDecisionRequest(BaseModel):
    action: HumanAction
    reviewer: str = "reviewer"
    notes: str = ""


class RetryAgentRequest(BaseModel):
    agent_name: str = Field(min_length=1)


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)


class MemorySearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)


class HealthResponse(BaseModel):
    status: str = "ok"
    llm_provider: str
    environment: str


class ScholarshipPresetResponse(BaseModel):
    code: str
    name: str
    description: str
