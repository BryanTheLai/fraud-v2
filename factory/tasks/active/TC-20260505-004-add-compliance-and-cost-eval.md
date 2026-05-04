---
id: TC-20260505-004
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
approval: yellow
supersedes:
expected_artifact: compliance draft export, cost-weighted threshold report, tests, commit
---

# Task Card: Add Compliance And Cost Evaluation

## Goal

Add local-safe compliance draft exports and fraud-specific model threshold
selection so the platform optimizes for operational cost instead of generic
classification vanity metrics.

## Scope

Allowed:

- add compliance draft contracts and JSON export
- make every draft explicitly human-review-only
- add CLI command for local draft export
- add cost assumptions and threshold candidates to baseline training
- add tests
- update docs and receipts
- create local commit

## Non-Goals

- do not file SARs
- do not claim legal compliance
- do not use real customer data
- do not call external compliance vendors
- do not push if GitHub auth is missing

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] train CLI includes profit threshold
- [x] compliance draft CLI smoke
- [x] Docker Compose config check
- [x] Docker image build
- [x] local commit
