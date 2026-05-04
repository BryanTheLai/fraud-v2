---
id: TC-20260505-003
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
expected_artifact: transactional outbox worker, mock connector/converter layer, tests, commit
---

# Task Card: Implement Outbox And Converters

## Goal

Move from API-only event persistence toward production-shaped ingestion by adding
a durable local outbox, a worker command, and typed mock connector/converter
boundaries.

## Scope

Allowed:

- keep all work local and synthetic
- add SQLite outbox persistence
- add a worker that publishes pending events through an injected publisher
- add safe retry/dead-letter state
- add mock KYC/device/consortium connector contracts
- add raw payload converters into canonical events
- add tests for success, duplicate idempotency, retry, dead-letter, and malformed input
- update docs and receipts
- create local commits

## Non-Goals

- do not call real vendors
- do not require Redpanda/Postgres/Redis/Neo4j for default tests
- do not process real PII
- do not push if GitHub auth is missing

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] outbox CLI smoke
- [x] converter CLI/API still compatible
- [x] Docker Compose config check
- [x] Docker image build
- [x] local commit
