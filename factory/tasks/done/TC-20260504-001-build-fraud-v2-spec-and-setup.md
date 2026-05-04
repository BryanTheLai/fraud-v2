---
id: TC-20260504-001
version: 1
created_at: 2026-05-04
updated_at: 2026-05-04
status: approved
repo: fraud-v2
area: repo-bootstrap
owner: Bryan
created_by: Codex
priority: high
risk: medium
approval: yellow
supersedes:
expected_artifact: docs/spec-plan.md and docs/setup.md
---

# Task Card: Build Fraud V2 Spec And Setup

## Goal

Turn Bryan's Fraud V2 prompt and BryansLab article into a reviewable local build
spec that can become an implementation plan.

## Scope

Allowed:

- create `docs/spec-plan.md`
- create `docs/setup.md`
- create a minimal `README.md`
- create Code Factory folders and receipt files
- inspect local hardware and installed tools
- research current technical references

## Non-Goals

- Do not implement product code.
- Do not install dependencies.
- Do not create a remote GitHub repo.
- Do not commit or push.
- Do not connect to real fraud/KYC/banking/compliance vendors.

## Context Links

- `startup/PROMPT.md`
- `code-factory/docs/principles.md`
- `code-factory/docs/protocol.md`
- `code-factory/templates/repo-spec-plan.md`
- `code-factory/templates/repo-setup.md`
- `https://www.bryanslab.com/blogs/fraud-2/`

## Assumptions To Check

| Assumption | How to check |
|---|---|
| `fraud-v2` does not contain unrelated files. | Inspect folder before writing. |
| Local machine has Python, uv, Docker, and NVIDIA GPU info available. | Run version and hardware commands. |
| Unknown production requirements should stay as open questions. | List vague areas in the spec. |

## Proof

Required proof:

- command: `Get-ChildItem -Recurse docs`
- expected exit code: `0`
- expected artifacts: `docs/spec-plan.md`, `docs/setup.md`

## Definition Of Done

- [x] `docs/spec-plan.md` exists.
- [x] `docs/setup.md` exists.
- [x] `README.md` links to both docs.
- [x] unknowns are listed as open questions.
- [x] no product code implemented.
- [x] no commit or push performed.
- [x] Run Record written.

## Approval Rules

Green:

- read templates
- create local markdown docs
- create local empty folders

Yellow:

- create Code Factory folders in the product repo
- choose default project structure
- pick a recommended stack

Red:

- create remote repo
- install dependencies
- commit or push
- spend money
- contact external systems
- use real PII or regulated data

## Stop Conditions

Stop if the target folder contains unrelated product code that would be
overwritten.

Stop if the task requires real vendor credentials, money movement, legal filing,
or remote writes.
