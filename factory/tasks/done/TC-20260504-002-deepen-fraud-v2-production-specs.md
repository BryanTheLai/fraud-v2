---
id: TC-20260504-002
version: 1
created_at: 2026-05-04
updated_at: 2026-05-04
status: approved
repo: fraud-v2
area: planning
owner: Bryan
created_by: Codex
priority: high
risk: medium
approval: yellow
supersedes:
expected_artifact: expanded docs under docs/
---

# Task Card: Deepen Fraud V2 Production Specs

## Goal

Make the Fraud V2 plans specific enough to start implementation without hidden
ambiguity.

## Scope

Allowed:

- identify what remains vague
- choose local V1 defaults where safe
- compare solution options and tradeoffs
- map dependencies between services, packages, and modules
- specify data acquisition and synthetic data plans
- specify GPT-5.5/Azure/OpenAI synthetic data usage
- specify local laptop run profiles and resource limits
- update docs and factory receipts

## Non-Goals

- Do not implement product code.
- Do not install dependencies.
- Do not create or call real vendor integrations.
- Do not use real PII.
- Do not commit or push.
- Do not file real compliance reports.

## Context Links

- `docs/spec-plan.md`
- `docs/setup.md`
- `https://www.bryanslab.com/blogs/fraud-2/`

## Assumptions To Check

| Assumption | How to check |
|---|---|
| The first local wedge can be chosen without blocking Bryan. | Pick a reversible local default and mark production as open. |
| GPT-5.5/Azure/OpenAI tokens should be used for synthetic data, not direct decisions. | Document rationale and validation gates. |
| Public datasets are incomplete for the full product. | Compare coverage against required fraud layers. |

## Proof

Required proof:

- `Get-ChildItem docs`
- banned filler scan over `README.md docs factory`
- ASCII scan over changed markdown

## Definition Of Done

- [x] vagueness register exists
- [x] solution tradeoffs exist
- [x] dependency map exists
- [x] data strategy exists
- [x] LLM synthetic data plan exists
- [x] local production profile exists
- [x] README links plan docs
- [x] Run Record written

## Approval Rules

Green:

- write local docs
- cite public references

Yellow:

- choose reversible local defaults
- update factory dashboard

Red:

- install dependencies
- write product code
- commit or push
- use real PII
- call real vendor APIs
- spend money
- file compliance reports
