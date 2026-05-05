---
id: TC-20260505-036
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
expected_artifact: Local stream service runner script, tests, docs, commit
---

# Task Card: Add Local Stream Service Runner

## Goal

Make stream supervision repeatable on Bryan's Windows laptop without pretending
the repo has a managed production stream platform.

## Scope

Allowed:

- add a PowerShell stream service loop script
- support one-shot and dry-run modes
- run `stream-supervise`, optional `stream-lag`, and `stream-health`
- write timestamped JSON/HTML artifacts under `data\local\stream-service`
- document a Windows Task Scheduler wrapper
- update tests, docs, receipts, version, and commit

Not allowed:

- register a scheduled task automatically
- install a Windows service
- call real vendor systems
- claim managed production stream monitoring

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] local stream service dry run
- [x] Docker Compose full-profile config
- [x] Docker image build
- [x] full profile smoke
- [x] local commit
