"""Tool 5 — Database Tool.

Storing applications, evaluations, and human decisions, and retrieving
previous cases — the traced entry point over ``EpisodeRepository``.
"""

from __future__ import annotations

from typing import Any

from scholarai.domain.ports.repositories import EpisodeRepository
from scholarai.infrastructure.observability import get_logger

log = get_logger(__name__)


async def save_episode(repository: EpisodeRepository, application_id: str, record: dict[str, Any]) -> None:
    await repository.save_episode(application_id, record)
    log.info("tool.database.save_episode", application_id=application_id)


async def get_previous_episode(repository: EpisodeRepository, application_id: str) -> dict[str, Any] | None:
    episode = await repository.get_episode(application_id)
    log.info("tool.database.get_episode", application_id=application_id, found=episode is not None)
    return episode


async def find_similar_episodes(
    repository: EpisodeRepository, student_id: str | None, *, limit: int = 5
) -> list[dict[str, Any]]:
    episodes = await repository.list_episodes(student_id=student_id, limit=limit)
    log.info("tool.database.list_episodes", student_id=student_id, found=len(episodes))
    return episodes


async def save_human_decision(repository: EpisodeRepository, application_id: str, decision: dict[str, Any]) -> None:
    await repository.save_human_decision(application_id, decision)
    log.info("tool.database.save_human_decision", application_id=application_id, action=decision.get("action"))
