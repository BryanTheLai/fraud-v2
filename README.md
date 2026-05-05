# fraud-v2

Local-first fraud decision lab built from the BryansLab Fraud Detection V2 idea.

It is a runnable Python/FastAPI system for synthetic fraud data, event loading,
rules and graph scoring, baseline ML, analyst review, safe compliance drafts,
stream ingestion, observability, backup rehearsal, and local readiness proof.

It is not a regulated production fraud system. It uses synthetic/public data by
default, mock vendor boundaries, local-only auth, and no real filings or real
money movement.

## Current Shape

| Mode | What Runs | Use It For |
|---|---|---|
| Lite | Python, FastAPI, SQLite, NetworkX, synthetic data | Fast laptop development and tests. |
| Full | Docker API, Postgres, Redis, Redpanda, Neo4j, Prometheus, Grafana | Production-shaped local smoke proof. |
| ML | Local sklearn training/eval artifacts | Baseline model and threshold experiments. |

Latest verified version: `0.49.0`.

## System Map

```text
synthetic/public data
        |
        v
  canonical events ---> SQLite lite store --------+
        |                                         |
        +------------> Postgres full store -------+--> rules + features
        |                                         |        |
        +------------> outbox / Redpanda ---------+        v
        |                                             decision engine
        v                                                   |
 mock connectors, converters, graph signals                 v
        |                                             safe reasons
        v                                                   |
 NetworkX lite / Neo4j full                                 v
                                                     analyst review
                                                           |
                                                           v
       audit hash chain, retention, evidence export, reports, readiness
```

Every decision is expected to expose a trace ID, policy version, feature-set
version, score, risk tier, action, and compliance-safe reasons.

## Fast Start

From PowerShell:

```powershell
cd C:\Users\wbrya\OneDrive\Documents\GitHub\fraud-v2
uv sync --extra dev
uv run fraud-v2 local-doctor `
  --output-path data\local\local-doctor.json `
  --dashboard-path data\local\local-doctor.html
```

Reset the local demo database, train the baseline, score one user:

```powershell
uv run fraud-v2 demo-reset --users 120 --db-path data\local\fraud_v2.sqlite
uv run fraud-v2 train --events-path data\synthetic\tiny\events.jsonl --output-dir data\models\baseline
uv run fraud-v2 mlops-report --events-path data\synthetic\tiny\events.jsonl --output-path data\local\mlops-report.json
uv run fraud-v2 score user_00000 --db-path data\local\fraud_v2.sqlite
```

Start the API:

```powershell
uv run uvicorn fraud_v2.api.main:app --host 127.0.0.1 --port 8000
```

Open:

- Demo cockpit: `http://127.0.0.1:8000/demo`
- Analyst dashboard: `http://127.0.0.1:8000/dashboard`
- Graph evidence: `http://127.0.0.1:8000/dashboard/graph?entity_id=user_00000`
- Human ops metrics: `http://127.0.0.1:8000/dashboard/ops`
- ML dashboard: `http://127.0.0.1:8000/dashboard/ml`
- Signal lab: `http://127.0.0.1:8000/dashboard/signals`
- API docs: `http://127.0.0.1:8000/docs`
- Raw Prometheus metrics: `http://127.0.0.1:8000/metrics`

Protected `/v1/*` calls use local bearer auth:

```text
Authorization: Bearer dev-token-change-me
```

Override with `FRAUD_API_TOKEN` or comma-separated role tokens in
`FRAUD_API_TOKENS`, for example
`admin:local-admin-token,analyst:local-analyst-token,system:local-system-token`.

## Verify And Clean

Use the single local gate:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify.ps1
```

Use the full gate when Docker is available:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify.ps1 -Full
```

Clean ignored caches and generated smoke artifacts:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\clean-local.ps1
```

`clean-local.ps1` keeps `.venv` and `data\public` by default.

## Full Local Profile

Start the production-shaped local stack:

```powershell
docker compose -f infra\docker-compose.yml --profile full up -d
docker compose -f infra\docker-compose.yml --profile full ps
```

Services:

| Service | Default URL/Port |
|---|---|
| API | `http://127.0.0.1:8000` |
| Postgres | `localhost:5432` |
| Redis | `localhost:6379` |
| Redpanda | `localhost:19092` |
| Neo4j | `http://127.0.0.1:7474` |
| Prometheus | `http://127.0.0.1:9090` |
| Grafana | `http://127.0.0.1:3000/d/fraud-v2-overview/fraud-v2-overview` |

Run the isolated full smoke:

```powershell
.\scripts\full-smoke.ps1
```

The smoke uses a separate Compose project and high host ports so it does not
disturb a normal dev server on port `8000`.

## Codebase Map

```text
src/fraud_v2/
  api/             FastAPI app, auth boundaries, dashboards, health, metrics.
  cli/             `fraud-v2` Typer commands.
  domain/          Pydantic events, decisions, reviews, enums, safe contracts.
  synthetic/       Deterministic synthetic event generator.
  public_data/     PaySim-style public CSV descriptor and converter.
  storage/         SQLite and Postgres stores.
  decision/        Decision orchestration and traceable outcomes.
  rules/           Rule scoring and reason codes.
  features/        Local feature assembly.
  graph/           NetworkX lite graph and Neo4j adapter paths.
  models/          sklearn baseline training, registry, shadow scoring.
  evaluation/      Monitoring, PSI drift, analyst Kappa, capacity receipts.
  policy/          Threshold policy packs, registry, signed approvals.
  review/          Analyst review and replayable label events.
  compliance/      Human-review-only compliance drafts and intervention previews.
  connectors/      Mock KYC/device/consortium plus local signal-lab checks.
  converters/      Raw payload to canonical event converters.
  workers/         Outbox and Redpanda stream workers.
  observability/   Metrics, request logs, trace artifact support.
  operations/      Doctor, readiness, runbook, backup/archive/capacity reports.
  security/        Local secrets scan and auth helpers.
```

```text
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

factory/
  dashboard.md
  README.md
  archive/code-factory-receipts-20260504-20260505.zip
```

The Code Factory receipt archive is lossless. Restore it with:

```powershell
Expand-Archive -LiteralPath factory\archive\code-factory-receipts-20260504-20260505.zip -DestinationPath factory -Force
```

## Main Commands

| Job | Command |
|---|---|
| Reset seeded local demo | `uv run fraud-v2 demo-reset --users 120 --db-path data\local\fraud_v2.sqlite` |
| Generate synthetic events | `uv run fraud-v2 generate --users 120 --output data\synthetic\tiny\events.jsonl` |
| Load events | `uv run fraud-v2 load data\synthetic\tiny\events.jsonl --db-path data\local\fraud_v2.sqlite` |
| Score one user | `uv run fraud-v2 score user_00000 --db-path data\local\fraud_v2.sqlite` |
| Train baseline | `uv run fraud-v2 train --events-path data\synthetic\tiny\events.jsonl --output-dir data\models\baseline` |
| MLOps drift/Kappa report | `uv run fraud-v2 mlops-report --events-path data\synthetic\tiny\events.jsonl --output-path data\local\mlops-report.json` |
| Local signal lab CLI | `uv run fraud-v2 signal-lab` |
| Replay decisions | `uv run fraud-v2 replay --events-path data\synthetic\tiny\events.jsonl` |
| Capacity receipt | `uv run fraud-v2 capacity-profile --profile smoke --overwrite` |
| Readiness report | `uv run fraud-v2 readiness-report --output-path data\local\readiness-report.json --dashboard-path data\local\readiness-report.html` |
| Local doctor | `uv run fraud-v2 local-doctor --output-path data\local\local-doctor.json --dashboard-path data\local\local-doctor.html` |
| Release runbook | `uv run fraud-v2 release-runbook --output-path data\local\release-runbook.md` |
| Secrets scan | `uv run fraud-v2 secrets-scan --root .` |
| GitHub handoff | `powershell -ExecutionPolicy Bypass -File scripts\github-handoff.ps1` |

Run `uv run fraud-v2 --help` for the full CLI list.

## Safety Boundaries

- No real PII.
- No real KYC, banking, liveness, consortium, SAR, payment, or compliance calls.
- No real regulatory filings.
- LLMs can generate synthetic scenarios and edge cases, but they do not make
  final fraud decisions.
- GPU is optional. CPU-first workflows must stay runnable on the Windows laptop.

## Documentation

| Doc | Purpose |
|---|---|
| [docs/setup.md](docs/setup.md) | Exact install, run, verify, cleanup, and troubleshooting path. |
| [docs/production-readiness.md](docs/production-readiness.md) | Current implemented capabilities and hard production blockers. |
| [docs/plan-index.md](docs/plan-index.md) | Planning index and current-vs-target notes. |
| [docs/spec-plan.md](docs/spec-plan.md) | Original full target specification. |
| [docs/dependency-map.md](docs/dependency-map.md) | Current dependency and module map. |
| [docs/data-strategy.md](docs/data-strategy.md) | Synthetic/public data strategy and data definitions. |
| [docs/llm-synthetic-data-lab.md](docs/llm-synthetic-data-lab.md) | LLM-assisted synthetic data plan. |
| [docs/local-production-profile.md](docs/local-production-profile.md) | Laptop resource profile and run modes. |
| [docs/vagueness-register.md](docs/vagueness-register.md) | Open ambiguity and local defaults. |
| [docs/blockers-and-vague-decisions.md](docs/blockers-and-vague-decisions.md) | Blunt blockers, options, and recommendations. |
| [docs/solution-tradeoffs.md](docs/solution-tradeoffs.md) | Architecture tradeoffs and decisions. |
| [docs/presentation-cockpit-and-gap-plan.md](docs/presentation-cockpit-and-gap-plan.md) | Demo cockpit, metrics, graph, ML, vendor, and blog-gap implementation plan. |
| [factory/dashboard.md](factory/dashboard.md) | Current Code Factory dashboard. |

## Current Blockers

- GitHub push/PR needs `gh auth login` if this machine is not authenticated.
- Real production needs a chosen fraud wedge, verified labels, legal/vendor
  approval, PII security design, deployment target, SLOs, and incident process.
