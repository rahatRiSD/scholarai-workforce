# Human-in-the-Loop

## The guarantee

**No application ever reaches `approved` or `rejected` status without an explicit human
decision.** This isn't a UI convention layered on top of an otherwise-autonomous system
— it's structural: `final_recommendation` and the terminal `status` values are set in
exactly one function, `application/use_cases/apply_human_decision.py`, which is never
called by any agent, the Supervisor, or the LangGraph workflow itself. It is only ever
invoked by a request a human reviewer makes (`POST
/applications/{id}/human-decision`, `scholarai decide`, or the Streamlit **Human
Review** page).

## Where the workflow pauses

The LangGraph workflow (`application/orchestration/graph.py`) always terminates at a
`human_review_gate` node: after the Critic Agent returns `PASS`, or after it returns
`REVISE` but the revision budget (`max_critic_revisions`, default 2) is exhausted. That
node sets `status="review_required"` and the graph's `ainvoke()` call simply returns —
there is no code path in the graph that proceeds past this point on its own.

## Why not `interrupt()` / a checkpointer

LangGraph offers `interrupt()` and checkpointer-backed persistence specifically for
workflows that need to pause and resume *mid-execution*, potentially at multiple
points, preserving partial in-flight state across a process restart. ScholarAI
Workforce has exactly **one** pause point, and it's always at the very end of a
self-contained `ainvoke()` call — there's no partial mid-agent state to preserve. Using
`interrupt()` here would mean taking on checkpointer configuration and resume-token
plumbing to solve a problem this system doesn't actually have. Instead: the graph
finishes, its final state is persisted in `ApplicationStore` (an in-process store keyed
by application ID — see `application/use_cases/application_store.py`), and "resuming"
is just: read that state, apply the human's decision to it, persist the result. This is
simpler to read, simpler to test (`apply_human_decision` is a plain async function with
no LangGraph machinery involved), and behaviorally identical from the reviewer's point
of view.

## The four actions

| Action | Effect |
|---|---|
| `approve` | `final_status = "approved"`, episode persisted, indexed into semantic memory |
| `reject` | `final_status = "rejected"`, episode persisted, indexed into semantic memory |
| `request_review` | `final_status = "review_required"` — the reviewer wants another pass; re-run `POST /applications/{id}/evaluate` to send it through the Supervisor again |
| `request_more_information` | `final_status = "review_required"` — the reviewer needs more documents from the applicant before deciding |

Every action, along with the reviewer's name and free-text notes, is recorded verbatim
in the persisted episode (`HumanDecisionRecord` / the episode's `human_decision` JSON
column) — the paper trail includes not just *what* was decided but *who* decided it and
*why*.

## What a reviewer sees before deciding

The Streamlit **Human Review** page (and the equivalent API responses) surface: the
Evaluation Agent's score and recommendation, its plain-language summary, any Critic
issues on record, any unresolved Verification conflicts, and — via **Evaluation
Details** — every piece of `Evidence` behind the recommendation with its quality label
(`direct` / `inferred` / `unavailable`). The design intent is that a reviewer never has
to take the AI's recommendation on faith; every claim underneath it is inspectable.
