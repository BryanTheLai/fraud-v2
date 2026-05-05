---
id: TC-20260505-038
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
expected_artifact: Secrets scan CLI, CI gate, tests, docs, commit
---

# Task Card: Add Secrets Scan

## Goal

Catch real-looking committed credentials before local work is pushed or shared.

## Scope

Allowed:

- scan repo text files for common secret/token/key patterns
- skip generated local data and binary/cache directories
- allow documented local placeholders
- add a CLI and CI gate
- update tests, docs, receipts, version, and commit

Not allowed:

- claim this replaces a managed secret scanner
- upload file contents anywhere
- print full secrets in findings
- require external security products

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run fraud-v2 secrets-scan --root .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] Docker Compose full-profile config
- [x] Docker image build
- [x] full profile smoke
- [x] local commit
