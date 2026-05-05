---
id: TC-20260505-037
version: 1
created_at: 2026-05-05
updated_at: 2026-05-05
status: review
repo: fraud-v2
area: implementation
owner: Bryan
created_by: Codex
priority: high
risk: low
approval: green
supersedes:
expected_artifact: Local trace export/report CLI, tests, docs, commit
---

# Task Card: Add Local Trace Reports

## Goal

Make local API trace evidence inspectable without requiring a full distributed
tracing backend.

## Scope

Allowed:

- add optional local JSONL request-span export
- add `FRAUD_TRACE_EXPORT_PATH`
- add `fraud-v2 trace-report`
- write JSON and static HTML trace summaries
- enable trace export in the Docker full profile
- expand full smoke to prove trace report generation
- update tests, docs, receipts, version, and commit

Not allowed:

- require OpenTelemetry services for lite mode
- send traces outside the laptop
- log request bodies or secrets
- claim production distributed tracing

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] trace report CLI smoke
- [x] Docker Compose full-profile config
- [x] Docker image build
- [x] full profile smoke
- [x] local commit
