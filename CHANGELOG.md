# Changelog

## 0.48.0 - 2026-05-05

- Added the `/demo` cockpit with seeded scenario buttons, custom local scoring
  controls, and local demo reset.
- Added case-detail, human ops, and in-app ML dashboards for presentation-grade
  review of decisions, metrics, and model economics.
- Improved graph evidence rendering and added Benford-derived income features
  to the decision/model feature vector.

## 0.47.0 - 2026-05-05

- Added `scripts\verify.ps1` as the single local verification entry point for
  lint, formatting, secrets scan, typecheck, tests, local doctor, readiness,
  release runbook, capacity profile, and optional full Docker smoke.
- Added `scripts\clean-local.ps1` to remove ignored local caches and generated
  smoke artifacts with repo-bound path checks.
- Moved completed task cards out of the active factory lane and compacted the
  factory dashboard while keeping run records and receipts.

## 0.46.0 - 2026-05-05

- Added `fraud-v2 local-doctor` to generate JSON and HTML runability checks for
  Python, repo files, disk, RAM, uv, git, Docker, optional NVIDIA GPU visibility,
  and GitHub handoff blockers.
- Added scope-aware readiness booleans for lite mode, full-profile Docker mode,
  and GitHub handoff so laptop blockers are plain instead of buried in logs.
- Added unit coverage for local-doctor scope classification, Docker blocker
  handling, artifact writing, and HTML escaping.

## 0.45.0 - 2026-05-05

- Added `fraud-v2 readiness-report` to generate JSON and HTML local readiness
  snapshots with environment checks, implemented capabilities, and hard
  production blockers.
- Added unit coverage for readiness report generation, artifact writing, and
  HTML escaping.
- Updated docs, PR draft, and factory receipts for the readiness snapshot path.

## 0.44.0 - 2026-05-05

- Added `fraud-v2 release-runbook` to generate a local Markdown operator
  handoff with lite/full-mode commands, verification gates, recovery rehearsals,
  GitHub handoff steps, and hard limits.
- Added unit coverage for release-runbook rendering and file writing.
- Updated docs, PR draft, and factory receipts for the generated runbook path.

## 0.43.0 - 2026-05-05

- Added `scripts/github-handoff.ps1` to report GitHub push/PR blockers as JSON
  and execute `git push` plus `gh pr create` once a remote and GitHub auth exist.
- Added unit coverage for the handoff script's blocker reporting and execute
  guard.
- Updated the local docs and PR draft with the executable GitHub handoff path.

## 0.42.0 - 2026-05-05

- Added `scripts/postgres-backup-rehearsal.ps1` to create a local full-profile
  Postgres `pg_dump` artifact, restore it into a scratch database, compare event
  counts, and write a SHA-256 manifest.
- Expanded `scripts/full-smoke.ps1` to verify the Postgres backup rehearsal
  during Docker-backed smoke runs.
- Added unit coverage for the backup script and full-smoke wiring.

## 0.41.0 - 2026-05-05

- Added `fraud-v2 capacity-profile` to run named synthetic capacity receipts
  with local throughput targets.
- Added JSON and HTML capacity reports that link the benchmark database,
  benchmark report, checks, risk tiers, and safe non-production disclaimer.
- Added unit coverage for passing, warning, and profile override behavior.

## 0.40.0 - 2026-05-05

- Added `fraud-v2 sqlite-backup` to copy the lite-mode SQLite database and
  write a SHA-256 verified manifest.
- Added `fraud-v2 sqlite-restore` with explicit `--overwrite` protection for
  local restore rehearsal.
- Added backup/restore tests so the laptop persistence path has a repeatable
  recovery proof.

## 0.39.0 - 2026-05-05

- Added `fraud-v2 audit-archive` to export local audit entries as JSONL plus a
  manifest.
- Added manifest fields for archive SHA-256, root entry hash, sequence bounds,
  and audit-chain verification status.
- Expanded the full-profile smoke to prove Postgres-backed audit archive
  generation.

## 0.38.0 - 2026-05-05

- Added `fraud-v2 secrets-scan` to scan text files for real-looking API keys,
  tokens, private keys, and high-entropy credential assignments.
- Added safe placeholder allowlisting so local docs and Docker dev secrets do
  not create false positives.
- Added the secrets scan to GitHub Actions before typechecking and tests.

## 0.37.0 - 2026-05-05

- Added optional local JSONL trace export for API requests through
  `FRAUD_TRACE_EXPORT_PATH`.
- Added `fraud-v2 trace-report` to summarize local trace spans into JSON and
  static HTML artifacts.
- Enabled local trace export in the Docker full profile and expanded the full
  smoke to prove trace report generation.

## 0.36.0 - 2026-05-05

- Added `scripts/local-stream-service.ps1` as a Windows-friendly local stream
  supervision loop that writes supervisor and stream-health artifacts.
- Added dry-run, once-only, lag-check, DLQ publish, and critical-health options
  so the runner can be tested safely before being scheduled.
- Documented a Task Scheduler path for running the local stream supervisor on a
  laptop without installing a production service.

## 0.35.0 - 2026-05-05

- Added `fraud-v2 stream-health` to write a local JSON and HTML stream
  operations report from lag, supervisor, and dead-letter signals.
- Added stream health thresholds for lag, stored dead letters, failed
  supervisor batches, and DLQ publish failures.
- Added optional report-file output for `stream-lag` and `stream-supervise` so
  repeated stream reliability checks can feed later health reports.

## 0.34.0 - 2026-05-05

- Added `fraud-v2 model-eval-dashboard` to render baseline model reports and
  optional shadow-score summaries into a local HTML dashboard.
- Added dashboard metrics for average precision, Brier score, model threshold,
  cost threshold, feature count, shadow rows, and shadow flag rate.
- Added threshold candidate and feature-column tables for local model review.

## 0.33.0 - 2026-05-05

- Added a PaySim public-dataset CSV converter that writes canonical JSONL fraud
  events for the existing load/replay/train pipeline.
- Added stable hashing of PaySim account identifiers so source dataset names do
  not become canonical entity IDs.
- Ignored local `data/public/` outputs so downloaded or converted public
  datasets are not accidentally committed.

## 0.32.0 - 2026-05-05

- Added encrypted local decision-evidence exports using AES-256-GCM with a
  Scrypt-derived passphrase key.
- Added `fraud-v2 evidence-export` for writing local encrypted decision bundles
  from SQLite or Postgres-backed stores.
- Limited evidence payloads to safe decision fields, signals, feature values,
  trace IDs, and explicit human-review/no-filing metadata.

## 0.31.0 - 2026-05-05

- Added `fraud-v2 load-benchmark` to generate deterministic synthetic users,
  load them into SQLite, score a sample, and write a local performance receipt.
- Added benchmark metrics for generation time, load throughput, scoring
  throughput, risk-tier counts, runtime platform, and output paths.
- Made benchmark overwrite Windows-safe by clearing benchmark tables instead of
  deleting an in-use SQLite file.

## 0.30.0 - 2026-05-05

- Added local Ed25519-signed threshold-policy approval records bound to policy
  version, policy SHA-256, approver, role, timestamp, and notes.
- Added policy approval key generation, approval, approval-status, and
  approved-promotion CLIs.
- Added distinct-approver counting so a local policy can require maker-checker
  style approval before using the approved promotion path.

## 0.29.0 - 2026-05-05

- Added a local `fraud-v2 stream-supervise` worker loop for repeated bounded
  Redpanda consume batches.
- Added supervisor reporting for completed batches, failed batches, idle
  batches, aggregate ingest counts, dead-letter counts, and last transient
  error.
- Expanded the full-profile smoke to publish a supervised stream event and
  prove the supervisor ingests it into Postgres.

## 0.28.0 - 2026-05-05

- Added a Redpanda consumer-group lag probe and `fraud-v2 stream-lag` CLI.
- Added partition-level lag reporting with high watermark, committed offset,
  and total lag.
- Expanded the full-profile smoke to prove the valid stream consumer group has
  zero lag after consuming the smoke event.

## 0.27.0 - 2026-05-05

- Added optional Redpanda dead-letter-topic publishing for invalid stream
  records while keeping database dead letters as the default local path.
- Added stream-consumer reporting for published and failed DLQ publishes.
- Expanded the full-profile smoke to publish an invalid Redpanda record,
  consume it with `--publish-dead-letters`, and prove the DLQ topic received a
  structured dead-letter payload.

## 0.26.0 - 2026-05-05

- Added a local threshold policy registry with candidate, active, and disabled
  statuses plus SHA-256 hashes for registered policy files.
- Added CLI commands to register, list, and promote threshold policies while
  keeping exactly one active policy in the registry.
- Added active-policy file export so promoted policies can be loaded by the API
  through `FRAUD_POLICY_PATH`.

## 0.25.0 - 2026-05-05

- Added persistent stream dead letters for invalid Redpanda messages, empty
  payloads, stream errors, and idempotency-key payload conflicts.
- Added admin API and CLI inspection paths for stream dead letters.
- Added retention reporting/pruning coverage for stream dead-letter records.
- Updated the full-profile smoke to prove the valid Redpanda consume path does
  not create dead letters.

## 0.24.0 - 2026-05-05

- Added versioned threshold policy packs so green/yellow/red boundaries,
  degraded-mode floors, and high-amount friction signals can be changed through
  JSON instead of hardcoded decision-engine constants.
- Added CLI/API support for loading a local policy file while preserving the
  default local policy behavior.
- Added policy validation and tests for custom policy loading and decision
  outcomes.

## 0.23.0 - 2026-05-05

- Added a Redpanda stream consumer CLI that reads canonical event envelopes and
  stores them through the same SQLite/Postgres app-store boundary.
- Made stream ingestion idempotent: exact duplicates are committed as safe
  no-ops, while payload conflicts and invalid messages are reported without
  advancing offsets.
- Expanded the full-profile smoke to publish a Redpanda event, consume it into
  Postgres, and prove the exact idempotency key exists in app state.

## 0.22.0 - 2026-05-05

- Added JWKS/OIDC-shaped JWT verification for asymmetric tokens through local
  JWKS files, direct JWKS URLs, or OIDC discovery URLs.
- Kept local HS256 JWT auth available while refusing HS algorithms whenever
  JWKS verification is configured.
- Added crypto-backed JWT test coverage for RS256 token validation.

## 0.21.0 - 2026-05-05

- Added explicit local retention pruning for expired events, decisions, review
  records, and outbox messages.
- Added admin API and CLI prune paths that default to dry-run and require
  `execute=true` or `--execute` before deleting local records.
- Preserved audit entries during pruning so local audit hash-chain verification
  remains valid.

## 0.20.0 - 2026-05-05

- Added a full Postgres app-store backend for events, decisions, review cases,
  review decisions, outbox messages, audit entries, and retention reports.
- Switched the Docker full profile API to use Postgres as primary app storage
  while keeping SQLite as the default lite-mode storage.
- Hardened the full-profile smoke so repeated runs start from an isolated clean
  smoke volume and exercise review-decision submission.
- Fixed review-case persistence so submitted review decisions close the case in
  both SQLite and Postgres list results.

## 0.19.0 - 2026-05-05

- Added a local dashboard graph evidence page that renders an entity
  neighborhood and relationship table for analyst review.
- Expanded the full-profile smoke to verify the graph evidence UI.

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
