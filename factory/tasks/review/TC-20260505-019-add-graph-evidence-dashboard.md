---
id: TC-20260505-019
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
expected_artifact: graph evidence dashboard, tests, full-smoke proof, commit
---

# Task Card: Add Graph Evidence Dashboard

## Goal

Give analysts a visual local graph evidence page for entity neighborhoods and
relationship reasons instead of forcing them to inspect JSON only.

## Scope

Allowed:

- add `/dashboard/graph`
- render a bounded SVG neighborhood for a target entity
- render a relationship table
- link recent decisions to graph evidence
- update tests, full smoke, docs, receipts, and commit

Not allowed:

- add a heavy frontend framework
- require external graph visualization services
- expose real PII

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] Docker Compose config check
- [x] Docker image build
- [x] full profile smoke
- [x] local commit
