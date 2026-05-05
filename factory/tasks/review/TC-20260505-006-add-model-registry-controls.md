---
id: TC-20260505-006
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
expected_artifact: local model registry, shadow/active controls, tests, commit
---

# Task Card: Add Model Registry Controls

## Goal

Add local model governance so trained artifacts can be registered, hashed,
listed, and promoted without silently changing production decision behavior.

## Scope

Allowed:

- add JSON-backed local model registry
- track model artifact hash, report hash, metrics, feature columns, thresholds,
  and deployment status
- support candidate, shadow, active, and disabled states
- support promotion with one active model at a time
- add CLI commands and tests
- update docs and receipts
- create local commit

## Non-Goals

- do not make ML the final decision authority yet
- do not require cloud model registry
- do not require GPU
- do not push if GitHub auth is missing

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] model registry CLI smoke
- [x] Docker Compose config check
- [x] Docker image build
- [x] local commit
