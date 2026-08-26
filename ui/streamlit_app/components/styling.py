"""Shared look-and-feel: page config, a small CSS injection, and badge/status
color helpers reused across every page so the app reads as one product
instead of five disconnected scripts."""

from __future__ import annotations

import streamlit as st

AGENT_DISPLAY_NAMES: dict[str, str] = {
    "document_agent": "Document Analysis",
    "eligibility_agent": "Eligibility",
    "academic_agent": "Academic Evaluation",
    "financial_agent": "Financial Need",
    "achievement_agent": "Achievement",
    "policy_agent": "Policy / RAG",
    "verification_agent": "Verification",
    "evaluation_agent": "Evaluation",
    "sop_agent": "SOP Writer",
    "critic_agent": "Critic",
}

FULL_AGENT_ORDER = tuple(AGENT_DISPLAY_NAMES.keys())

_STATUS_COLORS = {
    "success": "#1a7f37",
    "failed": "#c62828",
    "skipped": "#8a6d00",
    "pending": "#6e7781",
    "running": "#0969da",
}

_RECOMMENDATION_COLORS = {
    "highly_recommended": "#1a7f37",
    "recommended": "#2e8b57",
    "review_required": "#b08800",
    "not_recommended": "#c62828",
    "ineligible": "#8b0000",
}

_APPLICATION_STATUS_COLORS = {
    "received": "#6e7781",
    "processing": "#0969da",
    "paused": "#7c3aed",
    "cancelling": "#b45309",
    "cancelled": "#6e7781",
    "failed": "#c62828",
    "review_required": "#b08800",
    "approved": "#1a7f37",
    "rejected": "#c62828",
}


def inject_base_styles() -> None:
    st.markdown(
        """
        <style>
        .scholarai-badge {
            display: inline-block; padding: 2px 10px; border-radius: 999px;
            font-size: 0.78rem; font-weight: 600; color: white; margin-right: 6px;
        }
        .scholarai-card {
            border: 1px solid rgba(120,120,120,0.25); border-radius: 10px;
            padding: 14px 16px; margin-bottom: 10px; background: rgba(120,120,120,0.04);
        }
        .scholarai-evidence-quote {
            border-left: 3px solid #0969da; padding-left: 10px; margin: 4px 0;
            font-style: italic; color: rgba(150,150,150,0.95);
        }
        .scholarai-trace-line {
            font-family: monospace; font-size: 0.82rem; padding: 2px 0;
        }
        .scholarai-live-dot {
            display:inline-block; width:9px; height:9px; margin-right:7px;
            border-radius:50%; background:#2563eb; animation:scholarai-pulse 1.25s infinite;
        }
        @keyframes scholarai-pulse {
            0% { opacity:.35; transform:scale(.8); }
            50% { opacity:1; transform:scale(1.15); }
            100% { opacity:.35; transform:scale(.8); }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def badge(text: str, color: str) -> str:
    return f'<span class="scholarai-badge" style="background:{color}">{text}</span>'


def status_badge(status: str) -> str:
    color = _STATUS_COLORS.get(status, "#6e7781")
    return badge(status.replace("_", " ").upper(), color)


def recommendation_badge(recommendation: str) -> str:
    color = _RECOMMENDATION_COLORS.get(recommendation, "#6e7781")
    return badge(recommendation.replace("_", " ").upper(), color)


def application_status_badge(status: str) -> str:
    color = _APPLICATION_STATUS_COLORS.get(status, "#6e7781")
    return badge(status.replace("_", " ").upper(), color)


def agent_display_name(agent_key: str) -> str:
    return AGENT_DISPLAY_NAMES.get(agent_key, agent_key.replace("_", " ").title())
