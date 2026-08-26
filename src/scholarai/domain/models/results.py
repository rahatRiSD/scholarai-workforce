"""Structured outputs returned by every specialist agent.

Every result carries the same explainability envelope (``status``,
``confidence``, ``evidence``, ``issues``) via ``AgentResult``, so the
Supervisor, Critic, and UI can treat any agent's output uniformly even though
each also carries domain-specific fields.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from scholarai.domain.models.explainability import Evidence


class AgentStatus(StrEnum):
    SUCCESS = "success"
    WARNING = "warning"
    FAILED = "failed"


class AgentResult(BaseModel):
    """Base envelope. Specialist results subclass this and add their fields."""

    model_config = ConfigDict(frozen=True)

    agent_name: str
    status: AgentStatus
    findings: tuple[str, ...] = ()
    evidence: tuple[Evidence, ...] = ()
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    issues: tuple[str, ...] = ()


class EligibilityResult(AgentResult):
    eligible: bool
    score: float = Field(ge=0.0, le=100.0)
    requirements_checked: tuple[str, ...] = ()
    failed_requirements: tuple[str, ...] = ()


class AcademicResult(AgentResult):
    cgpa: float | None = None
    normalized_score: float = Field(ge=0.0, le=100.0)
    trend: Literal["improving", "declining", "stable", "unknown"] = "unknown"
    credits_completed: int | None = None
    failed_course_count: int = 0
    consistency: Literal["excellent", "good", "fair", "poor", "unknown"] = "unknown"
    assessment: str = ""


class FinancialResult(AgentResult):
    financial_need_score: float = Field(ge=0.0, le=100.0)
    missing_information: tuple[str, ...] = ()
    needs_human_review: bool = False


class AchievementResult(AgentResult):
    achievement_score: float = Field(ge=0.0, le=100.0)
    achievements_evaluated: int = 0
    categories: tuple[str, ...] = ()


class PolicyResult(AgentResult):
    policy_questions_answered: tuple[str, ...] = ()
    interpretation: str = ""
    citations_found: int = 0


class VerificationResult(AgentResult):
    conflicts: tuple[str, ...] = ()
    unsupported_claims: tuple[str, ...] = ()
    missing_evidence: tuple[str, ...] = ()
    conflict_detected: bool = False
