---
id: TC-20260505-029
version: 1
created_at: 2026-05-05
updated_at: 2026-05-05
status: review
repo: fraud-v2
area: implementation
owner: Bryan
created_by: Codex
priority: high
risk: medium
approval: green
supersedes:
expected_artifact: Stream supervisor CLI, tests, smoke proof, docs, commit
---

# Task Card: Add Stream Supervisor CLI

## Goal

Give the local Redpanda stream consumer a production-shaped supervised run mode
with bounded batches, backoff, aggregate health reporting, and a Docker smoke
proof.

## Scope

Allowed:

- add a reusable local stream supervisor
- run repeated bounded consume batches
- report completed, failed, and idle batches
- aggregate ingest, duplicate, invalid, conflict, and dead-letter counts
- back off after transient runtime failures
- expose `fraud-v2 stream-supervise`
- prove supervised ingest in full smoke
- update docs, receipts, version, and commit

Not allowed:

- claim Kubernetes, Windows service, systemd, or managed stream deployment
- claim exactly-once semantics
- require the supervisor for lite-mode tests
- store real PII

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] Docker Compose full-profile config
- [x] Docker image build
- [x] full profile smoke
- [x] local commit
