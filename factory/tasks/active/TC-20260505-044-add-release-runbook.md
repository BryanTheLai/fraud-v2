---
id: TC-20260505-044
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
expected_artifact: Release runbook CLI, tests, docs, commit
---

# Task Card: Add Release Runbook

## Goal

Generate one local operator handoff artifact so running, verifying, recovering,
and handing off the repo is not spread across memory and scattered notes.

## Scope

Allowed:

- add `fraud-v2 release-runbook`
- include version, branch, and latest commit
- include lite/full-mode commands
- include verification gates
- include recovery rehearsals
- include GitHub handoff commands
- include hard limits and non-production boundary
- update tests, docs, receipts, version, and commit

Not allowed:

- claim deployment approval
- claim real production readiness
- include secrets or real PII
- replace the detailed docs

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run fraud-v2 secrets-scan --root .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] release-runbook CLI smoke
- [x] Docker Compose full-profile config
- [x] Docker image build
- [x] full profile smoke
- [x] local commit
