"""``scholarai demo`` — a one-command, end-to-end tour of the whole system.

Runs all five synthetic sample applications (build spec §27) through
Supervisor planning, the specialist agents, tool usage, RAG retrieval, the
Critic's audit loop, a simulated human decision, and long-term memory —
every stage build spec §36 asks the demo to show. Runs fully offline (no
API key required); with a real LLM provider configured it uses that
instead, automatically.
"""

from __future__ import annotations

from pathlib import Path

from scholarai.application.use_cases.apply_human_decision import apply_human_decision
from scholarai.application.use_cases.get_memory import find_similar_cases
from scholarai.application.use_cases.run_evaluation import run_evaluation
from scholarai.application.use_cases.submit_application import create_application
from scholarai.composition import bootstrap, build_container, build_workflow_graph
from scholarai.domain.models.human import HumanAction, HumanDecision

_SAMPLE_ROOT = Path("data/sample_applications")

_STUDENTS = [
    ("student_a_strong_academic", "merit_scholarship", "Strong academic candidate"),
    ("student_b_missing_financial", "merit_scholarship", "Missing financial document"),
    ("student_c_conflicting_cgpa", "merit_scholarship", "Conflicting CGPA information"),
    ("student_d_ineligible_cgpa", "merit_scholarship", "Ineligible due to CGPA"),
    ("student_e_financial_need", "need_based_scholarship", "Strong financial need, average academics"),
]

_DECISION_FOR_RECOMMENDATION = {
    "highly_recommended": HumanAction.APPROVE,
    "recommended": HumanAction.APPROVE,
    "review_required": HumanAction.REQUEST_REVIEW,
    "not_recommended": HumanAction.REJECT,
    "ineligible": HumanAction.REJECT,
}


def _rule(char: str = "-", width: int = 78) -> str:
    return char * width


async def run_demo() -> None:
    print(_rule("="))
    print("ScholarAI Workforce — end-to-end demo")
    print(_rule("="))

    container = build_container()
    await bootstrap(container)
    graph = build_workflow_graph(container)

    print(f"\nLLM provider : {container.llm.provider_name}")
    print(f"Database     : {container.settings.database.url}")

    results = []
    for folder_name, scholarship_code, description in _STUDENTS:
        folder = _SAMPLE_ROOT / folder_name
        files = [(path.name, path.read_bytes()) for path in sorted(folder.iterdir())]

        print(f"\n{_rule()}")
        print(f"CASE: {folder_name}  ({description})")
        print(f"Scholarship: {scholarship_code}   Documents: {[f[0] for f in files]}")
        print(_rule())

        application = create_application(
            container.application_store, container.document_reader, scholarship_code, files
        )
        print(f"[supervisor] created application {application.application_id}")

        final_state = await run_evaluation(container.application_store, graph, application.application_id)

        print(f"[supervisor] plan executed: {' -> '.join(final_state['plan'])}")
        for event in final_state["trace"]:
            marker = {"completed": "OK", "failed": "FAIL", "waiting": "WAIT", "started": "..", "info": "II"}.get(
                event["status"], "  "
            )
            print(f"  [{marker}] {event['actor']:<20} {event['event']:<45} {event.get('detail', '')}")

        evaluation = final_state.get("evaluation") or {}
        recommendation = evaluation.get("recommendation", "unknown")
        print(
            f"\n  Evaluation Agent -> overall score {evaluation.get('overall_score', 0):.1f}/100, "
            f"recommendation={recommendation}"
        )
        print(
            f"  Critic Agent     -> {final_state['critic_result']['verdict'].upper()} "
            f"(after {final_state['critic_revisions']} revision(s))"
        )

        action = _DECISION_FOR_RECOMMENDATION.get(recommendation, HumanAction.REQUEST_REVIEW)
        decision = HumanDecision(
            application_id=application.application_id,
            action=action,
            reviewer="demo-reviewer",
            notes=f"auto-selected in `scholarai demo` based on recommendation={recommendation}",
        )
        final = await apply_human_decision(
            container.application_store,
            container.episode_repository,
            container.semantic_memory,
            application.application_id,
            decision,
        )
        final_status = final["final_recommendation"]["final_status"]
        print(f"  Human reviewer   -> {action.value} -> final status: {final_status}")
        results.append((application.application_id, folder_name, recommendation, final_status))

    print(f"\n{_rule('=')}")
    print("MEMORY: searching for cases similar to 'strong academic record with financial hardship'")
    similar = await find_similar_cases(container.semantic_memory, "strong academic record with financial hardship")
    for item in similar:
        print(f"  {item['application_id']} (score={item['score']:.2f}): {item['summary']}")

    print(f"\n{_rule('=')}")
    print("SUMMARY")
    print(_rule("="))
    for application_id, name, recommendation, final_status in results:
        print(f"  {application_id:>12} | {name:<28} | AI: {recommendation:<18} | Final: {final_status}")
    print(_rule("="))
    print("Demo complete.")
