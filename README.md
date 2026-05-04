# fraud-v2

Local-first, Python-heavy fraud decision platform spec based on the BryansLab
Fraud Detection V2 article.

Start here:

- [Plan Index](docs/plan-index.md)
- [Spec Plan](docs/spec-plan.md)
- [Setup](docs/setup.md)
- [Vagueness Register](docs/vagueness-register.md)
- [Blockers And Vague Decisions](docs/blockers-and-vague-decisions.md)
- [Solution Tradeoffs](docs/solution-tradeoffs.md)
- [Dependency Map](docs/dependency-map.md)
- [Data Strategy](docs/data-strategy.md)
- [LLM Synthetic Data Lab](docs/llm-synthetic-data-lab.md)
- [Local Production Profile](docs/local-production-profile.md)
- [Production Readiness](docs/production-readiness.md)
- [Code Factory Dashboard](factory/dashboard.md)

Current state: local MVP plus full-profile adapter layer implemented. It runs in
lite mode with synthetic data, SQLite storage, rules/graph scoring, baseline
model training, FastAPI endpoints, dashboard, metrics, tests, CI workflow, and
Docker Compose scaffolding. Full mode includes replaceable Postgres, Redis,
Redpanda, and Neo4j adapter boundaries.

## Run Lite Mode

```powershell
uv sync --extra dev
uv run fraud-v2 generate --users 120 --output data/synthetic/tiny/events.jsonl
uv run fraud-v2 load data/synthetic/tiny/events.jsonl --db-path data/local/fraud_v2.sqlite
uv run fraud-v2 score user_00000 --db-path data/local/fraud_v2.sqlite
uv run uvicorn fraud_v2.api.main:app --host 127.0.0.1 --port 8000
```

Local URLs:

- API docs: `http://127.0.0.1:8000/docs`
- Analyst dashboard: `http://127.0.0.1:8000/dashboard`
- Metrics: `http://127.0.0.1:8000/metrics`

Protected `/v1/*` endpoints require `Authorization: Bearer dev-token-change-me`
by default. Override `FRAUD_API_TOKEN` locally instead of committing secrets.

## Run Full Local Infra

```powershell
docker compose -f infra\docker-compose.yml --profile full up -d
docker compose -f infra\docker-compose.yml --profile full ps
```

The full profile starts the API container plus Postgres, Redis, Redpanda, Neo4j,
Prometheus, and Grafana.

Full-profile smoke:

```powershell
.\scripts\full-smoke.ps1
.\scripts\full-smoke.ps1 -KeepRunning
```

## Reports

```powershell
uv run fraud-v2 replay --events-path data/synthetic/tiny/events.jsonl
uv run fraud-v2 monitor --events-path data/synthetic/tiny/events.jsonl
uv run fraud-v2 llm-stub
uv run fraud-v2 llm-generate --provider offline
uv run fraud-v2 outbox-drain --db-path data/local/fraud_v2.sqlite --dry-run
uv run fraud-v2 compliance-draft <decision-id> --db-path data/local/fraud_v2.sqlite
uv run fraud-v2 model-register --status shadow
uv run fraud-v2 model-promote baseline-20260505-001
uv run fraud-v2 shadow-score --status active
uv run fraud-v2 public-dataset paysim
```

OpenAI/Azure-backed synthetic scenario generation is available through
`llm-generate --provider openai` or `--provider azure`, but the repo defaults to
`offline` so local tests never require credentials or network calls.

## Quality Gate

```powershell
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest -q
```
