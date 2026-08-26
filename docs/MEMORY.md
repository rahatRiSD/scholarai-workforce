# Memory

ScholarAI Workforce has two memory layers, both written to only once — by
`apply_human_decision()`, the single place a human's decision finalizes an application
(see [HUMAN_IN_LOOP.md](HUMAN_IN_LOOP.md)). The AI never writes to long-term memory on
its own initiative.

## 1. Structured episode history (SQL)

`infrastructure/database/models.py`'s `EvaluationEpisode` table stores, per
application: student ID, scholarship code, final status, overall score, recommendation,
and full JSON snapshots of every agent's findings, the policy evidence gathered, the
evaluation result, the Critic's feedback, the human decision, and the complete trace
timeline. `SqlEpisodeRepository` (`infrastructure/memory/sql_episode_repository.py`)
implements the `EpisodeRepository` port — `save_episode` (upsert), `get_episode`,
`list_episodes` (optionally filtered by student), `save_human_decision`, and
`summary_counts()` (used by the Dashboard).

Use this for: "show me everything that happened on application APP-XXXXXXXX", "what's
this student's prior scholarship history", fleet-level dashboard counts.

## 2. Semantic episode memory (vector)

`infrastructure/memory/semantic_memory.py`'s `EpisodicSemanticMemory` builds a short,
deliberately PII-minimal summary of each completed episode (scholarship, status, score,
recommendation, review reasons — never raw document text, names, or financial figures)
and embeds + upserts it into its own Qdrant collection (`scholarai_episodes`, separate
from the policy knowledge base's collection).

Use this for: "have we seen a case like this before?" — free-text semantic search over
past decisions, exposed via `find_similar_cases()` / `POST /memory/search` / the
Streamlit **Memory → Find similar cases** tab. `scholarai demo` uses this at the end of
its run to search for cases similar to "strong academic record with financial
hardship."

## Why PII-minimal summaries, not raw records

The vector index exists to help a reviewer find *comparable prior decisions*, not to be
a second copy of sensitive student data — that's what the SQL episode table (which is
access-controlled the same way the rest of the API is) is for. Keeping the semantic
summary to non-identifying aggregate facts means the vector store can be inspected,
exported, or even accidentally exposed with far lower privacy risk than the primary
database.
