# RAG (Retrieval-Augmented Generation)

## Purpose

The Policy Agent must never assert what a scholarship's rules say from an LLM's general
knowledge — Northfield University's policies are entirely fictional, so an LLM has no
real training-data knowledge of them anyway, but the design principle holds generally:
**policy claims must be traceable to an actual indexed document.**

## Pipeline

1. **Source documents** — `data/knowledge_base/*.md`: `scholarship_policy.md`,
   `academic_regulations.md`, `financial_aid_policy.md`, `student_handbook.md`. Plain
   Markdown, structured with `#`/`##`/`###` headings that double as citable section
   names.
2. **Chunking** (`infrastructure/rag/chunking.py`) — walks the Markdown, tracking the
   most recent heading as each chunk's `section`. Target chunk size ~800 characters,
   minimum 40 (short trailing fragments are merged rather than indexed as noise).
3. **Embedding** (`infrastructure/embeddings/`) — `HashingEmbedder` by default: a
   deterministic blake2b-based hash of unigrams + bigrams, L2-normalized to 256
   dimensions. No API key, no network call, fully reproducible — the same text always
   produces the same vector, and semantically similar text produces higher cosine
   similarity purely from shared n-grams. If `SCHOLARAI_LLM__PROVIDER=openai` and a key
   is set, `build_embedder()` swaps in real OpenAI embeddings instead — the rest of the
   pipeline is unchanged.
4. **Storage** (`infrastructure/vectorstore/qdrant_store.py`) — Qdrant, either a real
   server (`SCHOLARAI_VECTORSTORE__URL`) or an in-process `:memory:` instance (the
   default, good enough for a laptop demo but not persisted across restarts). Chunk IDs
   are a stable blake2b hash of `(source, chunk_index)` so re-ingesting the same file
   upserts rather than duplicates.
5. **Retrieval** (`infrastructure/rag/retriever.py`'s `PolicyRetriever`) — embeds the
   query, searches the collection, returns `RetrievedChunk` objects (`text`, `source`,
   `section`, `score`, `metadata`).
6. **Consumption** — the Policy Agent applies a relevance threshold (0.15) before
   trusting a result; below that, it records `EvidenceQuality.UNAVAILABLE` rather than
   answering. The Critic Agent separately checks that any policy question the agent
   claims to have answered actually has ≥1 citation attached.

## Adding new policy documents

Either drop a `.md` file into `data/knowledge_base/` and restart (bootstrap re-ingests
on every startup), or use the Streamlit **Knowledge Base → Upload** page / the
`POST /knowledge-base/upload` endpoint at runtime — both call the same
`ingest_knowledge_base()` function.

## Why hashing embeddings, not a real embedding model, by default

The build brief requires the whole system to run with zero API keys. A learned
embedding model needs either a paid API or a multi-hundred-megabyte local model
download — neither fits "runnable on a normal laptop out of the box." Hashing
embeddings are a well-known fallback technique (the same idea scikit-learn's
`HashingVectorizer` uses) that gets meaningfully-similar text to score higher without
any of that — good enough for a synthetic, four-document knowledge base, and swapped
for real embeddings automatically the moment an API key is configured.
