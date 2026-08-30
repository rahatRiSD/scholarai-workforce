"""Session-scoped helpers shared by every page: the API client and the
"currently selected application" that ties the New Evaluation / Agent
Workforce / Evaluation Details / Human Review pages together."""

from __future__ import annotations

import os

import streamlit as st

from ui.streamlit_app.client import ScholarAIClient


def initialize_connection_state() -> None:
    """Seed widget-backed connection settings before widgets are created."""

    st.session_state.setdefault(
        "api_base_url",
        os.environ.get("SCHOLARAI_API_BASE_URL", "http://localhost:8000"),
    )
    st.session_state.setdefault("api_key", os.environ.get("SCHOLARAI_API_KEY", ""))


def get_client() -> ScholarAIClient:
    """Build a client without mutating state owned by rendered widgets."""

    default_url = os.environ.get("SCHOLARAI_API_BASE_URL", "http://localhost:8000")
    base_url = str(st.session_state.get("api_base_url", default_url)).strip()
    if not base_url:
        base_url = default_url
    elif not base_url.startswith(("http://", "https://")):
        base_url = f"http://{base_url}"
    api_key = str(st.session_state.get("api_key", os.environ.get("SCHOLARAI_API_KEY", "")))
    return ScholarAIClient(base_url=base_url, api_key=api_key)


def get_selected_application_id() -> str | None:
    return st.session_state.get("selected_application_id")


def set_selected_application_id(application_id: str) -> None:
    st.session_state["selected_application_id"] = application_id


def require_selected_application() -> str | None:
    application_id = get_selected_application_id()
    if not application_id:
        st.info("No application selected yet. Submit one on **New Evaluation**, or pick one below.")
    return application_id
