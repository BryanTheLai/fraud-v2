---
id: TC-20260505-009
version: 1
created_at: 2026-05-05
updated_at: 2026-05-05
status: review
repo: fraud-v2
area: implementation
owner: Bryan
created_by: Codex
priority: medium
risk: medium
approval: green
supersedes:
expected_artifact: denser analyst dashboard, tests, commit
---

# Task Card: Polish Analyst Dashboard

## Goal

Make the local dashboard useful for analyst review instead of only showing
summary counts.

## Scope

Allowed:

- add recent decision table
- add open review case table
- keep dashboard read-only and local
- add tests
- update docs and receipts
- create local commit

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] dashboard smoke
- [x] Docker Compose config check
- [x] Docker image build
- [x] local commit
