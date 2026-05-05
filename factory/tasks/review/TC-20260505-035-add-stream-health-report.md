---
id: TC-20260505-035
version: 1
created_at: 2026-05-05
updated_at: 2026-05-05
status: review
repo: fraud-v2
area: implementation
owner: Bryan
created_by: Codex
priority: high
risk: low
approval: green
supersedes:
expected_artifact: Stream health report CLI, tests, docs, commit
---

# Task Card: Add Stream Health Report

## Goal

Make local stream operations reviewable from one report that combines consumer
lag, stream supervisor receipts, and stored stream dead letters.

## Scope

Allowed:

- build a local stream health report model
- read optional JSON outputs from `stream-lag` and `stream-supervise`
- inspect SQLite/Postgres stream dead letters
- write JSON and static HTML stream health artifacts
- expose thresholds for lag, failed batches, dead letters, and DLQ publish
  failures
- update tests, docs, receipts, version, and commit

Not allowed:

- claim managed alerting
- add PagerDuty/Alertmanager/cloud monitoring
- run an unbounded worker
- call real vendor systems

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] stream health CLI smoke
- [x] Docker Compose full-profile config
- [x] Docker image build
- [x] full profile smoke
- [x] local commit
