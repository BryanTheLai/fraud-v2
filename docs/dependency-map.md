---
project: fraud-v2
owner: Bryan
created_at: 2026-05-04
updated_at: 2026-05-05
status: current
source_task: TC-20260504-002
version: 2
---

# Dependency Map

Business contracts must not depend on infrastructure choices.

`domain` owns schemas, enums, and safe invariants. It must not import FastAPI,
SQLite/Postgres clients, Redis, Redpanda, Neo4j, OpenAI, or Grafana concerns.

## Runtime Graph

```text
api/cli
  |
  +--> domain contracts
  +--> storage -------------> SQLite lite / Postgres full
  +--> decision ------------> rules + features + graph + models + policy
  +--> review --------------> replayable label events
  +--> compliance ----------> human-review-only drafts
  +--> operations ----------> doctor/readiness/runbook/backup/capacity

workers
  |
  +--> outbox drain
  +--> Redpanda consume/supervise/lag/dead letters
  +--> storage

observability
  |
  +--> /metrics + Prometheus
  +--> structured logs
  +--> X-Trace-ID + optional JSONL trace reports

full Docker profile
  |
  +--> API + Postgres + Redis + Redpanda + Neo4j + Prometheus + Grafana
```

## Package Direction

| Area | Can Depend On | Must Not Depend On |
|---|---|---|
| `domain` | Pydantic, standard library | API, storage, vendors, OpenAI, Docker services |
| `config` | Pydantic settings | business policy |
| `api` | services, auth, observability | model training internals |
| `cli` | public service APIs | private route handlers |
| `storage` | domain contracts, sqlite3, optional psycopg | FastAPI routes |
| `decision` | domain, features, graph, models, policy, rules | raw vendor clients |
| `rules` | domain, feature values | persistence clients |
| `features` | domain, storage-facing values | API framework |
| `graph` | NetworkX, optional Neo4j adapter | UI framework |
| `models` | sklearn, pandas/numpy, joblib | live route mutation |
| `policy` | threshold schema, signatures | legal approval claims |
| `review` | domain, storage | direct model promotion |
| `compliance` | domain decision evidence | real filing APIs |
| `connectors` | mock vendor contracts | real external vendor calls |
| `converters` | raw payload schemas, domain events | decision side effects |
| `workers` | storage, streams, outbox | FastAPI route objects |
| `operations` | repo probes, reports, backup helpers | real deployment approval |
| `llm_lab` | OpenAI/Azure boundary, schema validation | final fraud scoring |

## Service Requirements

| Service | Lite | Full | Purpose |
|---|---:|---:|---|
| Python/FastAPI | yes | yes | API, dashboards, CLI package. |
| SQLite | yes | no | Default lite persistence. |
| Postgres | no | yes | Full-profile app store and backup rehearsal. |
| Redis | no | yes | Cache/feature adapter proof. |
| Redpanda | no | yes | Event bus, consumer, supervisor, DLQ proof. |
| Neo4j | no | yes | Full graph adapter proof. |
| NetworkX | yes | yes | Deterministic lite graph behavior. |
| Prometheus | no | yes | Metrics scrape and alert rules. |
| Grafana | no | yes | Provisioned local dashboard. |

## Failure Responses

| Dependency Fails | Local Response |
|---|---|
| SQLite/Postgres store | API readiness fails; do not claim local product ready. |
| Redpanda | Outbox remains inspectable; stream health/lag reports show failure. |
| Redis | Full smoke catches adapter failure; lite mode does not require Redis. |
| Neo4j | Graph adapter proof fails; decision engine can still use NetworkX/lite paths. |
| Model artifact | Rules-only/degraded decision path remains available. |
| OpenAI/Azure | Synthetic LLM generation stops; fraud scoring unaffected. |
| Grafana/Prometheus | Full smoke/readiness catches observability failure; API can still serve. |
| GitHub auth/remote | Local product can be ready; push/PR remains blocked. |

## Dependency Groups

| Group | Install When | Contents |
|---|---|---|
| default | Always | FastAPI, Pydantic, Typer, metrics, NetworkX, numpy/pandas/sklearn. |
| `dev` | Normal local work | pytest, ruff, mypy, httpx. |
| `infra` | Full-profile Python client work | psycopg, redis, neo4j, confluent-kafka. |
| `llm` | OpenAI/Azure synthetic lab | openai, jsonschema. |
| `graph-ml` | Optional experiments only | torch, torch-geometric. |

Do not use `graph-ml` in required tests or startup paths.

## Implementation Order

The current build has completed the local M1-M8 path: contracts, synthetic
data, storage, decisions, graph evidence, baseline ML, review, compliance
drafts, streams, observability, operations reports, and full smoke proof.

Future production work should start from the hard blockers in
`docs/production-readiness.md`, not by adding more local-only services.
