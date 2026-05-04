# Implement local fraud-v2 platform

## Summary

This PR turns the Fraud V2 plan into a runnable local fraud decision platform.

Implemented:

- Python/FastAPI local fraud API with token/JWT-protected `/v1/*` routes.
- Deterministic synthetic data generation and SQLite lite storage.
- Rules + graph decision engine with safe reasons and trace IDs.
- Manual review case creation.
- Analyst review decisions append canonical review and label events for replay
  and training.
- Submitted review decisions close review cases consistently in SQLite and
  Postgres list results.
- Transactional outbox and dry-run outbox worker.
- Mock KYC/device/consortium connector boundaries.
- Raw application/payment converters.
- Full-profile adapter boundaries for Postgres, Redis, Redpanda, and Neo4j.
- Docker full-profile API uses Postgres as primary app storage.
- Replay, monitoring, compliance draft, model registry, and shadow scoring CLIs.
- Local synthetic load benchmark CLI that writes generation/load/scoring
  performance receipts.
- Cost-weighted model threshold reporting.
- Analyst dashboard with recent decisions and open review queue.
- Graph evidence dashboard for local analyst review.
- Docker Compose full profile and `scripts/full-smoke.ps1`.
- Provisioned Grafana dashboard for full-profile observability.
- Local role-aware API authorization for admin, analyst, and system tokens.
- JWT/OIDC-shaped local auth mode with a token minting CLI for offline testing.
- JWKS/OIDC-shaped JWT verification for asymmetric tokens using local JWKS
  files, direct JWKS URLs, or discovery URLs.
- Request trace IDs, structured JSON request logs, HTTP metrics, and local
  Prometheus alert rules.
- Tamper-evident local audit log and admin audit verification endpoints.
- Dry-run local retention reporting plus explicit local retention pruning for
  expired events, decisions, reviews, and outbox records.
- Versioned threshold policy packs for green/yellow/red bands, degraded-mode
  floors, and high-amount signals.
- Local threshold policy registry for candidate/active promotion and active
  policy file export.
- Local Ed25519 signed policy approvals and approved-promotion CLI for
  maker-checker governance rehearsal.
- Full-profile Docker image installs infra extras and smoke-tests the Postgres
  event-store adapter.
- Full-profile smoke verifies Redis feature cache, Neo4j graph projector, and
  Redpanda publisher and consumer adapters.
- Bounded Redpanda stream consumer CLI ingests canonical event envelopes into
  SQLite/Postgres with idempotent duplicate handling.
- Local Redpanda stream supervisor CLI runs repeated bounded consume batches
  with backoff, idle accounting, and failure accounting.
- Persistent stream dead letters capture invalid/conflicting Redpanda records
  for admin inspection and retention pruning.
- Optional Redpanda DLQ topic publishing for stream dead letters, with full
  smoke proof.
- Redpanda consumer-group lag CLI with partition-level lag reporting and full
  smoke zero-lag proof.
- GitHub Actions test, Docker build, and API image smoke workflow.

## Test Plan

```powershell
uv sync --extra dev --extra infra --extra llm
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest -q
docker compose -f infra\docker-compose.yml --profile full config --quiet
docker build -t fraud-v2:local .
.\scripts\full-smoke.ps1 -TimeoutSeconds 240
```

Latest local result:

- Ruff format/check: pass
- Mypy: pass
- Pytest: pass, 83 collected tests
- Docker build: pass
- Full profile smoke: pass, including API scoring, review-decision submission,
  retention prune dry-run/execute, dashboard, metrics, Grafana, Prometheus
  scrape, Postgres insert/list, Redis feature cache, Neo4j projection, and
  Redpanda publish-consume-to-Postgres with zero stream dead letters on the
  valid path, zero lag after valid consume, supervised stream ingest, plus
  invalid-record DLQ topic proof

## Known Limits

- Synthetic data only.
- Mock vendors only.
- Compliance drafts only; no filings.
- Local bearer-token/JWT auth only; no external user lifecycle or sessions yet.
- Stream supervisor is local CLI only; no OS service manager, DLQ alerting, or
  lag dashboard yet.
- Stream dead letters persist safe local diagnostics, not production PII-safe
  evidence storage.
- Policy packs, promotion registry, and signed approvals are local files only;
  no external KMS/HSM, legal approval workflow, or production policy registry
  yet.
- No real production deployment target yet.
- GitHub push/PR creation is blocked locally until `gh auth login` succeeds
  and a remote is configured.
