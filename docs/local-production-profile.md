---
project: fraud-v2
owner: Bryan
created_at: 2026-05-04
updated_at: 2026-05-04
status: draft
source_task: TC-20260504-002
version: 1
---

# Local Production Profile

## Machine Constraint

Observed target machine:

| Resource | Value |
|---|---|
| CPU | AMD Ryzen 7 5800H, 8 cores, 16 logical processors |
| GPU | NVIDIA GeForce RTX 3050 Laptop GPU |
| VRAM | 4096 MiB |
| Python | 3.12.9 |
| uv | 0.7.3 |
| Docker | 28.4.0 |
| NVIDIA driver | 565.90 |
| CUDA reported by driver | 12.7 |

Implication:

- API, workers, Postgres, Redis, Redpanda, Neo4j, and observability can run
  locally if dataset sizes are controlled.
- GPU must be optional.
- GNN training must be optional and small-batch only.
- XGBoost/LightGBM CPU training is the practical baseline.

## Run Profiles

### Lite

Use for coding and fast tests.

| Component | Mode |
|---|---|
| API | local process |
| DB | SQLite or Postgres |
| Feature online | in-memory or Redis |
| Feature offline | DuckDB/Parquet |
| Graph | NetworkX |
| Stream | disabled or in-process queue |
| Observability | metrics endpoint and logs only |

Target:

- start under 15 seconds
- run unit tests under 30 seconds
- tiny dataset under 500 events

### Full

Use for the real local demo.

| Component | Mode |
|---|---|
| API | local process or container |
| DB | Postgres |
| Feature online | Redis |
| Feature offline | DuckDB/Parquet |
| Event bus | Redpanda |
| Graph | Neo4j |
| Observability | Prometheus, Grafana, Loki, OTel Collector |
| UI | NiceGUI |

Target:

- 100k event demo dataset
- 50 events/sec replay
- p95 decision under 500ms without external vendors
- feature freshness p95 under 3s for velocity features

### ML

Use for training and evaluation.

| Component | Mode |
|---|---|
| Training | local Python process |
| Dataset | DuckDB/Parquet |
| Model registry | local file plus Postgres metadata |
| GPU | optional |

Target:

- baseline train under 15 minutes on 100k event dataset
- evaluate thresholds and write report
- no service uptime required

## Local Service Budgets

Initial Docker memory targets:

| Service | Memory Budget | Notes |
|---|---:|---|
| Postgres | 512 MB | Enough for local event/review tables. |
| Redis | 128 MB | Feature cache and circuit state. |
| Redpanda | 768 MB | Single-node local. |
| Neo4j | 1.0-1.5 GB | Keep graph dataset bounded. |
| Prometheus | 256 MB | Local retention only. |
| Grafana | 256 MB | Dashboards. |
| Loki | 512 MB | Local logs only. |
| OTel Collector | 128 MB | Local collector. |
| API + workers | 1-2 GB total | Python processes. |

Laptop guardrail:

- full profile should stay under roughly 6-8 GB active memory before browser
  overhead.
- stress generation and ML training should not run while full profile is under
  heavy replay unless testing resource contention.

## Dataset Size Limits

| Dataset | Events | Entities | Use |
|---|---:|---:|---|
| tiny | 500 | 100 | tests and golden cases |
| demo | 100,000 | 10,000 | local product demo and baseline ML |
| stress | 1,000,000 | 100,000 | optional throughput and graph guard testing |

Stress dataset rules:

- generated in chunks
- not loaded all into memory
- optional command
- never required for normal tests

## GPU Policy

Use GPU only for:

- small PyTorch/PyG experiments
- embedding experiments if memory fits
- optional profiling

Do not use GPU for:

- API serving
- required tests
- default model training
- default local demo

Why:

- 4GB VRAM is tight for graph neural networks.
- CPU GBDT models are strong for structured fraud features.
- Required workflows must not fail because CUDA packages are missing.

## Production-Shaped Local Controls

| Control | Local Implementation |
|---|---|
| Idempotency | request key plus payload hash in Postgres |
| Outbox | Postgres outbox table plus publisher worker |
| DLQ | `dead_letters` table plus Redpanda topic |
| Circuit breaker | per dependency state in Redis or process fallback |
| Health | `/health/live` and `/health/ready` |
| Metrics | `/metrics` plus Prometheus |
| Dashboards | Grafana provisioned with local Fraud V2 overview |
| Traces | OTel spans around decision path |
| Logs | JSON logs with redaction |
| Replay | read event stream from Parquet/DuckDB and compare decisions |
| Model rollback | active model pointer in registry |
| Shadow mode | candidate scores logged but no action impact |
| Safe reasons | reason-code registry and compliance converter |

## What Would Not Be Production Yet

Even with full local profile, these are not production complete:

- legal approval
- real auth/RBAC
- secrets manager
- cloud backups
- retention policy
- vendor contracts
- incident on-call
- real customer communication
- SAR filing integration
- fairness/disparate-impact review
- penetration test
- model risk committee

## Minimum Production Readiness Bar

Before any real data or real action:

1. security review
2. privacy review
3. data retention policy
4. RBAC
5. secret manager
6. audit immutability plan
7. vendor contract review
8. adverse action counsel review if credit-adjacent
9. SAR process review if AML-adjacent
10. incident response runbook
11. model governance and rollback procedure
12. fairness/disparate impact analysis
