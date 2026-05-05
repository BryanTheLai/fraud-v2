---
id: TC-20260505-042
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
expected_artifact: Postgres backup rehearsal script, smoke wiring, tests, docs, commit
---

# Task Card: Add Postgres Backup Rehearsal

## Goal

Make Docker full-mode Postgres recovery rehearsal executable and verified
locally instead of leaving backup as an operator TODO.

## Scope

Allowed:

- run `pg_dump` inside the full-profile Postgres container
- copy a custom-format dump to `data\local`
- compute a local SHA-256 manifest
- restore into a scratch database
- compare source and restored event counts
- clean up the scratch database by default
- wire the rehearsal into full-profile smoke
- update tests, docs, receipts, version, and commit

Not allowed:

- claim managed backup, PITR, cloud DR, WORM storage, or legal retention
- restore over the primary Postgres database
- require real production data
- require a cloud provider

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run fraud-v2 secrets-scan --root .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] PowerShell script parse
- [x] Docker Compose full-profile config
- [x] Docker image build
- [x] full profile smoke with Postgres backup rehearsal
- [x] local commit
