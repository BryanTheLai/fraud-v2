---
id: TC-20260505-008
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
expected_artifact: full-profile smoke script, docs, verification, commit
---

# Task Card: Add Full Profile Smoke

## Goal

Make the Docker-backed full profile repeatable and easy to verify on Bryan's
laptop.

## Scope

Allowed:

- add PowerShell smoke script
- validate compose config
- build/start full profile
- check API, Prometheus, and Neo4j
- clean up by default
- update docs and receipts
- create local commit

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] `docker compose -f infra\docker-compose.yml --profile full config --quiet`
- [x] `docker build -t fraud-v2:local .`
- [x] `.\scripts\full-smoke.ps1`
- [x] local commit
