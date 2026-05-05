---
id: TC-20260505-040
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
expected_artifact: SQLite backup/restore CLI, tests, docs, commit
---

# Task Card: Add SQLite Backup Restore

## Goal

Make lite-mode persistence recoverable on Bryan's laptop with a simple local
backup and restore rehearsal.

## Scope

Allowed:

- copy SQLite database files
- write SHA-256 verified backup manifests
- restore backups to an explicit path
- require `--overwrite` before replacing an existing restore target
- update tests, docs, receipts, version, and commit

Not allowed:

- overwrite a database by default
- claim cloud backup or managed disaster recovery
- handle Postgres backup/restore
- upload data outside the laptop

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run fraud-v2 secrets-scan --root .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] SQLite backup/restore CLI smoke
- [x] Docker Compose full-profile config
- [x] Docker image build
- [x] full profile smoke
- [x] local commit
