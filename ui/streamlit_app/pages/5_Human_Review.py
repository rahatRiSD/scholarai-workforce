"""Human Review: the human-in-the-loop controls (build spec §20 "pause,
resume, approve, retry"). The workflow always halts at the human review
gate — nothing here is auto-approved."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ui.streamlit_app.client import ScholarAIAPIError  # noqa: E402
from ui.streamlit_app.components.styling import (  # noqa: E402
    application_status_badge,
    inject_base_styles,
    page_header,
    recommendation_badge,
)
from ui.streamlit_app.services.session import (  # noqa: E402
    get_client,
    get_selected_application_id,
    set_selected_application_id,
)

inject_base_styles()
page_header(
    "✅",
    "Responsible AI control point",
    "Human Review",
    "Every recommendation pauses here. A qualified reviewer retains final authority over each scholarship decision.",
    ("No auto-approval", "Reviewer accountable", "Decision audit trail"),
)

client = get_client()
application_id = st.text_input("Application ID", value=get_selected_application_id() or "", placeholder="APP-XXXXXXXX")
if not application_id:
    st.info("Enter or select an application ID.")
    st.stop()
set_selected_application_id(application_id)

try:
    app_state = client.get_application(application_id)
except ScholarAIAPIError as exc:
    st.error(str(exc))
    st.stop()

status = app_state.get("status", "received")
st.markdown(f"**Current status:** {application_status_badge(status)}", unsafe_allow_html=True)

evaluation = app_state.get("evaluation")
if evaluation is None:
    st.info("No evaluation to review yet — run the workflow from **New Evaluation** first.")
    st.stop()

st.markdown(
    f"### AI recommendation: {evaluation['overall_score']:.1f}/100 "
    f"{recommendation_badge(evaluation['recommendation'])}",
    unsafe_allow_html=True,
)
st.write(evaluation.get("summary", ""))

if app_state.get("critic_result", {}).get("issues"):
    st.warning("Critic issues on record: " + "; ".join(app_state["critic_result"]["issues"]))

if app_state.get("conflicts"):
    st.error("Unresolved conflicts: " + "; ".join(app_state["conflicts"]))

if app_state.get("final_recommendation"):
    st.success("A human decision has already been recorded for this application:")
    st.json(app_state["final_recommendation"])

st.divider()
st.subheader("Record your decision")

reviewer = st.text_input("Reviewer name", value="reviewer")
notes = st.text_area("Notes (optional)")

action_labels = {
    "approve": "✅ Approve",
    "reject": "❌ Reject",
    "request_review": "🔁 Request additional review (re-run Supervisor)",
    "request_more_information": "📎 Request more information from applicant",
}
action = st.radio("Action", options=list(action_labels.keys()), format_func=lambda a: action_labels[a])

if st.button("Submit decision", type="primary"):
    try:
        with st.spinner("Recording decision..."):
            result = client.submit_human_decision(application_id, action, reviewer, notes)
    except ScholarAIAPIError as exc:
        st.error(str(exc))
    else:
        if action == "request_review":
            st.success("Review request recorded. The Supervisor has started a fresh background run.")
            st.page_link("pages/3_Agent_Workforce.py", label="👁️ Watch the rerun live")
        elif action == "request_more_information":
            st.success("Information request recorded. The application remains at the human review gate.")
        else:
            final = result.get("final_recommendation", {})
            st.success(f"Recorded. Final status: `{final.get('final_status', action)}`")
        if action == "approve":
            st.balloons()
