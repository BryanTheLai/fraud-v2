# Code Factory Dashboard: fraud-v2

Updated: 2026-05-05

## Active Task

- [TC-20260505-042 - Add Postgres Backup Rehearsal](tasks/active/TC-20260505-042-add-postgres-backup-rehearsal.md)

## Runs Waiting For Bryan

- [RR-20260505-001](runs/RR-20260505-001.md)
- [RR-20260505-002](runs/RR-20260505-002.md)
- [RR-20260505-003](runs/RR-20260505-003.md)
- [RR-20260505-004](runs/RR-20260505-004.md)
- [RR-20260505-005](runs/RR-20260505-005.md)
- [RR-20260505-006](runs/RR-20260505-006.md)
- [RR-20260505-007](runs/RR-20260505-007.md)
- [RR-20260505-008](runs/RR-20260505-008.md)
- [RR-20260505-009](runs/RR-20260505-009.md)
- [RR-20260505-010](runs/RR-20260505-010.md)
- [RR-20260505-011](runs/RR-20260505-011.md)
- [RR-20260505-012](runs/RR-20260505-012.md)
- [RR-20260505-013](runs/RR-20260505-013.md)
- [RR-20260505-014](runs/RR-20260505-014.md)
- [RR-20260505-015](runs/RR-20260505-015.md)
- [RR-20260505-016](runs/RR-20260505-016.md)
- [RR-20260505-017](runs/RR-20260505-017.md)
- [RR-20260505-018](runs/RR-20260505-018.md)
- [RR-20260505-019](runs/RR-20260505-019.md)
- [RR-20260505-020](runs/RR-20260505-020.md)
- [RR-20260505-021](runs/RR-20260505-021.md)
- [RR-20260505-022](runs/RR-20260505-022.md)
- [RR-20260505-023](runs/RR-20260505-023.md)
- [RR-20260505-024](runs/RR-20260505-024.md)
- [RR-20260505-025](runs/RR-20260505-025.md)
- [RR-20260505-026](runs/RR-20260505-026.md)
- [RR-20260505-027](runs/RR-20260505-027.md)
- [RR-20260505-028](runs/RR-20260505-028.md)
- [RR-20260505-029](runs/RR-20260505-029.md)
- [RR-20260505-030](runs/RR-20260505-030.md)
- [RR-20260505-031](runs/RR-20260505-031.md)
- [RR-20260505-032](runs/RR-20260505-032.md)
- [RR-20260505-033](runs/RR-20260505-033.md)
- [RR-20260505-034](runs/RR-20260505-034.md)
- [RR-20260505-035](runs/RR-20260505-035.md)
- [RR-20260505-036](runs/RR-20260505-036.md)
- [RR-20260505-037](runs/RR-20260505-037.md)
- [RR-20260505-038](runs/RR-20260505-038.md)
- [RR-20260505-039](runs/RR-20260505-039.md)
- [RR-20260505-040](runs/RR-20260505-040.md)
- [RR-20260505-041](runs/RR-20260505-041.md)
- [RR-20260505-042](runs/RR-20260505-042.md)

## Blocked Work

- None.

## Done This Week

- Drafted the initial spec and setup docs.
- Added detailed vagueness, tradeoff, dependency, data, LLM synthetic data, and local production specs.
- Bryan approved the planning artifacts with `lgtm for now`.
- Implemented the local MVP and left it waiting for review.
- Added full-profile adapter boundaries, replay reports, monitoring reports,
  public dataset registry, and LLM provider boundaries.
- Added transactional outbox, outbox drain worker, mock connectors, and raw
  event converters.
- Added human-review-only compliance drafts and cost-weighted threshold
  reporting.
- Hardened protected API routes to require bearer tokens by default.
- Added local model registry controls for shadow and active model governance.
- Added registered-model shadow scoring reports that do not alter decisions.
- Added full-profile Docker smoke script.
- Upgraded the analyst dashboard with recent decisions and open review queue.
- Added Grafana provisioning and expanded the full-profile smoke to verify API
  scoring, dashboard content, metrics, Grafana, and Prometheus scraping.
- Added local role-aware API authorization for admin, analyst, and system
  tokens.
- Added local request trace IDs, structured request logs, HTTP metrics, and
  Prometheus alert rules.
- Added a local tamper-evident audit log with admin verification endpoints.
- Added dry-run local retention reporting through API and CLI.
- Installed infra extras in the Docker API image and added a Postgres adapter
  smoke inside the full profile.
- Added full-profile smoke coverage for Redis, Neo4j, and Redpanda adapters.
- Added analyst review feedback events for replayable review and label signals.
- Added JWT/OIDC-shaped local auth with issuer, audience, expiry, and role
  validation.
- Added a local graph evidence dashboard for analyst review.
- Switched Docker full mode to use Postgres as the primary app store.
- Added explicit local retention pruning with dry-run defaults.
- Added offline-testable JWKS/OIDC-shaped JWT verification.
- Added a bounded Redpanda stream consumer with idempotent duplicate handling
  and full-smoke publish-consume-Postgres proof.
- Added versioned threshold policy packs for local green/yellow/red decision
  boundaries.
- Added persistent stream dead letters with admin inspection and retention
  coverage.
- Added a local threshold policy promotion registry with active-policy export.
- Added optional Redpanda DLQ topic publishing for stream dead letters.
- Added Redpanda consumer-group lag inspection through CLI and smoke proof.
- Added local Redpanda stream supervision with backoff and smoke proof.
- Added local signed threshold-policy approvals and approved promotion.
- Added a local synthetic load benchmark receipt CLI.
- Added encrypted local decision-evidence exports.
- Added PaySim public dataset conversion into canonical local events.
- Added a static local model eval dashboard artifact.
- Added a local stream health report and dashboard for lag, supervisor, and
  dead-letter signals.
- Added a Windows local stream service runner for supervised consume and
  stream-health artifact loops.
- Added optional local request trace JSONL export and trace report artifacts.
- Added local and CI secrets scanning for real-looking committed credentials.
- Added local audit archive export with manifest hash and chain proof.
- Added local SQLite backup and restore rehearsal with SHA-256 verification.
- Added local capacity-profile receipts with throughput target checks.
- Added full-profile Postgres backup rehearsal with scratch restore proof.

## Lessons Added

- None. This run did not create reusable evidence beyond the spec.

## Stale Lessons

- None.

## One Next Task

Review local MVP through M42 Postgres backup rehearsal. Next implementation
task should add generated release/runbook packaging if Bryan chooses to go
deeper.
