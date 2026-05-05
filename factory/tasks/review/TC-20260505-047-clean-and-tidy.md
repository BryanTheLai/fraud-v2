---
id: TC-20260505-047
version: 1
created_at: 2026-05-05
updated_at: 2026-05-05
status: review
repo: fraud-v2
area: operations
owner: Bryan
created_by: Codex
priority: medium
risk: low
approval: green
supersedes:
expected_artifact: verify script, cleanup script, compact dashboard, docs, commit
---

# Task Card: Clean And Tidy

## Goal

Reduce repo operating noise without deleting source, specs, tests, or proof.

## Scope

Allowed:

- add one verification entry point
- add one local cleanup script
- move completed task cards out of the active lane
- compact dashboard prose and links
- update docs and PR templates to point at the new scripts
- remove ignored local caches and generated smoke artifacts from the laptop

Not allowed:

- delete source code, tests, specs, run records, or factory proof
- delete `.venv` or `data\public` by default
- weaken verification gates
- claim production readiness

## Proof

- [x] `uv run ruff format --check .`
- [x] `uv run ruff check .`
- [x] `uv run fraud-v2 secrets-scan --root .`
- [x] `uv run mypy src`
- [x] `uv run pytest -q`
- [x] `powershell -ExecutionPolicy Bypass -File scripts\verify.ps1`
- [x] `powershell -ExecutionPolicy Bypass -File scripts\verify.ps1 -Full`
- [x] `powershell -ExecutionPolicy Bypass -File scripts\clean-local.ps1`
- [x] local commit
