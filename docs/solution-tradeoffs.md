---
project: fraud-v2
owner: Bryan
created_at: 2026-05-04
updated_at: 2026-05-05
status: current
source_task: TC-20260504-002
version: 2
---

# Solution Tradeoffs

Decision standard:

1. run on Bryan's Windows laptop,
2. prove the Fraud V2 architecture end to end,
3. stay modular enough to replace later,
4. avoid fake production claims,
5. prefer verified local evidence over impressive-sounding scope.

## Product Wedge

| Option | Tradeoff | Current Recommendation |
|---|---|---|
| Instant-cash fintech simulation | Broad enough to exercise identity, device, money movement, repayments, review, and safe reasons. | Keep as the local V1 wedge. |
| Card testing / ATO / money mule / APP-BEC | Useful typologies, but each is too narrow alone. | Keep as synthetic scenarios inside the simulator. |
| Crypto AML or ecommerce | Useful adjacent benchmarks, different product obligations. | Future modules after data/wedge decisions. |
| Real production domain | Best signal, highest legal/security burden. | Blocked until Bryan chooses action authority and data boundary. |

## Data

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| Deterministic simulator | Full control, no PII, replayable labels. | Can become too clean. | Default local source. |
| Public datasets | Real benchmark texture. | No single dataset covers the whole product. | Optional converter path; manual download only. |
| LLM synthetic scenarios | Great edge-case coverage. | Needs schema validation and dedupe. | Use for scenario/payload generation, not final truth. |
| Real data | Best production signal. | Regulated and unavailable in this repo. | Production blocker. |

## Storage And Streams

| Choice | Why |
|---|---|
| SQLite lite mode | Fast, simple, deterministic, no Docker requirement. |
| Postgres full mode | Production-shaped app persistence for Docker smoke. |
| Transactional outbox | Lets event publishing fail/retry without losing local state. |
| Redpanda | Kafka-compatible local event bus with lower laptop burden than a full Kafka stack. |
| Bounded/supervised Python consumers | Clear, testable local reliability proof before adding heavier stream frameworks. |

Upgrade path: managed Kafka/Flink or cloud streams only after real throughput,
SLO, and deployment decisions exist.

## Graph

| Choice | Why |
|---|---|
| NetworkX in lite mode | Deterministic, testable, no service required. |
| Neo4j in full mode | Better production-shaped graph proof and browser/debug UX. |
| GNNs later | 4GB VRAM and missing real graph labels make GNN-first wasteful. |

## Model Strategy

| Option | Verdict |
|---|---|
| Rules | Required for explainability, fallback, and no-label startup. |
| sklearn tabular baseline | Implemented and CPU-friendly. |
| XGBoost/LightGBM | Strong next champion candidate when dependency/scope warrants it. |
| GNN | Research/shadow path after graph rules prove value. |
| LLM fraud classifier | Reject as primary scorer; use LLMs for synthetic generation and eval support only. |

## UI

| Option | Current Status |
|---|---|
| CLI | Implemented for operations and automation. |
| FastAPI HTML dashboards | Implemented for analyst dashboard, graph evidence, readiness-style artifacts. |
| NiceGUI | Original plan option, not current implementation. |
| React/TypeScript | Future option if the analyst UI becomes a real product surface. |

Current recommendation: keep the lightweight FastAPI dashboards until product
workflow pain justifies a frontend stack.

## Observability

| Option | Current Status |
|---|---|
| Structured logs | Implemented. |
| `X-Trace-ID` | Implemented for API responses. |
| JSONL local trace export/report | Implemented. |
| Prometheus metrics and alert rules | Implemented. |
| Grafana dashboard | Implemented in full mode. |
| Loki/OpenTelemetry Collector | Original plan option, not current implementation. |

Current recommendation: do not add more observability services until a real
deployment target and alert-routing owner exist.

## Security And Governance

| Area | Local Choice | Production Upgrade |
|---|---|---|
| Auth | Bearer token, role tokens, local JWT/JWKS-shaped validation. | External OIDC, real user lifecycle, RBAC. |
| Secrets | Local repo scan for real-looking credentials. | Managed secret scanner and vault/KMS. |
| Audit | Hash chain plus local archive manifest. | WORM/object-lock storage and legal retention. |
| Policy governance | JSON registry plus local signed approvals. | Maker-checker workflow, KMS/HSM, change management. |
| Evidence | Local AES-256-GCM bundle. | External custody, access policy, retention/legal hold. |

## Local Resource Strategy

| Choice | Why |
|---|---|
| Profiles: lite/full/ml | Keeps laptop iteration fast while preserving a production-shaped full proof. |
| CPU-first model path | Reliable on Ryzen laptop and avoids CUDA fragility. |
| Optional GPU experiments | RTX 3050 is useful for experiments, not required workflows. |
| Synthetic capacity receipts | Gives repeatable local evidence without pretending to be production load. |

## What To Build Next

Do not add more local-only subsystems by default. The next high-value work is:

1. choose the real fraud product wedge,
2. define action authority and legal constraints,
3. get real or redacted labels,
4. choose deployment target and SLOs,
5. harden auth, secrets, PII storage, audit immutability, and incident response.
