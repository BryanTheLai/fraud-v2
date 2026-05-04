---
id: TC-20260505-002
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
expected_artifact: full-profile adapter layer, replay/eval reports, tests, commit
---

# Task Card: Implement Full Profile Adapters

## Goal

Reduce the gap between the local MVP and the Fraud V2 full architecture by
adding replaceable infrastructure adapters and evaluation reports.

## Scope

Allowed:

- add project `AGENTS.md`
- add optional Postgres, Redis, Redpanda/Kafka, and Neo4j adapter interfaces
- add replay report tooling
- add drift/fairness report tooling over synthetic data
- add public dataset loader placeholders with clear errors
- add LLM structured-generation CLI wrapper with offline stub
- add tests that run without real external credentials
- update docs and receipts
- create local commits

## Non-Goals

- Do not use real PII.
- Do not call paid external vendors.
- Do not require Docker for default tests.
- Do not push if GitHub auth is missing.

## Proof

- [x] `uv sync --extra dev --extra infra --extra llm`
- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] replay CLI smoke
- [x] evaluation report CLI smoke
- [x] LLM lab offline smoke
- [x] Docker Compose config check
- [x] Docker image build
- [x] local commit
