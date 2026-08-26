# Final Submission Checklist

## Required artifacts

- [ ] Source code opens and installs from a clean clone.
- [ ] GitHub repository URL is included in the submission.
- [x] Architecture diagram: `docs/assets/scholarai-workforce-architecture.png`
- [x] Setup and run instructions: `README.md` and `docs/DEPLOYMENT.md`
- [x] Presentation: `docs/presentation/ScholarAI_Workforce_Presentation.pptx`
- [ ] Real Teams approval evidence is attached.
- [ ] Real weekly-progress evidence is attached.
- [ ] Hosted Streamlit URL is included and tested in an incognito window.

## Live demonstration

- [ ] Start a new application and receive HTTP 202/background status.
- [ ] Show active-agent progress and the live trace.
- [ ] Pause and resume the workflow.
- [ ] Cancel a disposable run.
- [ ] Retry one agent and show downstream reruns.
- [ ] Show agent communication and actual LangGraph topology.
- [ ] Show actual provider token usage/cost.
- [ ] Download the log/error JSON.
- [ ] Show shared memory and policy RAG/web context.
- [ ] Download the fact-grounded SOP.
- [ ] Request review and show the Supervisor restart.
- [ ] Approve/reject only through the human gate.

## Final quality gate

```bash
SCHOLARAI_ENVIRONMENT=test SCHOLARAI_WEBSEARCH__ENABLED=false uv run pytest -q
uv run ruff check src ui tests
uv run mypy src
docker compose config
```

- [ ] No `.env`, API key, applicant upload, or private evidence is committed.
- [ ] README contains the final GitHub and hosted URLs.
- [ ] Free-database expiry and single-worker demo limitations are understood.
