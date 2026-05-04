---
id: TC-20260505-017
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
expected_artifact: review feedback events, label events, tests, commit
---

# Task Card: Add Review Feedback Events

## Goal

Make analyst review outcomes feed the canonical event stream so replay,
training, monitoring, and active-learning loops can consume them.

## Scope

Allowed:

- append `MANUAL_REVIEW_DECIDED` events when analysts decide cases
- append `LABEL_CREATED` events for confirmed fraud and confirmed legitimate
  outcomes
- avoid labels for non-final outcomes such as `NEEDS_MORE_INFO`
- update tests, docs, receipts, and commit

Not allowed:

- overwrite historical review decisions
- use real analyst data
- claim human-label quality without real inter-rater review

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] Docker Compose config check
- [x] Docker image build
- [x] full profile smoke
- [x] local commit
