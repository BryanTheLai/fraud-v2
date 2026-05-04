# Code Factory Dashboard: fraud-v2

Updated: 2026-05-05

## Active Task

- [TC-20260505-015 - Prove Postgres Adapter](tasks/active/TC-20260505-015-prove-postgres-adapter.md)

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

## Lessons Added

- None. This run did not create reusable evidence beyond the spec.

## Stale Lessons

- None.

## One Next Task

Review local MVP through M15 Postgres adapter proof. Next implementation task
should add a real OIDC design or move more runtime storage paths to Postgres if
Bryan chooses to go deeper on production hardening.
