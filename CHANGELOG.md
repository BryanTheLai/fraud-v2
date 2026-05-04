# Changelog

## 0.18.0 - 2026-05-05

- Added JWT/OIDC-shaped local auth mode with issuer, audience, expiry, subject,
  role-claim validation, and a 32+ byte local secret requirement.
- Added a local `fraud-v2 auth-token` helper for minting offline HS256 test
  tokens without requiring an external identity provider.

## 0.17.0 - 2026-05-05

- Added analyst feedback-loop events so confirmed manual review outcomes append
  canonical review and label events for replay and training.

## 0.16.0 - 2026-05-05

- Expanded the full-profile smoke to verify Redis, Neo4j, and Redpanda adapter
  boundaries inside the Docker network.
- Fixed Redpanda Compose advertised listeners so container clients and laptop
  clients use the correct bootstrap addresses.

## 0.15.0 - 2026-05-05

- Updated the Docker API image to install full-profile infrastructure extras.
- Expanded `scripts/full-smoke.ps1` to verify the Postgres event-store adapter
  inside the Docker network.

## 0.14.0 - 2026-05-05

- Added dry-run local retention reports with per-table expiry counts and
  configurable retention windows.
- Added admin-only retention report API and CLI support.
- Expanded tests and full-profile smoke to verify retention reporting.

## 0.13.0 - 2026-05-05

- Added a local tamper-evident audit log with hash-chained entries for event
  ingestion, decisions, review cases, review decisions, and outbox status
  changes.
- Added admin-only audit listing and hash-chain verification endpoints.
- Expanded full-profile smoke and tests to verify audit chain integrity.

## 0.12.0 - 2026-05-05

- Added request trace IDs with `X-Trace-ID` response headers and structured
  JSON request logs.
- Added HTTP request counters and latency histograms.
- Added local Prometheus alert rules for API availability, decision latency,
  and HTTP 5xx responses.

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
