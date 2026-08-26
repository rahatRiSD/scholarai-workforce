"""SQL-backed long-term memory: implements ``domain.ports.repositories.EpisodeRepository``.

This is what answers "what happened during the previous evaluation of this
application?" and "have similar cases been reviewed before?" (build spec
§15). Semantic (embedding-based) recall across episodes is layered on top by
``EpisodicSemanticMemory`` in ``semantic_memory.py``, which reuses the same
rows rather than duplicating storage.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from scholarai.infrastructure.database.models import EvaluationEpisode, HumanDecisionRecord


class SqlEpisodeRepository:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sessionmaker = sessionmaker

    async def save_episode(self, application_id: str, record: dict[str, Any]) -> None:
        async with self._sessionmaker() as session:
            existing = await session.get(EvaluationEpisode, application_id)
            if existing is None:
                existing = EvaluationEpisode(application_id=application_id)
                session.add(existing)
            existing.student_id = record.get("student_id")
            existing.scholarship_code = record.get("scholarship_code", "")
            existing.status = record.get("status", "unknown")
            existing.overall_score = record.get("overall_score")
            existing.recommendation = record.get("recommendation")
            existing.agent_findings = record.get("agent_findings", {})
            existing.policy_evidence = record.get("policy_evidence", {})
            existing.evaluation = record.get("evaluation", {})
            existing.critic_feedback = record.get("critic_feedback", {})
            existing.human_decision = record.get("human_decision", {})
            existing.timeline = record.get("timeline", [])
            existing.updated_at = datetime.utcnow()
            await session.commit()

    async def get_episode(self, application_id: str) -> dict[str, Any] | None:
        async with self._sessionmaker() as session:
            episode = await session.get(EvaluationEpisode, application_id)
            return _to_dict(episode) if episode else None

    async def list_episodes(self, student_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        async with self._sessionmaker() as session:
            stmt = select(EvaluationEpisode).order_by(EvaluationEpisode.created_at.desc()).limit(limit)
            if student_id:
                stmt = stmt.where(EvaluationEpisode.student_id == student_id)
            result = await session.execute(stmt)
            return [_to_dict(row) for row in result.scalars().all()]

    async def save_human_decision(self, application_id: str, decision: dict[str, Any]) -> None:
        async with self._sessionmaker() as session:
            session.add(
                HumanDecisionRecord(
                    application_id=application_id,
                    action=decision.get("action", "unknown"),
                    reviewer=decision.get("reviewer", "reviewer"),
                    notes=decision.get("notes", ""),
                )
            )
            episode = await session.get(EvaluationEpisode, application_id)
            if episode is not None:
                episode.human_decision = decision
                episode.status = _status_for_action(decision.get("action", ""))
                episode.updated_at = datetime.utcnow()
            await session.commit()

    async def summary_counts(self) -> dict[str, int]:
        async with self._sessionmaker() as session:
            result = await session.execute(select(EvaluationEpisode))
            episodes = result.scalars().all()
        counts = {"total": len(episodes), "pending_review": 0, "approved": 0, "rejected": 0, "review_required": 0}
        for episode in episodes:
            status = episode.status
            if status in counts:
                counts[status] += 1
            elif status == "processing":
                counts["pending_review"] += 1
        return counts


def _status_for_action(action: str) -> str:
    return {
        "approve": "approved",
        "reject": "rejected",
        "request_review": "review_required",
        "request_more_information": "review_required",
    }.get(action, "review_required")


def _to_dict(episode: EvaluationEpisode) -> dict[str, Any]:
    return {
        "application_id": episode.application_id,
        "student_id": episode.student_id,
        "scholarship_code": episode.scholarship_code,
        "status": episode.status,
        "overall_score": episode.overall_score,
        "recommendation": episode.recommendation,
        "agent_findings": episode.agent_findings,
        "policy_evidence": episode.policy_evidence,
        "evaluation": episode.evaluation,
        "critic_feedback": episode.critic_feedback,
        "human_decision": episode.human_decision,
        "timeline": episode.timeline,
        "created_at": episode.created_at.isoformat(),
        "updated_at": episode.updated_at.isoformat(),
    }
