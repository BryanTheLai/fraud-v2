---
project: fraud-v2
owner: Bryan
created_at: 2026-05-06
status: current
source: https://www.bryanslab.com/blogs/fraud-2/
---

# Target Goal Gap And Issue Spec

## Intent

Build the Bryan's Lab Fraud Detection V2 article as a truthful, local-first,
production-shaped fraud lab. The repo must show what is real, what is simulated,
what is blocked, and what is still vague.

This is not a demo that pretends to have regulated production powers. The local
product proves architecture, contracts, feature logic, graph explanations,
review workflows, model evaluation, observability, resilience, and operating
discipline without real PII, real money movement, real vendor calls, or real
compliance filings.

## Target Goal Summary

The target article describes five layers:

| Article Layer | Target Capability |
|---|---|
| Layer 1: Gateway | KYC/KYB shape, deep camera/device metadata, synthetic identity surveillance, and consortium-risk signals. |
| Layer 2: Real-time orchestration | Unified Kappa-style stream processing, feature freshness, online/offline parity, and circuit breakers. |
| Layer 3: Decision engine | Heterogeneous graph risk, behavioral entropy, graph explanation UI, and GNN-ready feature boundaries. |
| Layer 4: Action, operations, compliance | Green/yellow/red action ladder, review queue, active learning, adverse-action-safe reasons, SAR draft boundaries, and dependency fallback. |
| Layer 5: MLOps feedback loop | Point-in-time correctness, calibration, Recall at 1 percent FPR, Brier score, PSI drift, Cohen's Kappa, shadow deployment, and custom profit objective. |

## Current State Versus Target

| Area | Current Truth | Gap | Decision |
|---|---|---|---|
| Gateway metadata | Local signal lab and mock/public-shape connectors exist. | No unified gateway signal contract tying KYC, KYB, liveness, device, public registry, and consortium mocks into decision features. | Implement now locally. |
| Synthetic identity surveillance | Deterministic synthetic generator covers rings and typologies. | No explicit birth-to-credit/impossible-timeline feature pack or novelty ledger for LLM-generated edge cases. | Implement now locally. |
| Consortium data | Mock risk list concept exists in docs. | No contract, feed schema, stale-feed behavior, or permitted-use flag. | Simulate locally; defer real provider. |
| Stream orchestration | Redpanda consumer, outbox, DLQ, lag, stream health, and supervisor exist. | Need one freshness/skew dashboard proving online/offline parity on the same feature definitions. | Implement now locally. |
| Feature store | Explicit event-derived feature builder exists; Redis cache exists in full profile. | Need feature-definition registry with source event IDs, freshness SLO, and parity tests. | Implement now locally. |
| Decision engine | Rules + graph features + threshold policy + model shadow pieces exist. | Need a formal hybrid decision contract showing rule score, model score, graph score, fallback reason, and final action. | Implement now locally. |
| Graph intelligence | NetworkX graph service, Neo4j projection, graph dashboard exist. | Need graph feature pack for WCC/community, shortest-path-to-fraud, supernode guard, and analyst explanation cards. | Implement now locally. |
| GNN | PyG optional extra exists as future path. | No real labels or scale for GNN. | Defer; keep graph-feature boundary ready. |
| Behavioral entropy | Synthetic behavior events and rules exist. | Need documented entropy feature definitions and false-positive counterexamples. | Implement now locally. |
| Action ladder | Green/yellow/red thresholds and simulated actions exist. | Need action contract preventing UI/API from implying real blocks, real SAR filing, or real customer messaging. | Implement now locally. |
| Manual review | Review cases and analyst decisions exist. | Need active-learning loop report: label event created, retrain candidate, IRR/Kappa from reviewer matrix. | Implement now locally. |
| Compliance | Safe reasons, evidence export, draft boundaries, audit chain exist. | Need adverse-action/SAR package spec with blocked/allowed fields, human approval gate, and no-filing proof. | Implement now locally. |
| ML baseline | sklearn baseline, registry, shadow scoring, eval dashboard exist. | Need champion/challenger model benchmark with optional XGBoost/LightGBM, calibration curve, profit objective, and rollback criteria. | Implement now locally, CPU-first. |
| Drift | PSI and simulated Kappa reports exist. | Need drift alert scenarios and shadow-deployment promotion gate tied to registry. | Implement now locally. |
| Observability | Prometheus/Grafana, logs, trace IDs, local trace reports, stream health exist. | Need one proof bundle tying request trace, decision trace, audit entry, stream lag, and dashboard screenshot per scenario. | Implement now locally. |
| Backups/resilience | SQLite and Postgres backup rehearsals exist. | Need outage matrix for Postgres, Redis, Redpanda, Neo4j, model registry, and trace export paths. | Implement now locally. |
| Production deployment | Docker local/full profile exists. | No cloud target, real SLO, or production secrets manager. | Defer until target environment exists. |

## Vagueness Register

| Ambiguous Item | Why It Matters | Options | Blockers | Next Practical Step |
|---|---|---|---|---|
| First production wedge | Fraud rules and laws differ across lending, banking, payments, ecommerce, payroll, and crypto. | Keep instant-cash; switch to ATO; switch to card testing; create multi-domain framework. | Real product owner and action authority. | Keep instant-cash as local V1; write product-wedge decision record. |
| Real labels | ML value depends on verified fraud/default/chargeback/SAR/review labels. | Synthetic only; public PaySim-like; redacted real labels; vendor labels. | Privacy, contracts, label governance. | Implement label-source taxonomy and delayed-label windows. |
| PII boundary | Real SSNs, documents, addresses, biometrics, and bank accounts change the entire security model. | No PII; hashed/synthetic PII; encrypted local PII; production vault. | Legal/privacy approval, DLP, retention, encryption. | Keep no-PII default and add PII refusal tests. |
| Real KYC/KYB/liveness vendors | Provider response schemas and failure modes shape policy. | Mock; one vendor; adapter interface; vendor marketplace. | Vendor contracts, money, permitted use. | Build adapter contract and failure matrix with mock implementations. |
| Consortium risk feed | Shared intelligence can be powerful but regulated and contractual. | No feed; local mock feed; purchased provider; partner exchange. | Enterprise access, legal basis, data sharing terms. | Simulate stale/fresh/mock feed and mark as blocked for production. |
| SAR filing | The article says SAR filed for red cases, but local software must not file. | No SAR; draft only; human-approved filing; vendor workflow. | BSA/FinCEN process, compliance officer, filing credentials. | Keep draft-only and add UI/API language guardrails. |
| Auto-block authority | Blocking real users creates legal, financial, and UX harm. | Simulate block; hold for review; real block; customer friction. | Product/legal approval and customer support operations. | Keep simulated action contract and require manual approval for real rails. |
| Credit/adverse-action status | Instant cash may trigger ECOA/Reg B style obligations. | Treat as credit-adjacent; non-credit fraud control; jurisdiction-specific. | Counsel and product definition. | Produce adverse-action-safe reason package without legal claim. |
| Real-time latency target | Architecture differs for 50ms, 500ms, 5s, and batch. | Local p95 <500ms; stream near-real-time; managed feature platform. | Real traffic profile and SLO. | Add local latency budget and capacity receipt to proof bundle. |
| Online/offline parity | Training-serving skew can create false-positive storms. | Manual shared code; feature registry; Feast/Tecton; custom DuckDB/Redis parity. | Real scale and platform access. | Implement local feature-definition registry and parity report. |
| Graph database target | NetworkX, Neo4j, Postgres CTEs, warehouse graph, and managed graph each change ops. | NetworkX lite; Neo4j full; managed graph; graph features only. | Production scale and deployment target. | Keep NetworkX/Neo4j split and add graph feature tests. |
| GNN timing | GNNs need graph labels, scale, and eval discipline. | No GNN; optional PyG experiment; production GNN. | Labels, GPU/infra, explainability. | Defer GNN; implement graph-feature baseline first. |
| LLM role | LLM fraud decisions are non-deterministic and hard to govern. | Synthetic generator; analyst note helper; evaluator; final scorer. | Governance, cost, determinism. | Use LLM only for synthetic scenarios and eval notes; never final action. |
| Production auth | Local role tokens do not equal enterprise auth. | Local token; JWT/JWKS; OIDC; SSO/RBAC. | IdP, secrets manager, user lifecycle. | Keep local auth and write OIDC/RBAC adapter issue. |
| Retention and audit immutability | Evidence retention and legal holds differ by jurisdiction. | Local hash chain; WORM object storage; legal hold service. | Counsel, cloud target, storage budget. | Keep local audit archive; specify production WORM boundary. |
| Fairness/disparate impact | Fraud systems can encode protected-class proxies. | Exclude demographics; synthetic fairness eval; real fairness review. | Real protected-class governance and counsel. | Add synthetic fairness probe and explicit blocked status for production. |

## Production-Level Local Contracts

### Canonical Events

Existing canonical event envelope stays the system boundary:

- `EventEnvelope`
- `ApplicationSubmitted`
- `DeviceObserved`
- `CameraMetadataObserved`
- `LoginAttempt`
- `BehavioralSignalObserved`
- `PaymentAttempted`
- `PaymentSettled`
- `ChargebackReceived`
- `ManualReviewDecided`
- `LabelCreated`

Required additions:

- `GatewaySignalObserved`
  - inputs: `provider`, `signal_type`, `status`, `confidence`, `raw_reference`, `safe_summary`, `blocked_reason`
  - outputs: canonical event refs for user/device/application/business
  - local truth: mock/public shape only
- `ConsortiumRiskObserved`
  - inputs: `feed_name`, `entity_ref`, `risk_code`, `observed_at`, `expires_at`, `permitted_use`
  - outputs: graph edge and feature signal
  - local truth: mock feed only
- `SyntheticIdentitySignalObserved`
  - inputs: `timeline_gap_code`, `age_of_credit_days`, `identity_age_days`, `document_age_days`, `source`
  - outputs: feature values and safe reason candidates
  - local truth: generated only

### Feature Contracts

Every feature must expose:

- `feature_name`
- `entity_ref`
- `as_of`
- `value`
- `freshness_status`
- `source_event_ids`
- `source_window`
- `definition_version`
- `online_value`
- `offline_value`
- `parity_status`

Feature groups:

- Gateway: camera metadata, KYB status, liveness mock, consortium mock.
- Velocity: login/payment/application/device counts across windows.
- Behavioral: keystroke variance, mouse entropy, session duration.
- Graph: one-hop fraud, shortest path to fraud, shared-device degree, WCC/community size, supernode flag.
- Financial: amount, rail, Benford leading digit, prior chargeback/default.
- Reliability: model health, graph health, feature freshness, stream lag.

### Decision Contract

`DecisionResponse` must remain explainable and add enough surface for hybrid mode:

- `rules_score`
- `model_score`
- `graph_score`
- `final_score`
- `risk_tier`
- `action`
- `safe_reasons`
- `unsafe_internal_reasons`
- `reasoning_trace_id`
- `policy_version`
- `model_version`
- `feature_set_version`
- `degraded_dependencies`
- `simulated_action_only`

The local system must never return a real-world action claim. Red means
`SIMULATED_BLOCK` or `SIMULATED_HOLD` unless explicit production rails are added
later.

### Converter Classes

Required converter boundaries:

- `RawEventConverter`: application/payment raw rows to canonical events.
- `PaySimConverter`: public PaySim-style rows to canonical payment/application/label events.
- `GatewaySignalConverter`: mock KYC/KYB/liveness/device/consortium outputs to canonical gateway events.
- `LlmSyntheticCaseConverter`: LLM-generated edge-case JSON to canonical synthetic events after schema validation and novelty-ledger checks.
- `ReviewLabelConverter`: analyst outcomes to label events with delayed label availability.

Every converter must test:

- valid input
- missing required field
- malformed enum
- duplicate idempotency key
- unsafe PII-like input rejection when relevant

### Data Connections

| Connection | Local Mode | Full Mode | Production Blocker |
|---|---|---|---|
| App store | SQLite | Postgres | Managed database target and secrets. |
| Stream bus | Bounded local worker | Redpanda | Managed Kafka/Flink and SLO. |
| Graph | NetworkX | Neo4j Community | Managed graph sizing and access control. |
| Feature cache | In-process/SQLite-derived | Redis | Real feature store choice. |
| Metrics | Prometheus client | Prometheus/Grafana | Alertmanager/PagerDuty. |
| LLM | Offline by default | OpenAI/Azure optional | Budget, policy, no PII. |
| Vendors | Mock/public-shape only | Mock/public-shape only | Contracts, legal, credentials. |

## Issue Split

Each issue below is designed to be independently buildable and reviewable.

### Issue 1: Gateway signal contract and mock vendor matrix

Build canonical gateway events and converters for KYC/KYB/liveness/device and
consortium-shaped signals without real vendor calls.

Acceptance:

- Adds typed events/enums for gateway and consortium signals.
- Adds mock connector outputs and converter tests.
- Exposes failures: timeout, stale, denied, review, unknown, malformed.
- Decision engine can consume a gateway signal without vendor-specific code.
- Docs state real vendors are blocked.

### Issue 2: Synthetic identity surveillance and novelty ledger

Build deterministic synthetic identity timelines plus an LLM edge-case novelty
ledger.

Acceptance:

- Adds synthetic identity impossible-timeline scenarios.
- Adds `data/synthetic/novelty-ledger.jsonl`.
- LLM-generated cases must be rejected if duplicate by normalized signature.
- No real PII fields are accepted.
- CLI writes generated events and ledger entries.

### Issue 3: Feature registry and online/offline parity report

Make feature definitions explicit and prove online/offline parity locally.

Acceptance:

- Adds `FeatureDefinition` registry.
- Each feature returns source event IDs and definition version.
- Report compares online and offline feature values on the same event window.
- Test covers rounded-value skew.
- Cockpit or HTML report shows parity pass/fail.

### Issue 4: Stream freshness SLO and circuit-breaker proof

Tie stream lag, feature freshness, and degraded decision behavior together.

Acceptance:

- Adds feature freshness SLO config.
- Decisions list degraded dependencies when freshness fails.
- Stream health report links lag to stale features.
- Tests simulate stale stream and verify yellow/manual-review fallback.
- UI shows degraded mode without claiming certainty.

### Issue 5: Graph feature pack and supernode guard

Turn graph evidence into measurable graph features.

Acceptance:

- Adds shortest path to fraud, shared-device degree, WCC/community size, and supernode flag.
- Adds tests for one-hop fraud, two-hop fraud, benign shared household, and supernode suppression.
- Graph dashboard shows feature values and relationship proof.
- No GNN is added.

### Issue 6: Hybrid decision contract and simulated-action guardrail

Formalize rules/model/graph score composition and prevent fake production
actions.

Acceptance:

- Decision response exposes rules, model, graph, final score, and fallback reason.
- All actions are explicitly simulated in local mode.
- Red tier never says real SAR filed or real funds blocked.
- Tests cover normal, model outage, graph outage, and stale-feature fallback.

### Issue 7: Manual review active-learning loop and IRR report

Make analyst review feed back into labels and model reports truthfully.

Acceptance:

- Review decisions create delayed `LabelCreated` events.
- Adds reviewer matrix fixture and Cohen's Kappa report.
- Retraining can include analyst labels after availability time.
- UI shows review outcome, label event, and retrain eligibility.

### Issue 8: Compliance package with adverse-action and SAR draft boundaries

Build a decision evidence package that is useful but cannot pretend to file.

Acceptance:

- Exports adverse-action-safe reasons and SAR draft separately.
- Redacts unsafe internals and raw PII-like fields.
- Requires human approval flag before export.
- Artifact says `DRAFT ONLY - NO FILING`.
- Tests reject `risk score only` reasons.

### Issue 9: Champion/challenger ML benchmark

Make ML pragmatic: calibrated tabular baselines first, optional stronger
champions only if locally runnable.

Acceptance:

- Benchmarks logistic regression/random forest and optional XGBoost or LightGBM if installed.
- Reports AUPRC, Recall at 1 percent FPR, Brier, profit, calibration, and feature importance.
- Registry can mark best model as shadow, not active by default.
- No LLM final scorer.

### Issue 10: Drift, shadow deployment, and rollback gate

Connect drift reports to model promotion and rollback.

Acceptance:

- PSI drift scenarios are generated locally.
- Shadow scores are compared against active rules outcome.
- Promotion fails when Brier/profit/PSI thresholds fail.
- Rollback command demotes active model and records audit entry.

### Issue 11: Full-profile outage matrix and recovery receipts

Prove local production shape across dependencies.

Acceptance:

- Tests or scripts simulate Postgres, Redis, Redpanda, Neo4j, model artifact, and trace-export failures where practical.
- Writes JSON/HTML outage matrix.
- Shows expected fallback for each dependency.
- Includes backup/restore receipt link.

### Issue 12: Proof cockpit and one-command local demo bundle

Make presentation dense, clean, and complete.

Acceptance:

- One command resets data, runs benchmark/report generation, starts API, and writes proof artifacts.
- Cockpit links scenario, graph, model, review, compliance draft, audit trace, stream health, and blockers.
- Screenshots are generated for cockpit desktop/mobile and graph depth scenario.
- README points to the proof bundle.

## Review Gates For Every Issue

Every PR must include:

- tests for the changed behavior
- docs for real/fake/blocked status
- screenshot or HTML artifact for UI/report changes
- `uv run ruff format --check .`
- `uv run ruff check .`
- `uv run mypy src`
- `uv run pytest -q`

If the issue touches Docker/full profile, also run:

- `docker compose -f infra\docker-compose.yml --profile full config --quiet`
- `docker build -t fraud-v2:local .`

