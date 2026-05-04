---
project: fraud-v2
owner: Bryan
created_at: 2026-05-05
status: current
---

# Production Readiness: Fraud V2

## Current Verdict

This repo is a production-shaped local fraud lab. It is not a regulated
production fraud system yet.

It now runs locally in two modes:

- Lite mode: Python, FastAPI, SQLite, synthetic data, rules, graph features,
  baseline ML, replay, monitoring, compliance drafts, model registry, shadow
  scoring, and analyst dashboard.
- Full mode: Docker Compose starts API, Postgres, Redis, Redpanda, Neo4j,
  Prometheus, and Grafana with Postgres as the primary app store, verified by
  `scripts/full-smoke.ps1`.

## Implemented

| Area | Status | Proof |
|---|---|---|
| Domain contracts | Done | Pydantic events, decisions, reviews, outbox, compliance drafts. |
| Synthetic data | Done | Deterministic local generator and JSONL loader. |
| Lite storage | Done | SQLite event store, decisions, review cases, and outbox. |
| API | Done | FastAPI routes, role-protected `/v1/*`, health, metrics, docs. |
| Rules/graph decisions | Done | Rules + NetworkX graph service, graph evidence dashboard, safe reasons, trace IDs. |
| Review workflow | Done | Manual-review decisions create cases and confirmed analyst outcomes append replayable label events. |
| Compliance drafts | Local-safe done | Draft export only; no filings, no legal claim. |
| Baseline ML | Done | sklearn random forest training report. |
| Cost evaluation | Done | Profit threshold and recall under 1 percent FPR. |
| Model registry | Done | JSON-backed artifact/report hashing and status controls. |
| Shadow scoring | Done | Registered model probabilities logged without changing decisions. |
| LLM synthetic lab | Local-safe done | Offline default plus OpenAI/Azure provider boundary. |
| Full Docker profile | Done | Full profile smoke passed locally with API app state on Postgres, review-decision submission, and adapter checks for Redis, Neo4j, and Redpanda. |
| Grafana observability | Local-safe done | Provisioned dashboard for decisions, latency, ingested events, and API target health. |
| Request tracing/logging | Local-safe done | `X-Trace-ID`, structured JSON request logs, HTTP metrics, and Prometheus alert rules. |
| Audit log | Local-safe done | SQLite hash chain for event, decision, review, and outbox actions. |
| Retention reporting | Local-safe done | Dry-run per-table retention report. No destructive pruning by default. |
| CI | Done | GitHub Actions for tests, Docker build, and API image smoke. |

## Still Fake Or Local-Only

| Area | Reality |
|---|---|
| KYC/device/consortium | Mock connectors only. No real vendors. |
| SAR/adverse action | Drafts only. No filing. No legal compliance claim. |
| Data | Synthetic only unless public datasets are manually downloaded. |
| Auth | Local role-token and JWT/OIDC-shaped auth modes exist. No external IdP, user lifecycle, or sessions. |
| Secrets | `.env` pattern only. No vault/KMS. |
| Audit immutability | Hash-chained SQLite only. No WORM/object-lock storage. |
| Retention enforcement | Report-only. No deletion jobs, legal holds, or archive tiers. |
| Persistence | SQLite remains the lite default; Docker full mode uses Postgres for app state. |
| Streaming | Redpanda publisher is smoke-tested; real stream worker topology is not complete. |
| Graph DB | Neo4j projector is smoke-tested; decision engine still uses NetworkX fallback. |
| Observability | Local metrics, dashboard, request logs, trace IDs, and Prometheus alerts exist; no distributed tracing backend yet. |
| Deployment | Local Docker only. No cloud/IaC/production deploy. |

## Hard Blockers To Real Production

| Blocker | Why It Matters | Next Practical Step |
|---|---|---|
| Real fraud domain and action authority | Rules/legal obligations change by product. | Choose first wedge: instant cash, ATO, card testing, ecommerce, crypto, or lending. |
| Real labels | ML quality is fake without verified fraud/legit outcomes. | Load public datasets or real redacted labels after governance. |
| Vendor/legal approval | KYC, liveness, sanctions, SAR, credit decisions need contracts and counsel. | Keep mock adapters until approved. |
| Data security | Real PII cannot live in this local repo casually. | Add external OIDC, encryption, audit retention, secrets manager, DLP rules. |
| Production deployment target | Architecture differs for VM, Kubernetes, managed cloud, or on-prem. | Pick target environment and SLOs. |
| GitHub auth | Push/PR cannot happen from this machine yet. | Run `gh auth login`, then push branch and create PR. |

## Commands That Passed

```powershell
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest -q
docker compose -f infra\docker-compose.yml --profile full config --quiet
docker build -t fraud-v2:local .
.\scripts\full-smoke.ps1 -TimeoutSeconds 240
```

## Current Branch

```text
feature/full-profile-adapters
```

## GitHub Blocker

`gh auth status` reports no logged-in GitHub host. No remote is configured.
Local commits are complete; push and PR creation require GitHub authentication.
