# Architecture

## Layering

ScholarAI Workforce follows a hexagonal / clean-architecture layout: dependencies only
ever point inward.

```
interfaces/       (FastAPI routes, CLI) -- depends on application + composition
        |
application/      (agents, LangGraph orchestration, tools, use cases) -- depends on domain (ports only)
        |
domain/            (Pydantic models, deterministic services, Protocol ports) -- depends on nothing
        ^
infrastructure/    (concrete adapters: OpenAI/Anthropic/Ollama/Offline LLM clients,
                     Qdrant vector store, SQLAlchemy repositories, PyMuPDF/docx readers,
                     structlog logging) -- implements domain ports
        |
composition.py      the ONE place a concrete infrastructure class is chosen and wired
                     into a `Container`
```

`domain/` never imports from `application/` or `infrastructure/`. `application/` agents
depend only on `domain.ports.*` Protocols (`LLMClient`, `VectorStore`/`Embedder`,
`EpisodeRepository`, `DocumentReader`, `WebSearchClient`) — never on `openai`,
`qdrant_client`, or `sqlalchemy` directly. Swapping OpenAI for Ollama, or SQLite for
PostgreSQL, is a `.env` change, not a code change, because the concrete choice is made
in exactly one place: `composition.build_container()`.

## Deterministic vs. LLM

Every number in an evaluation — GPA normalization, eligibility pass/fail, financial
need score, achievement score, the weighted overall score — comes from pure Python in
`domain/services/*.py`. These functions take typed inputs and return typed outputs; they
have no side effects and are directly unit-tested (`tests/unit/`).

LLMs are used **only** to narrate those already-computed numbers into readable prose —
e.g. "Evaluation Agent" asks the LLM to summarize a `ComponentScores` object it already
built deterministically, not to invent the scores themselves. This means:

- The system produces identical scores/recommendations regardless of which LLM
  provider is configured (or none at all, in offline mode) — only the wording of
  narrative summaries changes.
- A CI run with `SCHOLARAI_LLM__PROVIDER=offline` exercises the *exact same*
  eligibility/scoring/verification logic that runs in production, just with
  `[offline mode]`-labeled narrative text instead of an LLM's prose.

## The Offline LLM client

`infrastructure/llm/offline_client.py`'s `OfflineLLMClient` never calls a network
service. For structured completions, it extracts whatever JSON context was embedded in
the prompt and uses `infrastructure/llm/schema_fill.py`'s `fill_model()` to build a
schema-valid Pydantic instance from it — copying fields that exist in the context and
using type-based defaults for the rest, with any generated narrative field explicitly
prefixed to make clear it's a canned offline response, never mistakeable for a real
model's reasoning. This is what makes `scholarai demo`, the full test suite, and a
first-time clone-and-run all work with zero API keys.

## RAG pipeline

`infrastructure/rag/chunking.py` splits Markdown policy documents on `#`/`##`/`###`
headings, tracking each chunk's nearest heading as its citable `section`. Chunks are
embedded (`infrastructure/embeddings/hashing.py`'s deterministic blake2b-based hashing
embedder by default, or OpenAI embeddings if configured) and stored in Qdrant
(`infrastructure/vectorstore/qdrant_store.py`, in-memory when no `QDRANT_URL` is set).
`PolicyRetriever` wraps search + a relevance threshold; the Policy Agent
(`application/agents/policy_rag.py`) marks evidence `unavailable` rather than
fabricating a citation when nothing relevant is retrieved.

## Human-in-the-loop as a terminal graph node

The LangGraph workflow (`application/orchestration/graph.py`) ends every run at
`human_review_gate` — a plain terminal node that sets `status="review_required"` and
returns. It deliberately does **not** use LangGraph's `interrupt()` primitive or a
checkpointer. Those exist to pause and resume *mid-graph* state across multiple
interruption points; this system has exactly one pause point (right before a
recommendation becomes final), and "resuming" — applying a human's decision — is
implemented as an ordinary, independently-testable Python function
(`application/use_cases/apply_human_decision.py`) rather than a second graph
invocation. This keeps the orchestration layer simpler without losing any required
behavior: the AI genuinely cannot proceed past this point without a human action,
which is the actual requirement (see [HUMAN_IN_LOOP.md](HUMAN_IN_LOOP.md)).

## Error handling

Each specialist node in the graph (`_specialist_node_factory` in `graph.py`) wraps its
agent call in a try/except: a failing agent is recorded into `state["errors"]` and
marked `status="failed"` in `state["agent_results"]`, but the workflow continues rather
than crashing outright, so one bad document or a flaky LLM call doesn't take down an
entire evaluation run. The final state's `errors` list is always surfaced in the API
(`GET /applications/{id}/status`) and Streamlit's Agent Workforce page.

## Live execution and operator control

`WorkflowRunManager` starts every evaluation as an asynchronous background task and
stores a per-application `RunControl`. LangGraph state snapshots are persisted after
each streamed graph update, so API polling and the Streamlit one-second fragment show
the active actor, progress, trace, messages, and errors while the run is still moving.
Pause blocks at the next graph checkpoint, resume releases it, cancel stops the task,
and retry constructs a Supervisor-owned recovery plan beginning at the selected agent
and including every required downstream consumer.

`request_review` is a real rerun, not a label change: it clears prior Critic/final
decision state, restores the full Supervisor plan, and begins a new background run.
Approve and reject remain the only actions that create a final recommendation.

## Topology, usage, and logs

The UI graph is built from `compiled.get_graph(xray=True).to_json()`—the real compiled
LangGraph topology returned by `/applications/workflow/topology`, not a separately
maintained drawing. LLM adapters record the provider response's input/output token
metadata inside an application-and-agent context. `/usage` aggregates those events and
calculates model-aware cost; offline calls are explicitly recorded with zero provider
tokens. `/logs` and `/logs/download` expose runtime state, trace, communication, and
errors as UI-visible and downloadable JSON.

## Privacy-safe web search

The Policy/RAG specialist can augment internal policy retrieval with public web
context. DuckDuckGo works without an API key and Tavily is optional. Only a generic
scholarship-policy query is sent outside the system; applicant names, identifiers,
documents, achievements, and financial data are never included. Web results are marked
as inferred public context and never replace authoritative internal evidence.

## SOP Writer Agent

The SOP Writer runs after deterministic evaluation and before the Critic. Its prompt is
restricted to verified extracted facts and computed results, forbids invented claims,
and produces a student-editable statement of purpose. Offline mode supplies a
deterministic fact-grounded draft, so the feature remains demonstrable without an API
key.

## Why a modular monolith, not microservices

The build brief was explicit: runnable on a normal laptop, understandable by a
university student, no fake functionality, and no overengineering. A single Python
process with a clean internal layering gets all the architectural benefits (testability,
swappable adapters, clear boundaries) that would be used to justify splitting into
services, without the operational cost (service discovery, network failure handling,
distributed tracing) that a project of this scope doesn't need. `docker-compose.yml`
does split out *stateful* dependencies (PostgreSQL, Qdrant) because those genuinely
benefit from being separate, persistent processes — but the application logic itself
stays one deployable unit.
