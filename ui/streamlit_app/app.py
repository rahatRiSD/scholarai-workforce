"""ScholarAI Workforce - Streamlit operations console (build spec §20-21).

Run with: ``streamlit run ui/streamlit_app/app.py``

This is a thin presentation layer only - every number shown here comes from
the FastAPI backend (see ``client.py``); the UI computes nothing about
eligibility, scores, or recommendations itself. Multi-page app using
Streamlit's native `st.navigation` / `pages/` convention.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Allow `from ui.streamlit_app...` imports when launched via `streamlit run`
# from an arbitrary working directory.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ui.streamlit_app.components.styling import inject_base_styles  # noqa: E402
from ui.streamlit_app.services.session import get_client  # noqa: E402

st.set_page_config(
    page_title="ScholarAI Workforce",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)


def render_sidebar_connection_settings() -> None:
    get_client()  # ensures st.session_state["api_base_url"] / ["api_key"] defaults exist
    with st.sidebar:
        st.markdown("### 🎓 ScholarAI Workforce")
        st.caption("Supervisor-orchestrated multi-agent scholarship evaluation")
        with st.expander("Backend connection", expanded=False):
            st.text_input("API base URL", key="api_base_url")
            st.text_input("API key (optional)", key="api_key", type="password")
            client = get_client()
            try:
                health = client.health()
                st.success(f"Connected · provider={health['llm_provider']} · env={health['environment']}")
            except Exception as exc:  # noqa: BLE001 - surfaced to the operator, not swallowed
                st.error(f"Backend unreachable: {exc}")


def main() -> None:
    inject_base_styles()
    render_sidebar_connection_settings()

    pages = {
        "Overview": [
            st.Page("pages/1_Dashboard.py", title="Dashboard", icon="📊"),
        ],
        "Workflow": [
            st.Page("pages/2_New_Evaluation.py", title="New Evaluation", icon="📝"),
            st.Page("pages/3_Agent_Workforce.py", title="Agent Workforce", icon="🤖"),
            st.Page("pages/4_Evaluation_Details.py", title="Evaluation Details", icon="🔍"),
            st.Page("pages/5_Human_Review.py", title="Human Review", icon="✅"),
        ],
        "Knowledge": [
            st.Page("pages/6_Memory.py", title="Memory", icon="🧠"),
            st.Page("pages/7_Knowledge_Base.py", title="Knowledge Base", icon="📚"),
        ],
    }
    navigation = st.navigation(pages)
    navigation.run()


if __name__ == "__main__":
    main()
