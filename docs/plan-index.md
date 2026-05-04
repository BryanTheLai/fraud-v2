---
project: fraud-v2
owner: Bryan
created_at: 2026-05-04
updated_at: 2026-05-04
status: draft
source_task: TC-20260504-002
version: 1
---

# Plan Index

## Purpose

This folder is the durable plan for building the BryansLab Fraud V2 article as
local runnable software.

The product goal is not a classifier notebook. The goal is a production-shaped
fraud operating system:

- event ingestion
- canonical contracts
- synthetic and public data inputs
- feature freshness
- graph intelligence
- rule and ML scoring
- decision trace
- manual review
- compliance-safe drafts
- observability
- replay
- resilience

## Current Documents

| Document | Purpose | Read When |
|---|---|---|
| `spec-plan.md` | Main product and architecture spec. | You need the full target system. |
| `setup.md` | Local run and environment plan. | You need to run or install the project. |
| `vagueness-register.md` | What is still vague, why it matters, and the local V1 default. | You need to remove ambiguity before coding. |
| `solution-tradeoffs.md` | Options considered and tradeoffs for each major architectural decision. | You need to challenge stack choices. |
| `dependency-map.md` | How services, packages, workers, and data stores depend on each other. | You need implementation sequencing or local resource planning. |
| `data-strategy.md` | How to get data, what public datasets cover, what they miss, and how to synthesize the rest. | You need inputs for training and demos. |
| `llm-synthetic-data-lab.md` | How to use GPT-5.5/Azure/OpenAI tokens to generate edge cases and synthetic data safely. | You need high-volume synthetic generation. |
| `local-production-profile.md` | Laptop-safe production profile, resource budgets, run modes, and hard limits. | You need to keep this runnable on Bryan's machine. |

## Decisions Made Now

| Decision | Pick | Why |
|---|---|---|
| First product wedge | Instant-cash fintech simulation | It exercises application fraud, device risk, identity, transactions, repayments, manual review, and compliance reasons. |
| Core runtime | Python 3.12 | Matches Bryan's preference and the current laptop. |
| Local infrastructure | Docker Compose | Available locally and enough for Postgres, Redis, Redpanda, Neo4j, and observability. |
| Serving model | Hybrid rules plus tabular ML | More practical than an LLM fraud classifier and stronger baseline than graph deep learning first. |
| LLM role | Synthetic data generator, edge-case inventor, analyst-note generator, reason-code evaluator | LLMs help create coverage and review artifacts; they should not be the primary fraud scoring model. |
| Default ML baseline | XGBoost or LightGBM plus calibration | Strong for tabular fraud data and CPU-friendly. |
| Graph V1 | Neo4j plus NetworkX fallback | Gives analyst graph queries while keeping tests local and deterministic. |
| Stream V1 | Redpanda plus Python stream workers | Kafka-compatible without running a heavy JVM stack. |
| Feature store V1 | Explicit Redis online store plus DuckDB/Parquet offline store | Easier to understand and test locally than installing a full feature platform first. |
| Feature-store upgrade path | Feast-compatible abstractions | Leaves a path to Feast/Tecton without committing early. |
| UI V1 | NiceGUI | Python-first and fast to build. React can come later if UI complexity demands it. |

## Build Sequence

### M1: Contracts And Synthetic Data

Goal:

- define enums
- define Pydantic event contracts
- define canonical entity refs
- define converter errors
- generate synthetic applications, devices, sessions, transactions, repayments,
  chargebacks, and labels

Exit proof:

- `uv run pytest tests/unit/domain tests/unit/synthetic -q`
- sample `data/synthetic/events.jsonl`
- schema validation report

### M2: Local API And Storage

Goal:

- FastAPI app
- Postgres tables
- idempotent event intake
- transactional outbox
- local health checks

Exit proof:

- `POST /v1/events` works
- duplicate idempotency test passes
- outbox recovery test passes

### M3: Features And Rules

Goal:

- velocity features
- device features
- payment features
- graph feature placeholders
- rule registry
- decision policy V1

Exit proof:

- golden decision cases pass
- stale feature test passes

### M4: Baseline ML

Goal:

- dataset builder
- point-in-time feature assembly
- XGBoost/LightGBM baseline
- calibration
- threshold optimization by financial reward

Exit proof:

- evaluation report includes AUPRC, Recall at 1 percent FPR, Brier score, PSI,
  and profit

### M5: Graph Intelligence

Goal:

- entity graph
- shared identifier edges
- WCC/community features
- graph explanation endpoint
- analyst graph view

Exit proof:

- graph explains a synthetic fraud ring
- supernode guard test passes

### M6: Manual Review And Compliance Drafts

Goal:

- review queue
- analyst outcomes
- label events
- safe reason export
- SAR draft export

Exit proof:

- yellow decision creates review case
- review outcome creates label
- no decision uses "risk score only" as the reason

### M7: Observability And Resilience

Goal:

- metrics
- traces
- structured logs
- circuit breakers
- DLQ
- replay

Exit proof:

- dependency outage matrix passes
- Grafana dashboard shows queue lag, latency, freshness, and DLQ

### M8: Local Product Demo

Goal:

- single documented local run path
- seeded fraud rings
- UI walkthrough
- screenshots

Exit proof:

- clean machine setup starts the stack
- local demo can ingest, score, explain, review, and retrain

## What Not To Build Yet

- real vendor integrations
- real SAR filing
- real adverse-action delivery
- real PII ingestion
- Kubernetes
- cloud deployment
- GNN-first scoring
- LLM-as-primary-fraud-classifier

## Next Implementation Task

Build M1:

- `src/fraud_v2/domain/enums.py`
- `src/fraud_v2/domain/events.py`
- `src/fraud_v2/domain/entities.py`
- `src/fraud_v2/domain/decisions.py`
- `src/fraud_v2/synthetic/generator.py`
- `tests/unit/domain/`
- `tests/unit/synthetic/`

