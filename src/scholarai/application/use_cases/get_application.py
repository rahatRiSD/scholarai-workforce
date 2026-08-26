"""Read-only lookups over in-flight and completed applications."""

from __future__ import annotations

from typing import Any

from scholarai.application.tools.database_tool import get_previous_episode
from scholarai.application.use_cases.application_store import ApplicationStore
from scholarai.domain.errors import ScholarAIError
from scholarai.domain.ports.repositories import EpisodeRepository


async def get_application_state(
    store: ApplicationStore, repository: EpisodeRepository, application_id: str
) -> dict[str, Any]:
    state = store.get(application_id)
    if state is not None:
        return dict(state)
    episode = await get_previous_episode(repository, application_id)
    if episode is None:
        msg = f"application {application_id!r} not found"
        raise ScholarAIError(msg)
    return episode


def list_active_applications(store: ApplicationStore) -> list[dict[str, Any]]:
    return [dict(state) for state in store.all()]
