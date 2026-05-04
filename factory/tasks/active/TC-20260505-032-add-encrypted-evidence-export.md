---
id: TC-20260505-032
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
expected_artifact: Encrypted evidence export CLI, tests, docs, commit
---

# Task Card: Add Encrypted Evidence Export

## Goal

Give local reviewers an encrypted decision-evidence bundle that preserves safe
reasoning context without pretending to be a regulatory filing or production
custody system.

## Scope

Allowed:

- export safe decision evidence for human review
- encrypt evidence with AES-256-GCM
- derive encryption keys from a passphrase with Scrypt
- require passphrase through an environment variable
- include no-filing and no-real-PII metadata
- support SQLite and Postgres store backends through existing store boundaries
- update tests, docs, receipts, version, and commit

Not allowed:

- claim SAR/adverse-action filing
- claim external KMS/HSM, legal hold, or production custody
- export raw real PII
- put passphrases in code, docs as real secrets, logs, or committed files

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] Docker Compose full-profile config
- [x] Docker image build
- [x] full profile smoke
- [x] local commit
