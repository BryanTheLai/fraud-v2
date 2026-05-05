# Code Factory Dashboard: fraud-v2

Updated: 2026-05-05

## Active Task

- None. Simulation workbench and ML feature-importance release is implemented
  and verified; final GitHub handoff is blocked only by GitHub CLI auth.

## Waiting For Bryan

- Review the compact receipt archive documented in [factory/README.md](README.md).

## Done This Week

- Planned the Fraud V2 product boundary, blockers, tradeoffs, dependencies,
  data strategy, LLM synthetic lab, and local production profile.
- Built the local Python/FastAPI fraud lab with synthetic data, SQLite lite
  mode, rules, graph features, baseline ML, analyst review, safe compliance
  drafts, model governance, policy governance, audit, retention, and reports.
- Added Docker full mode with Postgres, Redis, Redpanda, Neo4j, Prometheus,
  Grafana, stream ingestion/supervision, stream lag, dead letters, DLQ proof,
  backup rehearsals, and full smoke verification.
- Added local operations tooling: secrets scan, trace reports, audit archive,
  SQLite backup/restore, capacity profile, GitHub handoff, release runbook,
  readiness report, local doctor, verify script, and cleanup script.
- Added the local simulation workbench (`/dashboard/simulate` and
  `fraud-v2 simulate-risk`) plus baseline model feature-importance reporting.

## Current Blockers

- GitHub PR creation still needs `gh auth login`. The `origin` remote exists
  and branch push works.
- Regulated production still needs a real fraud wedge, real labels, legal/vendor
  approval, real PII security design, deployment target, and production SLOs.

## Next Practical Command

```powershell
gh auth login
powershell -ExecutionPolicy Bypass -File scripts\github-handoff.ps1 -Execute
```
