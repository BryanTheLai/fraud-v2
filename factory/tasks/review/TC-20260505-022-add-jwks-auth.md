---
id: TC-20260505-022
version: 1
created_at: 2026-05-05
updated_at: 2026-05-05
status: review
repo: fraud-v2
area: implementation
owner: Bryan
created_by: Codex
priority: high
risk: high
approval: green
supersedes:
expected_artifact: JWKS/OIDC-shaped JWT verification, tests, docs, commit
---

# Task Card: Add JWKS Auth

## Goal

Move JWT auth beyond local HS256-only tokens by adding production-shaped
JWKS/OIDC verification that remains testable without a real identity provider.

## Scope

Allowed:

- validate asymmetric JWTs against a local JWKS file
- support direct JWKS URL and OIDC discovery URL configuration
- refuse symmetric HS algorithms when JWKS is configured
- keep local HS256 JWT mode working
- update dependencies, tests, docs, receipts, and commit

Not allowed:

- require a live external IdP for tests
- add real user lifecycle or sessions
- weaken local token auth defaults

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] Docker image build
- [x] full profile smoke
- [x] local commit
