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
- [Code Factory Dashboard](factory/dashboard.md)

Current state: local MVP implemented. It runs in lite mode with synthetic data,
SQLite storage, rules/graph scoring, baseline model training, FastAPI endpoints,
dashboard, metrics, tests, CI workflow, and Docker Compose scaffolding.

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
- Dashboard: `http://127.0.0.1:8000/dashboard`
- Metrics: `http://127.0.0.1:8000/metrics`

## Run Full Local Infra

```powershell
docker compose -f infra\docker-compose.yml --profile full up -d
docker compose -f infra\docker-compose.yml --profile full ps
```

The app still runs as a local Python process in this MVP. The full profile
starts local infrastructure for the production-shaped path.

## Quality Gate

```powershell
uv run ruff format .
uv run ruff check .
uv run mypy src
uv run pytest -q
```
