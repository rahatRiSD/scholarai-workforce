"""The workflow trace: what the UI's "live execution trace" and "agent
communication history" panels actually render.

This is deliberately not just log lines — it's typed, structured data
attached to the LangGraph state (``ScholarshipState.trace`` /
``ScholarshipState.messages``) so the Streamlit dashboard can render it live
without scraping stdout, and so tests can assert on it directly.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class TraceStatus(StrEnum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING = "waiting"
    INFO = "info"


class TraceEvent(BaseModel):
    """One line of the workflow timeline — "[document_agent] processing"."""

    actor: str
    event: str
    status: TraceStatus
    detail: str = ""
    duration_ms: float | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentMessage(BaseModel):
    """One agent-to-agent (or Supervisor-to-agent) communication.

    Agents don't call each other directly — they read/write the shared
    ``ScholarshipState`` — but every meaningful handoff is still recorded
    here explicitly so "agent communication" is a real, inspectable channel
    rather than an implicit side effect of shared memory.
    """

    from_agent: str
    to_agent: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


def event(
    actor: str,
    description: str,
    status: TraceStatus,
    detail: str = "",
    duration_ms: float | None = None,
) -> TraceEvent:
    return TraceEvent(actor=actor, event=description, status=status, detail=detail, duration_ms=duration_ms)


def message(from_agent: str, to_agent: str, content: str) -> AgentMessage:
    return AgentMessage(from_agent=from_agent, to_agent=to_agent, content=content)
