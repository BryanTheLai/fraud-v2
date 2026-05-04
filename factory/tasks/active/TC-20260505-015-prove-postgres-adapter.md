---
id: TC-20260505-015
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
expected_artifact: Docker infra extras, Postgres adapter smoke, tests, commit
---

# Task Card: Prove Postgres Adapter

## Goal

Make the full Docker profile prove the Postgres event-store adapter works inside
the Docker network.

## Scope

Allowed:

- install infra extras in the Docker API image
- wait for Postgres readiness in full smoke
- insert/list a synthetic event through `PostgresEventStore`
- update tests, docs, receipts, and commit

Not allowed:

- switch the default API store from SQLite
- destructive database reset
- real data

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] Docker Compose config check
- [x] Docker image build
- [x] full profile smoke
- [x] local commit
