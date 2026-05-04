---
id: TC-20260505-007
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
expected_artifact: shadow score report, CLI, tests, commit
---

# Task Card: Add Shadow Scoring

## Goal

Allow registered models to score historical/local events in shadow mode without
changing production decisions.

## Scope

Allowed:

- load a registered active or shadow model
- rebuild feature rows from local events
- write model probability, threshold, would-flag, and feature values
- add CLI command and tests
- keep decision authority in rules/graph policy
- update docs and receipts
- create local commit

## Non-Goals

- do not make ML approve/block users directly
- do not require GPU
- do not require external registry
- do not push if GitHub auth is missing

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] shadow score CLI smoke
- [x] Docker Compose config check
- [x] Docker image build
- [x] local commit
