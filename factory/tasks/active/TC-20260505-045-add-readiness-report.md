---
id: TC-20260505-045
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
expected_artifact: Readiness report CLI, tests, docs, commit
---

# Task Card: Add Readiness Report

## Goal

Make local readiness and remaining hard blockers machine-readable so Bryan can
see what is done, what is blocked, and what is not production-ready without
reading every doc.

## Scope

Allowed:

- add `fraud-v2 readiness-report`
- write JSON and HTML reports
- include version, branch, and latest commit
- include worktree, remote, GitHub auth, and artifact checks
- include implemented local capabilities
- include hard production blockers
- keep regulated production readiness false
- update tests, docs, receipts, version, and commit

Not allowed:

- claim real production readiness
- call external vendors
- include secrets or real PII
- replace full verification gates

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run fraud-v2 secrets-scan --root .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] readiness-report CLI smoke
- [x] Docker Compose full-profile config
- [x] Docker image build
- [x] full profile smoke
- [x] local commit
