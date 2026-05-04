---
id: TC-20260505-005
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
expected_artifact: protected API token enforcement, tests, docs, commit
---

# Task Card: Harden Local API Auth

## Goal

Prevent protected local API endpoints from accepting missing credentials by
default.

## Scope

Allowed:

- require bearer token when `FRAUD_API_TOKEN` is non-empty
- keep health, dashboard, metrics, and docs open for local operations
- allow explicit local auth disablement only by setting an empty token
- update tests and docs
- create local commit

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] Docker Compose config check
- [x] Docker image build
- [x] local commit
