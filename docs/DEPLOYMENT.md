# Deployment Guide

This project includes a Docker image, `docker-compose.yml`, and a Render Blueprint.
The recommended public-demo deployment is GitHub + Render: two web services (FastAPI
and Streamlit) plus PostgreSQL.

## 1. Verify locally

```bash
cp .env.example .env
uv sync --all-extras --dev
SCHOLARAI_ENVIRONMENT=test SCHOLARAI_WEBSEARCH__ENABLED=false uv run pytest -q
uv run ruff check src ui tests
uv run mypy src
docker compose up --build
```

Open `http://localhost:8501`, submit a sample application, and verify the live trace,
pause/resume, retry-agent, logs download, SOP output, and human review rerun.

## 2. Publish the repository

```bash
git init -b main                       # only if this folder is not already a repo
git add .
git commit -m "Build ScholarAI multi-agent workforce"
gh repo create scholarai-workforce --private --source . --remote origin --push
```

Change `--private` to `--public` only when the repository is ready for assessment.
Never commit `.env`, provider keys, applicant files, or real approval screenshots that
contain private information.

## 3. Create the Render Blueprint

1. In Render, choose **New → Blueprint** and connect the GitHub repository.
2. Select the repository and root `render.yaml`.
3. Provide the prompted secrets:
   - `SCHOLARAI_API__API_KEYS`: JSON list such as `["a-long-random-demo-key"]`
   - `SCHOLARAI_LLM__OPENAI_API_KEY`: your provider key
   - `SCHOLARAI_API_KEY`: the same demo API key used by the backend
4. After creation, copy the real API URL and set the UI service's
   `SCHOLARAI_API_BASE_URL` to it if Render assigned a different name.
5. Redeploy the UI service.

The Blueprint uses free instances for demonstration. Render's free Postgres currently
expires after 30 days and has no backups, so use a paid database or export evidence
before expiry for any persistent showcase.

## 4. Verify the hosted system

1. Open `https://<api-host>/health` and confirm `status` is healthy.
2. Open the Streamlit URL and create an application.
3. Start evaluation and watch the one-second live trace.
4. Test pause → resume, retry one completed agent, and download logs.
5. Confirm the topology, provider usage, SOP draft, and human review pages load.
6. Choose **Request review** and verify the Supervisor starts a fresh run.

## Operational limitation

The run manager is in-process, so the supplied API deployment deliberately uses one
worker. A restart interrupts active jobs, although the latest streamed state remains
in the application store. Before horizontal scaling, move run coordination and control
signals to a durable queue/shared store such as Celery or RQ with Redis.

## Official references

- [Render Blueprints](https://render.com/docs/infrastructure-as-code)
- [Blueprint YAML reference](https://render.com/docs/blueprint-spec)
- [Docker on Render](https://render.com/docs/docker)
- [Deploying FastAPI](https://render.com/docs/deploy-fastapi)
- [Free-instance limits](https://render.com/docs/free)
