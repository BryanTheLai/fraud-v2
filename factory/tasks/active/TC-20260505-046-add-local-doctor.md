---
id: TC-20260505-046
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
expected_artifact: Local doctor CLI, tests, docs, commit
---

# Task Card: Add Local Doctor

## Goal

Make laptop runability explicit so Bryan can see whether lite mode,
full-profile Docker mode, optional GPU experiments, and GitHub handoff are
ready on the current machine.

## Scope

Allowed:

- add `fraud-v2 local-doctor`
- write JSON and HTML reports
- check Python, package import, repo contract files, disk, RAM, uv, git, Docker,
  Docker Compose, Compose files, full-smoke script, optional NVIDIA GPU,
  GitHub remote, GitHub auth, and GitHub handoff script
- make GPU optional and non-blocking
- classify checks by `lite`, `full`, `github`, and `optional_gpu` scopes
- update tests, docs, receipts, version, and commit

Not allowed:

- require GPU for local runability
- claim regulated production readiness
- call external vendors
- include secrets or real PII

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run fraud-v2 secrets-scan --root .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] local-doctor CLI smoke
- [x] readiness-report CLI smoke
- [x] Docker Compose full-profile config
- [x] Docker image build
- [x] full profile smoke
- [x] local commit
