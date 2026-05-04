# Code Factory Dashboard: fraud-v2

Updated: 2026-05-05

## Active Task

- [TC-20260505-005 - Harden Local API Auth](tasks/active/TC-20260505-005-harden-local-api-auth.md)

## Runs Waiting For Bryan

- [RR-20260505-001](runs/RR-20260505-001.md)
- [RR-20260505-002](runs/RR-20260505-002.md)
- [RR-20260505-003](runs/RR-20260505-003.md)
- [RR-20260505-004](runs/RR-20260505-004.md)
- [RR-20260505-005](runs/RR-20260505-005.md)

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

## Lessons Added

- None. This run did not create reusable evidence beyond the spec.

## Stale Lessons

- None.

## One Next Task

Review local MVP through M5 auth hardening. Next implementation task should add
Docker-backed integration tests and analyst UI polish.
