---
id: TC-20260505-001
version: 1
created_at: 2026-05-05
updated_at: 2026-05-05
status: needs_review
repo: fraud-v2
area: implementation
owner: Bryan
created_by: Codex
priority: urgent
risk: high
approval: yellow
supersedes:
expected_artifact: runnable local MVP with tests and local git commit
---

# Task Card: Implement Local Fraud V2 MVP

## Goal

Build a runnable local MVP that narrows the gap between the Fraud V2 specs and
working software.

## Scope

Allowed:

- initialize local git repo
- add Python project scaffolding
- add domain enums and Pydantic contracts
- add deterministic synthetic data generator
- add SQLite-backed event/decision/review store for lite mode
- add feature extraction, graph features, rules, decision engine
- add baseline sklearn model training/evaluation
- add FastAPI endpoints
- add CLI commands
- add metrics endpoint
- add GitHub Actions workflow file
- add Docker Compose scaffolding
- run tests and commit locally

## Non-Goals

- Do not use real PII.
- Do not call real KYC, banking, liveness, consortium, or SAR APIs.
- Do not spend money.
- Do not push to GitHub if `gh` is not authenticated.
- Do not claim regulated production readiness.

## Proof

Required:

- [x] `uv sync --extra dev`
- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] local smoke command for synthetic data
- [x] local smoke command for API and decision CLI
- [x] Docker image build and container health smoke
- [x] local git commit

## Stop Conditions

Stop only for hard blockers:

- package install cannot complete after three distinct fixes
- tests cannot be made green after root-cause investigation
- GitHub auth missing for push/PR
