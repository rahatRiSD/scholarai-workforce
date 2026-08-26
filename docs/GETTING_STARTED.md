# Getting Started

## Fastest path: Docker Compose

```bash
git clone <this-repo>
cd scholarai-workforce
cp .env.example .env
docker compose up --build
```

- API: http://localhost:8000/docs
- Streamlit: http://localhost:8501

No API key required — the LLM layer runs in offline mode automatically. Set
`SCHOLARAI_LLM__OPENAI_API_KEY` (or `..._ANTHROPIC_API_KEY`) in your shell before `up`
to use a real provider instead.

## Local (no Docker)

Requires Python 3.12+ and [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync --all-extras --dev
cp .env.example .env

# sanity check — prints resolved config, LLM provider, DB, vector store
uv run scholarai status

# the full guided tour: 5 synthetic students through the real Supervisor workflow
uv run scholarai demo
```

Then, in two separate terminals:

```bash
uv run scholarai serve                                  # terminal 1: API on :8000
uv run streamlit run ui/streamlit_app/app.py             # terminal 2: UI on :8501
```

## Your first evaluation, step by step

```bash
# 1. Submit an application with a real sample transcript
uv run scholarai submit -s merit_scholarship \
    -f data/sample_applications/student_a_strong_academic/transcript.txt \
    -f data/sample_applications/student_a_strong_academic/financial_statement.txt

# -> prints the created application, note its "application_id" (APP-XXXXXXXX)

# 2. Run it through the Supervisor's full agent workforce
uv run scholarai evaluate --application APP-XXXXXXXX

# -> prints status=review_required, critic revisions, and the evaluation result

# 3. Record a human decision
uv run scholarai decide --application APP-XXXXXXXX -a approve --reviewer "Jane Reviewer"
```

Or do all three visually: **New Evaluation** → submit → **Agent Workforce** (watch the
trace) → **Evaluation Details** (read the scores + evidence) → **Human Review** (decide).

## Running the tests

```bash
uv run pytest -v
```

See [testing section of the README](../README.md#18-testing) for what's covered.

## Next steps

- [ARCHITECTURE.md](ARCHITECTURE.md) — how the layers fit together and why
- [AGENTS.md](AGENTS.md) — what each of the 9 specialists actually does
- [DEMO.md](DEMO.md) — what each of the 5 synthetic sample students is designed to show
- [HUMAN_IN_LOOP.md](HUMAN_IN_LOOP.md) — the review/decision workflow in detail
