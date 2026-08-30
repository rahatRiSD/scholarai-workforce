"""Memory viewer: a student's prior episodes (SQL long-term memory), and
semantic search over past evaluations (build spec §20 "Memory viewer")."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ui.streamlit_app.client import ScholarAIAPIError  # noqa: E402
from ui.streamlit_app.components.styling import application_status_badge, inject_base_styles, page_header  # noqa: E402
from ui.streamlit_app.services.session import get_client  # noqa: E402

inject_base_styles()
page_header(
    "🧠",
    "Persistent institutional intelligence",
    "Memory Explorer",
    "Review structured student history and retrieve semantically similar decisions from long-term memory.",
    ("PostgreSQL episodes", "Vector similarity", "Case precedent"),
)

client = get_client()

tab_history, tab_similar = st.tabs(["Student history", "Find similar cases"])

with tab_history:
    student_id = st.text_input("Student ID", placeholder="STU-00000001")
    if student_id and st.button("Look up history"):
        try:
            history = client.student_history(student_id)
        except ScholarAIAPIError as exc:
            st.error(str(exc))
        else:
            episodes = history.get("episodes", [])
            if not episodes:
                st.info("No prior episodes on record for this student.")
            for episode in episodes:
                status = episode.get("status", "unknown")
                with st.expander(
                    f"{episode.get('application_id')} · {episode.get('scholarship_code')} · "
                    f"score={episode.get('overall_score')}"
                ):
                    st.markdown(application_status_badge(status), unsafe_allow_html=True)
                    st.write(f"Recommendation: {episode.get('recommendation')}")
                    st.json(episode.get("human_decision") or {})

with tab_similar:
    query = st.text_area(
        "Describe the case you want similar precedent for",
        placeholder="e.g. strong CGPA, conflicting self-reported vs transcript data",
    )
    limit = st.slider("Max results", 1, 20, 5)
    if query and st.button("Search similar cases"):
        try:
            results = client.search_similar_cases(query, limit)
        except ScholarAIAPIError as exc:
            st.error(str(exc))
        else:
            matches = results.get("results", [])
            if not matches:
                st.info("No similar cases found in memory yet.")
            for match in matches:
                st.markdown(f"**Score: {match.get('score', 0):.3f}**")
                st.markdown(f"<div class='scholarai-card'>{match.get('summary', match)}</div>", unsafe_allow_html=True)
