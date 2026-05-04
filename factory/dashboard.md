# Code Factory Dashboard: fraud-v2

Updated: 2026-05-05

## Active Task

- [TC-20260505-010 - Harden Full Profile Observability](tasks/active/TC-20260505-010-harden-full-profile-observability.md)

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

## Lessons Added

- None. This run did not create reusable evidence beyond the spec.

## Stale Lessons

- None.

## One Next Task

Review local MVP through M10 full-profile observability hardening. Next
implementation task should add OIDC/RBAC design or local logs/traces if Bryan
chooses to go deeper on production hardening.
