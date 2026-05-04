---
project: fraud-v2
owner: Bryan
created_at: 2026-05-04
updated_at: 2026-05-04
status: draft
source_task: TC-20260504-002
version: 1
---

# Solution Tradeoffs

## Decision Standard

Pick the option that:

1. runs on Bryan's laptop,
2. proves the Fraud V2 architecture end to end,
3. stays modular enough to replace later,
4. avoids fake production claims,
5. gives strong evidence with tests and replay.

## Product Wedge

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| Instant-cash fintech | Covers identity, device, application, transaction, repayment/default, manual review, adverse-action-like reasons. | Synthetic economics required. | Pick for V1. |
| Card testing | Easy to simulate velocity and card attempts. | Narrow; misses identity and synthetic identity depth. | Add as typology inside V1. |
| Account takeover | Strong real-time behavior and device problem. | Needs auth/session data and user history. | Add as typology inside V1. |
| Synthetic identity only | Matches article theme. | Long time horizon and sparse labels are hard to demo. | Include as scenario, not only wedge. |
| Crypto AML | Great graph use case and public Elliptic data exists. | Less connected to KYC/credit/adverse action. | Future module. |
| Ecommerce fraud | Public datasets exist. | Does not force repayment/default or SAR/adverse-action style thinking. | Useful public-data benchmark. |

Decision:

- Build instant-cash fintech first.
- Include card testing, ATO, synthetic identity, first-party fraud, money mule,
  and APP/BEC as typologies.

## Data Strategy

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| Public datasets only | Realistic labels for some fraud tasks; quick benchmarks. | No single public dataset covers identity, device, graph, behavior, manual review, and compliance. | Use for benchmarking, not product truth. |
| Pure simulator | Full control, labels, edge cases, time travel. | Can become too clean and teach models simulator artifacts. | Core local V1 source. |
| LLM-only synthetic data | Massive variety and edge cases. | Needs validation; can hallucinate impossible fields. | Use for scenario and payload generation behind schemas. |
| Hybrid simulator plus LLM plus public data | Best coverage and validation. | More moving parts. | Pick for V1. |
| Real data | Best production signal. | Not available, risky, regulated. | Not in local V1. |

Decision:

- Build a deterministic simulator first.
- Use GPT-5.5/Azure/OpenAI to generate scenario specs, edge cases, analyst notes,
  and rare payload variants.
- Use public datasets as external benchmarks only.

## Event Architecture

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| API writes Postgres only | Simple and laptop-friendly. | Hides streaming, freshness, replay, and consumer lag problems. | Use in `lite` profile only. |
| Postgres outbox plus Redpanda | Production-shaped, Kafka-compatible, local friendly. | More infra than a toy app. | Pick for full V1. |
| Kafka plus Flink | Strong stream semantics and exactly-once workflows. | Heavy on Windows laptop; JVM/ops overhead. | Production later if needed. |
| Pub/Sub cloud stack | Managed and scalable. | Not local-first. | Not V1. |

Decision:

- Use transactional outbox plus Redpanda.
- Consumers must be idempotent.
- Exactly-once stream processing is not the first goal; exactly-once external
  action is handled by idempotency.

## Stream Worker Framework

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| Plain Kafka consumer | Maximum control and fewer dependencies. | Windowing/state boilerplate can grow fast. | Good fallback. |
| Quix Streams | Pure Python, Kafka-native, local friendly, stateful processing. | Smaller ecosystem than Flink/Spark. | Pick for V1 if dependency install is clean. |
| Bytewax | Python dataflows and stateful stream processing. | Different mental model and smaller Kafka ecosystem. | Alternative. |
| Flink | Mature state, checkpoints, exactly-once semantics. | Heavy and less Python-native. | Production upgrade path. |

Decision:

- Start with Quix Streams or plain consumer wrappers.
- Keep feature definitions independent so Flink can replace workers later.

## Feature Store

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| Hand-rolled Redis online plus DuckDB/Parquet offline | Transparent, local, easy to test. | Must implement point-in-time joins and registry discipline. | Pick for V1. |
| Feast | Open-source feature store, online/offline concepts, materialization. | Extra framework and operational choices before pain is proven. | Evaluate after M3. |
| Tecton | Strong production feature platform. | Commercial/cloud; not laptop-first. | Later only. |
| Pure SQL features | Easy start. | Weak online latency and streaming freshness. | Use only for offline/replay. |

Decision:

- Implement explicit feature registry and point-in-time dataset builder.
- Name interfaces so Feast can replace internals later.

## Graph Layer

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| NetworkX only | Easy, deterministic, no service dependency. | Not production-like for large graph queries. | Test fallback. |
| Neo4j Community | Strong graph query UX, local Docker, analyst explainability. | Extra service and memory. | Pick for full V1. |
| Postgres graph tables | Fewer services. | Recursive graph queries and visualization are weaker. | Store canonical edge audit, not main graph UX. |
| TigerGraph/Memgraph | Strong graph systems. | More operational overhead or unfamiliar stack. | Not V1. |
| PyG-only graph tensors | Useful for GNN research. | Bad analyst UX and not a graph database. | Optional ML experiment only. |

Decision:

- Store canonical edges in Postgres.
- Project edges into Neo4j for queries and UI.
- Use NetworkX in unit tests and `lite` profile.

## Model Strategy

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| Rules only | Explainable, reliable, no labels needed. | Lower recall and brittle to new patterns. | Required baseline and fallback. |
| Logistic regression | Transparent and fast. | May underfit nonlinear fraud patterns. | First benchmark. |
| XGBoost/LightGBM | Strong tabular baseline, CPU-friendly, handles nonlinear interactions. | Needs careful calibration and leakage control. | Pick for V1 champion candidate. |
| Isolation Forest/autoencoder | Useful for unknown anomalies. | Harder to convert into action and business profit. | Secondary anomaly signal. |
| GNN | Matches graph theme, can detect relational risk. | Needs graph labels, careful sampling, more compute, harder explainability. | Research track after graph rules work. |
| LLM classifier | Flexible and "smart". | Non-deterministic, costly, hard to calibrate, likely worse than GBDT on structured tabular data. | Do not use as primary scorer. |

Decision:

- Build rules plus calibrated XGBoost/LightGBM.
- Use graph features as inputs.
- Use GNN as optional shadow experiment only.
- Use LLMs for data generation and review, not final scoring.

## LLM Usage

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| Generate synthetic scenarios | Excellent coverage and creativity. | Needs schema validation and dedupe. | Pick. |
| Generate raw events directly | Fast volume. | Can produce inconsistent event timelines. | Only after simulator validates. |
| Generate analyst notes | Great for UI realism and NLP evals. | Notes must not drive labels without validation. | Pick. |
| Generate adverse-action reason drafts | Useful wording coverage. | Must not replace compliance rules. | Pick as draft generator only. |
| Judge model explanations | Useful eval signal. | LLM judge can be wrong or biased. | Use as auxiliary eval. |
| Score fraud directly | Fast prototype. | Bad governance and calibration. | Reject for V1. |

Decision:

- LLM generates inputs to deterministic validators.
- Validators, schemas, and tests decide whether generated data enters training.

## UI

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| CLI only | Fast and testable. | Does not prove analyst workflow. | Keep for ops, not enough. |
| Streamlit | Fast data app. | Less suited to structured app with role flows. | Alternative. |
| NiceGUI | Python-first app UI, interactive components. | Smaller ecosystem than React. | Pick for V1. |
| React/TypeScript | Best long-term frontend. | More stack and context. | Later if UI hardens. |

Decision:

- NiceGUI for local product.
- API remains clean enough for React later.

## Observability

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| Logs only | Simple. | Not production-level; misses latency/freshness/lag. | Not enough. |
| Prometheus metrics only | Good numeric visibility. | No traces/log correlation. | Part of V1. |
| OpenTelemetry plus Prometheus/Grafana/Loki | Production-shaped and local. | More Docker services. | Pick for full V1. |
| SaaS observability | Strong product. | External cost and secrets. | Later. |

Decision:

- Implement structured logs, Prometheus metrics, and OTel traces.
- `lite` profile may skip Grafana/Loki but not instrumentation.

## Local Resource Strategy

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| Everything always on | Production-shaped. | Too heavy for laptop iteration. | Not default. |
| Profiles: lite/full/ml | Fits task and resource constraints. | More setup logic. | Pick. |
| Cloud-only dev | Scales. | Violates local-first goal. | Reject. |

Decision:

- `lite`: API, Postgres or SQLite, Redis optional, DuckDB, NetworkX.
- `full`: API, Postgres, Redis, Redpanda, Neo4j, Prometheus, Grafana, Loki.
- `ml`: offline training and eval; GPU optional.

## Security Model

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| No auth local | Fast. | Builds bad habits and unsafe routes. | Reject. |
| Local API token and role headers | Simple and testable. | Not production auth. | Pick for V1. |
| Full OIDC/RBAC now | Production-like. | Too much upfront. | Production hardening. |

Decision:

- Local token plus explicit role checks.
- No route gets added without auth boundary documented.

