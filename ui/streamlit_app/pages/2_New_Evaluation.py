"""New Evaluation: create an application (with document uploads), pick a
scholarship, and kick off the Supervisor workflow (build spec §20 "New
Evaluation page")."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ui.streamlit_app.client import ScholarAIAPIError  # noqa: E402
from ui.streamlit_app.components.styling import inject_base_styles  # noqa: E402
from ui.streamlit_app.services.session import get_client, set_selected_application_id  # noqa: E402

inject_base_styles()
st.title("📝 New Evaluation")
st.caption("Submit a student's documents, then run them through the Supervisor's 10-agent workforce.")

client = get_client()

try:
    scholarships = client.list_scholarships()
except ScholarAIAPIError as exc:
    st.error(str(exc))
    st.stop()

if not scholarships:
    st.warning("No scholarship presets are configured on the backend.")
    st.stop()

scholarship_labels = {f"{item['name']} ({item['code']})": item for item in scholarships}
selected_label = st.selectbox("Scholarship", options=list(scholarship_labels.keys()))
selected = scholarship_labels[selected_label]
st.caption(selected["description"])

uploaded_files = st.file_uploader(
    "Application documents (transcript, financial statement, ID, application form, etc.)",
    type=["pdf", "txt", "docx"],
    accept_multiple_files=True,
)

if st.button("Submit application", type="primary"):
    payloads = []
    for uploaded in uploaded_files or []:
        content_type = uploaded.type or "application/octet-stream"
        payloads.append((uploaded.name, uploaded.getvalue(), content_type))
    try:
        with st.spinner("Submitting application..."):
            created = client.submit_application(selected["code"], payloads)
    except ScholarAIAPIError as exc:
        st.error(str(exc))
    else:
        st.success(f"Application `{created['application_id']}` created with status `{created['status']}`.")
        set_selected_application_id(created["application_id"])

        run_now = st.session_state.pop("run_now_after_submit", True)
        if run_now:
            try:
                started = client.evaluate_application(created["application_id"])
            except ScholarAIAPIError as exc:
                st.error(f"Evaluation could not start: {exc}")
            else:
                st.success(f"Workflow started in the background: `{started.get('run_status', 'queued')}`.")
                st.page_link("pages/3_Agent_Workforce.py", label="→ Watch the live agent execution trace")

st.divider()
st.subheader("Run an existing application")
existing_id = st.text_input("Application ID", placeholder="APP-XXXXXXXX")
col1, col2 = st.columns(2)
if col1.button("Run evaluation"):
    if not existing_id:
        st.warning("Enter an application ID first.")
    else:
        try:
            result = client.evaluate_application(existing_id)
        except ScholarAIAPIError as exc:
            st.error(str(exc))
        else:
            set_selected_application_id(existing_id)
            st.success(f"Background run: `{result.get('run_status', 'queued')}`")
            st.page_link("pages/3_Agent_Workforce.py", label="→ Watch live execution")
if col2.button("Open in Agent Workforce") and existing_id:
    set_selected_application_id(existing_id)
    st.switch_page("pages/3_Agent_Workforce.py")
