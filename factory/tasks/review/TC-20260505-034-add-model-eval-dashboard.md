---
id: TC-20260505-034
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
expected_artifact: Model eval dashboard CLI, tests, docs, commit
---

# Task Card: Add Model Eval Dashboard

## Goal

Make local model review visible by rendering training reports and optional
shadow-score summaries into a static HTML dashboard.

## Scope

Allowed:

- read existing baseline training report JSON
- optionally summarize shadow-score JSON
- write a static HTML dashboard
- report summary metrics as CLI JSON
- include feature columns and threshold candidates
- update tests, docs, receipts, version, and commit

Not allowed:

- promote models
- change fraud decisions
- add a frontend framework
- claim production model monitoring

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] Docker Compose full-profile config
- [x] Docker image build
- [x] full profile smoke
- [x] local commit
