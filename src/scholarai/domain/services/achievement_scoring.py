"""Deterministic achievement scoring.

Each achievement category carries a fixed point value; the LLM (Achievement
Agent) still has to *find and describe* the achievements and cite where each
one is documented, but it does not decide how many points they're worth.
"""

from __future__ import annotations

from dataclasses import dataclass

from scholarai.domain.models.documents import Achievement

_CATEGORY_POINTS: dict[str, float] = {
    "publication": 25.0,
    "award": 20.0,
    "competition": 18.0,
    "leadership": 15.0,
    "certification": 12.0,
    "project": 10.0,
    "volunteering": 8.0,
    "community contribution": 8.0,
    "extracurricular": 6.0,
}
_DEFAULT_POINTS = 5.0
_MAX_SCORE = 100.0


@dataclass(frozen=True)
class AchievementScore:
    score: float
    evaluated: int
    categories: tuple[str, ...]
    unevidenced: tuple[str, ...]


def score_achievements(achievements: tuple[Achievement, ...]) -> AchievementScore:
    if not achievements:
        return AchievementScore(score=0.0, evaluated=0, categories=(), unevidenced=())

    total = 0.0
    categories: list[str] = []
    unevidenced: list[str] = []
    for achievement in achievements:
        points = _CATEGORY_POINTS.get(achievement.category.lower(), _DEFAULT_POINTS)
        if not achievement.evidence_document:
            points *= 0.5
            unevidenced.append(achievement.title)
        total += points
        categories.append(achievement.category)

    score = round(min(total, _MAX_SCORE), 2)
    return AchievementScore(
        score=score,
        evaluated=len(achievements),
        categories=tuple(dict.fromkeys(categories)),
        unevidenced=tuple(unevidenced),
    )
