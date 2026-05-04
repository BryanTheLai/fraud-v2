# Changelog

## 0.11.0 - 2026-05-05

- Added local role-aware API authorization with `admin`, `analyst`, and
  `system` roles.
- Added `FRAUD_API_TOKENS` support for role-specific local tokens while keeping
  the legacy `FRAUD_API_TOKEN` as an all-roles dev token.
- Added `/v1/auth/whoami` and tests proving role boundaries.

## 0.10.0 - 2026-05-05

- Added Grafana provisioning for the full local profile with a Fraud V2 overview
  dashboard backed by Prometheus.
- Expanded `scripts/full-smoke.ps1` to exercise synthetic generation, scoring,
  review queue creation, dashboard rendering, API metrics, Grafana, and
  Prometheus scraping.

## 0.9.0 - 2026-05-05

- Upgraded the local dashboard into a denser analyst cockpit with recent
  decisions and open review queue tables.

## 0.8.0 - 2026-05-05

- Added `scripts/full-smoke.ps1` to build, start, verify, and optionally keep
  the Docker full profile running locally.

## 0.7.0 - 2026-05-05

- Added shadow scoring for registered active or shadow models against local
  event streams.
- Added `fraud-v2 shadow-score` to write model probability, threshold,
  would-flag, and feature values without changing the rules/graph decision.

## 0.6.0 - 2026-05-05

- Added a JSON-backed local model registry with artifact/report hashes,
  feature columns, metrics, thresholds, notes, and deployment status.
- Added model register, list, and promote CLI commands.
- Added shadow/active controls so promoting one model demotes any prior active
  model back to shadow.

## 0.5.0 - 2026-05-05

- Hardened protected API endpoints so missing bearer tokens return `401`
  unless auth is explicitly disabled with an empty local token.
- Updated integration tests to prove both authorized and unauthorized paths.

## 0.4.0 - 2026-05-05

- Added human-review-only compliance draft JSON exports with safe reasons and
  explicit no-filing/no-legal-advice disclaimers.
- Added cost-weighted threshold candidates, profit estimates, and
  recall-under-1-percent-FPR reporting to baseline model training.
- Added CLI support for local compliance draft generation from stored decisions.

## 0.3.0 - 2026-05-05

- Added a SQLite-backed transactional outbox and dry-run outbox worker so local
  event ingestion has a replayable publish path.
- Added mock KYC, device-intelligence, and consortium connector boundaries that
  emit safe synthetic signals only.
- Added raw application/payment converters that reject malformed local payloads
  before they enter canonical event storage.
- Synced API/package version metadata with the release version.

## 0.2.0 - 2026-05-05

- Added full-profile adapter boundaries for Postgres, Redis, Redpanda, and
  Neo4j while keeping the default local path offline and laptop-safe.
- Added deterministic replay, monitoring reports, public dataset registry, and
  LLM scenario generation commands.
- Added the repo startup prompt, optional OpenAI/Azure structured-generation
  provider boundary, JSON CLI output, optional-extra CI install, and Docker
  compose/build checks.

## 0.1.0 - 2026-05-05

- Initialized `fraud-v2` as a local Python project.
- Added domain contracts, deterministic synthetic data, SQLite lite storage,
  graph/rules decisioning, baseline ML training, FastAPI endpoints, dashboard,
  tests, Docker Compose scaffolding, and CI workflow.
