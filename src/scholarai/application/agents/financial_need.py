"""Financial Need Agent (build spec §8).

If financial information is missing, this agent must not invent it — it
reports ``UNKNOWN / NEEDS HUMAN REVIEW`` and flags the application for
human review, verbatim per the build spec.
"""

from __future__ import annotations

from typing import Any

from scholarai.application.agents.deps import AgentDeps
from scholarai.application.agents.support import add_message, add_trace, timed
from scholarai.application.orchestration.trace import TraceStatus
from scholarai.domain.errors import AgentExecutionError
from scholarai.domain.models.documents import ExtractedApplicationData
from scholarai.domain.models.explainability import Evidence, EvidenceQuality
from scholarai.domain.models.results import AgentStatus, FinancialResult
from scholarai.domain.services.financial_need import score_financial_need
from scholarai.infrastructure.observability import get_logger

AGENT_NAME = "financial_agent"
log = get_logger(__name__)

_SYSTEM = (
    "You are the Financial Need Agent. You are given a deterministically computed financial "
    "need score and the underlying (already redacted where sensitive) inputs. Write one "
    "sentence summarizing the household's financial situation relative to tuition. Never state "
    "a number that was not given to you."
)

UNKNOWN_LABEL = "UNKNOWN / NEEDS HUMAN REVIEW"


async def run(state: dict[str, Any], deps: AgentDeps) -> dict[str, Any]:
    trace = list(state.get("trace", []))
    messages = list(state.get("messages", []))
    add_trace(trace, AGENT_NAME, "assessing financial need", TraceStatus.STARTED)
    add_message(messages, "supervisor", AGENT_NAME, "assess financial need")

    data = ExtractedApplicationData.model_validate(state["extracted_data"])

    async with timed() as t:
        outcome = score_financial_need(data)

        if outcome.score is None:
            findings = (UNKNOWN_LABEL,)
            issues = tuple(f"missing: {field}" for field in outcome.missing_fields)
            evidence = (
                Evidence(
                    source="Financial Need Engine",
                    detail=UNKNOWN_LABEL,
                    quality=EvidenceQuality.UNAVAILABLE,
                ),
            )
            result = FinancialResult(
                agent_name=AGENT_NAME,
                status=AgentStatus.WARNING,
                findings=findings,
                evidence=evidence,
                confidence=0.0,
                issues=issues,
                financial_need_score=0.0,
                missing_information=outcome.missing_fields,
                needs_human_review=True,
            )
        else:
            ratio = outcome.affordability_ratio
            summary = f"Financial need score {outcome.score:.1f}/100 (tuition/income ratio {ratio:.2f})."
            if deps.llm.provider_name != "offline":
                summary = await _narrate(deps, outcome)
            result = FinancialResult(
                agent_name=AGENT_NAME,
                status=AgentStatus.SUCCESS,
                findings=(summary,),
                evidence=(
                    Evidence(
                        source="Financial Need Engine",
                        detail=f"score {outcome.score:.1f}/100",
                        quality=EvidenceQuality.INFERRED,
                    ),
                ),
                confidence=0.85,
                financial_need_score=outcome.score,
                missing_information=(),
                needs_human_review=False,
            )

    add_trace(
        trace,
        AGENT_NAME,
        "assessing financial need",
        TraceStatus.COMPLETED,
        detail=f"score={result.financial_need_score}",
        duration_ms=t["ms"],
    )
    add_message(messages, AGENT_NAME, "supervisor", result.findings[0] if result.findings else "no result")

    agent_results = dict(state.get("agent_results", {}))
    agent_results[AGENT_NAME] = result.model_dump(mode="json")
    return {"agent_results": agent_results, "trace": trace, "messages": messages}


async def _narrate(deps: AgentDeps, outcome: Any) -> str:
    context = {"financial_need_score": outcome.score, "affordability_ratio": outcome.affordability_ratio}
    try:
        return await deps.llm.complete(_SYSTEM, f"CONTEXT:\n{context}")
    except AgentExecutionError as exc:
        log.warning("agent.financial.narration_failed", error=str(exc))
        return f"Financial need score {outcome.score:.1f}/100."
