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
rules/graph scoring, and baseline model training. Full local infrastructure
runs the API against Postgres with Redis, Redpanda, Neo4j, Prometheus, and a
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
| Redpanda | 19092 | Kafka-compatible event bus. |
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
| `FRAUD_STORE_BACKEND` | no | `sqlite` or `postgres` | Lite mode defaults to SQLite. Docker full mode sets Postgres. |
| `FRAUD_POSTGRES_DSN` | only for Postgres | `postgresql://fraud:fraud@localhost:5432/fraud_v2` | App-state Postgres DSN. |
| `FRAUD_POLICY_PATH` | no | `data\policies\strict.json` | Optional local threshold policy JSON. Defaults to the built-in local policy. |
| `FRAUD_API_TOKEN` | yes | `dev-token-change-me` | Local only. Do not commit real secrets. |
| `FRAUD_AUTH_MODE` | no | `token` or `jwt` | `token` keeps the default local path. `jwt` validates local HS256 JWTs. |
| `FRAUD_JWT_SECRET` | only for JWT | 32+ byte local secret | Required when `FRAUD_AUTH_MODE=jwt`. Do not commit it. |
| `FRAUD_JWT_ISSUER` | no | `fraud-v2-local` | Expected JWT issuer. |
| `FRAUD_JWT_AUDIENCE` | no | `fraud-v2-api` | Expected JWT audience. |
| `FRAUD_JWT_ALGORITHMS` | no | `HS256` or `RS256` | Allowed JWT algorithms. JWKS mode must use asymmetric algorithms. |
| `FRAUD_JWT_JWKS_PATH` | no | `C:\path\to\jwks.json` | Local JWKS file for offline asymmetric token verification. |
| `FRAUD_JWT_JWKS_URL` | no | `https://issuer.example/.well-known/jwks.json` | Direct JWKS endpoint. |
| `FRAUD_JWT_OIDC_DISCOVERY_URL` | no | `https://issuer.example/.well-known/openid-configuration` | OIDC discovery document with `jwks_uri`. |
| `FRAUD_TRACE_EXPORT_PATH` | no | `data\local\traces.jsonl` | Optional local JSONL request-span export path. |
| `DATABASE_URL` | yes | `postgresql+psycopg://fraud:fraud@localhost:5432/fraud_v2` | App database. |
| `REDIS_URL` | yes | `redis://localhost:6379/0` | Online feature store. |
| `REDPANDA_BOOTSTRAP_SERVERS` | yes | `localhost:19092` | Event bus. |
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
| `lite` | Fast contract, rules, and synthetic-data work. | `uv run uvicorn fraud_v2.api.main:app --host 127.0.0.1 --port 8000` |
| `full` | Production-shaped local demo with event bus, graph, and observability. | `docker compose -f infra\docker-compose.yml --profile full up -d` |
| `ml` | Offline training and evaluation. | `uv run fraud-v2 train --events-path data\synthetic\tiny\events.jsonl --output-dir data\models\baseline` |

Command:

```powershell
docker compose -f infra\docker-compose.yml --profile full up -d
```

Full-profile smoke with cleanup:

```powershell
.\scripts\full-smoke.ps1
```

The smoke uses a separate Docker Compose project, `fraud-v2-smoke`, and high
host ports by default so it does not collide with a local dev API on `8000`: API
`18000`, Grafana `13000`, Prometheus `19090`, and Neo4j HTTP `17474`. Override
with parameters such as `-ApiPort 18001` if needed. It resets only that isolated
smoke project, then verifies Postgres-backed API state, review decisions,
Postgres, Redis, Neo4j, Redpanda publish, and Redpanda consume-to-Postgres from
inside the API container, then writes a local stream health report before the
invalid-record DLQ smoke.

Keep services running for manual inspection:

```powershell
.\scripts\full-smoke.ps1 -KeepRunning
```

Expected services:

```powershell
docker compose -f infra\docker-compose.yml --profile full ps
```

## Initialize Local State

Commands:

```powershell
New-Item -ItemType Directory -Force data\synthetic\tiny, data\local
uv run fraud-v2 generate --users 120 --output data\synthetic\tiny\events.jsonl
uv run fraud-v2 load data\synthetic\tiny\events.jsonl --db-path data\local\fraud_v2.sqlite
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
uv run fraud-v2 load-benchmark --users 1000 --score-users 50 --overwrite
uv run fraud-v2 llm-generate --provider offline
uv run fraud-v2 outbox-drain --db-path data\local\fraud_v2.sqlite --dry-run
uv run fraud-v2 stream-consume --bootstrap-servers localhost:19092 --topic fraud.events --max-messages 10
uv run fraud-v2 stream-supervise --bootstrap-servers localhost:19092 --topic fraud.events --group-id fraud-v2-local --max-batches 3 --batch-size 100 --output-path data\local\stream-supervisor.json
uv run fraud-v2 stream-consume --bootstrap-servers localhost:19092 --topic fraud.events --max-messages 10 --publish-dead-letters --dead-letter-topic fraud.dead_letters --allow-errors
uv run fraud-v2 stream-lag --bootstrap-servers localhost:19092 --topic fraud.events --group-id fraud-v2-local --output-path data\local\stream-lag.json
uv run fraud-v2 stream-dead-letters --db-path data\local\fraud_v2.sqlite
uv run fraud-v2 stream-health --db-path data\local\fraud_v2.sqlite --lag-report-path data\local\stream-lag.json --supervision-report-path data\local\stream-supervisor.json --allow-critical
powershell -ExecutionPolicy Bypass -File scripts\local-stream-service.ps1 -Once -DryRun
powershell -ExecutionPolicy Bypass -File scripts\local-stream-service.ps1 -Once -CheckLag -AllowCritical
uv run fraud-v2 trace-report --trace-path data\local\traces.jsonl --output-path data\local\trace-report.json --dashboard-path data\local\trace-report.html
uv run fraud-v2 secrets-scan --root .
uv run fraud-v2 compliance-draft <decision-id> --db-path data\local\fraud_v2.sqlite
$env:FRAUD_EVIDENCE_PASSPHRASE="replace-with-local-review-passphrase"
uv run fraud-v2 evidence-export <decision-id> --db-path data\local\fraud_v2.sqlite --output-path data\local\evidence\decision-evidence.enc.json
uv run fraud-v2 retention-report --db-path data\local\fraud_v2.sqlite
uv run fraud-v2 retention-prune --db-path data\local\fraud_v2.sqlite
uv run fraud-v2 retention-prune --db-path data\local\fraud_v2.sqlite --execute
uv run fraud-v2 policy-show
uv run fraud-v2 policy-register data\policies\strict.json --status candidate
uv run fraud-v2 policy-keygen --private-key-path data\policies\alice-policy.pem --public-key-path data\policies\alice-policy.pub.pem
uv run fraud-v2 policy-approve strict-policy-test --approver-id alice --private-key-path data\policies\alice-policy.pem
uv run fraud-v2 policy-approval-status strict-policy-test
uv run fraud-v2 policy-promote strict-policy-test
uv run fraud-v2 policy-promote-approved strict-policy-test --required-approvals 2
uv run fraud-v2 model-register --status shadow
uv run fraud-v2 model-promote baseline-20260505-001
uv run fraud-v2 shadow-score --status active
uv run fraud-v2 model-eval-dashboard --report-path data\models\baseline\baseline-report.json --output-path data\models\eval-dashboard.html
uv run fraud-v2 public-dataset paysim
uv run fraud-v2 public-dataset-convert paysim data\public\raw\paysim.csv --output-path data\public\converted\paysim-events.jsonl --limit-rows 10000
```

Local URLs after implementation:

- API docs: `http://localhost:8000/docs`
- Analyst dashboard: `http://localhost:8000/dashboard`
- Graph evidence: `http://localhost:8000/dashboard/graph?entity_id=user_00000`
- Grafana: `http://localhost:3000`
- Grafana Fraud V2 overview: `http://localhost:3000/d/fraud-v2-overview/fraud-v2-overview`
- Redpanda Console: `http://localhost:8080`
- Neo4j Browser: `http://localhost:7474`

All API responses include `X-Trace-ID`. Send `X-Request-ID` to pin a local trace
ID while debugging.

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

JWT/OIDC-shaped local auth:

```powershell
$env:FRAUD_AUTH_MODE="jwt"
$env:FRAUD_JWT_SECRET="replace-with-local-only-secret-32b-min"
uv run fraud-v2 auth-token --secret $env:FRAUD_JWT_SECRET --subject local-admin
```

Use the printed token as `Authorization: Bearer <token>`. JWT mode validates
issuer, audience, expiry, subject, and role claims. It is an offline local
boundary for production-shaped development, not a real external identity
provider.

JWKS/OIDC-shaped JWT verification:

```powershell
$env:FRAUD_AUTH_MODE="jwt"
$env:FRAUD_JWT_ALGORITHMS="RS256"
$env:FRAUD_JWT_JWKS_PATH="C:\path\to\jwks.json"
```

Use `FRAUD_JWT_JWKS_URL` for a direct JWKS endpoint or
`FRAUD_JWT_OIDC_DISCOVERY_URL` for OIDC discovery. Do not allow HS algorithms in
JWKS mode; the API fails closed if HS is configured with JWKS.

Admin-only audit checks:

```powershell
Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer dev-token-change-me" } `
  -Uri http://127.0.0.1:8000/v1/audit/verify
```

The local audit log is hash-chained in SQLite. It detects local tampering but is
not production WORM storage.

Dry-run retention report:

```powershell
uv run fraud-v2 retention-report --db-path data\local\fraud_v2.sqlite
```

The retention report counts expired local records by table. It does not delete
data.

Explicit local retention prune:

```powershell
uv run fraud-v2 retention-prune --db-path data\local\fraud_v2.sqlite
uv run fraud-v2 retention-prune --db-path data\local\fraud_v2.sqlite --execute
```

The prune command defaults to dry-run. `--execute` deletes expired events,
decisions, review records, outbox messages, and stream dead letters. It
preserves audit entries so hash-chain verification remains valid.

Bounded stream consume from local Redpanda:

```powershell
uv run fraud-v2 stream-consume `
  --bootstrap-servers localhost:19092 `
  --topic fraud.events `
  --group-id fraud-v2-local `
  --store-backend sqlite `
  --db-path data\local\fraud_v2.sqlite `
  --max-messages 10
```

The stream consumer uses at-least-once semantics with idempotency keys. Exact
duplicates are committed as safe no-ops. Invalid messages, empty payloads,
stream message errors, and idempotency-key payload conflicts are written to a
local dead-letter table before the worker commits the offset.

Supervised local stream consume:

```powershell
uv run fraud-v2 stream-supervise `
  --bootstrap-servers localhost:19092 `
  --topic fraud.events `
  --group-id fraud-v2-local `
  --store-backend sqlite `
  --db-path data\local\fraud_v2.sqlite `
  --max-batches 3 `
  --batch-size 100 `
  --max-empty-polls 3 `
  --restart-backoff-seconds 5 `
  --output-path data\local\stream-supervisor.json
```

The supervisor repeatedly runs bounded consume batches, reports aggregate
ingest/dead-letter counts, counts idle batches, and backs off after transient
consumer creation/runtime failures. It is still a local CLI, not a Windows
service, Kubernetes deployment, or managed stream platform.

Inspect stream dead letters:

```powershell
uv run fraud-v2 stream-dead-letters --db-path data\local\fraud_v2.sqlite
```

Dead letters store safe error text, payload hash, and a short payload preview
for synthetic/local debugging. Do not use this repo with real PII.

Optionally also publish stream dead letters to Redpanda:

```powershell
uv run fraud-v2 stream-consume `
  --bootstrap-servers localhost:19092 `
  --topic fraud.events `
  --max-messages 10 `
  --publish-dead-letters `
  --dead-letter-topic fraud.dead_letters `
  --allow-errors
```

When DLQ publishing is enabled, the worker commits the bad input only after the
dead letter is saved locally and published to the DLQ topic. If DLQ publishing
fails, the worker records `dead_letter_publish_failed` and does not commit the
source offset.

Inspect stream lag for a consumer group:

```powershell
uv run fraud-v2 stream-lag `
  --bootstrap-servers localhost:19092 `
  --topic fraud.events `
  --group-id fraud-v2-local `
  --output-path data\local\stream-lag.json
```

The report includes low/high watermarks, committed offsets, per-partition lag,
and total lag. If a group has no committed offset yet, lag is reported as
unknown for that partition instead of inventing precision.

Write a local stream health report and dashboard:

```powershell
uv run fraud-v2 stream-health `
  --db-path data\local\fraud_v2.sqlite `
  --lag-report-path data\local\stream-lag.json `
  --supervision-report-path data\local\stream-supervisor.json `
  --output-path data\local\stream-health-report.json `
  --dashboard-path data\local\stream-health-dashboard.html `
  --allow-critical
```

The health report combines lag, recent supervisor counts, and stored stream dead
letters into a simple `healthy`, `degraded`, or `critical` status. By default it
does not require Redpanda; pass `--live-lag` to query Redpanda directly. This is
a local operator artifact, not Alertmanager, PagerDuty, or managed stream
monitoring.

Run the local Windows stream service loop once:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\local-stream-service.ps1 `
  -Once `
  -CheckLag `
  -AllowCritical
```

Dry-run the exact commands without touching Redpanda:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\local-stream-service.ps1 `
  -Once `
  -DryRun
```

The script writes timestamped supervisor, lag, stream-health JSON, and
stream-health HTML artifacts under `data\local\stream-service\`. It is intended
for local laptop supervision and can be wrapped by Windows Task Scheduler. It is
not installed automatically.

Optional Task Scheduler wrapper:

```powershell
$repo = "C:\Users\wbrya\OneDrive\Documents\GitHub\fraud-v2"
$script = Join-Path $repo "scripts\local-stream-service.ps1"
$args = "-ExecutionPolicy Bypass -File `"$script`" -Once -CheckLag -AllowCritical"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $args -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
  -RepetitionInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask `
  -TaskName "fraud-v2-local-stream-supervisor" `
  -Action $action `
  -Trigger $trigger `
  -Description "Local fraud-v2 stream supervisor and stream-health artifact writer"
```

This scheduled task assumes the full local Docker profile is running. Delete it
with:

```powershell
Unregister-ScheduledTask -TaskName fraud-v2-local-stream-supervisor -Confirm:$false
```

Show the active default threshold policy:

```powershell
uv run fraud-v2 policy-show
```

Use a local threshold policy JSON for CLI scoring:

```powershell
uv run fraud-v2 score user_00049 `
  --db-path data\local\fraud_v2.sqlite `
  --policy-path data\policies\strict.json
```

For the API, set `FRAUD_POLICY_PATH` before starting Uvicorn. Policy packs
validate green/yellow/red ordering, degraded-score floor, high-amount threshold,
severity, safe reason, and version. They do not replace legal approval or a
production policy promotion workflow.

Local policy registry flow:

```powershell
uv run fraud-v2 policy-register data\policies\strict.json --status candidate
uv run fraud-v2 policy-list
uv run fraud-v2 policy-promote strict-policy-test `
  --active-policy-path data\policies\active-threshold-policy.json
$env:FRAUD_POLICY_PATH="data\policies\active-threshold-policy.json"
```

Promotion keeps one local active policy in `data\policies\registry.json` and
writes the active policy JSON file that the API can load. This is a local
governance rail, not a substitute for maker-checker approval, signatures, or
legal policy review.

Local signed policy approval flow:

```powershell
uv run fraud-v2 policy-keygen `
  --private-key-path data\policies\alice-policy.pem `
  --public-key-path data\policies\alice-policy.pub.pem
uv run fraud-v2 policy-keygen `
  --private-key-path data\policies\bob-policy.pem `
  --public-key-path data\policies\bob-policy.pub.pem
uv run fraud-v2 policy-approve strict-policy-test `
  --approver-id alice `
  --approver-role risk `
  --private-key-path data\policies\alice-policy.pem `
  --notes "local risk approval"
uv run fraud-v2 policy-approve strict-policy-test `
  --approver-id bob `
  --approver-role compliance `
  --private-key-path data\policies\bob-policy.pem `
  --notes "local compliance approval"
uv run fraud-v2 policy-approval-status strict-policy-test --required-approvals 2
uv run fraud-v2 policy-promote-approved strict-policy-test --required-approvals 2
```

Approvals are local Ed25519 signatures over policy version, policy SHA-256,
approver ID, approver role, approval timestamp, notes, and signature algorithm.
The approved-promotion path counts distinct verified approvers. It is still
local governance rehearsal, not a production legal approval system or external
KMS/HSM-backed signing process.

## Local Observability

The API emits:

- structured JSON request logs
- `X-Trace-ID` response headers
- optional local JSONL request spans when `FRAUD_TRACE_EXPORT_PATH` is set
- `fraud_http_requests_total`
- `fraud_http_request_latency_seconds`
- fraud decision and event counters

Prometheus loads local alert rules from `infra/prometheus-alerts.yml`:

- API unavailable
- decision p95 latency above 500ms
- HTTP 5xx responses

Check the current token:

```powershell
Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer dev-token-change-me" } `
  -Uri http://127.0.0.1:8000/v1/auth/whoami
```

Write and summarize local request spans:

```powershell
$env:FRAUD_TRACE_EXPORT_PATH="data\local\traces.jsonl"
uv run uvicorn fraud_v2.api.main:app --host 127.0.0.1 --port 8000
```

After sending API traffic:

```powershell
uv run fraud-v2 trace-report `
  --trace-path data\local\traces.jsonl `
  --output-path data\local\trace-report.json `
  --dashboard-path data\local\trace-report.html
```

The trace report summarizes request span counts, unique trace IDs, status codes,
and latency percentiles. It is local JSONL/HTML evidence, not a distributed
tracing backend.

## Local Load Benchmark

Run a deterministic synthetic throughput receipt:

```powershell
uv run fraud-v2 load-benchmark `
  --users 1000 `
  --score-users 50 `
  --db-path data\local\load-benchmark.sqlite `
  --output-path data\local\load-benchmark-report.json `
  --overwrite
```

The report records synthetic generation time, SQLite load throughput, decision
scoring throughput, risk-tier counts, and basic runtime platform details. It is
a local laptop receipt, not a production capacity plan. Increase `--users` and
`--score-users` when you want a heavier run; keep `--overwrite` explicit so the
benchmark does not silently mix old and new data.

## Secrets Hygiene

Run the local secrets scan before pushing or sharing logs:

```powershell
uv run fraud-v2 secrets-scan --root .
```

The scanner checks committed text files for real-looking OpenAI/Azure keys,
GitHub tokens, AWS access keys, private key material, and high-entropy
credential assignments. It skips generated local data and allows documented dev
placeholders such as `dev-token-change-me`. It does not replace a managed
secret scanner, DLP, or a vault.

## Public Dataset Conversion

Public datasets are not downloaded automatically. Download only datasets you are
allowed to use, keep them under ignored `data\public\raw\`, then convert them:

```powershell
uv run fraud-v2 public-dataset paysim
uv run fraud-v2 public-dataset-convert paysim `
  data\public\raw\paysim.csv `
  --output-path data\public\converted\paysim-events.jsonl `
  --limit-rows 10000
uv run fraud-v2 load data\public\converted\paysim-events.jsonl `
  --db-path data\local\paysim.sqlite
```

The PaySim converter expects columns such as `step`, `type`, `amount`,
`nameOrig`, `nameDest`, and `isFraud`. It hashes source account names into
stable local entity IDs and writes canonical payment, settlement, chargeback,
and label events. This is a public/synthetic benchmark path, not permission to
load real PII.

## Model Eval Dashboard

After training a baseline model, render a local HTML dashboard:

```powershell
uv run fraud-v2 train `
  --events-path data\synthetic\tiny\events.jsonl `
  --output-dir data\models\baseline
uv run fraud-v2 model-eval-dashboard `
  --report-path data\models\baseline\baseline-report.json `
  --output-path data\models\eval-dashboard.html
```

If shadow scores exist, include them:

```powershell
uv run fraud-v2 model-eval-dashboard `
  --report-path data\models\baseline\baseline-report.json `
  --shadow-scores-path data\models\shadow-scores.json `
  --output-path data\models\eval-dashboard.html
```

The dashboard is a static local artifact with training metrics, threshold
candidates, feature columns, and optional shadow-score flag rate. It does not
promote a model or change fraud decisions.

## Encrypted Local Evidence Export

After scoring a decision, export an encrypted human-review bundle:

```powershell
$env:FRAUD_EVIDENCE_PASSPHRASE="replace-with-local-review-passphrase"
uv run fraud-v2 evidence-export <decision-id> `
  --db-path data\local\fraud_v2.sqlite `
  --output-path data\local\evidence\decision-evidence.enc.json
```

The export uses AES-256-GCM with a Scrypt-derived key from
`FRAUD_EVIDENCE_PASSPHRASE`. The plaintext bundle is limited to the decision,
safe reasons, signals, feature values, policy/model versions, trace IDs, and
explicit no-filing metadata. This is local encrypted evidence handling, not a
regulatory filing or external KMS/HSM custody workflow.

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
| secrets | `uv run fraud-v2 secrets-scan --root .` | yes |
| typecheck | `uv run mypy src` | yes |
| tests | `uv run pytest -q` | yes |
| integration | `uv run pytest tests\integration -q` | yes before feature complete |
| replay | `uv run pytest tests\replay -q` | yes before model/policy changes |
| train/eval | `uv run fraud-v2 train --events-path data\synthetic\tiny\events.jsonl --output-dir data\models\baseline` | yes before model changes |

## Common Tasks

| Task | Command | Notes |
|---|---|---|
| Start infra | `docker compose -f infra\docker-compose.yml --profile full up -d` | Runs local dependencies. |
| Full-profile smoke | `.\scripts\full-smoke.ps1` | Builds and starts full profile, scores data through the API, checks dashboard/metrics/Grafana/Prometheus/Neo4j, then stops it. |
| Stop infra | `docker compose -f infra\docker-compose.yml --profile full down` | Does not delete volumes by default. |
| Reset local data | `docker compose -f infra\docker-compose.yml --profile full down -v` | Destructive. Requires explicit approval in Code Factory runs. |
| Seed synthetic data | `uv run fraud-v2 generate --users 120 --output data\synthetic\tiny\events.jsonl` | No real PII. |
| Start API | `uv run uvicorn fraud_v2.api.main:app --host 127.0.0.1 --port 8000` | API docs at `/docs`. |
| Open dashboard | `uv run uvicorn fraud_v2.api.main:app --host 127.0.0.1 --port 8000` | Dashboard at `/dashboard`. |
| Train baseline | `uv run fraud-v2 train --events-path data\synthetic\tiny\events.jsonl --output-dir data\models\baseline` | CPU default. |
| Evaluate model | `uv run fraud-v2 train --events-path data\synthetic\tiny\events.jsonl --output-dir data\models\baseline` | Writes metrics, cost, and threshold report. |
| Local load benchmark | `uv run fraud-v2 load-benchmark --users 1000 --score-users 50 --overwrite` | Writes a synthetic generation/load/scoring throughput receipt. |
| Drain local outbox | `uv run fraud-v2 outbox-drain --db-path data\local\fraud_v2.sqlite --dry-run` | Publishes through a dry-run publisher by default. |
| Consume Redpanda stream | `uv run fraud-v2 stream-consume --bootstrap-servers localhost:19092 --topic fraud.events --max-messages 10` | Bounded local consumer for canonical event envelopes. |
| Supervise Redpanda stream | `uv run fraud-v2 stream-supervise --bootstrap-servers localhost:19092 --topic fraud.events --group-id fraud-v2-local --max-batches 3 --batch-size 100 --output-path data\local\stream-supervisor.json` | Repeated bounded consumes with backoff, idle accounting, and failure accounting. |
| Consume with Redpanda DLQ | `uv run fraud-v2 stream-consume --bootstrap-servers localhost:19092 --topic fraud.events --publish-dead-letters --dead-letter-topic fraud.dead_letters --allow-errors` | Writes bad records to app-store dead letters and a Redpanda DLQ topic. |
| Inspect stream lag | `uv run fraud-v2 stream-lag --bootstrap-servers localhost:19092 --topic fraud.events --group-id fraud-v2-local --output-path data\local\stream-lag.json` | Reports partition watermarks, committed offsets, and total consumer lag. |
| Inspect stream dead letters | `uv run fraud-v2 stream-dead-letters --db-path data\local\fraud_v2.sqlite` | Shows invalid/conflicting stream records stored for admin inspection. |
| Stream health report | `uv run fraud-v2 stream-health --db-path data\local\fraud_v2.sqlite --lag-report-path data\local\stream-lag.json --output-path data\local\stream-health-report.json --dashboard-path data\local\stream-health-dashboard.html --allow-critical` | Writes JSON and static HTML health artifacts from lag, supervisor, and dead-letter signals. |
| Local stream service loop | `powershell -ExecutionPolicy Bypass -File scripts\local-stream-service.ps1 -Once -CheckLag -AllowCritical` | Runs supervised stream consume once and writes timestamped health artifacts for Windows Task Scheduler or manual loops. |
| Local trace report | `uv run fraud-v2 trace-report --trace-path data\local\traces.jsonl --output-path data\local\trace-report.json --dashboard-path data\local\trace-report.html` | Summarizes optional local request spans into JSON and HTML. |
| Secrets scan | `uv run fraud-v2 secrets-scan --root .` | Scans repo text files for real-looking credentials before commit or CI. |
| Export compliance draft | `uv run fraud-v2 compliance-draft <decision-id> --db-path data\local\fraud_v2.sqlite` | Writes a human-review-only local draft. |
| Export encrypted evidence | `uv run fraud-v2 evidence-export <decision-id> --db-path data\local\fraud_v2.sqlite` | Writes an AES-256-GCM encrypted local decision evidence bundle. |
| Retention report | `uv run fraud-v2 retention-report --db-path data\local\fraud_v2.sqlite` | Counts expired records without deleting them. |
| Retention prune | `uv run fraud-v2 retention-prune --db-path data\local\fraud_v2.sqlite --execute` | Deletes expired local non-audit records. |
| Register model | `uv run fraud-v2 model-register --status shadow` | Stores model/report hashes and metrics in `data\models\registry.json`. |
| Promote model | `uv run fraud-v2 model-promote baseline-20260505-001` | Marks one model active and demotes the previous active model to shadow. |
| Shadow score | `uv run fraud-v2 shadow-score --status active` | Scores registered model output without changing decisions. |
| Model eval dashboard | `uv run fraud-v2 model-eval-dashboard --report-path data\models\baseline\baseline-report.json --output-path data\models\eval-dashboard.html` | Writes a static local model review dashboard. |
| Describe public dataset | `uv run fraud-v2 public-dataset paysim` | Shows manual download and access notes. |
| Convert PaySim CSV | `uv run fraud-v2 public-dataset-convert paysim data\public\raw\paysim.csv --output-path data\public\converted\paysim-events.jsonl` | Converts a manually downloaded PaySim-style CSV into canonical events. |
| Show threshold policy | `uv run fraud-v2 policy-show` | Prints the built-in or file-backed threshold policy. |
| Register policy | `uv run fraud-v2 policy-register data\policies\strict.json --status candidate` | Hashes and records a threshold policy candidate. |
| Promote policy | `uv run fraud-v2 policy-promote strict-policy-test` | Marks one policy active and writes `data\policies\active-threshold-policy.json`. |
| Generate policy approval key | `uv run fraud-v2 policy-keygen --private-key-path data\policies\alice-policy.pem --public-key-path data\policies\alice-policy.pub.pem` | Creates a local Ed25519 keypair for signing policy approvals. Do not commit private keys. |
| Approve policy | `uv run fraud-v2 policy-approve strict-policy-test --approver-id alice --private-key-path data\policies\alice-policy.pem` | Writes a signed local approval record bound to the registered policy hash. |
| Check policy approvals | `uv run fraud-v2 policy-approval-status strict-policy-test --required-approvals 2` | Counts distinct verified approvers and reports whether the policy is approved. |
| Promote approved policy | `uv run fraud-v2 policy-promote-approved strict-policy-test --required-approvals 2` | Promotes only after enough verified approvals exist. |

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
