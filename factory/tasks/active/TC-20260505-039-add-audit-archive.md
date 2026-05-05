---
id: TC-20260505-039
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
expected_artifact: Audit archive CLI, tests, docs, smoke proof, commit
---

# Task Card: Add Audit Archive

## Goal

Export local audit entries into a portable archive with enough manifest metadata
to verify custody and chain integrity.

## Scope

Allowed:

- export audit entries to JSONL
- write a manifest with archive hash, sequence bounds, root hash, and chain
  verification
- support SQLite and Postgres stores through existing store boundaries
- expand full smoke to prove Postgres-backed archive generation
- update tests, docs, receipts, version, and commit

Not allowed:

- claim WORM/object-lock storage
- delete or prune audit entries
- upload audit data outside the laptop
- file compliance reports

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run fraud-v2 secrets-scan --root .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] audit archive CLI smoke
- [x] Docker Compose full-profile config
- [x] Docker image build
- [x] full profile smoke
- [x] local commit
