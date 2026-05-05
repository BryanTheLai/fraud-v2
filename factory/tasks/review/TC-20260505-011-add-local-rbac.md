---
id: TC-20260505-011
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
expected_artifact: local role-aware auth, tests, docs, commit
---

# Task Card: Add Local RBAC

## Goal

Replace the single protected-route token check with a production-shaped local
role boundary that still runs fully offline.

## Scope

Allowed:

- add local `admin`, `analyst`, and `system` roles
- keep the legacy dev token as all-roles
- add `FRAUD_API_TOKENS` for role-specific local tokens
- add `/v1/auth/whoami`
- enforce endpoint role boundaries
- add tests, docs, receipts, and commit

Not allowed:

- real OIDC provider
- real user sessions
- real PII
- external auth service calls

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] Docker Compose config check
- [x] Docker image build
- [x] full profile smoke
- [x] local commit
