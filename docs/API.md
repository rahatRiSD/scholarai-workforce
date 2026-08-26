# API Reference

Base URL: `http://localhost:8000` (interactive docs at `/docs` once running).
Authentication: bearer API key, only enforced when `SCHOLARAI_API__API_KEYS` is set
(see [security considerations](../README.md#21-security-considerations)).

## Health

| Method | Path | Description |
|---|---|---|
| GET | `/health` | `{status, llm_provider, environment}` |

## Scholarships

| Method | Path | Description |
|---|---|---|
| GET | `/scholarships` | List available scholarship presets (`code`, `name`, `description`) |

## Applications

| Method | Path | Description |
|---|---|---|
| POST | `/applications` | Create an application. Form fields: `scholarship_code`, `files` (multipart, repeated) |
| GET | `/applications` | List all in-flight/recent applications |
| GET | `/applications/{id}` | Full raw workflow state for one application |
| POST | `/applications/{id}/evaluate` | Start the Supervisor in the background; returns HTTP 202 and runtime state |
| GET | `/applications/{id}/status` | Poll workflow and runtime status, progress, active actor, and errors |
| POST | `/applications/{id}/pause` | Pause at the next streamed graph checkpoint |
| POST | `/applications/{id}/resume` | Resume a paused run |
| POST | `/applications/{id}/cancel` | Cancel an active or paused run |
| POST | `/applications/{id}/retry` | Body: `{agent_name}`; retry that specialist and required downstream agents |
| GET | `/applications/{id}/agents` | Agent results, live trace, messages, and runtime state |
| GET | `/applications/{id}/logs` | Runtime, trace, communication, and error report |
| GET | `/applications/{id}/logs/download` | Download the execution/error report as JSON |
| GET | `/applications/{id}/usage` | Actual provider token events, totals, and estimated API cost |
| GET | `/applications/workflow/topology` | Real compiled LangGraph JSON and Mermaid topology |
| GET | `/applications/{id}/evaluation` | Evaluation, Critic result, final recommendation, and SOP draft |
| GET | `/applications/{id}/evidence` | Every `Evidence` record across all agents + policy citations, plus detected conflicts |
| POST | `/applications/{id}/human-decision` | Body: `{action, reviewer, notes}`. `request_review` clears prior review state and starts a full Supervisor rerun |

## Dashboard

| Method | Path | Description |
|---|---|---|
| GET | `/dashboard/summary` | `{total_applications, pending_review, approved, rejected, review_required, average_score}` |

## Knowledge base

| Method | Path | Description |
|---|---|---|
| POST | `/knowledge-base/upload` | Multipart `file` (Markdown/text) — chunks and indexes it, returns `{filename, total_chunks_indexed}` |
| POST | `/knowledge-base/search` | Body: `{query, limit}` — returns matching policy chunks with citations |

## Memory

| Method | Path | Description |
|---|---|---|
| GET | `/memory/{student_id}` | Prior episodes for a student |
| POST | `/memory/search` | Body: `{query, limit}` — semantic search over past evaluation episodes |

## Errors

Handled centrally in `interfaces/api/errors.py`:

| Domain exception | HTTP status |
|---|---|
| `DocumentProcessingError` | 422 |
| `AgentExecutionError` | 502 |
| `ScholarAIError` (base, e.g. unknown application/scholarship) | 404 |
| anything else | 500 |

Every error response body is `{"detail": "<message>"}`, which is what
`ui/streamlit_app/client.py`'s `ScholarAIAPIError` surfaces.
