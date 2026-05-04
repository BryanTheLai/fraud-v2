# Fraud V2 Startup Prompt

This repo exists to turn the Fraud Detection V2 article into runnable software,
not just planning prose.

## Operating Contract

- Ship verified outcomes, not claims.
- Keep the default path runnable on Bryan's Windows laptop.
- Treat Docker-backed infra as optional full mode, not a prerequisite for tests.
- Use Python-first implementations unless a narrower tool is clearly better.
- Keep synthetic data and mock integrations as the default safety boundary.
- Never use real PII, real banking actions, real vendor calls, or real compliance
  filings without explicit approval.
- Keep every fraud decision explainable with a trace ID, policy version, feature
  set version, score, tier, action, and compliance-safe reasons.
- Prefer strong tabular baselines and graph rules before speculative deep models.
- Use LLMs to generate scenarios, edge cases, prompt packs, and test fixtures;
  do not make an LLM the final decision authority.
- Make repeated workflows executable as CLIs, scripts, tests, docs, or factory
  receipts.

## Local Definition Of Done

- `uv run ruff format --check .`
- `uv run ruff check .`
- `uv run mypy src`
- `uv run pytest -q`
- `docker compose -f infra\docker-compose.yml --profile full config --quiet`
- `docker build -t fraud-v2:local .`

## Product Boundary

The useful local product is an instant-cash/fintech fraud lab with versioned
events, synthetic data, deterministic replay, rules, graph intelligence,
baseline ML, analyst review, safe compliance reasons, observability, and a clear
path from SQLite lite mode to Docker-backed full mode.
