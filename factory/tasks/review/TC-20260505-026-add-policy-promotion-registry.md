---
id: TC-20260505-026
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
expected_artifact: Local policy registry, promotion CLI, tests, docs, commit
---

# Task Card: Add Policy Promotion Registry

## Goal

Add a local governance rail for threshold policies so candidate policies are
hashed, listed, promoted one-at-a-time, and exported to the active policy file
used by the API.

## Scope

Allowed:

- add local JSON threshold policy registry
- support candidate, active, and disabled statuses
- keep exactly one active policy on promotion
- write the promoted active policy file
- add CLI commands, tests, docs, receipts, version, and commit

Not allowed:

- claim real maker-checker approval
- add legal policy workflow
- add external signing/KMS
- make API startup depend on registry state

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] Docker Compose full-profile config
- [x] Docker image build
- [x] full profile smoke
- [x] local commit
