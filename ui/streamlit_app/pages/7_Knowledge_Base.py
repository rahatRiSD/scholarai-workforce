"""Knowledge Base admin: upload policy documents into the RAG index and
search it directly (build spec §20 "Knowledge Base admin page")."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ui.streamlit_app.client import ScholarAIAPIError  # noqa: E402
from ui.streamlit_app.components.styling import inject_base_styles, page_header  # noqa: E402
from ui.streamlit_app.services.session import get_client  # noqa: E402

inject_base_styles()
page_header(
    "📚",
    "Grounded policy intelligence",
    "Knowledge Base",
    "Curate the source-of-truth policies used by the RAG agent, then verify retrieval with direct semantic search.",
    ("Qdrant retrieval", "Citable sections", "Policy-only answers"),
)

client = get_client()

tab_upload, tab_search = st.tabs(["Upload policy document", "Search knowledge base"])

with tab_upload:
    uploaded = st.file_uploader(
        "Policy document (Markdown preferred — headings become citable sections)", type=["md", "txt"]
    )
    if uploaded and st.button("Index document"):
        try:
            content_type = uploaded.type or "text/markdown"
            with st.spinner("Chunking and indexing..."):
                result = client.upload_policy_document(uploaded.name, uploaded.getvalue(), content_type)
        except ScholarAIAPIError as exc:
            st.error(str(exc))
        else:
            st.success(f"Indexed `{result['filename']}` — {result['total_chunks_indexed']} chunks added.")

with tab_search:
    query = st.text_input("Query", placeholder="What is the minimum CGPA for the merit scholarship?")
    limit = st.slider("Max results", 1, 20, 5)
    if query and st.button("Search"):
        try:
            results = client.search_knowledge_base(query, limit)
        except ScholarAIAPIError as exc:
            st.error(str(exc))
        else:
            matches = results.get("results", [])
            if not matches:
                st.info("No matching policy chunks found — the Policy Agent would mark evidence UNAVAILABLE here.")
            for match in matches:
                section = match.get("section") or match.get("source", "")
                with st.expander(f"Score {match.get('score', 0):.3f} — {section}"):
                    st.write(match.get("text", ""))
                    st.caption(f"Source: {match.get('source', '')}")
