"""Aggregate counts for the Streamlit dashboard / ``GET /applications``."""

from __future__ import annotations

from scholarai.application.use_cases.application_store import ApplicationStore
from scholarai.domain.ports.repositories import EpisodeRepository


async def get_dashboard_summary(store: ApplicationStore, repository: EpisodeRepository) -> dict[str, float | int]:
    persisted = await repository.summary_counts()
    in_flight = [s for s in store.all() if s.get("status") == "processing"]
    scores = []
    for state in store.all():
        score = (state.get("evaluation") or {}).get("overall_score")
        if isinstance(score, (int, float)):
            scores.append(float(score))
    average_score = round(sum(scores) / len(scores), 1) if scores else 0.0

    total = max(persisted.get("total", 0), len(store.all()))
    return {
        "total_applications": total,
        "pending_review": persisted.get("pending_review", 0) + len(in_flight),
        "approved": persisted.get("approved", 0),
        "rejected": persisted.get("rejected", 0),
        "review_required": persisted.get("review_required", 0),
        "average_score": average_score,
    }
