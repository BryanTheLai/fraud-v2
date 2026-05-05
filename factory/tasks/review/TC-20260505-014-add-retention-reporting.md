---
id: TC-20260505-014
version: 1
created_at: 2026-05-05
updated_at: 2026-05-05
status: review
repo: fraud-v2
area: implementation
owner: Bryan
created_by: Codex
priority: high
risk: low
approval: green
supersedes:
expected_artifact: dry-run retention reports, API/CLI access, tests, commit
---

# Task Card: Add Retention Reporting

## Goal

Make local data retention explicit and executable without deleting data by
default.

## Scope

Allowed:

- add retention policy and report models
- count expired records by table
- add admin-only API endpoint
- add CLI command
- expand full smoke, tests, docs, and receipts
- create local commit

Not allowed:

- destructive deletion
- production legal hold logic
- cloud archive tiers
- real PII

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] Docker Compose config check
- [x] Docker image build
- [x] full profile smoke
- [x] local commit
