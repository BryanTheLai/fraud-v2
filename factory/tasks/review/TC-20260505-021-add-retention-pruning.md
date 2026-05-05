---
id: TC-20260505-021
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
expected_artifact: Explicit local retention prune API/CLI, store support, tests, smoke, commit
---

# Task Card: Add Retention Pruning

## Goal

Turn dry-run retention reporting into an explicit local retention enforcement
path without making destructive cleanup the default.

## Scope

Allowed:

- add a `prune_retention` store boundary
- implement pruning for SQLite and Postgres app stores
- keep audit entries preserved so hash-chain verification remains valid
- add admin-only API support with `execute=false` dry-run default
- add CLI support with explicit `--execute`
- update tests, docs, smoke, receipts, and commit

Not allowed:

- automatically delete data in normal reporting paths
- delete audit hash-chain entries without an archive/WORM design
- introduce cloud storage, legal holds, or real compliance workflows

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] Docker Compose config check
- [x] Docker image build
- [x] full profile smoke
- [x] local commit
