---
id: TC-20260505-020
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
expected_artifact: Postgres app-store backend, full-profile Postgres storage, tests, smoke, commit
---

# Task Card: Use Postgres In Full Profile

## Goal

Make Docker full mode use Postgres as the primary app store instead of only
starting Postgres beside a SQLite-backed API.

## Scope

Allowed:

- add a full Postgres store for events, decisions, reviews, outbox, audit, and
  retention reports
- add a store protocol so SQLite lite and Postgres full mode share the same API
  boundary
- switch Docker Compose API env to `FRAUD_STORE_BACKEND=postgres`
- keep SQLite as the default lite-mode store
- update tests, docs, receipts, and commit

Not allowed:

- remove SQLite lite mode
- introduce destructive migrations
- require cloud-managed Postgres

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] Docker Compose config check
- [x] Docker image build
- [x] full profile smoke
- [x] local commit
