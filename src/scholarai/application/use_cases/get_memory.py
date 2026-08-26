"""Answer "what happened before?" questions over long-term memory."""

from __future__ import annotations

from typing import Any

from scholarai.application.tools.database_tool import find_similar_episodes
from scholarai.domain.ports.repositories import EpisodeRepository
from scholarai.infrastructure.memory.semantic_memory import EpisodicSemanticMemory


async def get_student_history(repository: EpisodeRepository, student_id: str) -> list[dict[str, Any]]:
    return await find_similar_episodes(repository, student_id)


async def find_similar_cases(
    semantic_memory: EpisodicSemanticMemory, query: str, limit: int = 5
) -> list[dict[str, Any]]:
    results = await semantic_memory.find_similar(query, limit=limit)
    return [
        {"application_id": chunk.source, "summary": chunk.text, "score": chunk.score, "metadata": chunk.metadata}
        for chunk in results
    ]
