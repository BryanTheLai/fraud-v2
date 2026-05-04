---
id: TC-20260505-031
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
expected_artifact: Load benchmark CLI, tests, docs, commit
---

# Task Card: Add Local Load Benchmark

## Goal

Turn "runs on Bryan's laptop" into a repeatable local receipt with measured
synthetic generation, SQLite load, and decision scoring throughput.

## Scope

Allowed:

- add deterministic synthetic load benchmark report
- time synthetic generation, SQLite load, and decision scoring
- write JSON benchmark receipts
- include runtime platform metadata
- refuse to mix old and new benchmark DBs unless overwrite is explicit
- keep benchmark CPU-first and local-only
- update tests, docs, receipts, version, and commit

Not allowed:

- claim production capacity or real traffic SLOs
- require GPU
- use real PII or real customer data
- make normal tests run a heavy benchmark

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] Docker Compose full-profile config
- [x] Docker image build
- [x] full profile smoke
- [x] local commit
