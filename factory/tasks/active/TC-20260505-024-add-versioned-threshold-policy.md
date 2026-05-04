---
id: TC-20260505-024
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
expected_artifact: Versioned threshold policy packs, tests, docs, commit
---

# Task Card: Add Versioned Threshold Policy

## Goal

Move decision thresholds out of hardcoded engine constants into a validated,
versioned local policy artifact that keeps the default behavior stable while
allowing safe local experiments.

## Scope

Allowed:

- define a threshold policy model
- preserve current default green/yellow/red behavior
- load policy JSON from CLI/API configuration
- expose a CLI command to inspect the active policy
- add tests, docs, receipts, version, and commit

Not allowed:

- claim legal approval or production policy governance
- add real vendor or compliance actions
- make local startup depend on external services

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] Docker Compose full-profile config
- [x] Docker image build
- [x] full profile smoke
- [x] local commit
