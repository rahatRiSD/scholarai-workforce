"""SQLAlchemy ORM models — the long-term memory schema.

Two tables, deliberately: ``evaluation_episodes`` (one row per completed
workflow run, everything needed to answer "what happened during the
previous evaluation of this application?") and ``human_decisions`` (the
audit trail of every human action). No normalization beyond that — this is
a modular monolith for a course-sized project, not a data warehouse (build
spec §38: "do not overengineer").
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class EvaluationEpisode(Base):
    __tablename__ = "evaluation_episodes"

    application_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    student_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    scholarship_code: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(String(32), nullable=True)

    agent_findings: Mapped[dict] = mapped_column(JSON, default=dict)
    policy_evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    evaluation: Mapped[dict] = mapped_column(JSON, default=dict)
    critic_feedback: Mapped[dict] = mapped_column(JSON, default=dict)
    human_decision: Mapped[dict] = mapped_column(JSON, default=dict)
    timeline: Mapped[list] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class HumanDecisionRecord(Base):
    __tablename__ = "human_decisions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    application_id: Mapped[str] = mapped_column(String(32), index=True)
    action: Mapped[str] = mapped_column(String(32))
    reviewer: Mapped[str] = mapped_column(String(128))
    notes: Mapped[str] = mapped_column(Text, default="")
    decided_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
