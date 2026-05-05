# Implement local fraud-v2 platform

## Summary

This PR turns the Fraud V2 plan into a runnable local fraud decision platform.

Implemented:

- Python/FastAPI local fraud API with token/JWT-protected `/v1/*` routes.
- Deterministic synthetic data generation and SQLite lite storage.
- PaySim-style public dataset conversion into canonical event JSONL.
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
- Static local model eval dashboard generated from training reports and optional
  shadow scores.
- Encrypted local decision evidence export CLI for human-review bundles.
- Local synthetic load benchmark CLI that writes generation/load/scoring
  performance receipts.
- Local capacity-profile CLI that writes JSON/HTML synthetic capacity receipts
  with target checks.
- Cost-weighted model threshold reporting.
- Demo cockpit with seeded local scenarios, custom scoring controls, and reset.
- Analyst dashboard with recent decisions and open review queue.
- Primary case detail page with point-in-time timeline, features, graph, and
  simulated decision rail.
- Graph evidence dashboard for local analyst review.
- Human-readable ops dashboard for queue, outbox, DLQ, audit, freshness, and
  Prometheus/Grafana links.
- In-app ML dashboard for baseline model calibration, Recall at 1 percent FPR,
  profit threshold, and feature review.
- Benford-derived declared-income features for the Instant Cash fraud lane.
- Docker Compose full profile and `scripts/full-smoke.ps1`.
- Provisioned Grafana dashboard for full-profile observability.
- Local role-aware API authorization for admin, analyst, and system tokens.
- JWT/OIDC-shaped local auth mode with a token minting CLI for offline testing.
- JWKS/OIDC-shaped JWT verification for asymmetric tokens using local JWKS
  files, direct JWKS URLs, or discovery URLs.
- Request trace IDs, structured JSON request logs, HTTP metrics, and local
  Prometheus alert rules.
- Optional local JSONL request trace spans and `trace-report` JSON/HTML
  artifacts.
- Local and CI secrets scan for real-looking API keys, tokens, private keys,
  and credential assignments.
- Tamper-evident local audit log and admin audit verification endpoints.
- Local audit archive export with JSONL entries and manifest hash/chain proof.
- Local SQLite backup/restore commands with SHA-256 verification.
- Local full-profile Postgres backup rehearsal with `pg_dump`, scratch restore,
  event-count verification, and manifest hash.
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
  Redpanda publisher and consumer adapters, plus Postgres backup rehearsal.
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
- Local stream health report CLI writes JSON and HTML from lag, supervisor, and
  dead-letter signals.
- Windows local stream service runner wraps supervised consume, optional lag
  inspection, and stream health artifacts for Task Scheduler or manual loops.
- GitHub Actions test, Docker build, and API image smoke workflow.
- GitHub Actions capacity-profile smoke artifact upload.
- Dry-run-safe GitHub handoff script for push/PR creation once auth and remote
  exist.
- Generated release runbook CLI for local operator handoff.
- Generated readiness report CLI for local checks, capabilities, and production
  blockers.
- Generated local doctor CLI for laptop runability, Docker/full-profile checks,
  optional GPU visibility, and GitHub handoff blockers.
- Single-command verify and local cleanup scripts for lower-noise handoff.

## Test Plan

```powershell
uv sync --extra dev --extra infra --extra llm
uv run ruff format --check .
uv run ruff check .
uv run fraud-v2 secrets-scan --root .
uv run mypy src
uv run pytest -q
uv run pytest --collect-only -q
powershell -ExecutionPolicy Bypass -File scripts\verify.ps1
powershell -ExecutionPolicy Bypass -File scripts\github-handoff.ps1
uv run fraud-v2 release-runbook --output-path data\local\release-runbook.md
uv run fraud-v2 readiness-report --output-path data\local\readiness-report.json --dashboard-path data\local\readiness-report.html
uv run fraud-v2 local-doctor --output-path data\local\local-doctor.json --dashboard-path data\local\local-doctor.html
uv run fraud-v2 capacity-profile --profile smoke --users 50 --score-users 5 --min-load-events-per-second 0.1 --min-score-decisions-per-second 0.1 --output-dir data\local\ci-capacity --overwrite --fail-on-target-miss
docker compose -f infra\docker-compose.yml --profile full config --quiet
docker build -t fraud-v2:local .
.\scripts\full-smoke.ps1 -TimeoutSeconds 240
powershell -ExecutionPolicy Bypass -File scripts\clean-local.ps1
```

Latest local result:

- Ruff format/check: pass
- Mypy: pass, 91 source files checked
- Secrets scan: pass, 172 files scanned, zero findings
- Pytest: pass, 123 collected tests
- GitHub handoff dry run: pass, reports missing `origin` remote and missing
  `gh auth status` as blockers
- Verify script: pass for core and `-Full` modes
- Release runbook smoke: pass, wrote a 2,356-byte Markdown runbook
- Readiness report smoke: pass, wrote JSON/HTML, reported 8 checks, 20
  implemented capabilities, 7 production blockers, and blocked status from
  missing GitHub remote/auth
- Local doctor smoke: pass, wrote JSON/HTML, reported `lite_ready: true`,
  `full_profile_ready: true`, `github_handoff_ready: false`, 16 checks, 14
  pass, 2 blocked, RTX 3050 Laptop GPU visible, 13.9 GiB RAM detected, and
  41.3 GiB free disk
- Capacity profile smoke: pass, 50 users, 316 events, 116.811 load events/sec,
  62.168 score decisions/sec, JSON/HTML artifacts written
- Docker build: pass, installed `fraud-v2==0.48.0`
- Full profile smoke: pass, including API scoring, review-decision submission,
  retention prune dry-run/execute, dashboard, metrics, Grafana, Prometheus
  scrape, Postgres insert/list, Postgres backup rehearsal with source/restored
  event counts of 194/194 and `verified: true`, audit archive proof over 196
  entries, Redis
  feature cache, Neo4j projection, and
  Redpanda publish-consume-to-Postgres with zero stream dead letters on the
  valid path, zero lag after valid consume, supervised stream ingest, stream
  health report with `status: healthy` and `health_score: 100`, local trace
  report proof, secrets scan proof, plus invalid-record DLQ topic proof
- Clean local artifacts: pass, removed removable ignored caches and generated
  smoke artifacts while keeping `.venv` and `data\public`; one generated
  `data\local\fraud_v2.sqlite` file remained locked by Windows and was skipped

## Known Limits

- Synthetic data only.
- Public dataset conversion requires manual dataset download and terms review.
- Mock vendors only.
- Compliance drafts only; no filings.
- Local bearer-token/JWT auth only; no external user lifecycle or sessions yet.
- Stream supervisor, stream health reports, trace reports, and Windows service loop are local
  artifacts only; no automatically installed OS service, Alertmanager/PagerDuty
  path, or managed stream monitor yet.
- Stream dead letters persist safe local diagnostics, not production PII-safe
  evidence storage.
- Encrypted evidence exports are local passphrase-protected files, not external
  KMS/HSM-backed evidence custody.
- Policy packs, promotion registry, and signed approvals are local files only;
  no external KMS/HSM, legal approval workflow, or production policy registry
  yet.
- No real production deployment target yet.
- GitHub push/PR creation is blocked locally until `gh auth login` succeeds
  and a remote is configured. `scripts\github-handoff.ps1` reports the blocker
  and can execute the push/PR once configured.
