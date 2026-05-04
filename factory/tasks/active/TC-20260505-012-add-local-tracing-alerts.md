---
id: TC-20260505-012
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
expected_artifact: local trace IDs, structured request logs, alert rules, tests, commit
---

# Task Card: Add Local Tracing And Alerts

## Goal

Close the next observability gap by making every local API request traceable and
by adding local Prometheus alert rules.

## Scope

Allowed:

- add `X-Trace-ID` response headers
- honor inbound `X-Request-ID`
- add structured JSON request logs
- add HTTP request metrics
- add Prometheus alert rules for local SLO checks
- update full smoke, tests, docs, and receipts
- create local commit

Not allowed:

- external tracing vendor
- cloud alert manager
- real production incident routing

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] Docker Compose config check
- [x] Docker image build
- [x] full profile smoke
- [x] local commit
