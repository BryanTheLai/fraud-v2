---
id: TC-20260505-016
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
expected_artifact: Redis, Neo4j, and Redpanda full-profile adapter smoke, tests, commit
---

# Task Card: Prove Remaining Infra Adapters

## Goal

Make the full Docker profile prove every local infrastructure adapter boundary
can be exercised from inside the API container.

## Scope

Allowed:

- wait for Redis, Redpanda, and Neo4j Bolt readiness in full smoke
- write/read a `FeatureVector` through `RedisFeatureCache`
- project a synthetic graph through `Neo4jGraphProjector`
- publish a synthetic event through `RedpandaEventPublisher`
- update tests, docs, receipts, and commit

Not allowed:

- switch the default API store from SQLite
- require external managed infrastructure
- require real data

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] Docker Compose config check
- [x] Docker image build
- [x] full profile smoke
- [x] local commit
