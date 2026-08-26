"""The core application lifecycle endpoints (build spec §19)."""

from __future__ import annotations

import json
from typing import Any, cast

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status

from scholarai.application.agents.supervisor import FULL_PLAN
from scholarai.application.orchestration.state import ScholarshipState
from scholarai.application.use_cases.apply_human_decision import apply_human_decision
from scholarai.application.use_cases.get_application import (
    get_application_state,
    list_active_applications,
)
from scholarai.application.use_cases.run_evaluation import start_background_evaluation
from scholarai.application.use_cases.submit_application import create_application
from scholarai.composition import Container, build_workflow_graph
from scholarai.domain.models.human import HumanDecision
from scholarai.infrastructure.llm.usage import usage_ledger
from scholarai.interfaces.api.deps import get_container
from scholarai.interfaces.api.schemas import ApplicationCreateResponse, HumanDecisionRequest, RetryAgentRequest
from scholarai.interfaces.api.security import RequiresAuth

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("", response_model=ApplicationCreateResponse, dependencies=[RequiresAuth])
async def submit_application(
    scholarship_code: str = Form(...),
    files: list[UploadFile] = File(default=[]),
    container: Container = Depends(get_container),
) -> ApplicationCreateResponse:
    allowed = container.settings.allowed_upload_extensions
    max_bytes = container.settings.max_upload_size_mb * 1024 * 1024
    payloads: list[tuple[str, bytes]] = []
    for upload in files:
        filename = upload.filename or "unnamed"
        if not filename.lower().endswith(allowed):
            raise ValueError(f"unsupported file type for {filename!r}; allowed: {allowed}")
        content = await upload.read()
        if len(content) > max_bytes:
            raise ValueError(f"{filename!r} exceeds the {container.settings.max_upload_size_mb}MB upload limit")
        payloads.append((filename, content))

    application = create_application(container.application_store, container.document_reader, scholarship_code, payloads)
    return ApplicationCreateResponse(
        application_id=application.application_id,
        scholarship_code=application.scholarship_code,
        status=application.status.value,
        documents_received=len(payloads),
    )


@router.get("", dependencies=[RequiresAuth])
async def list_applications(container: Container = Depends(get_container)) -> list[dict[str, Any]]:
    return list_active_applications(container.application_store)


@router.get("/{application_id}", dependencies=[RequiresAuth])
async def get_application(application_id: str, container: Container = Depends(get_container)) -> dict[str, Any]:
    return await get_application_state(container.application_store, container.episode_repository, application_id)


@router.post("/{application_id}/evaluate", dependencies=[RequiresAuth], status_code=status.HTTP_202_ACCEPTED)
async def evaluate_application(application_id: str, container: Container = Depends(get_container)) -> dict[str, Any]:
    graph = build_workflow_graph(container)
    try:
        return await start_background_evaluation(
            container.application_store, graph, container.run_manager, application_id
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{application_id}/status", dependencies=[RequiresAuth])
async def get_status(application_id: str, container: Container = Depends(get_container)) -> dict[str, Any]:
    state = await get_application_state(container.application_store, container.episode_repository, application_id)
    return {
        "application_id": application_id,
        "status": state.get("status"),
        "plan": state.get("plan", []),
        "current_step": state.get("current_step", 0),
        "critic_revisions": state.get("critic_revisions", 0),
        "errors": state.get("errors", []),
        **container.run_manager.status(application_id),
    }


def _set_operator_status(container: Container, application_id: str, workflow_status: str) -> None:
    state = container.application_store.get(application_id)
    if state is not None:
        updated = cast(ScholarshipState, dict(state))
        updated["status"] = workflow_status
        container.application_store.save(application_id, updated)


@router.post("/{application_id}/pause", dependencies=[RequiresAuth])
async def pause_application(application_id: str, container: Container = Depends(get_container)) -> dict[str, Any]:
    try:
        snapshot = container.run_manager.pause(application_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _set_operator_status(container, application_id, "paused")
    return snapshot


@router.post("/{application_id}/resume", dependencies=[RequiresAuth])
async def resume_application(application_id: str, container: Container = Depends(get_container)) -> dict[str, Any]:
    try:
        snapshot = container.run_manager.resume(application_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _set_operator_status(container, application_id, "processing")
    return snapshot


@router.post("/{application_id}/cancel", dependencies=[RequiresAuth])
async def cancel_application(application_id: str, container: Container = Depends(get_container)) -> dict[str, Any]:
    try:
        snapshot = container.run_manager.cancel(application_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _set_operator_status(container, application_id, "cancelling")
    return snapshot


@router.post("/{application_id}/retry", dependencies=[RequiresAuth], status_code=status.HTTP_202_ACCEPTED)
async def retry_agent(
    application_id: str, payload: RetryAgentRequest, container: Container = Depends(get_container)
) -> dict[str, Any]:
    if payload.agent_name not in FULL_PLAN:
        raise HTTPException(status_code=422, detail=f"unknown retry agent: {payload.agent_name}")
    downstream = {
        "evaluation_agent": ["sop_agent", "critic_agent"],
        "sop_agent": ["critic_agent"],
        "critic_agent": [],
    }
    suffix = downstream.get(payload.agent_name, ["evaluation_agent", "sop_agent", "critic_agent"])
    requested_plan = [payload.agent_name, *suffix]
    graph = build_workflow_graph(container)
    try:
        return await start_background_evaluation(
            container.application_store,
            graph,
            container.run_manager,
            application_id,
            requested_plan=requested_plan,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{application_id}/agents", dependencies=[RequiresAuth])
async def get_agent_statuses(application_id: str, container: Container = Depends(get_container)) -> dict[str, Any]:
    state = await get_application_state(container.application_store, container.episode_repository, application_id)
    return {
        "agent_results": state.get("agent_results", {}),
        "trace": state.get("trace", []),
        "messages": state.get("messages", []),
        "runtime": container.run_manager.status(application_id),
    }


@router.get("/{application_id}/logs", dependencies=[RequiresAuth])
async def get_execution_logs(application_id: str, container: Container = Depends(get_container)) -> dict[str, Any]:
    state = await get_application_state(container.application_store, container.episode_repository, application_id)
    return {
        "application_id": application_id,
        "runtime": container.run_manager.status(application_id),
        "trace": state.get("trace", []),
        "messages": state.get("messages", []),
        "errors": state.get("errors", []),
    }


@router.get("/{application_id}/usage", dependencies=[RequiresAuth])
async def get_llm_usage(application_id: str, container: Container = Depends(get_container)) -> dict[str, Any]:
    await get_application_state(container.application_store, container.episode_repository, application_id)
    return usage_ledger.summary(application_id)


@router.get("/{application_id}/logs/download", dependencies=[RequiresAuth])
async def download_execution_logs(application_id: str, container: Container = Depends(get_container)) -> Response:
    payload = await get_execution_logs(application_id, container)
    return Response(
        content=json.dumps(payload, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{application_id}-execution-log.json"'},
    )


@router.get("/workflow/topology", dependencies=[RequiresAuth])
async def workflow_topology(container: Container = Depends(get_container)) -> dict[str, Any]:
    compiled = build_workflow_graph(container)
    drawable = compiled.get_graph(xray=True)
    return {"graph": drawable.to_json(), "mermaid": drawable.draw_mermaid()}


@router.get("/{application_id}/evaluation", dependencies=[RequiresAuth])
async def get_evaluation(application_id: str, container: Container = Depends(get_container)) -> dict[str, Any]:
    state = await get_application_state(container.application_store, container.episode_repository, application_id)
    return {
        "evaluation": state.get("evaluation"),
        "critic_result": state.get("critic_result"),
        "final_recommendation": state.get("final_recommendation"),
        "sop": state.get("sop"),
    }


@router.get("/{application_id}/evidence", dependencies=[RequiresAuth])
async def get_evidence(application_id: str, container: Container = Depends(get_container)) -> dict[str, Any]:
    state = await get_application_state(container.application_store, container.episode_repository, application_id)
    evidence: list[dict[str, Any]] = []
    for result in state.get("agent_results", {}).values():
        evidence.extend(result.get("evidence", []))
    evidence.extend(state.get("policy_evidence", []))
    return {"evidence": evidence, "conflicts": state.get("conflicts", [])}


@router.post("/{application_id}/human-decision", dependencies=[RequiresAuth])
async def submit_human_decision(
    application_id: str, payload: HumanDecisionRequest, container: Container = Depends(get_container)
) -> dict[str, Any]:
    decision = HumanDecision(
        application_id=application_id, action=payload.action, reviewer=payload.reviewer, notes=payload.notes
    )
    state = await apply_human_decision(
        container.application_store,
        container.episode_repository,
        container.semantic_memory,
        application_id,
        decision,
    )
    if payload.action.value == "request_review":
        graph = build_workflow_graph(container)
        try:
            runtime = await start_background_evaluation(
                container.application_store,
                graph,
                container.run_manager,
                application_id,
                requested_plan=list(FULL_PLAN),
                reset_supervisor=True,
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {**state, "runtime": runtime}
    return state
