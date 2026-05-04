# Code Factory Dashboard: fraud-v2

Updated: 2026-05-05

## Active Task

- [TC-20260505-002 - Implement Full Profile Adapters](tasks/active/TC-20260505-002-implement-full-profile-adapters.md)

## Runs Waiting For Bryan

- [RR-20260505-001](runs/RR-20260505-001.md)
- [RR-20260505-002](runs/RR-20260505-002.md)

## Blocked Work

- None.

## Done This Week

- Drafted the initial spec and setup docs.
- Added detailed vagueness, tradeoff, dependency, data, LLM synthetic data, and local production specs.
- Bryan approved the planning artifacts with `lgtm for now`.
- Implemented the local MVP and left it waiting for review.
- Added full-profile adapter boundaries, replay reports, monitoring reports,
  public dataset registry, and LLM provider boundaries.

## Lessons Added

- None. This run did not create reusable evidence beyond the spec.

## Stale Lessons

- None.

## One Next Task

Review the local MVP and M2 adapter layer. Next implementation task should add
actual worker loops, transactional outbox processing, and local full-profile
integration tests when Docker services are running.
