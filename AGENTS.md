# Agent Instructions

This repo follows the operator contract from `startup/PROMPT.md` and the
Code Factory workflow.

## Rules

- Ship verified outcomes, not claims.
- Think of all possible solutions, think of tradeoffs for each, then think about whether we should implement or keep it as is. Do this for everything we are talking about. Don't be afraid to boil the ocean, but do keep in mind hard blockers like lack of enterprise-level access and whether the juice is worth the squeeze. Do not confuse effort to build with resources to build; effort to build should be ignored, but resources should be evaluated properly.
- Keep local laptop runability as a hard requirement.
- Do not use real PII.
- Do not call real KYC, banking, liveness, consortium, SAR, or payment vendors.
- Do not file real compliance reports.
- Keep GPU optional.
- Keep rules, features, graph, models, compliance, and storage modular.
- Every external action must be simulated unless Bryan explicitly approves it.
- Every decision must expose safe reasons and a trace ID.
- Every repeated workflow should become a command, test, doc, or factory receipt.

## Required Gates

Run before claiming completion:

```powershell
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest -q
```

For Docker changes:

```powershell
docker compose -f infra\docker-compose.yml --profile full config --quiet
docker build -t fraud-v2:local .
```

## Current Product Shape

- Lite mode is the default local path.
- Full mode is Docker-backed infrastructure.
- GPT/OpenAI/Azure is for synthetic data and eval support, not final fraud
  decision authority.
- XGBoost/LightGBM/sklearn-style tabular models are the practical baseline.
- Graph rules and graph features come before GNNs.

## Ship Boundary

GitHub push and PR creation require `gh auth login` and a remote. If auth is
missing, finish local commits and record the blocker in the Run Record.
