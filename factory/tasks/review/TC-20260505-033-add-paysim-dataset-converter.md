---
id: TC-20260505-033
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
expected_artifact: PaySim converter CLI, tests, docs, commit
---

# Task Card: Add PaySim Dataset Converter

## Goal

Make at least one manually downloaded public fraud dataset usable by the local
Fraud V2 pipeline without introducing real PII or bypassing dataset terms.

## Scope

Allowed:

- convert PaySim-style CSV rows into canonical JSONL events
- hash source account names into stable local entity IDs
- emit payment attempted, payment settled, chargeback, and label events
- expose `fraud-v2 public-dataset-convert paysim`
- ignore local `data/public/` files
- update tests, docs, receipts, version, and commit

Not allowed:

- auto-download datasets
- scrape Kaggle or mirrors
- commit public/raw/converted datasets
- claim real product labels
- support real PII

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] Docker Compose full-profile config
- [x] Docker image build
- [x] full profile smoke
- [x] local commit
