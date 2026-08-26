# Agents

All agent modules live in `src/scholarai/application/agents/` and share one shape: an
async `run(state: dict, deps: AgentDeps) -> dict` that reads from the shared
`ScholarshipState`, does its work, and returns a partial state update (LangGraph merges
partial dict returns into the running state). Agents don't call each other directly —
they communicate through the shared state plus an explicit `AgentMessage` log
(`add_message`) so every handoff is inspectable, not an implicit side effect.

## Supervisor (`agents/supervisor.py`)

Not a graph node that "does work" — it's the planning/routing logic. `build_plan(preset,
has_achievements)` returns the ordered list of specialists to run for a given
scholarship, skipping any agent the scholarship's `ScoringWeights` gives zero weight
(e.g. a purely need-based scholarship skips the Achievement Agent unless the applicant
actually has achievements). On a Critic `REVISE` verdict, `choose_revise_targets(issues)`
maps the Critic's specific issue strings to the agent(s) responsible (keyword matching:
"academic"/"cgpa" → academic_agent, "financial" → financial_agent, "conflict" →
verification_agent, etc.) — so a revision re-runs only what's implicated, not the whole
pipeline, then always re-runs `evaluation_agent` and `critic_agent`.

## Document Analysis Agent (`agents/document_analysis.py`)

Runs deterministic regex extraction (`infrastructure/documents/extraction.py`) over
every submitted document first, then — only for fields the regex extraction left
empty — asks the LLM to fill gaps from the raw text. The LLM is never allowed to
*overwrite* a value the deterministic extractor already found; it can only fill genuine
gaps. Produces the `ExtractedApplicationData` every other agent reads.

## Eligibility Agent (`agents/eligibility.py`)

Wraps `domain/services/eligibility_rules.check_eligibility()`: checks CGPA, credits,
current semester, failed-course count, and required-document presence against the
scholarship's `EligibilityRequirements`. Distinguishes "we don't have this data" from
"this data fails the requirement" — the former needs a human, the latter is a
deterministic ineligibility.

## Academic Evaluation Agent (`agents/academic_evaluation.py`)

Wraps `domain/services/academic_scoring.py`: normalizes CGPA to a 0-100 scale, detects
an improving/declining/stable trend from semester-by-semester GPA history (first-half
vs. second-half mean, 0.05 epsilon), and assesses consistency by GPA spread (≤0.25
excellent, ≤0.5 good, ≤1.0 fair, else poor).

## Financial Need Agent (`agents/financial_need.py`)

Wraps `domain/services/financial_need.py`. If family income, household size, or tuition
cost is missing, it does **not** guess — it returns `score=None`,
`needs_human_review=True`, and a finding string containing the literal text
"UNKNOWN / NEEDS HUMAN REVIEW" (asserted directly in `tests/e2e/test_demo_scenarios.py`).

## Achievement Agent (`agents/achievement.py`)

Wraps `domain/services/achievement_scoring.py`: per-category point values (publication
25, award 20, competition 18, leadership 15, certification 12, project 10,
volunteering/community 8, extracurricular 6, unclassified 5), with unevidenced
achievements scored at half weight. Dynamically dropped from the plan entirely if the
applicant has zero achievements (see the "why not just check at planning time" note in
`orchestration/graph.py` — extracted data doesn't exist yet when the initial plan is
built, so the plan is corrected once `document_agent` actually runs).

## Policy / RAG Agent (`agents/policy_rag.py`)

Generates ~4 scholarship-specific policy questions, retrieves supporting chunks via
`PolicyRetriever` (relevance threshold 0.15), and asks the LLM to answer strictly from
retrieved text. If nothing relevant is retrieved for a question, the agent records
`EvidenceQuality.UNAVAILABLE` rather than answering from the LLM's general knowledge —
the Critic Agent specifically checks for "answered questions but zero citations" as a
hallucination signal.

## Verification Agent (`agents/verification.py`)

Re-runs the deterministic regex extractor per individual document (rather than on the
merged data) specifically to catch cross-document contradictions — e.g. a transcript
reporting CGPA 3.58 and a self-reported application form claiming 3.95. Conflicts are
recorded as human-readable "CONFLICT DETECTED: ..." strings via
`domain/services/verification.find_cgpa_conflict()` (0.01 tolerance).

## Evaluation Agent (`agents/evaluation.py`)

Combines every prior agent's deterministic component score into a weighted
`overall_score` via `domain/services/evaluation.compute_overall_score()`, classifies it
into a `Recommendation` band via the scholarship's `RecommendationThresholds`, and — the
one place an LLM writes prose in this pipeline that a human will actually read as the
primary artifact — asks the LLM to write a plain-language summary of the already-final
numbers. Forces `INELIGIBLE` regardless of score if the Eligibility Agent found the
applicant ineligible; flags `requires_human_review=True` when the score sits within 5
points of a threshold boundary.

## Critic Agent (`agents/critic.py`)

An independent audit, not a rubber stamp — it does not just re-ask the LLM "does this
look right?". It recomputes the overall score itself from the reported component scores
and weights (0.5-point tolerance) and checks six things: (1) the recomputed score
matches the reported score, (2) policy claims have supporting citations, (3) the
supporting-evidence component score isn't suspiciously low (<25), (4) no
`Verification Agent` conflict went unresolved, (5) no specialist agent failed outright,
and (6) the recommendation actually matches the score band the thresholds imply. Any
failure returns `REVISE` with the specific issue strings the Supervisor uses to target
its re-run.

## SOP Writer Agent (`agents/sop_writer.py`)

Runs after the deterministic evaluation and writes a polished, student-editable
statement of purpose using only extracted and verified application facts. Its prompt
explicitly prohibits invented institutions, awards, goals, or personal history. The
draft is stored in shared state, included in the communication trace, downloadable from
Evaluation Details, and checked by the Critic when the SOP agent is part of the plan.
Offline mode produces a deterministic draft so demonstrations do not depend on an API
key.

## Human Review Gate

Not an "agent" in the LLM sense — a terminal graph node
(`_human_review_gate_node_factory` in `orchestration/graph.py`) that sets
`status="review_required"` and stops. See [HUMAN_IN_LOOP.md](HUMAN_IN_LOOP.md).
