---
id: TC-20260505-043
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
expected_artifact: GitHub handoff script, tests, docs, commit
---

# Task Card: Add GitHub Handoff

## Goal

Make the remaining push/PR blocker executable and obvious: report missing GitHub
auth, missing remote, dirty worktree, and exact commands; execute push and PR
creation only when configured.

## Scope

Allowed:

- add dry-run-safe `scripts/github-handoff.ps1`
- report branch, remote, auth, PR body, and worktree readiness as JSON
- print exact next commands
- push and create PR only behind `-Execute`
- refuse execution when remote/auth/body/clean-worktree gates are not met
- update tests, docs, receipts, version, and commit

Not allowed:

- force push
- create a remote repo
- bypass `gh auth login`
- push with a dirty worktree
- claim PR creation if blocked

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run fraud-v2 secrets-scan --root .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] PowerShell script parse
- [x] GitHub handoff dry run
- [x] Docker Compose full-profile config
- [x] Docker image build
- [x] full profile smoke
- [x] local commit
