"""The LangGraph workflow state — the system's short-term (working) memory.

Every specialist agent reads from and writes to this single typed
dictionary; they never call each other directly (build spec §42: "Agents
communicate through shared typed workflow state"). Each node returns only
the keys it changed — LangGraph shallow-merges partial updates — except for
the accumulator lists (``trace``, ``messages``, ``errors``), which nodes
must read, append to, and return in full, since there is no parallel
fan-out in this graph that would need a reducer.
"""

from __future__ import annotations

from typing import Any, TypedDict


class ScholarshipState(TypedDict, total=False):
    # --- Identity / request ---
    application_id: str
    scholarship_code: str
    student: dict[str, Any] | None

    # --- Documents (transient — never persisted verbatim to long-term memory) ---
    documents: list[dict[str, Any]]

    # --- Extracted + derived facts ---
    extracted_data: dict[str, Any] | None
    eligibility: dict[str, Any] | None
    policy_evidence: list[dict[str, Any]]
    conflicts: list[str]

    # --- Planning / routing ---
    plan: list[str]
    requested_plan: list[str]
    current_step: int
    critic_revisions: int
    revise_target: str | None

    # --- Agent outputs ---
    agent_results: dict[str, Any]
    evaluation: dict[str, Any] | None
    critic_result: dict[str, Any] | None
    sop: str | None

    # --- Human-in-the-loop ---
    human_decision: dict[str, Any] | None
    final_recommendation: dict[str, Any] | None

    # --- Bookkeeping ---
    status: str
    errors: list[str]
    trace: list[dict[str, Any]]
    messages: list[dict[str, Any]]


def new_state(application_id: str, scholarship_code: str) -> ScholarshipState:
    return ScholarshipState(
        application_id=application_id,
        scholarship_code=scholarship_code,
        student=None,
        documents=[],
        extracted_data=None,
        eligibility=None,
        policy_evidence=[],
        conflicts=[],
        plan=[],
        requested_plan=[],
        current_step=0,
        critic_revisions=0,
        revise_target=None,
        agent_results={},
        evaluation=None,
        critic_result=None,
        sop=None,
        human_decision=None,
        final_recommendation=None,
        status="received",
        errors=[],
        trace=[],
        messages=[],
    )
