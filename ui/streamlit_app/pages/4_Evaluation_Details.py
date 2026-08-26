"""Evaluation Details: scores, recommendation, confidence, evidence, policy
citations, conflicts, and missing information (build spec §20 "Final
report/output viewer")."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ui.streamlit_app.client import ScholarAIAPIError  # noqa: E402
from ui.streamlit_app.components.styling import inject_base_styles, recommendation_badge  # noqa: E402
from ui.streamlit_app.services.session import (  # noqa: E402
    get_client,
    get_selected_application_id,
    set_selected_application_id,
)

inject_base_styles()
st.title("🔍 Evaluation Details")
st.caption("The Evaluation Agent's deterministic scoring, the Critic's verdict, and every citable piece of evidence.")

client = get_client()
application_id = st.text_input("Application ID", value=get_selected_application_id() or "", placeholder="APP-XXXXXXXX")
if not application_id:
    st.info("Enter or select an application ID.")
    st.stop()
set_selected_application_id(application_id)

try:
    evaluation_payload = client.get_evaluation(application_id)
    evidence_payload = client.get_evidence(application_id)
except ScholarAIAPIError as exc:
    st.error(str(exc))
    st.stop()

evaluation = evaluation_payload.get("evaluation")
critic_result = evaluation_payload.get("critic_result")
final_recommendation = evaluation_payload.get("final_recommendation")
sop = evaluation_payload.get("sop")

if evaluation is None:
    st.info("This application hasn't been evaluated yet. Run it from **New Evaluation**.")
    st.stop()

st.subheader("Recommendation")
st.markdown(
    f"### {evaluation['overall_score']:.1f} / 100 &nbsp; {recommendation_badge(evaluation['recommendation'])}",
    unsafe_allow_html=True,
)
if evaluation.get("summary"):
    st.write(evaluation["summary"])
if evaluation.get("requires_human_review"):
    st.warning("Requires human review: " + "; ".join(evaluation.get("review_reasons", [])))

st.divider()
st.subheader("Component scores")
scores = evaluation["component_scores"]
weights = evaluation.get("weights_used", {})
score_df = pd.DataFrame(
    [
        {"Component": key.replace("_", " ").title(), "Score": value, "Weight %": weights.get(key, 0)}
        for key, value in scores.items()
    ]
)
col1, col2 = st.columns([2, 3])
col1.dataframe(score_df, width="stretch", hide_index=True)
col2.bar_chart(score_df.set_index("Component")["Score"])

st.divider()
st.subheader("Critic verdict")
if critic_result is None:
    st.info("The Critic hasn't run yet.")
else:
    verdict = critic_result["verdict"]
    color = "🟢" if verdict == "pass" else "🟠"
    st.markdown(f"{color} **{verdict.upper()}** · confidence {critic_result.get('confidence', 0):.0%}")
    st.caption("Checked: " + ", ".join(critic_result.get("checked", [])))
    if critic_result.get("issues"):
        for issue in critic_result["issues"]:
            st.warning(issue)

st.divider()
st.subheader("Conflicts detected")
conflicts = evidence_payload.get("conflicts", [])
if not conflicts:
    st.success("No data conflicts detected across submitted documents.")
else:
    for conflict in conflicts:
        st.error(conflict)

st.divider()
st.subheader("Evidence & policy citations")
evidence_items = evidence_payload.get("evidence", [])
if not evidence_items:
    st.info("No evidence recorded.")
for item in evidence_items:
    quality = item.get("quality", "unavailable")
    icon = {"direct": "📄", "inferred": "🧮", "unavailable": "❓"}.get(quality, "❓")
    with st.expander(f"{icon} {item.get('source', 'Unknown source')} — {quality.upper()}"):
        st.write(item.get("detail", ""))
        if item.get("quote"):
            st.markdown(f"<div class='scholarai-evidence-quote'>“{item['quote']}”</div>", unsafe_allow_html=True)
        if item.get("page_or_section"):
            st.caption(f"Location: {item['page_or_section']}")

st.divider()
st.subheader("Student statement of purpose")
if sop:
    st.markdown(f"<div class='scholarai-card'>{sop}</div>", unsafe_allow_html=True)
    st.download_button(
        "Download SOP",
        data=sop,
        file_name=f"{application_id}-statement-of-purpose.txt",
        mime="text/plain",
    )
else:
    st.info("The SOP Writer has not produced a draft yet.")

st.divider()
st.subheader("Final recommendation (post human review)")
if final_recommendation is None:
    st.info("No human decision has been recorded yet — see **Human Review**.")
else:
    st.json(final_recommendation)
