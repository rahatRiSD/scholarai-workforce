"""Agent Workforce: live agent status, execution trace, agent-to-agent
communication history, the workflow graph, and an estimated token/cost
readout (build spec §20 "Live agent execution trace / Agent communication
history / Execution graph / Token usage and API cost estimation")."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ui.streamlit_app.client import ScholarAIAPIError  # noqa: E402
from ui.streamlit_app.components.graph_view import render_workflow_graph  # noqa: E402
from ui.streamlit_app.components.styling import (  # noqa: E402
    agent_display_label,
    application_status_badge,
    inject_base_styles,
    page_header,
    status_badge,
)
from ui.streamlit_app.components.workflow_controls import control_availability  # noqa: E402
from ui.streamlit_app.services.session import (  # noqa: E402
    get_client,
    get_selected_application_id,
    set_selected_application_id,
)

inject_base_styles()
page_header(
    "🤖",
    "Live multi-agent orchestration",
    "Agent Workforce",
    "Observe specialist reasoning, communication, tool activity, token usage, and Supervisor control in real time.",
    ("LangGraph topology", "Live trace", "Pause · Resume · Retry"),
)

client = get_client()

with st.container():
    col1, col2 = st.columns([3, 1])
    application_id = col1.text_input(
        "Application ID", value=get_selected_application_id() or "", placeholder="APP-XXXXXXXX"
    )
    if col2.button("Refresh", width="stretch"):
        st.rerun()

if not application_id:
    st.info("Enter or select an application ID to view its agent workforce.")
    st.stop()

set_selected_application_id(application_id)


@st.fragment(run_every="1s")
def live_workforce() -> None:
    try:
        app_state = client.get_application(application_id)
        agents_payload = client.get_agents(application_id)
        runtime = client.get_status(application_id)
        usage = client.get_usage(application_id)
        logs = client.get_execution_logs(application_id)
        topology_payload = client.get_workflow_topology()
    except ScholarAIAPIError as exc:
        st.error(str(exc))
        return

    status = app_state.get("status", "received")
    run_status = runtime.get("run_status", "idle")
    plan = app_state.get("plan", []) or []
    agent_results = agents_payload.get("agent_results", {}) or {}
    trace = agents_payload.get("trace", []) or []
    messages = agents_payload.get("messages", []) or []

    if run_status in {"queued", "running", "paused", "cancelling"}:
        st.markdown(
            f"<span class='scholarai-live-dot'></span><b>LIVE</b> · "
            f"{run_status.upper()} · {agent_display_label(runtime.get('current_actor', 'supervisor'))}",
            unsafe_allow_html=True,
        )
    st.progress(float(runtime.get("progress", 0.0)), text=f"Workflow progress: {runtime.get('current_step', 0)} steps")
    st.markdown(
        f"**Status:** {application_status_badge(status)} &nbsp;·&nbsp; "
        f"**Critic revisions:** {app_state.get('critic_revisions', 0)} &nbsp;·&nbsp; "
        f"**Plan:** {', '.join(agent_display_label(a) for a in plan) or '—'}",
        unsafe_allow_html=True,
    )

    pause_col, resume_col, cancel_col, retry_col = st.columns(4)
    enabled = control_availability(run_status)
    if pause_col.button("⏸ Pause", disabled=not enabled["pause"], width="stretch"):
        client.pause_application(application_id)
        st.rerun(scope="fragment")
    if resume_col.button("▶ Resume", disabled=not enabled["resume"], width="stretch"):
        client.resume_application(application_id)
        st.rerun(scope="fragment")
    if cancel_col.button("■ Cancel", disabled=not enabled["cancel"], width="stretch"):
        client.cancel_application(application_id)
        st.rerun(scope="fragment")

    failed_agents = [key for key, value in agent_results.items() if value.get("status") == "failed"]
    retry_choices = failed_agents or list(agent_results.keys())
    retry_agent = (
        retry_col.selectbox("Retry agent", retry_choices, format_func=agent_display_label, label_visibility="collapsed")
        if retry_choices
        else None
    )
    if retry_agent and retry_col.button("↻ Retry agent", disabled=not enabled["retry"], width="stretch"):
        client.retry_agent(application_id, retry_agent)
        st.rerun(scope="fragment")

    if logs.get("errors"):
        with st.expander(f"⚠️ {len(logs['errors'])} error(s) recorded", expanded=True):
            for error in logs["errors"]:
                st.error(error)
            st.download_button(
                "Download error report",
                data=json.dumps(logs, indent=2),
                file_name=f"{application_id}-error-report.json",
                mime="application/json",
            )

    tabs = st.tabs(["Agents", "Live trace", "Messages", "LangGraph topology", "Tokens & cost", "Logs"])
    with tabs[0]:
        if not agent_results:
            st.info("No agents have run yet. Trigger an evaluation from **New Evaluation**.")
        for agent_key, result in agent_results.items():
            st.markdown(
                f"**{agent_display_label(agent_key)}** {status_badge(result.get('status', 'success'))}",
                unsafe_allow_html=True,
            )
            st.markdown(f"<div class='scholarai-card'>{result.get('findings', '')}</div>", unsafe_allow_html=True)
            if result.get("issues"):
                st.warning("Issues: " + "; ".join(result["issues"]))
            st.caption(f"Confidence: {result.get('confidence', 0):.0%}")

    with tabs[1]:
        if not trace:
            st.info("No trace events recorded yet.")
        for entry in trace:
            icon = {"completed": "✅", "failed": "❌", "started": "▶️", "waiting": "⏳"}.get(entry.get("status"), "ℹ️")
            line = f"{icon} `{entry.get('timestamp', '')}` **{entry.get('actor')}** — {entry.get('event')}"
            if entry.get("detail"):
                line += f" _({entry['detail']})_"
            if entry.get("duration_ms") is not None:
                line += f" · {entry['duration_ms']:.0f}ms"
            st.markdown(f"<div class='scholarai-trace-line'>{line}</div>", unsafe_allow_html=True)

    with tabs[2]:
        if not messages:
            st.info("No agent-to-agent messages recorded yet.")
        for message in messages:
            st.markdown(f"**{message.get('from_agent')} → {message.get('to_agent')}**")
            st.markdown(f"<div class='scholarai-card'>{message.get('content', '')}</div>", unsafe_allow_html=True)

    with tabs[3]:
        render_workflow_graph(topology_payload.get("graph", {}), agent_results)
        st.caption("This diagram is generated from the currently compiled LangGraph, including conditional routes.")

    with tabs[4]:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Provider calls", usage.get("api_calls", 0))
        c2.metric("Input tokens", usage.get("input_tokens", 0))
        c3.metric("Output tokens", usage.get("output_tokens", 0))
        c4.metric("API cost (USD)", f"${usage.get('cost_usd', 0):.6f}")
        if usage.get("has_estimates"):
            st.info("One or more providers returned estimated rather than billed token counts.")
        if usage.get("events"):
            st.dataframe(usage["events"], width="stretch", hide_index=True)
        else:
            st.caption(
                "Offline mode records zero-token calls. Configure OpenAI, Anthropic, or Ollama for provider usage."
            )

    with tabs[5]:
        st.json(logs)
        st.download_button(
            "Download complete execution log",
            data=json.dumps(logs, indent=2),
            file_name=f"{application_id}-execution-log.json",
            mime="application/json",
        )


live_workforce()
