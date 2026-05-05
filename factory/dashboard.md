# Code Factory Dashboard: fraud-v2

Updated: 2026-05-05

## Active Task

- None. Local implementation work is waiting for review.

## Waiting For Bryan

- Review run records in [factory/runs](runs/), latest:
  [RR-20260505-047](runs/RR-20260505-047.md).
- Review task cards in [factory/tasks/review](tasks/review/).

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

## Current Blockers

- GitHub push/PR still needs `gh auth login` and `git remote add origin <repo-url>`.
- Regulated production still needs a real fraud wedge, real labels, legal/vendor
  approval, real PII security design, deployment target, and production SLOs.

## Next Practical Command

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify.ps1 -Full
```
