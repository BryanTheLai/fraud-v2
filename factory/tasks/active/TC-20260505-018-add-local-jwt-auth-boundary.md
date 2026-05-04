---
id: TC-20260505-018
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
expected_artifact: JWT auth mode, local token CLI, tests, docs, commit
---

# Task Card: Add Local JWT Auth Boundary

## Goal

Move beyond static local bearer tokens by adding a production-shaped JWT auth
boundary that still runs offline on Bryan's laptop.

## Scope

Allowed:

- add `FRAUD_AUTH_MODE=jwt`
- validate HS256 JWT issuer, audience, expiry, subject, and roles
- add a local CLI helper to mint test tokens
- keep the existing static token path as the default
- update tests, docs, receipts, and commit

Not allowed:

- require a real external identity provider
- add real users, sessions, or PII
- commit JWT secrets

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] Docker Compose config check
- [x] Docker image build
- [x] full profile smoke
- [x] local commit
