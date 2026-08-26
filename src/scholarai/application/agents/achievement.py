"""Achievement Agent (build spec §9).

Every achievement claim must have supporting evidence — achievements without
an ``evidence_document`` are still scored (at half weight, see
``domain.services.achievement_scoring``) but explicitly flagged as
unsupported.
"""

from __future__ import annotations

from typing import Any

from scholarai.application.agents.deps import AgentDeps
from scholarai.application.agents.support import add_message, add_trace, timed
from scholarai.application.orchestration.trace import TraceStatus
from scholarai.domain.errors import AgentExecutionError
from scholarai.domain.models.documents import ExtractedApplicationData
from scholarai.domain.models.explainability import Evidence, EvidenceQuality
from scholarai.domain.models.results import AchievementResult, AgentStatus
from scholarai.domain.services.achievement_scoring import score_achievements
from scholarai.infrastructure.observability import get_logger

AGENT_NAME = "achievement_agent"
log = get_logger(__name__)

_SYSTEM = (
    "You are the Achievement Agent. Given a list of extracurricular achievements and a "
    "deterministically computed score, write one sentence highlighting the strongest "
    "achievement. Do not invent achievements not in the list."
)


async def run(state: dict[str, Any], deps: AgentDeps) -> dict[str, Any]:
    trace = list(state.get("trace", []))
    messages = list(state.get("messages", []))
    add_trace(trace, AGENT_NAME, "evaluating achievements", TraceStatus.STARTED)
    add_message(messages, "supervisor", AGENT_NAME, "evaluate extracurricular achievements")

    data = ExtractedApplicationData.model_validate(state["extracted_data"])

    async with timed() as t:
        outcome = score_achievements(data.achievements)
        summary = (
            f"{outcome.evaluated} achievement(s) evaluated across {len(outcome.categories)} categor"
            f"{'y' if len(outcome.categories) == 1 else 'ies'}; score {outcome.score:.1f}/100."
        )
        if deps.llm.provider_name != "offline" and data.achievements:
            summary = await _narrate(deps, data, outcome)

    evidence = [
        Evidence(
            source=achievement.evidence_document or "self-reported (no document)",
            detail=f"{achievement.category}: {achievement.title}",
            quality=EvidenceQuality.DIRECT if achievement.evidence_document else EvidenceQuality.UNAVAILABLE,
        )
        for achievement in data.achievements
    ]

    result = AchievementResult(
        agent_name=AGENT_NAME,
        status=AgentStatus.SUCCESS,
        findings=(summary,),
        evidence=tuple(evidence),
        confidence=0.85 if data.achievements else 0.5,
        issues=tuple(f"unsupported claim: {title}" for title in outcome.unevidenced),
        achievement_score=outcome.score,
        achievements_evaluated=outcome.evaluated,
        categories=outcome.categories,
    )

    add_trace(
        trace,
        AGENT_NAME,
        "evaluating achievements",
        TraceStatus.COMPLETED,
        detail=f"score={outcome.score}",
        duration_ms=t["ms"],
    )
    add_message(messages, AGENT_NAME, "supervisor", summary)

    agent_results = dict(state.get("agent_results", {}))
    agent_results[AGENT_NAME] = result.model_dump(mode="json")
    return {"agent_results": agent_results, "trace": trace, "messages": messages}


async def _narrate(deps: AgentDeps, data: ExtractedApplicationData, outcome: Any) -> str:
    context = {
        "achievements": [a.model_dump() for a in data.achievements],
        "score": outcome.score,
    }
    try:
        return await deps.llm.complete(_SYSTEM, f"CONTEXT:\n{context}")
    except AgentExecutionError as exc:
        log.warning("agent.achievement.narration_failed", error=str(exc))
        return f"{outcome.evaluated} achievement(s) evaluated; score {outcome.score:.1f}/100."
