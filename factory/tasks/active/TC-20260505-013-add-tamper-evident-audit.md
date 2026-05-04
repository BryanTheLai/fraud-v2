---
id: TC-20260505-013
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
expected_artifact: tamper-evident local audit log, API endpoints, tests, commit
---

# Task Card: Add Tamper Evident Audit

## Goal

Add a local audit trail for fraud decisions and review actions that can detect
tampering during local development.

## Scope

Allowed:

- add hash-chained SQLite audit entries
- audit event ingestion, decisions, review cases, review decisions, and outbox status changes
- expose admin-only audit list and verification endpoints
- update full smoke, tests, docs, and receipts
- create local commit

Not allowed:

- real WORM storage
- cloud object lock
- external audit vendor
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
