---
id: TC-20260505-023
version: 1
created_at: 2026-05-05
updated_at: 2026-05-05
status: review
repo: fraud-v2
area: implementation
owner: Bryan
created_by: Codex
priority: high
risk: high
approval: green
supersedes:
expected_artifact: Redpanda stream consumer, CLI, tests, smoke proof, docs, commit
---

# Task Card: Add Redpanda Stream Consumer

## Goal

Close the local streaming loop by consuming canonical event envelopes from
Redpanda into the app store while preserving the repo's safety boundary:
synthetic/local data only, idempotent writes, bounded runs, and no external
vendor calls.

## Scope

Allowed:

- add a bounded Redpanda consumer worker
- commit offsets only after successful store insert or safe duplicate no-op
- support SQLite and Postgres app stores from the CLI
- avoid re-enqueueing stream-consumed events into the outbox
- add unit coverage and full-profile smoke proof
- update docs, receipts, version, and PR draft

Not allowed:

- add a real vendor integration
- require a long-running service for unit tests
- claim exactly-once stream processing
- hide invalid messages or idempotency conflicts

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] Docker Compose full-profile config
- [x] Docker image build
- [x] full profile smoke
- [x] local commit
