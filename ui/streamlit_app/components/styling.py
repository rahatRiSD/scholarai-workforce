"""Shared visual system for the ScholarAI operations console."""

from __future__ import annotations

from html import escape

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

AGENT_ICONS: dict[str, str] = {
    "document_agent": "📑",
    "eligibility_agent": "🛡️",
    "academic_agent": "🎓",
    "financial_agent": "💳",
    "achievement_agent": "🏆",
    "policy_agent": "📚",
    "verification_agent": "🔎",
    "evaluation_agent": "📊",
    "sop_agent": "✍️",
    "critic_agent": "⚖️",
}

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
        :root {
            --sai-ink: #15213c;
            --sai-muted: #62708a;
            --sai-indigo: #4f46e5;
            --sai-violet: #7c3aed;
            --sai-cyan: #0891b2;
            --sai-surface: rgba(255, 255, 255, 0.84);
            --sai-border: rgba(99, 102, 241, 0.16);
            --sai-shadow: 0 16px 45px rgba(62, 55, 135, 0.10);
        }

        html { scroll-behavior: smooth; }

        .stApp {
            color: var(--sai-ink);
            background:
                radial-gradient(circle at 8% 8%, rgba(99, 102, 241, .13), transparent 27rem),
                radial-gradient(circle at 92% 18%, rgba(6, 182, 212, .10), transparent 25rem),
                radial-gradient(circle at 52% 92%, rgba(168, 85, 247, .08), transparent 30rem),
                linear-gradient(145deg, #fbfcff 0%, #f6f7ff 52%, #f9fcff 100%);
            background-attachment: fixed;
        }

        .stApp::before {
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            opacity: .34;
            background-image:
                linear-gradient(rgba(79,70,229,.045) 1px, transparent 1px),
                linear-gradient(90deg, rgba(79,70,229,.045) 1px, transparent 1px);
            background-size: 42px 42px;
            mask-image: linear-gradient(to bottom, black, transparent 80%);
            animation: scholarai-grid-drift 26s linear infinite;
        }

        [data-testid="stHeader"] { background: transparent; }
        [data-testid="stMainBlockContainer"] {
            max-width: 1320px;
            padding-top: 2.1rem;
            padding-bottom: 4rem;
            animation: scholarai-page-in .48s ease-out both;
        }

        [data-testid="stSidebar"] {
            border-right: 1px solid rgba(99,102,241,.12);
            background:
                radial-gradient(circle at 20% 0%, rgba(99,102,241,.13), transparent 18rem),
                rgba(250, 251, 255, .94);
            backdrop-filter: blur(18px);
        }
        [data-testid="stSidebar"] [data-testid="stSidebarContent"] { padding-top: 1.1rem; }
        [data-testid="stSidebarNav"] a {
            border-radius: 12px;
            margin: 2px 8px;
            transition: transform .18s ease, background .18s ease, box-shadow .18s ease;
        }
        [data-testid="stSidebarNav"] a:hover {
            background: rgba(79,70,229,.08);
            box-shadow: 0 6px 18px rgba(79,70,229,.08);
            transform: translateX(3px);
        }
        [data-testid="stSidebarNav"] a[aria-current="page"] {
            color: #fff;
            background: linear-gradient(110deg, var(--sai-indigo), var(--sai-violet));
            box-shadow: 0 10px 24px rgba(79,70,229,.24);
        }

        .scholarai-brand {
            position: relative;
            overflow: hidden;
            padding: 17px 16px;
            margin: 2px 0 15px;
            border: 1px solid rgba(99,102,241,.16);
            border-radius: 18px;
            color: #fff;
            background: linear-gradient(135deg, #172554 0%, #4338ca 60%, #7c3aed 100%);
            box-shadow: 0 14px 34px rgba(49,46,129,.22);
        }
        .scholarai-brand::after {
            content: "";
            position: absolute;
            width: 110px;
            height: 110px;
            right: -35px;
            top: -52px;
            border: 1px solid rgba(255,255,255,.24);
            border-radius: 50%;
            box-shadow: 0 0 0 18px rgba(255,255,255,.05), 0 0 0 36px rgba(255,255,255,.03);
            animation: scholarai-orbit 8s ease-in-out infinite;
        }
        .scholarai-brand-row { display:flex; align-items:center; gap:11px; }
        .scholarai-brand-mark {
            display:grid; place-items:center; width:42px; height:42px;
            border-radius:13px; font-size:1.32rem; background:rgba(255,255,255,.15);
            border:1px solid rgba(255,255,255,.24);
        }
        .scholarai-brand-name { font-size:1.05rem; font-weight:800; letter-spacing:-.02em; }
        .scholarai-brand-copy { margin-top:3px; font-size:.72rem; color:rgba(255,255,255,.76); }

        .scholarai-page-hero {
            position: relative;
            overflow: hidden;
            padding: 25px 28px 24px;
            margin: 0 0 1.45rem;
            border-radius: 24px;
            border: 1px solid rgba(99,102,241,.16);
            color: #fff;
            background:
                radial-gradient(circle at 85% 5%, rgba(34,211,238,.32), transparent 15rem),
                linear-gradient(120deg, #172554 0%, #3730a3 55%, #6d28d9 100%);
            box-shadow: 0 22px 55px rgba(49,46,129,.22);
        }
        .scholarai-page-hero::before,
        .scholarai-page-hero::after {
            content:""; position:absolute; border-radius:50%; pointer-events:none;
            border:1px solid rgba(255,255,255,.18);
        }
        .scholarai-page-hero::before {
            width:220px; height:220px; right:-75px; bottom:-125px;
            box-shadow: 0 0 0 25px rgba(255,255,255,.035), 0 0 0 50px rgba(255,255,255,.025);
            animation: scholarai-float 7s ease-in-out infinite;
        }
        .scholarai-page-hero::after {
            width:9px; height:9px; right:24%; top:24%; background:#67e8f9;
            border:none; box-shadow: 44px 35px 0 -2px #c4b5fd, 87px -6px 0 -3px #fff;
            animation: scholarai-twinkle 2.8s ease-in-out infinite;
        }
        .scholarai-hero-content { position:relative; z-index:1; max-width:920px; }
        .scholarai-eyebrow {
            display:inline-flex; align-items:center; gap:7px; margin-bottom:9px;
            color:#a5f3fc; font-size:.72rem; font-weight:800; letter-spacing:.13em; text-transform:uppercase;
        }
        .scholarai-eyebrow::before {
            content:""; width:20px; height:2px; border-radius:2px; background:#67e8f9;
        }
        .scholarai-page-title {
            display:flex; align-items:center; gap:13px; margin:0;
            color:#fff; font-size:clamp(1.65rem, 3vw, 2.35rem); line-height:1.08;
            font-weight:850; letter-spacing:-.035em;
        }
        .scholarai-page-icon {
            display:inline-grid; place-items:center; flex:0 0 auto;
            width:50px; height:50px; border-radius:15px; font-size:1.55rem;
            background:rgba(255,255,255,.13); border:1px solid rgba(255,255,255,.22);
            box-shadow: inset 0 1px 0 rgba(255,255,255,.18);
        }
        .scholarai-page-subtitle {
            max-width:820px; margin:10px 0 0; color:rgba(255,255,255,.78);
            font-size:.96rem; line-height:1.55;
        }
        .scholarai-hero-chips { display:flex; flex-wrap:wrap; gap:8px; margin-top:16px; }
        .scholarai-chip {
            padding:5px 10px; border-radius:999px; font-size:.72rem; font-weight:700;
            color:#eef2ff; background:rgba(255,255,255,.10); border:1px solid rgba(255,255,255,.16);
        }

        [data-testid="stMetric"] {
            min-height: 112px;
            padding: 17px 18px;
            border: 1px solid var(--sai-border);
            border-radius: 18px;
            background: var(--sai-surface);
            box-shadow: var(--sai-shadow);
            backdrop-filter: blur(12px);
            transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease;
        }
        [data-testid="stMetric"]:hover {
            transform: translateY(-4px);
            border-color: rgba(79,70,229,.32);
            box-shadow: 0 19px 42px rgba(62,55,135,.15);
        }
        [data-testid="stMetricLabel"] { color:var(--sai-muted); font-weight:650; }
        [data-testid="stMetricValue"] { color:var(--sai-ink); font-weight:800; letter-spacing:-.03em; }

        [data-testid="stVerticalBlockBorderWrapper"] {
            border-color: var(--sai-border) !important;
            border-radius: 18px !important;
        }
        [data-testid="stExpander"], [data-testid="stFileUploaderDropzone"] {
            border:1px solid var(--sai-border);
            border-radius:16px;
            background:rgba(255,255,255,.74);
            box-shadow:0 8px 26px rgba(62,55,135,.06);
        }
        [data-testid="stFileUploaderDropzone"] {
            background:linear-gradient(135deg, rgba(238,242,255,.86), rgba(236,254,255,.78));
        }
        [data-testid="stAlert"] { border-radius:14px; box-shadow:0 8px 24px rgba(30,41,59,.06); }
        [data-testid="stDataFrame"] { border-radius:16px; overflow:hidden; box-shadow:var(--sai-shadow); }

        .stButton > button, .stDownloadButton > button, [data-testid="stPageLink-NavLink"] {
            border-radius: 12px !important;
            border: 1px solid rgba(79,70,229,.22) !important;
            font-weight: 750 !important;
            transition: transform .16s ease, box-shadow .16s ease, border-color .16s ease !important;
        }
        .stButton > button:hover, .stDownloadButton > button:hover, [data-testid="stPageLink-NavLink"]:hover {
            transform: translateY(-2px);
            border-color: rgba(79,70,229,.50) !important;
            box-shadow: 0 9px 22px rgba(79,70,229,.16) !important;
        }
        .stButton > button[kind="primary"] {
            color:#fff !important; border:none !important;
            background:linear-gradient(110deg, var(--sai-indigo), var(--sai-violet)) !important;
            box-shadow:0 10px 24px rgba(79,70,229,.25) !important;
        }
        .stButton > button[kind="primary"]:hover { box-shadow:0 13px 30px rgba(79,70,229,.34) !important; }
        .stTextInput input, .stTextArea textarea, [data-baseweb="select"] > div {
            border-color:rgba(99,102,241,.19) !important;
            border-radius:12px !important;
            background:rgba(255,255,255,.88) !important;
        }
        .stTextInput input:focus, .stTextArea textarea:focus {
            border-color:var(--sai-indigo) !important;
            box-shadow:0 0 0 3px rgba(79,70,229,.10) !important;
        }
        [data-baseweb="tab-list"] {
            gap:5px; padding:5px; border-radius:14px; background:rgba(238,242,255,.75);
        }
        [data-baseweb="tab"] { border-radius:10px; font-weight:700; }
        [aria-selected="true"][data-baseweb="tab"] { background:#fff; box-shadow:0 5px 14px rgba(79,70,229,.10); }

        .scholarai-badge {
            display: inline-block; padding: 3px 10px; border-radius: 999px;
            font-size: 0.72rem; font-weight: 800; letter-spacing:.035em;
            color: white; margin-right: 6px; box-shadow:0 5px 12px rgba(30,41,59,.13);
        }
        .scholarai-card {
            border: 1px solid var(--sai-border); border-radius: 16px;
            padding: 16px 18px; margin-bottom: 11px; background: var(--sai-surface);
            box-shadow:0 10px 30px rgba(62,55,135,.07); line-height:1.58;
        }
        .scholarai-evidence-quote {
            border-left: 3px solid var(--sai-indigo); padding:10px 13px; margin: 8px 0;
            border-radius:0 10px 10px 0; font-style: italic; color:var(--sai-muted);
            background:rgba(238,242,255,.72);
        }
        .scholarai-trace-line {
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.80rem;
            padding: 8px 10px; margin:4px 0; border-left:2px solid rgba(99,102,241,.32);
            border-radius:0 9px 9px 0; background:rgba(248,250,252,.82);
        }
        .scholarai-live-dot {
            display:inline-block; width:9px; height:9px; margin-right:7px;
            border-radius:50%; background:#22c55e; box-shadow:0 0 0 4px rgba(34,197,94,.13);
            animation:scholarai-pulse 1.25s infinite;
        }
        .scholarai-empty {
            display:flex; align-items:center; gap:14px; padding:19px 20px; border-radius:17px;
            color:var(--sai-muted); background:rgba(255,255,255,.70); border:1px dashed rgba(99,102,241,.27);
        }
        .scholarai-empty-icon { font-size:1.6rem; }
        .scholarai-footer {
            margin-top:3rem; padding:18px 4px 4px; border-top:1px solid rgba(99,102,241,.12);
            display:flex; justify-content:space-between; gap:12px; flex-wrap:wrap;
            color:var(--sai-muted); font-size:.76rem;
        }
        .scholarai-footer strong { color:var(--sai-indigo); }

        @keyframes scholarai-page-in {
            from { opacity:0; transform:translateY(8px); }
            to { opacity:1; transform:translateY(0); }
        }
        @keyframes scholarai-grid-drift {
            from { background-position:0 0, 0 0; }
            to { background-position:42px 42px, 42px 42px; }
        }
        @keyframes scholarai-float {
            0%,100% { transform:translate3d(0,0,0); }
            50% { transform:translate3d(-12px,-9px,0); }
        }
        @keyframes scholarai-orbit {
            0%,100% { transform:translateY(0) rotate(0); }
            50% { transform:translateY(9px) rotate(8deg); }
        }
        @keyframes scholarai-twinkle {
            0%,100% { opacity:.45; transform:scale(.8); }
            50% { opacity:1; transform:scale(1.15); }
        }
        @keyframes scholarai-pulse {
            0% { opacity:.35; transform:scale(.8); }
            50% { opacity:1; transform:scale(1.15); }
            100% { opacity:.35; transform:scale(.8); }
        }

        @media (max-width: 760px) {
            [data-testid="stMainBlockContainer"] { padding-top:1rem; }
            .scholarai-page-hero { padding:21px 19px; border-radius:19px; }
            .scholarai-page-icon { width:43px; height:43px; font-size:1.3rem; }
            .scholarai-page-title { font-size:1.55rem; }
            .scholarai-page-subtitle { font-size:.88rem; }
        }
        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                scroll-behavior:auto !important;
                animation:none !important;
                transition:none !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_brand() -> None:
    st.markdown(
        """
        <div class="scholarai-brand">
          <div class="scholarai-brand-row">
            <div class="scholarai-brand-mark">🎓</div>
            <div>
              <div class="scholarai-brand-name">ScholarAI Workforce</div>
              <div class="scholarai-brand-copy">Human-guided multi-agent intelligence</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_header(icon: str, eyebrow: str, title: str, subtitle: str, chips: tuple[str, ...] = ()) -> None:
    chip_html = "".join(f'<span class="scholarai-chip">{escape(chip)}</span>' for chip in chips)
    chips_block = f'<div class="scholarai-hero-chips">{chip_html}</div>' if chip_html else ""
    st.markdown(
        f"""
        <section class="scholarai-page-hero">
          <div class="scholarai-hero-content">
            <div class="scholarai-eyebrow">{escape(eyebrow)}</div>
            <h1 class="scholarai-page-title">
              <span class="scholarai-page-icon">{escape(icon)}</span>{escape(title)}
            </h1>
            <p class="scholarai-page-subtitle">{escape(subtitle)}</p>
            {chips_block}
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def empty_state(icon: str, message: str) -> None:
    st.markdown(
        f'<div class="scholarai-empty"><span class="scholarai-empty-icon">{escape(icon)}</span>'
        f"<span>{escape(message)}</span></div>",
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    st.markdown(
        """
        <div class="scholarai-footer">
          <span><strong>ScholarAI Workforce</strong> · Responsible scholarship intelligence</span>
          <span>LangGraph · FastAPI · Streamlit · Groq · PostgreSQL · Qdrant</span>
        </div>
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


def agent_display_label(agent_key: str) -> str:
    return f"{AGENT_ICONS.get(agent_key, '🤖')} {agent_display_name(agent_key)}"
