---
id: TC-20260505-025
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
expected_artifact: Persistent stream dead letters, API/CLI inspection, tests, smoke proof, docs, commit
---

# Task Card: Add Stream Dead Letters

## Goal

Make stream failures inspectable and non-blocking by persisting invalid or
conflicting Redpanda records to local app-store dead letters before committing
their offsets.

## Scope

Allowed:

- persist stream dead letters in SQLite and Postgres
- capture safe error, payload hash, and short local payload preview
- expose admin API and CLI inspection paths
- include dead letters in retention reporting and pruning
- update stream worker tests and full-profile smoke
- update docs, receipts, version, and commit

Not allowed:

- store real PII
- claim a production WORM evidence store
- add a managed Kafka/Flink topology
- call real external vendors

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] Docker Compose full-profile config
- [x] Docker image build
- [x] full profile smoke
- [x] local commit
