---
id: TC-20260505-028
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
expected_artifact: Stream lag CLI, tests, smoke proof, docs, commit
---

# Task Card: Add Stream Lag CLI

## Goal

Give the local operator a way to inspect Redpanda consumer-group lag so stream
workers are observable instead of black boxes.

## Scope

Allowed:

- add Redpanda lag probe
- report partition watermarks, committed offsets, per-partition lag, and total
  lag
- expose `fraud-v2 stream-lag`
- prove zero lag in full smoke after a valid consume
- update docs, receipts, version, and commit

Not allowed:

- require a long-running worker daemon
- claim managed monitoring or alerting
- add external services beyond local Redpanda

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] Docker Compose full-profile config
- [x] Docker image build
- [x] full profile smoke
- [x] local commit
