---
id: TC-20260505-010
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
expected_artifact: Grafana provisioning, deeper full-profile smoke, tests, commit
---

# Task Card: Harden Full Profile Observability

## Goal

Make the Docker full profile prove more than container startup by exercising the
fraud API, analyst dashboard, metrics, Prometheus scrape, and Grafana dashboard.

## Scope

Allowed:

- provision Grafana data source and dashboard files
- expand `scripts/full-smoke.ps1` with API scoring and observability checks
- add tests for full-profile infra files
- update docs and receipts
- create local commit

Not allowed:

- real vendor calls
- real PII
- real compliance actions
- cloud deployment

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] Docker Compose config check
- [x] Docker image build
- [x] full profile smoke
- [x] local commit
