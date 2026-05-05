---
id: TC-20260505-027
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
expected_artifact: Optional Redpanda DLQ publisher, CLI flag, tests, smoke proof, docs, commit
---

# Task Card: Add Redpanda DLQ Publisher

## Goal

Make stream dead letters optionally publish to a Redpanda DLQ topic after they
are persisted locally, so bad records are inspectable and replayable through
stream tooling.

## Scope

Allowed:

- add a Redpanda dead-letter JSON publisher
- add stream consumer CLI flags for DLQ publishing
- commit source offsets only after local dead-letter save and DLQ publish
- add unit tests for successful and failed DLQ publishing
- expand full smoke to prove invalid record -> app-store dead letter -> Redpanda
  DLQ topic
- update docs, receipts, version, and commit

Not allowed:

- make DLQ publishing required for lite mode
- store real PII
- claim managed streaming or Flink semantics

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] Docker Compose full-profile config
- [x] Docker image build
- [x] full profile smoke
- [x] local commit
