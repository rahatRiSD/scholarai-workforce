"""Dashboard: the landing page - fleet-level metrics plus the list of
applications in flight (build spec §20 "Dashboard showing active agents and
workflow")."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ui.streamlit_app.client import ScholarAIAPIError  # noqa: E402
from ui.streamlit_app.components.styling import application_status_badge, inject_base_styles  # noqa: E402
from ui.streamlit_app.services.session import get_client, set_selected_application_id  # noqa: E402

inject_base_styles()
st.title("📊 Dashboard")
st.caption("Fleet-level view of every scholarship application moving through the Supervisor workflow.")

client = get_client()

try:
    summary = client.dashboard_summary()
except ScholarAIAPIError as exc:
    st.error(str(exc))
    st.stop()

cols = st.columns(6)
cols[0].metric("Total applications", summary["total_applications"])
cols[1].metric("Pending review", summary["pending_review"])
cols[2].metric("Approved", summary["approved"])
cols[3].metric("Rejected", summary["rejected"])
cols[4].metric("Review required", summary["review_required"])
cols[5].metric("Average score", summary["average_score"])

st.divider()
st.subheader("Active & recent applications")

try:
    applications = client.list_applications()
except ScholarAIAPIError as exc:
    st.error(str(exc))
    st.stop()

if not applications:
    st.info("No applications yet. Go to **New Evaluation** to submit the first one.")
else:
    rows = []
    for app_state in applications:
        evaluation = app_state.get("evaluation") or {}
        rows.append(
            {
                "Application ID": app_state.get("application_id", ""),
                "Scholarship": app_state.get("scholarship_code", ""),
                "Status": app_state.get("status", "received"),
                "Overall score": evaluation.get("overall_score"),
                "Recommendation": evaluation.get("recommendation"),
                "Critic revisions": app_state.get("critic_revisions", 0),
            }
        )
    df = pd.DataFrame(rows)
    st.dataframe(df, width="stretch", hide_index=True)

    st.markdown("**Jump into an application:**")
    for row in rows:
        application_id = row["Application ID"]
        badge_html = application_status_badge(row["Status"])
        col_a, col_b = st.columns([5, 1])
        col_a.markdown(f"`{application_id}` · {row['Scholarship']} &nbsp; {badge_html}", unsafe_allow_html=True)
        if col_b.button("Open", key=f"open-{application_id}"):
            set_selected_application_id(application_id)
            st.switch_page("pages/3_Agent_Workforce.py")
