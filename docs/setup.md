---
project: fraud-v2
owner: Bryan
created_at: 2026-05-04
updated_at: 2026-05-05
status: draft
source_task: TC-20260504-001
version: 2
---

# Setup: Fraud V2

Current state: local MVP plus full-profile adapter layer implemented. Lite mode
runs with Python, SQLite, synthetic data, FastAPI, dashboard, metrics,
rules/graph scoring, and baseline model training. Full local infrastructure is
scaffolded with Docker Compose, replaceable adapters, Prometheus, and a
provisioned Grafana dashboard.

## Prerequisites

Observed on Bryan's machine:

| Tool | Version | Check Command |
|---|---|---|
| Windows PowerShell | local shell | `$PSVersionTable.PSVersion` |
| Python | 3.12.9 | `python --version` |
| uv | 0.7.3 | `uv --version` |
| Docker | 28.4.0 | `docker --version` |
| NVIDIA driver | 565.90 | `nvidia-smi` |
| CUDA runtime reported by driver | 12.7 | `nvidia-smi` |

Target local services:

| Service | Local Port | Purpose |
|---|---:|---|
| FastAPI | 8000 | Fraud API and OpenAPI docs. |
| NiceGUI | 8088 | Analyst/operator UI. |
| Postgres | 5432 | Durable app state. |
| Redis | 6379 | Online features and circuit state. |
| Redpanda | 9092 | Kafka-compatible event bus. |
| Redpanda Console | 8080 | Topic inspection. |
| Neo4j HTTP | 7474 | Graph browser/API. |
| Neo4j Bolt | 7687 | Graph driver. |
| Prometheus | 9090 | Metrics. |
| Grafana | 3000 | Dashboards. |
| Loki | 3100 | Logs. |
| OTel Collector | 4317/4318 | Traces/metrics/logs intake. |

## Environment Variables

| Name | Required | Example | Notes |
|---|---|---|---|
| `FRAUD_ENV` | yes | `local` | Environment name. |
| `FRAUD_API_TOKEN` | yes | `dev-token-change-me` | Local only. Do not commit real secrets. |
| `DATABASE_URL` | yes | `postgresql+psycopg://fraud:fraud@localhost:5432/fraud_v2` | App database. |
| `REDIS_URL` | yes | `redis://localhost:6379/0` | Online feature store. |
| `REDPANDA_BOOTSTRAP_SERVERS` | yes | `localhost:9092` | Event bus. |
| `NEO4J_URI` | yes | `bolt://localhost:7687` | Graph DB. |
| `NEO4J_USER` | yes | `neo4j` | Local graph user. |
| `NEO4J_PASSWORD` | yes | `fraud-local-password` | Local secret. |
| `MODEL_REGISTRY_PATH` | yes | `./data/models` | Local artifacts. |
| `OFFLINE_STORE_PATH` | yes | `./data/offline` | DuckDB/Parquet path. |
| `LLM_PROVIDER` | no | `offline` | Structured scenario generation provider. |
| `OPENAI_MODEL` | no | `gpt-5.5` | Model or Azure deployment name. |
| `OPENAI_API_KEY` | no | empty | Required only for `LLM_PROVIDER=openai`. |
| `OPENAI_BASE_URL` | no | empty | Optional OpenAI-compatible endpoint override. |
| `AZURE_OPENAI_API_KEY` | no | empty | Required only for `LLM_PROVIDER=azure`. |
| `AZURE_OPENAI_ENDPOINT` | no | empty | Azure OpenAI resource endpoint. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | no | `http://localhost:4317` | Observability. |
| `LOG_LEVEL` | no | `INFO` | Structured logs. |

## Install

Commands:

```powershell
cd C:\Users\wbrya\OneDrive\Documents\GitHub\fraud-v2
uv python pin 3.12
uv sync --all-extras
```

CPU-first install should be the default. GPU dependencies should be optional:

```powershell
uv sync --extra gpu
```

Do not make GPU packages required for API, workers, or UI.

## Run Local Infrastructure

Use profiles:

| Profile | Purpose | Command |
|---|---|---|
| `lite` | Fast contract, rules, and synthetic-data work. | `uv run python -m fraud_v2.dev lite` |
| `full` | Production-shaped local demo with event bus, graph, and observability. | `docker compose -f infra\docker-compose.yml --profile full up -d` |
| `ml` | Offline training and evaluation. | `uv run fraud-v2 train --events-path data\synthetic\tiny\events.jsonl --output-dir data\models\baseline` |

Command:

```powershell
docker compose -f infra\docker-compose.yml up -d
```

Full-profile smoke with cleanup:

```powershell
.\scripts\full-smoke.ps1
```

The smoke uses a separate Docker Compose project, `fraud-v2-smoke`, and high
host ports by default so it does not collide with a local dev API on `8000`: API
`18000`, Grafana `13000`, Prometheus `19090`, and Neo4j HTTP `17474`. Override
with parameters such as `-ApiPort 18001` if needed.

Keep services running for manual inspection:

```powershell
.\scripts\full-smoke.ps1 -KeepRunning
```

Expected services:

```powershell
docker compose -f infra\docker-compose.yml ps
```

## Initialize Local State

Commands:

```powershell
uv run alembic upgrade head
uv run python -m fraud_v2.seed.synthetic --events 10000 --output data\synthetic
uv run python -m fraud_v2.seed.load --input data\synthetic\events.parquet
```

## Run Locally

Terminal 1:

```powershell
uv run uvicorn fraud_v2.api.main:app --host 127.0.0.1 --port 8000
```

Generate and load data:

```powershell
uv run fraud-v2 generate --users 120 --output data\synthetic\tiny\events.jsonl
uv run fraud-v2 load data\synthetic\tiny\events.jsonl --db-path data\local\fraud_v2.sqlite
```

Score a user:

```powershell
uv run fraud-v2 score user_00000 --db-path data\local\fraud_v2.sqlite
```

Train baseline:

```powershell
uv run fraud-v2 train --events-path data\synthetic\tiny\events.jsonl --output-dir data\models\baseline
```

Reports and LLM scenario generation:

```powershell
uv run fraud-v2 replay --events-path data\synthetic\tiny\events.jsonl
uv run fraud-v2 monitor --events-path data\synthetic\tiny\events.jsonl
uv run fraud-v2 llm-generate --provider offline
uv run fraud-v2 outbox-drain --db-path data\local\fraud_v2.sqlite --dry-run
uv run fraud-v2 compliance-draft <decision-id> --db-path data\local\fraud_v2.sqlite
uv run fraud-v2 model-register --status shadow
uv run fraud-v2 model-promote baseline-20260505-001
uv run fraud-v2 shadow-score --status active
```

Local URLs after implementation:

- API docs: `http://localhost:8000/docs`
- Analyst dashboard: `http://localhost:8000/dashboard`
- Grafana: `http://localhost:3000`
- Grafana Fraud V2 overview: `http://localhost:3000/d/fraud-v2-overview/fraud-v2-overview`
- Redpanda Console: `http://localhost:8080`
- Neo4j Browser: `http://localhost:7474`

Protected API calls require:

```text
Authorization: Bearer dev-token-change-me
```

Use a different local `FRAUD_API_TOKEN` in `.env`; do not commit real secrets.
The legacy token has all local roles for dev speed.

For local role testing:

```text
FRAUD_API_TOKENS=admin:local-admin-token,analyst:local-analyst-token,system:local-system-token
```

Role boundaries:

| Role | Local Scope |
|---|---|
| `system` | Ingest events, generate synthetic data, score decisions. |
| `analyst` | Read decisions, graph neighborhoods, and review queue; submit review outcomes. |
| `admin` | All local actions. |

Check the current token:

```powershell
Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer dev-token-change-me" } `
  -Uri http://127.0.0.1:8000/v1/auth/whoami
```

## Test

Quality gate:

```powershell
uv run ruff format .
uv run ruff check .
uv run mypy src
uv run pytest -q
```

Integration/replay checks:

```powershell
uv run pytest tests\integration -q
uv run pytest tests\replay -q
uv run fraud-v2 train --events-path data\synthetic\tiny\events.jsonl --output-dir data\models\baseline
```

## Build

Local container build:

```powershell
docker compose -f infra\docker-compose.yml build
```

## Repo Layout

```text
fraud-v2/
  README.md
  docs/
    spec-plan.md
    setup.md
  src/
    fraud_v2/
      api/
      compliance/
      config/
      connectors/
      converters/
      decision/
      domain/
      features/
      graph/
      ingestion/
      models/
      observability/
      resilience/
      review/
      rules/
      ui/
      workers/
  tests/
    unit/
    integration/
    replay/
  infra/
    docker-compose.yml
    prometheus/
    grafana/
    otel/
  scripts/
    dev.ps1
    test.ps1
  data/
    synthetic/
    offline/
    models/
  factory/
```

## Cookiecutter File Template

Use this when adding a new module:

```text
src/fraud_v2/<area>/<thing>/
  __init__.py
  <thing>.py
  <thing>_types.py
  <thing>_errors.py
tests/unit/<area>/test_<thing>.py
tests/integration/<area>/test_<thing>.py
```

For simple areas, use files instead of nested folders:

```text
src/fraud_v2/domain/events.py
src/fraud_v2/domain/enums.py
src/fraud_v2/domain/errors.py
tests/unit/domain/test_events.py
```

## Code Rules

- no import fallback hacks
- no try/catch around imports
- no catch-all exception handlers that swallow errors
- no secrets in code, logs, tests, or docs
- clear names over short names
- domain names over generic names
- one source of truth for business rules
- tests must assert behavior, not only existence
- routes must delegate business logic to services
- converters must be explicit and tested
- decisions must include policy version, model version, feature set version, and trace ID
- model outages must degrade through policy, not crash the API

## Quality Commands

| Check | Command | Required Before PR |
|---|---|---|
| format | `uv run ruff format .` | yes |
| lint | `uv run ruff check .` | yes |
| typecheck | `uv run mypy src` | yes |
| tests | `uv run pytest -q` | yes |
| integration | `uv run pytest tests\integration -q` | yes before feature complete |
| replay | `uv run pytest tests\replay -q` | yes before model/policy changes |
| train/eval | `uv run fraud-v2 train --events-path data\synthetic\tiny\events.jsonl --output-dir data\models\baseline` | yes before model changes |

## Common Tasks

| Task | Command | Notes |
|---|---|---|
| Start infra | `docker compose -f infra\docker-compose.yml up -d` | Runs local dependencies. |
| Full-profile smoke | `.\scripts\full-smoke.ps1` | Builds and starts full profile, scores data through the API, checks dashboard/metrics/Grafana/Prometheus/Neo4j, then stops it. |
| Stop infra | `docker compose -f infra\docker-compose.yml down` | Does not delete volumes by default. |
| Reset local data | `docker compose -f infra\docker-compose.yml down -v` | Destructive. Requires explicit approval in Code Factory runs. |
| Seed synthetic data | `uv run python -m fraud_v2.seed.synthetic --events 10000` | No real PII. |
| Start API | `uv run fastapi dev src\fraud_v2\api\main.py --port 8000` | API docs at `/docs`. |
| Open dashboard | `uv run uvicorn fraud_v2.api.main:app --host 127.0.0.1 --port 8000` | Dashboard at `/dashboard`. |
| Train baseline | `uv run fraud-v2 train --events-path data\synthetic\tiny\events.jsonl --output-dir data\models\baseline` | CPU default. |
| Evaluate model | `uv run fraud-v2 train --events-path data\synthetic\tiny\events.jsonl --output-dir data\models\baseline` | Writes metrics, cost, and threshold report. |
| Drain local outbox | `uv run fraud-v2 outbox-drain --db-path data\local\fraud_v2.sqlite --dry-run` | Publishes through a dry-run publisher by default. |
| Export compliance draft | `uv run fraud-v2 compliance-draft <decision-id> --db-path data\local\fraud_v2.sqlite` | Writes a human-review-only local draft. |
| Register model | `uv run fraud-v2 model-register --status shadow` | Stores model/report hashes and metrics in `data\models\registry.json`. |
| Promote model | `uv run fraud-v2 model-promote baseline-20260505-001` | Marks one model active and demotes the previous active model to shadow. |
| Shadow score | `uv run fraud-v2 shadow-score --status active` | Scores registered model output without changing decisions. |

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| Docker ports already in use | Another local stack is running. | Change Compose port env vars or pass full-smoke port parameters such as `-ApiPort 18001`. |
| GPU install fails | CUDA/PyTorch package mismatch or 4GB VRAM limit. | Use CPU install. GPU is optional. |
| API returns degraded decisions | Model, graph, Redis, or feature freshness policy is failing. | Check `/health/ready`, Grafana, and DLQ. |
| Graph query is slow | Supernode or wide neighborhood query. | Lower depth, filter edge types, inspect supernode guard. |
| Replay decisions differ | Policy/model/feature version not pinned. | Pin versions and rerun replay. |
| Tests log sensitive values | Redaction failure. | Fix logger before continuing. |

## Definition Of Done

- [ ] install works from a clean checkout.
- [ ] local run command works.
- [ ] tests run.
- [ ] required environment variables are documented.
- [ ] repo layout is explained.
- [ ] quality commands are listed.
- [ ] GPU is optional, not required.
