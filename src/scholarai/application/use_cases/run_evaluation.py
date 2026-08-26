"""Run the Supervisor workflow for an application through to the human-review gate."""

from __future__ import annotations

import asyncio
from typing import Any, cast

from scholarai.application.agents.support import add_trace
from scholarai.application.orchestration.runtime import RunControl, WorkflowRunManager
from scholarai.application.orchestration.state import ScholarshipState
from scholarai.application.orchestration.trace import TraceStatus
from scholarai.application.use_cases.application_store import ApplicationStore
from scholarai.domain.errors import ScholarAIError
from scholarai.infrastructure.observability import get_logger

log = get_logger(__name__)


async def run_evaluation(store: ApplicationStore, graph: Any, application_id: str) -> dict[str, Any]:
    """``graph`` is the compiled LangGraph workflow (``CompiledStateGraph``) from
    ``application.orchestration.graph.build_graph`` — typed ``Any`` here to avoid
    depending on LangGraph's internal class path, which has moved between
    versions; only ``.ainvoke`` is used.
    """
    stored_state = store.get(application_id)
    if stored_state is None:
        msg = f"application {application_id!r} not found"
        raise ScholarAIError(msg)

    log.info("use_case.run_evaluation.start", application_id=application_id)
    final_state = await graph.ainvoke(stored_state)
    store.save(application_id, final_state)
    log.info(
        "use_case.run_evaluation.complete",
        application_id=application_id,
        status=final_state.get("status"),
        overall_score=(final_state.get("evaluation") or {}).get("overall_score"),
    )
    return final_state


async def start_background_evaluation(
    store: ApplicationStore,
    graph: Any,
    manager: WorkflowRunManager,
    application_id: str,
    *,
    requested_plan: list[str] | None = None,
    reset_supervisor: bool = False,
) -> dict[str, Any]:
    """Start a controllable LangGraph stream and return immediately."""
    stored_state = store.get(application_id)
    if stored_state is None:
        msg = f"application {application_id!r} not found"
        raise ScholarAIError(msg)

    state: ScholarshipState = cast(ScholarshipState, dict(stored_state))
    if requested_plan is not None:
        state["requested_plan"] = requested_plan
        state["current_step"] = 0
    if reset_supervisor:
        state["critic_revisions"] = 0
        state["critic_result"] = None
        state["final_recommendation"] = None
        state["errors"] = []
    state["status"] = "queued"
    store.save(application_id, state)

    async def runner(control: RunControl) -> dict[str, Any]:
        latest: ScholarshipState = cast(ScholarshipState, dict(state))
        try:
            async for snapshot in graph.astream(state, stream_mode="values"):
                latest = cast(ScholarshipState, dict(snapshot))
                control.current_step = int(latest.get("current_step", 0))
                control.total_steps = max(len(latest.get("plan", [])), 1)
                trace = latest.get("trace", []) or []
                if trace:
                    control.current_actor = str(trace[-1].get("actor", control.current_actor))
                store.save(application_id, latest)
                await control.checkpoint()
        except asyncio.CancelledError:
            cancelled = cast(ScholarshipState, dict(store.get(application_id) or latest))
            cancelled["status"] = "cancelled"
            trace = list(cancelled.get("trace", []))
            add_trace(trace, "supervisor", "workflow cancelled by human operator", TraceStatus.INFO)
            cancelled["trace"] = trace
            store.save(application_id, cancelled)
            raise
        except Exception as exc:
            failed = cast(ScholarshipState, dict(store.get(application_id) or latest))
            failed["status"] = "failed"
            errors = list(failed.get("errors", []))
            errors.append(f"workflow failed: {exc}")
            failed["errors"] = errors
            store.save(application_id, failed)
            raise

        store.save(application_id, latest)
        return dict(latest)

    return await manager.start(application_id, runner)
