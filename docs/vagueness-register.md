---
project: fraud-v2
owner: Bryan
created_at: 2026-05-04
updated_at: 2026-05-06
status: current
source_task: TC-20260504-002
version: 2
---

# Vagueness Register

## Rule

Vague requirements are not ignored. They get one of three treatments:

- `DECIDED_FOR_LOCAL_V1`: specific enough to build now.
- `OPEN_FOR_PRODUCTION`: fine for the local build, not safe for production.
- `BLOCKER`: cannot build that part until answered.

## Register

| Area | What Is Vague | Why It Matters | Local V1 Decision | Production Status |
|---|---|---|---|---|
| Product domain | "Fraud V2" could mean lending, payments, ecommerce, crypto, banking, payroll, or marketplace abuse. | Data shape, labels, rules, actions, and law change by domain. | `DECIDED_FOR_LOCAL_V1`: instant-cash fintech simulation. | `OPEN_FOR_PRODUCTION`: choose real first wedge before live use. |
| Customer action | "Block", "approve", "SAR filed", and "manual review" imply real authority. | Wrong action can create legal, customer, or financial harm. | `DECIDED_FOR_LOCAL_V1`: simulate all external actions. | `BLOCKER`: legal and product owner must approve real actions. |
| Jurisdiction | User is likely in the US, but product scope may be global. | Adverse action, AML, privacy, and retention rules differ by jurisdiction. | `DECIDED_FOR_LOCAL_V1`: US-inspired controls, no legal claims. | `BLOCKER`: jurisdiction matrix required. |
| Credit status | Instant cash may be credit, lending, earned wage access, or cash advance. | ECOA/Reg B adverse-action rules may apply if credit. | `DECIDED_FOR_LOCAL_V1`: treat as credit-adjacent and generate specific safe reasons. | `BLOCKER`: counsel review before live decisions. |
| PII | The blog references SSNs, documents, camera metadata, and identities. | Real PII changes security, storage, access, retention, and breach risk. | `DECIDED_FOR_LOCAL_V1`: no real PII; synthetic and hashed identifiers only. | `BLOCKER`: privacy/security design required before real data. |
| Labels | Fraud labels can come from chargebacks, defaults, repayments, SAR outcomes, analyst reviews, or confirmed ATO. | Label delays and label noise dominate model quality. | `DECIDED_FOR_LOCAL_V1`: synthetic ground truth plus analyst labels. | `OPEN_FOR_PRODUCTION`: define label taxonomy and delay windows. |
| Label timing | Fraud is often known days, weeks, or months later. | Training on future labels leaks information. | `DECIDED_FOR_LOCAL_V1`: every label has `label_available_at`. | `OPEN_FOR_PRODUCTION`: real label SLAs needed. |
| Data availability | Public data may not match identity plus device plus graph plus behavior. | A model trained on the wrong world is misleading. | `DECIDED_FOR_LOCAL_V1`: hybrid public data, simulator, and LLM-generated edge cases. | `OPEN_FOR_PRODUCTION`: validate against real historical data. |
| KYC vendors | Vendor shape, latency, pricing, error modes, and allowed use are unknown. | Connectors and decision policy depend on vendor outputs. | `DECIDED_FOR_LOCAL_V1`: mock adapters with realistic statuses and timeouts. | `OPEN_FOR_PRODUCTION`: vendor-specific contract tests. |
| Device fingerprint | Browser fingerprint, device ID, IP, user agent, and cookies are not specified. | Privacy and stability differ by identifier. | `DECIDED_FOR_LOCAL_V1`: synthetic device IDs and hashed browser fingerprints. | `OPEN_FOR_PRODUCTION`: approved fingerprinting policy. |
| Camera/deepfake | "Virtual camera" and EXIF checks are signals, not proof. | Bad rule can create false positives. | `DECIDED_FOR_LOCAL_V1`: metadata risk signal only; never sole red block. | `OPEN_FOR_PRODUCTION`: liveness vendor and policy needed. |
| Behavioral biometrics | Keystroke/touch/mouse features need client instrumentation. | Collection may be invasive and noisy. | `DECIDED_FOR_LOCAL_V1`: generate synthetic telemetry and entropy features. | `OPEN_FOR_PRODUCTION`: privacy review and consent language. |
| Consortium data | Shared blacklist availability is unknown. | Real consortium data is contractual and regulated. | `DECIDED_FOR_LOCAL_V1`: local mock risk list. | `BLOCKER`: contract and permitted-use review. |
| Payment rails | ACH, RTP, debit, push-to-card have different costs and finality. | Financial reward function and controls depend on rail economics. | `DECIDED_FOR_LOCAL_V1`: simulate ACH, RTP, debit, push-to-card with configurable costs. | `OPEN_FOR_PRODUCTION`: real unit economics required. |
| Fraud typologies | The blog names many typologies. Scope can explode. | Too many typologies early causes fake completeness. | `DECIDED_FOR_LOCAL_V1`: cover nine local typologies in deterministic synthetic data: synthetic identity, ATO, card testing, first-party fraud, money mule, APP scam, BEC, deepfake liveness, and bust-out. | `OPEN_FOR_PRODUCTION`: expand policy only with real labels and action authority. |
| Thresholds | Green/yellow/red thresholds are illustrative. | Thresholds control financial and customer harm. | `DECIDED_FOR_LOCAL_V1`: start 0-20, 21-79, 80-100, then optimize by reward. | `OPEN_FOR_PRODUCTION`: threshold governance required. |
| SLOs | "Real time" is vague. | Stack choices differ for 50ms, 500ms, and 5s. | `DECIDED_FOR_LOCAL_V1`: local p95 decision under 500ms without vendors. | `OPEN_FOR_PRODUCTION`: real SLO and traffic profile. |
| Throughput | Local and production event rates are unknown. | Redpanda, Redis, Postgres, and workers need sizing. | `DECIDED_FOR_LOCAL_V1`: laptop capacity receipt plus a tracked 720-user/4,703-event demo dataset; larger synthetic runs are generated on demand instead of committed. | `OPEN_FOR_PRODUCTION`: traffic model, SLO, and capacity plan. |
| Stream semantics | Exactly-once vs at-least-once is not specified. | Fraud systems must tolerate retries without double actions. | `DECIDED_FOR_LOCAL_V1`: at-least-once stream plus idempotent consumers and outbox. | `OPEN_FOR_PRODUCTION`: Flink/exactly-once only if needed. |
| Feature store | Feast, Tecton, custom Redis, or pure SQL are all possible. | Online/offline parity and point-in-time correctness are core. | `DECIDED_FOR_LOCAL_V1`: explicit feature builder over canonical events, SQLite/Postgres storage, Redis full-profile cache, and JSON/HTML model reports. | `OPEN_FOR_PRODUCTION`: add DuckDB/Parquet/Feast/Tecton only after real scale or parity needs justify it. |
| Graph database | Neo4j, NetworkX, Postgres recursive CTEs, TigerGraph, Memgraph are options. | Analyst explainability and graph algorithms depend on this. | `DECIDED_FOR_LOCAL_V1`: Neo4j Community plus NetworkX fallback. | `OPEN_FOR_PRODUCTION`: choose managed graph or graph-in-warehouse strategy. |
| GNN | The blog mentions GNNs, but GNNs need graph labels and careful eval. | GNN-first can waste time and underperform tabular models. | `DECIDED_FOR_LOCAL_V1`: graph rules and graph features first; PyG optional. | `OPEN_FOR_PRODUCTION`: use only after baseline beats rules. |
| LLM role | GPT-5.5 tokens could be used in many ways. | LLM scoring can be expensive, non-deterministic, and hard to govern. | `DECIDED_FOR_LOCAL_V1`: LLM generates scenarios, data, analyst notes, and evals; does not make final fraud decisions. | `OPEN_FOR_PRODUCTION`: LLM policy and eval gates needed. |
| UI | Analyst, investigator, compliance, ML engineer, and SRE all need different UIs. | One UI can become unfocused. | `DECIDED_FOR_LOCAL_V1`: analyst queue plus operator dashboard. | `OPEN_FOR_PRODUCTION`: role-based workflows. |
| Auth | Local token vs real RBAC is open. | Review and compliance data need access control. | `DECIDED_FOR_LOCAL_V1`: local token, route-level role structure. | `BLOCKER`: production IdP/RBAC required. |
| Audit retention | Retention periods are not specified. | Fraud decisions and regulatory evidence need retention policy. | `DECIDED_FOR_LOCAL_V1`: keep local synthetic audit indefinitely unless reset. | `BLOCKER`: legal retention schedule. |
| Model governance | Approval, rollback, shadow, and champion/challenger policies need owners. | Bad model releases can create systemic harm. | `DECIDED_FOR_LOCAL_V1`: no model active without eval report and pinned artifact. | `OPEN_FOR_PRODUCTION`: model risk management policy. |
| Fairness | Protected-class and proxy variables are not defined. | Fraud controls can create disparate impact. | `DECIDED_FOR_LOCAL_V1`: synthetic demographic fields excluded from decisions unless explicitly used for bias testing. | `BLOCKER`: fairness review before production. |
| Incident response | What happens when false positives spike is not specified. | Production fraud systems need kill switches. | `DECIDED_FOR_LOCAL_V1`: circuit breakers and manual policy override. | `OPEN_FOR_PRODUCTION`: incident runbooks and on-call. |

## Highest-Risk Unknowns

1. Real domain and action authority.
2. Real labels and label delay.
3. Real PII/data handling.
4. Real compliance scope.
5. Real unit economics.

## Non-Blocking Defaults

For local implementation, these defaults are specific enough:

- domain: instant-cash fintech simulation
- data: deterministic 720-user synthetic core plus optional public datasets
- action: simulated only
- model: rules plus calibrated sklearn tabular ML; XGBoost/LightGBM remain optional next champions
- graph: Neo4j plus NetworkX
- stream: Redpanda plus Python workers
- UI: analyst queue plus operator dashboard
- LLM: data generation and eval support, not final scoring
