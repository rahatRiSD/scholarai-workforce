# Demo

`uv run scholarai demo` (`src/scholarai/interfaces/cli/demo.py`) runs all five
synthetic sample students under `data/sample_applications/` through the real Supervisor
workflow — the exact same code path the API and CLI use, not a scripted fake — end to
end: application creation, agent planning, tool usage, RAG retrieval, the Critic's
audit, a simulated human decision, and a semantic memory search. It runs fully offline
by default; with a real LLM provider configured (`SCHOLARAI_LLM__PROVIDER=openai` +
key) it uses that automatically instead.

## What each case demonstrates

| Case | Scholarship | What it's designed to show |
|---|---|---|
| `student_a_strong_academic` | Merit | Strong CGPA (3.91) and complete documents → `highly_recommended`/`recommended`, Critic passes cleanly |
| `student_b_missing_financial` | Merit | No financial statement submitted → Financial Need Agent reports "UNKNOWN / NEEDS HUMAN REVIEW" instead of guessing a score |
| `student_c_conflicting_cgpa` | Merit | Transcript says CGPA 3.58, self-reported application form says 3.95 → Verification Agent raises a `CONFLICT DETECTED`, which routes through the Critic's revision loop |
| `student_d_ineligible_cgpa` | Merit | CGPA 2.85, below the merit scholarship's 3.5 minimum → Eligibility Agent fails it, Evaluation Agent forces `ineligible` regardless of any other score |
| `student_e_financial_need` | Need-based | Low household income relative to tuition → Financial Need Agent scores high need (≥50/100), demonstrating the need-based scholarship's different weighting |

Each of these is also asserted directly against the real graph and real files in
`tests/e2e/test_demo_scenarios.py` — the demo output and the test suite are checking the
same behavior, not different code paths.

## Reading the demo output

For each case, the demo prints: the created application ID, the Supervisor's resolved
plan (which agents ran, and in what order), the full execution trace (with OK/FAIL/WAIT
markers), the Evaluation Agent's overall score and recommendation, the Critic's verdict
and how many revision cycles it took to reach it, and the simulated human reviewer's
action (auto-selected from the recommendation via a fixed mapping — highly
recommended/recommended → approve, review required → request review, not
recommended/ineligible → reject) and the resulting final status.

At the end, it searches semantic memory for cases similar to "strong academic record
with financial hardship" and prints whatever it finds among the five just-created
episodes — a live demonstration of the memory layer working, not a canned example.

## Running it against a real LLM

```bash
export SCHOLARAI_LLM__PROVIDER=openai
export SCHOLARAI_LLM__OPENAI_API_KEY=sk-...
uv run scholarai demo
```

The deterministic scores, eligibility outcomes, and conflict detections will be
*identical* to the offline run — only the narrative summaries and policy-question
phrasing change, since those are the only places an LLM's output feeds into the result
(see [ARCHITECTURE.md](ARCHITECTURE.md#deterministic-vs-llm)).
