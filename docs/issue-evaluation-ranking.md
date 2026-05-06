---
project: fraud-v2
owner: Bryan
created_at: 2026-05-06
status: current
source: GitHub issues #2-#13
---

# Issue Evaluation Ranking

## Ranking Logic

Truth-First ranking asks:

1. Does this unlock other issues?
2. Can it be built locally without real PII, vendors, money movement, customer
   messaging, or compliance filing?
3. Does it reduce the chance that the local lab lies?
4. Does it create reusable contracts instead of one-off UI proof?

## Ranked Build Order

| Rank | Issue | Feasibility | Why This Order |
|---|---|---|---|
| P0-1 | [#7 Hybrid decision contract and simulated-action guardrail](https://github.com/BryanTheLai/fraud-v2/issues/7) | Feasible locally; production actions blocked. | Prevents every downstream feature from implying real block/SAR/message authority. |
| P0-2 | [#4 Feature registry and online/offline parity report](https://github.com/BryanTheLai/fraud-v2/issues/4) | Feasible locally. | Makes features versioned, sourced, and parity-tested before ML/stream/decision expansion. |
| P0-3 | [#2 Gateway signal contract and mock vendor matrix](https://github.com/BryanTheLai/fraud-v2/issues/2) | Feasible locally; real vendors blocked. | Converts KYC/KYB/liveness/device/consortium shape into canonical events without vendor coupling. |
| P0-4 | [#3 Synthetic identity surveillance and novelty ledger](https://github.com/BryanTheLai/fraud-v2/issues/3) | Feasible locally; production realism blocked by real labels and PII. | Supplies target-article synthetic identity depth and prevents repeated/generated data theater. |
| P1-1 | [#6 Graph feature pack and supernode guard](https://github.com/BryanTheLai/fraud-v2/issues/6) | Feasible locally; GNN deferred. | Turns graph evidence into decision-grade features while avoiding supernode false positives. |
| P1-2 | [#5 Stream freshness SLO and circuit-breaker proof](https://github.com/BryanTheLai/fraud-v2/issues/5) | Feasible locally; production SLOs blocked. | Connects stream lag and feature freshness to degraded decision behavior. |
| P1-3 | [#8 Manual review active-learning loop and IRR report](https://github.com/BryanTheLai/fraud-v2/issues/8) | Feasible locally; real workforce blocked. | Makes analyst labels/retrain eligibility/IRR truthful. |
| P1-4 | [#9 Compliance package with adverse-action and SAR draft boundaries](https://github.com/BryanTheLai/fraud-v2/issues/9) | Feasible locally; real filing/notification blocked. | Makes legal-tail artifacts useful without pretending to file or notify. |
| P1-5 | [#10 Champion/challenger ML benchmark](https://github.com/BryanTheLai/fraud-v2/issues/10) | Feasible locally; optional deps skip-safe. | Upgrades ML from baseline to profit/calibration-driven model comparison. |
| P1-6 | [#11 Drift, shadow deployment, and rollback gate](https://github.com/BryanTheLai/fraud-v2/issues/11) | Feasible locally. | Converts drift/shadow scoring into model promotion and rollback gates. |
| P2-1 | [#12 Proof cockpit and one-command local demo bundle](https://github.com/BryanTheLai/fraud-v2/issues/12) | Feasible locally. | Packages proof after core contracts exist so presentation does not outrun truth. |
| P2-2 | [#13 Full-profile outage matrix and recovery receipts](https://github.com/BryanTheLai/fraud-v2/issues/13) | Partially feasible locally. | Useful resilience proof, but most valuable after fallback and proof-bundle contracts stabilize. |

## Connector Map

| Connector / Boundary | Issues | Local Truth |
|---|---|---|
| `GatewaySignalConverter` | #2 | Converts mock/public-shape gateway outputs to canonical events. |
| Mock KYC / device intel / consortium | #2 | No real vendor calls. |
| `LlmSyntheticCaseConverter` | #3 | Offline-safe by default; LLM only generates synthetic cases. |
| Feature registry / parity runner | #4, #5, #10, #11 | Shared feature definitions prevent training-serving skew. |
| Stream lag / freshness reporter | #5, #13 | Local Redpanda/full-profile proof only. |
| NetworkX / Neo4j graph boundary | #6 | NetworkX lite is source of local tests; Neo4j is full-profile projection. |
| Decision score breakdown | #7 | Rules/model/graph/gateway scores compose into final local decision. |
| Review service / label converter | #8 | Analyst outcomes become delayed labels locally. |
| Evidence/compliance export | #9 | Draft-only, no filing, no customer notification. |
| Model registry / shadow scorer | #10, #11 | Champion defaults to shadow; promotion requires gates. |
| Proof bundle script | #12 | Aggregates screenshots, reports, command outputs. |
| Outage matrix runner | #13 | Automates safe local simulations; documents unsafe/non-local failures. |

## Data Class Map

| Class / Contract | Issues | Purpose |
|---|---|---|
| `GatewaySignalObserved` | #2 | Canonical event for KYC/KYB/liveness/device/public-shape signals. |
| `ConsortiumRiskObserved` | #2 | Canonical mock consortium risk event. |
| `SyntheticIdentityProfile` | #3 | Synthetic impossible-timeline profile without real PII. |
| `NoveltyLedgerEntry` | #3 | Prevents repeated generated scenarios. |
| `FeatureDefinition` | #4 | Versioned feature definition. |
| `FeatureParityReport` | #4 | Online/offline parity proof. |
| `DependencyDegradation` | #5, #7 | Explains degraded decision mode. |
| `GraphFeatureVector` | #6 | Decision-grade graph measurements. |
| `DecisionScoreBreakdown` | #7 | Rules/model/graph/final score contract. |
| `ActionExecutionMode` | #7, #9 | Prevents fake real-world action claims. |
| `IrrReport` | #8 | Cohen's Kappa/manual-review consistency proof. |
| `RetrainEligibility` | #8 | Label availability and point-in-time guard. |
| `DecisionEvidencePackage` | #9 | Safe decision evidence export. |
| `ModelBenchmarkResult` | #10 | Profit/calibration-first benchmark row. |
| `PromotionDecision` | #11 | Model promotion gate output. |
| `ProofBundleManifest` | #12 | One-command proof index. |
| `OutageMatrixReport` | #13 | Dependency failure/recovery receipt. |

## Hard Production Blockers

- real PII
- real KYC/KYB/liveness/sanctions/consortium contracts
- real fraud/default/chargeback/SAR labels
- real money movement or customer messaging authority
- legal approval for adverse action and SAR workflows
- production deployment target, SLOs, secrets manager, and on-call process

