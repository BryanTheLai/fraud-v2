---
id: TC-20260505-041
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
expected_artifact: Capacity-profile CLI, JSON/HTML receipts, tests, docs, commit
---

# Task Card: Add Capacity Profile

## Goal

Turn local load benchmarking into a named capacity receipt with explicit laptop
targets, JSON/HTML artifacts, and an optional failing exit code for release
rehearsals.

## Scope

Allowed:

- add `smoke`, `laptop`, and `stress` synthetic capacity profiles
- allow profile size and target overrides
- write JSON and HTML capacity receipts
- upload lightweight CI capacity artifacts
- mark capacity profile as local synthetic evidence, not production SLO proof
- reuse the existing load benchmark code path
- update tests, docs, receipts, version, and commit

Not allowed:

- claim real production capacity
- require GPU
- require real traffic or real customer data
- make normal tests run a heavy benchmark

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run fraud-v2 secrets-scan --root .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] capacity-profile CLI smoke
- [x] Docker Compose full-profile config
- [x] Docker image build
- [x] full profile smoke
- [x] local commit
