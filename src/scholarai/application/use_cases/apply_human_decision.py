"""Apply a human reviewer's decision and finalize the application.

This is the workflow's "resume" — see the design note in
``application.orchestration.graph`` for why it's a plain function rather
than a second LangGraph invocation. It is the ONLY place a
``final_recommendation`` is ever set, and it is the only place a completed
episode is written to long-term memory — the AI never reaches this point
on its own (build spec §14).
"""

from __future__ import annotations

from typing import Any

from scholarai.application.tools.database_tool import save_episode, save_human_decision
from scholarai.application.use_cases.application_store import ApplicationStore
from scholarai.domain.errors import ScholarAIError
from scholarai.domain.models.human import HumanDecision
from scholarai.domain.ports.repositories import EpisodeRepository
from scholarai.infrastructure.memory.semantic_memory import EpisodicSemanticMemory
from scholarai.infrastructure.observability import get_logger

log = get_logger(__name__)

_FINAL_STATUS = {
    "approve": "approved",
    "reject": "rejected",
    "request_review": "review_required",
    "request_more_information": "review_required",
}


async def apply_human_decision(
    store: ApplicationStore,
    repository: EpisodeRepository,
    semantic_memory: EpisodicSemanticMemory | None,
    application_id: str,
    decision: HumanDecision,
) -> dict[str, Any]:
    state = store.get(application_id)
    if state is None:
        msg = f"application {application_id!r} not found"
        raise ScholarAIError(msg)

    decision_dict = decision.model_dump(mode="json")
    final_status = _FINAL_STATUS.get(decision.action.value, "review_required")

    evaluation = state.get("evaluation") or {}
    is_final = decision.action.value in {"approve", "reject"}
    final_recommendation = (
        {**evaluation, "final_status": final_status, "human_decision": decision_dict} if is_final else None
    )

    state = {
        **state,
        "human_decision": decision_dict,
        "final_recommendation": final_recommendation,
        "status": final_status,
    }
    store.save(application_id, state)

    extracted = state.get("extracted_data") or {}
    record = {
        "student_id": extracted.get("student_id"),
        "scholarship_code": state["scholarship_code"],
        "status": final_status,
        "overall_score": evaluation.get("overall_score"),
        "recommendation": evaluation.get("recommendation"),
        "agent_findings": state.get("agent_results", {}),
        "policy_evidence": state.get("policy_evidence", []),
        "evaluation": evaluation,
        "critic_feedback": state.get("critic_result", {}),
        "human_decision": decision_dict,
        "timeline": state.get("trace", []),
    }
    await save_episode(repository, application_id, record)
    await save_human_decision(repository, application_id, decision_dict)

    if semantic_memory is not None and is_final:
        await semantic_memory.index_episode(application_id, record)

    log.info(
        "use_case.apply_human_decision",
        application_id=application_id,
        action=decision.action.value,
        final_status=final_status,
    )
    return dict(state)
