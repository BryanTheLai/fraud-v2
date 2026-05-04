---
id: TC-20260505-030
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
expected_artifact: Signed policy approval workflow, tests, docs, commit
---

# Task Card: Add Signed Policy Approvals

## Goal

Make threshold-policy promotion more production-shaped by adding a local
maker-checker approval trail with cryptographic signatures tied to the exact
policy hash.

## Scope

Allowed:

- add local Ed25519 policy approval signatures
- bind approval payloads to policy version and SHA-256
- count distinct verified approvers
- add policy keygen, approve, status, and approved-promote CLIs
- keep existing fast local promotion available
- update tests, docs, receipts, version, and commit

Not allowed:

- claim real legal/compliance approval
- claim external KMS/HSM, enterprise change management, or production policy
  registry
- require signed approvals for every local dev command
- commit private keys

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] Docker Compose full-profile config
- [x] Docker image build
- [x] full profile smoke
- [x] local commit
