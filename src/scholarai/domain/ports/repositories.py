"""Persistence ports: applications, evaluation episodes, human decisions."""

from __future__ import annotations

from typing import Any, Protocol


class EpisodeRepository(Protocol):
    """Long-term structured memory: one row per completed evaluation episode."""

    async def save_episode(self, application_id: str, record: dict[str, Any]) -> None: ...

    async def get_episode(self, application_id: str) -> dict[str, Any] | None: ...

    async def list_episodes(self, student_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]: ...

    async def save_human_decision(self, application_id: str, decision: dict[str, Any]) -> None: ...

    async def summary_counts(self) -> dict[str, int]: ...
