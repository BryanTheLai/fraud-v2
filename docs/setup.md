---
project: fraud-v2
owner: Bryan
created_at: 2026-05-04
updated_at: 2026-05-06
status: current
source_task: TC-20260504-001
version: 3
---

# Setup: Fraud V2

This is the practical runbook for the current repo. Use it when setting up a
fresh checkout, running the local API, proving Docker full mode, cleaning local
artifacts, or finding the right command.

## What Should Work

| Path | Requirement | Command |
|---|---|---|
| Lite local app | Python 3.12 + uv | `uv run uvicorn fraud_v2.api.main:app --host 127.0.0.1 --port 8000` |
| Full local app | Docker Desktop | `.\scripts\full-smoke.ps1` |
| Quality gate | Python 3.12 + uv | `powershell -ExecutionPolicy Bypass -File scripts\verify.ps1` |
| Full quality gate | Python 3.12 + uv + Docker | `powershell -ExecutionPolicy Bypass -File scripts\verify.ps1 -Full` |

Observed on Bryan's laptop:

| Tool | Observed |
|---|---|
| OS | Windows 11 |
| Python | 3.12.9 |
| CPU | AMD Ryzen 7 class laptop CPU |
| GPU | NVIDIA GeForce RTX 3050 Laptop GPU, optional |
| RAM | about 14 GiB visible to Python |
| Docker | 28.4.0 |

GPU is optional. Do not make CUDA or graph-ML packages required for normal
tests, API serving, or the local demo.

## Install

```powershell
cd C:\Users\wbrya\OneDrive\Documents\GitHub\fraud-v2
uv python pin 3.12
uv sync --extra dev
```

Use infra dependencies when working directly with Postgres, Redis, Redpanda, or
Neo4j clients from local Python:

```powershell
uv sync --extra dev --extra infra
```

Use LLM dependencies only when testing OpenAI/Azure synthetic generation:

```powershell
uv sync --extra dev --extra llm
```

Avoid `--all-extras` for normal setup because `graph-ml` can pull heavy optional
GPU/torch packages.

## Local Doctor

Run this first on a new machine:

```powershell
uv run fraud-v2 local-doctor `
  --output-path data\local\local-doctor.json `
  --dashboard-path data\local\local-doctor.html
```

The doctor checks Python, package import, required repo files, disk, RAM, uv,
git, Docker, Docker Compose, optional NVIDIA GPU visibility, GitHub remote/auth,
and whether lite/full/GitHub handoff paths are ready.

## Lite Mode

Generate synthetic data:

```powershell
uv run fraud-v2 generate --users 120 --output data\synthetic\tiny\events.jsonl
```

Load SQLite:

```powershell
uv run fraud-v2 load data\synthetic\tiny\events.jsonl --db-path data\local\fraud_v2.sqlite
```

Or reset the whole seeded local demo database in one command:

```powershell
uv run fraud-v2 demo-reset --users 120 --db-path data\local\fraud_v2.sqlite
```

Score one user:

```powershell
uv run fraud-v2 score user_00000 --db-path data\local\fraud_v2.sqlite
```

Generate the baseline model report used by the ML dashboard:

```powershell
uv run fraud-v2 train `
  --events-path data\synthetic\tiny\events.jsonl `
  --output-dir data\models\baseline
```

Generate the local model benchmark used by the cockpit:

```powershell
uv run fraud-v2 model-benchmark `
  --events-path data\synthetic\tiny\events.jsonl `
  --output-path data\models\benchmark-report.json
```

Generate the local MLOps report used by the ML dashboard:

```powershell
uv run fraud-v2 mlops-report `
  --events-path data\synthetic\tiny\events.jsonl `
  --output-path data\local\mlops-report.json `
  --simulate-score-shift-points 12
```

Start the API:

```powershell
uv run uvicorn fraud_v2.api.main:app --host 127.0.0.1 --port 8000
```

Open:

| Page | URL |
|---|---|
| Main cockpit | `http://127.0.0.1:8000/cockpit` |
| Demo cockpit | `http://127.0.0.1:8000/demo` |
| Analyst dashboard | `http://127.0.0.1:8000/dashboard` |
| Graph evidence | `http://127.0.0.1:8000/dashboard/graph?entity_id=user_00000` |
| Human ops metrics | `http://127.0.0.1:8000/dashboard/ops` |
| ML dashboard | `http://127.0.0.1:8000/dashboard/ml` |
| Signal lab | `http://127.0.0.1:8000/dashboard/signals` |
| Simulation workbench | `http://127.0.0.1:8000/dashboard/simulate` |
| API docs | `http://127.0.0.1:8000/docs` |
| Raw Prometheus metrics | `http://127.0.0.1:8000/metrics` |

## Local Auth

Protected `/v1/*` routes require bearer auth.

Default local token:

```text
Authorization: Bearer dev-token-change-me
```

Override it locally:

```powershell
$env:FRAUD_API_TOKEN="replace-with-local-only-token"
```

Role-token mode:

```powershell
$env:FRAUD_API_TOKENS="admin:local-admin-token,analyst:local-analyst-token,system:local-system-token"
```

Roles:

| Role | Local Scope |
|---|---|
| `system` | Ingest events, generate data, score decisions. |
| `analyst` | Read decisions, graph evidence, review queue; submit review outcomes. |
| `admin` | All local actions. |

JWT/OIDC-shaped local auth:

```powershell
$env:FRAUD_AUTH_MODE="jwt"
$env:FRAUD_JWT_SECRET="replace-with-local-only-secret-32b-min"
uv run fraud-v2 auth-token --secret $env:FRAUD_JWT_SECRET --subject local-admin
```

JWKS verification is available with `FRAUD_JWT_JWKS_PATH`,
`FRAUD_JWT_JWKS_URL`, or `FRAUD_JWT_OIDC_DISCOVERY_URL`. HS algorithms are
rejected when JWKS verification is configured.

## Full Docker Mode

Start the stack:

```powershell
docker compose -f infra\docker-compose.yml --profile full up -d
docker compose -f infra\docker-compose.yml --profile full ps
```

Services:

| Service | Port | Purpose |
|---|---:|---|
| API | 8000 | Fraud API, dashboard, metrics. |
| Postgres | 5432 | Full-profile app state. |
| Redis | 6379 | Feature/cache adapter proof. |
| Redpanda | 19092 | Kafka-compatible local event bus. |
| Redpanda admin | 9644 | Local broker admin endpoint. |
| Neo4j HTTP | 7474 | Graph browser/API. |
| Neo4j Bolt | 7687 | Graph driver. |
| Prometheus | 9090 | Metrics scrape and local alerts. |
| Grafana | 3000 | Provisioned Fraud V2 dashboard. |

The Docker profile sets `FRAUD_STORE_BACKEND=postgres`. Lite mode still defaults
to SQLite.

Run the isolated full smoke:

```powershell
.\scripts\full-smoke.ps1
```

Keep the smoke stack running for manual inspection:

```powershell
.\scripts\full-smoke.ps1 -KeepRunning
```

The smoke uses Compose project `fraud-v2-smoke` and high ports by default:
API `18000`, Grafana `13000`, Prometheus `19090`, Neo4j HTTP `17474`. It proves
API scoring, dashboard rendering, metrics, Grafana, Prometheus, Postgres,
Redis, Neo4j, Redpanda consume, stream supervision, stream health, DLQ, traces,
audit archive, and Postgres backup/restore.

## Verification

Normal gate:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify.ps1
```

Full gate:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify.ps1 -Full
```

What the normal gate runs:

- `uv run ruff format --check .`
- `uv run ruff check .`
- `uv run fraud-v2 secrets-scan --root .`
- `uv run mypy src`
- `uv run pytest -q`
- `uv run pytest --collect-only -q`
- `local-doctor`
- `readiness-report`
- `release-runbook`
- `model-benchmark`
- `capacity-profile --profile smoke`

`-Full` also runs Docker Compose config, Docker build, and `full-smoke.ps1`.

## Cleanup

```powershell
powershell -ExecutionPolicy Bypass -File scripts\clean-local.ps1
```

The cleanup script removes ignored caches and generated local artifacts. It
keeps `.venv` and `data\public` by default.

Options:

| Option | Behavior |
|---|---|
| `-DryRun` | Print what would be removed. |
| `-IncludeVenv` | Also remove `.venv`. |
| `-IncludePublicData` | Also remove manually downloaded `data\public`. |
| `-Strict` | Fail instead of skipping locked files. |

## Main CLI Commands

Run `uv run fraud-v2 --help` for the generated Typer help. The high-use commands
are grouped here.

| Area | Commands |
|---|---|
| Data | `generate`, `load`, `public-dataset`, `public-dataset-convert` |
| Decisions | `demo-reset`, `score`, `replay`, `monitor` |
| ML | `train`, `model-benchmark`, `model-register`, `model-list`, `model-promote`, `shadow-score`, `model-eval-dashboard` |
| Policy | `policy-show`, `policy-register`, `policy-list`, `policy-promote`, `policy-keygen`, `policy-approve`, `policy-approval-status`, `policy-promote-approved` |
| Streams | `outbox-drain`, `stream-consume`, `stream-supervise`, `stream-lag`, `stream-dead-letters`, `stream-health` |
| Review/compliance | `compliance-draft`, `evidence-export`, `retention-report`, `retention-prune` |
| Operations | `local-doctor`, `readiness-report`, `release-runbook`, `capacity-profile`, `load-benchmark`, `trace-report`, `audit-archive`, `sqlite-backup`, `sqlite-restore`, `secrets-scan` |
| LLM lab | `llm-stub`, `llm-generate` |

## Operational Recipes

Train and render a model eval dashboard:

```powershell
uv run fraud-v2 train `
  --events-path data\synthetic\tiny\events.jsonl `
  --output-dir data\models\baseline
uv run fraud-v2 model-eval-dashboard `
  --report-path data\models\baseline\baseline-report.json `
  --output-path data\models\eval-dashboard.html
```

Generate readiness artifacts:

```powershell
uv run fraud-v2 readiness-report `
  --output-path data\local\readiness-report.json `
  --dashboard-path data\local\readiness-report.html
```

Generate a release runbook:

```powershell
uv run fraud-v2 release-runbook --output-path data\local\release-runbook.md
```

Write and summarize local request traces:

```powershell
$env:FRAUD_TRACE_EXPORT_PATH="data\local\traces.jsonl"
uv run uvicorn fraud_v2.api.main:app --host 127.0.0.1 --port 8000
uv run fraud-v2 trace-report `
  --trace-path data\local\traces.jsonl `
  --output-path data\local\trace-report.json `
  --dashboard-path data\local\trace-report.html
```

Back up and restore SQLite:

```powershell
uv run fraud-v2 sqlite-backup `
  --db-path data\local\fraud_v2.sqlite `
  --output-dir data\local\backups\sqlite
uv run fraud-v2 sqlite-restore `
  data\local\backups\sqlite\fraud_v2.sqlite.bak `
  --restore-path data\local\fraud_v2-restored.sqlite
```

Rehearse Postgres backup and scratch restore while full mode is running:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\postgres-backup-rehearsal.ps1 `
  -ComposeProject fraud-v2 `
  -BackupDir data\local\postgres-backups
```

Export encrypted local evidence:

```powershell
$env:FRAUD_EVIDENCE_PASSPHRASE="replace-with-local-review-passphrase"
uv run fraud-v2 evidence-export <decision-id> `
  --db-path data\local\fraud_v2.sqlite `
  --output-path data\local\evidence\decision-evidence.enc.json
```

Convert a manually downloaded PaySim-style CSV:

```powershell
uv run fraud-v2 public-dataset paysim
uv run fraud-v2 public-dataset-convert paysim `
  data\public\raw\paysim.csv `
  --output-path data\public\converted\paysim-events.jsonl `
  --limit-rows 10000
```

Run a manual local simulation without touching the database:

```powershell
uv run fraud-v2 simulate-risk `
  --amount 1000 `
  --virtual-camera `
  --one-hop-from-fraud `
  --app-bec-pattern
```

Run GitHub handoff dry-run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\github-handoff.ps1
```

The `origin` remote is configured on the current branch and `gh auth status`
passes on this machine. Use `-Execute` when you want the script to push and
create or update the PR.

## Environment Variables

| Name | Needed For | Notes |
|---|---|---|
| `FRAUD_ENV` | Local app | Defaults to local behavior. |
| `FRAUD_STORE_BACKEND` | Storage mode | `sqlite` or `postgres`; Docker full sets `postgres`. |
| `FRAUD_SQLITE_PATH` | SQLite | Optional override for lite DB path. |
| `FRAUD_POSTGRES_DSN` | Postgres | Required when using Postgres store. |
| `FRAUD_API_TOKEN` | Local bearer auth | Do not commit real secrets. |
| `FRAUD_API_TOKENS` | Local role auth | Comma-separated `role:token` pairs. |
| `FRAUD_AUTH_MODE` | Auth mode | `token` or `jwt`. |
| `FRAUD_JWT_SECRET` | HS JWT mode | 32+ byte local secret. |
| `FRAUD_JWT_JWKS_PATH` | Offline JWKS | Local asymmetric JWT verification. |
| `FRAUD_JWT_JWKS_URL` | Remote JWKS | Direct JWKS endpoint. |
| `FRAUD_JWT_OIDC_DISCOVERY_URL` | OIDC-shaped local testing | Discovery document with `jwks_uri`. |
| `FRAUD_POLICY_PATH` | Threshold policy | Optional active policy JSON. |
| `FRAUD_TRACE_EXPORT_PATH` | Local traces | Writes JSONL request spans. |
| `FRAUD_EVIDENCE_PASSPHRASE` | Evidence export | Required to encrypt evidence bundle. |
| `OPENAI_API_KEY` / Azure equivalents | LLM synthetic lab | Only for `llm-generate --provider openai` or `azure`. |

## Repo Layout

```text
fraud-v2/
  README.md
  AGENTS.md
  startup/PROMPT.md
  pyproject.toml
  uv.lock
  src/fraud_v2/
    api/
    cli/
    compliance/
    config/
    connectors/
    converters/
    decision/
    domain/
    evaluation/
    features/
    graph/
    infrastructure/
    llm_lab/
    models/
    observability/
    operations/
    policy/
    public_data/
    replay/
    review/
    rules/
    security/
    storage/
    synthetic/
    workers/
  tests/
    integration/
    unit/
  infra/
    docker-compose.yml
    prometheus.yml
    prometheus-alerts.yml
    grafana/
  scripts/
    verify.ps1
    clean-local.ps1
    full-smoke.ps1
    github-handoff.ps1
    local-stream-service.ps1
    postgres-backup-rehearsal.ps1
  docs/
  factory/
    dashboard.md
    README.md
    archive/
```

## Code Rules

- No real PII.
- No real vendor, banking, liveness, consortium, SAR, payment, or filing calls.
- No committed secrets.
- Routes delegate business logic to services.
- Converters are explicit and tested.
- Decisions include trace ID, policy version, model/feature versions, score,
  tier, action, and safe reasons.
- LLMs generate scenarios and fixtures only; they do not make final decisions.
- GPU must stay optional.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| `local-doctor` blocks GitHub handoff | No `origin` or no `gh auth login`. | Configure remote/auth, then rerun `scripts\github-handoff.ps1`. |
| Docker ports are busy | Another local stack is running. | Stop it or pass full-smoke port parameters such as `-ApiPort 18001`. |
| SQLite cleanup skips a file | A local API process is holding the DB. | Stop `uvicorn`, then rerun `scripts\clean-local.ps1`. |
| GPU install fails | Optional GPU dependencies are heavy for 4GB VRAM. | Use CPU/default install. |
| API returns degraded decisions | Missing model/graph/feature dependency or stale features. | Check `/health/ready`, metrics, graph evidence, stream health, and logs. |
| Public data command has no file | Public datasets are never auto-downloaded. | Manually download allowed data into ignored `data\public\raw`. |

## Definition Of Done

- `powershell -ExecutionPolicy Bypass -File scripts\verify.ps1` passes.
- Docker changes also pass `powershell -ExecutionPolicy Bypass -File scripts\verify.ps1 -Full`.
- Generated local artifacts are cleaned or intentionally ignored.
- No real PII or secrets are introduced.
- Production claims remain explicitly blocked until legal/vendor/data/deploy
  decisions are made.
