---
project: fraud-v2
owner: Bryan
created_at: 2026-05-04
updated_at: 2026-05-06
status: current
version: 2
---

# Blockers And Vague Decisions

## Short Version

We can build the local laptop version now.

We cannot claim real production readiness until the blockers below are answered.

Local V1 means:

- synthetic data
- no real PII
- mock vendors
- simulated approve/block/SAR actions
- instant-cash fintech demo
- rules plus calibrated sklearn tabular baselines; XGBoost/LightGBM are optional
  next champions
- graph rules before GNN
- LLM for synthetic data and edge cases, not final fraud scoring

## True Production Blockers

These do not block the local build. They block real users, real money, real PII,
or real compliance claims.

| # | Blocker | ELI10 Meaning | Option A | Option B | Option C | Recommendation |
|---:|---|---|---|---|---|---|
| 1 | Real action authority | Who is allowed to say yes/no to a real customer? | Simulate actions only. Safe, fast, no legal harm. Not production. | Human-gated actions. Safer pilot, slower ops. | Auto-block/auto-approve. Fast, highest risk. | Local: simulate. Pilot: human-gated. Production auto-actions only after legal/product approval. |
| 2 | Jurisdiction | Which country's rules apply? | US-inspired only. Simple local default. | One real jurisdiction. Narrow and reviewable. | Global matrix. Complete but heavy. | Local: US-inspired. Production: pick first real jurisdiction before launch. |
| 3 | Credit/legal status | Is instant cash legally credit, wage access, cash advance, or something else? | Treat as non-credit demo. Fast, but may hide duties. | Treat as credit-adjacent. Safer reasons and audit trail. | Full credit compliance. Heavy, needs counsel. | Local: credit-adjacent safe reasons. Production: counsel decides. |
| 4 | Real PII | Can we store SSNs, IDs, faces, bank accounts? | Synthetic only. Safest. | Hashed/pseudonymous production-like data. Medium risk. | Raw PII. Highest risk, needs serious controls. | Local: synthetic only. Production: no raw PII until privacy/security design exists. |
| 5 | Consortium/vendor data | Can we use shared blacklists, KYC, liveness, device intel? | Mock adapters. Safe and testable. | Public datasets. Real-ish but incomplete. | Real vendors. Best signal, contracts/secrets needed. | Local: mock adapters. Production: vendor contract tests before use. |
| 6 | Auth/RBAC | Who can see decisions, reviews, and compliance drafts? | Local token. Simple, not production. | OIDC/RBAC. Realistic and manageable. | Full enterprise IAM. Strong, heavier. | Local: token plus role structure. Production: OIDC/RBAC required. |
| 7 | Audit retention | How long do we keep decisions and evidence? | Keep synthetic data forever. Fine locally. | Fixed retention windows. Better hygiene. | Immutable audit store plus legal schedule. Production-grade. | Local: keep synthetic. Production: legal retention schedule plus immutable audit path. |
| 8 | Fairness/disparate impact | Could the system unfairly hurt protected groups? | Exclude sensitive fields. Safer but blind to bias. | Include only for bias testing. Better eval, controlled. | Use in decisions. High legal/ethical risk. | Local: exclude from decisions, allow separate bias eval. Production: formal fairness review. |

## Still Vague, But Not Blocking Local Build

These are open for production, but we have safe local defaults.

| # | Vague Area | ELI10 Meaning | Options And Tradeoffs | Recommendation |
|---:|---|---|---|---|
| 1 | First fraud wedge | What exact fraud game are we simulating first? | Instant cash covers identity, device, graph, repayments. Card testing is simpler but narrow. Crypto graph is interesting but less aligned. | Use instant-cash fintech first. Add card testing and ATO inside it. |
| 2 | Labels | How do we know what was fraud? | Synthetic labels are controllable. Public labels are real-ish but incomplete. Real labels are best but unavailable/risky. | Use synthetic ground truth plus analyst labels now. |
| 3 | Label timing | When does the truth arrive? | Instant labels are easy but fake. Delayed labels are realistic and harder. | Every label must have `label_available_at`. No future leakage. |
| 4 | Data availability | Where do inputs come from? | Public datasets benchmark pieces. Simulator covers full product. LLM expands rare cases. Real data later. | Hybrid: simulator + LLM scenarios + public benchmarks. |
| 5 | KYC vendor shape | What does KYC return? | Generic mock is fast. Vendor-specific mock is more realistic. Real vendor waits on contract. | Start generic mock, keep adapter interface vendor-ready. |
| 6 | Device fingerprint | What identifies a device? | Synthetic IDs are safe. Browser fingerprints are realistic but privacy-sensitive. Real SDK is production work. | Synthetic device IDs plus hashed browser fingerprints. |
| 7 | Camera/deepfake | How do we detect virtual camera/deepfake? | EXIF metadata is cheap but weak. Liveness vendor is stronger but external. Multi-signal is best. | Metadata is a risk signal only. Never red-block from this alone. |
| 8 | Behavioral biometrics | Do we use keystrokes/mouse/touch? | Simulated telemetry is safe. Real instrumentation is invasive. Skip loses bot signals. | Simulate now. Real collection needs privacy review. |
| 9 | Payment rail economics | What does each rail cost and risk? | Fixed defaults let models train. Real fees are better. Sensitivity analysis shows range. | Use explicit local defaults plus sensitivity tests. Replace with real economics later. |
| 10 | Fraud typology scope | Which fraud types are in V1? | All types sounds complete but dilutes focus. One type is too narrow. Nine gives breadth while staying local and deterministic. | Local V1 covers synthetic identity, ATO, card testing, first-party fraud, money mule, APP scam, BEC, deepfake liveness, and bust-out. |
| 11 | Thresholds | What score means approve/review/block? | Fixed bands are easy. Cost-optimized bands are better. Human-approved bands are safest. | Start 0-20, 21-79, 80-100. Then optimize by profit. |
| 12 | Latency SLO | How fast must scoring be? | 50ms is hard. 500ms is realistic locally. 5s is too slow for realtime. | Local target: p95 decision under 500ms without vendors. |
| 13 | Throughput | How many events per second? | Tiny is easy but fake. A tracked 4.7k-event dataset is enough for clear visuals. Huge load belongs in generated receipts, not the repo. | Local target: pass capacity-profile receipts on laptop; keep 720-user/4,703-event fixture tracked and generate larger runs on demand. |
| 14 | Stream semantics | How do we avoid double actions? | At-least-once plus idempotency is simple and reliable. Exactly-once Flink is heavier. | Use at-least-once streams plus idempotent consumers and outbox. |
| 15 | Feature store | Where do live and training features live? | Explicit event-derived features are easiest to audit. Redis helps full mode. DuckDB/Parquet/Feast/Tecton add value only when online/offline parity or scale demands it. | Keep explicit builder + SQLite/Postgres + Redis cache now; add DuckDB/Parquet/Feast-compatible layer later if real parity pressure appears. |
| 16 | Graph database | How do we store entity connections? | NetworkX is easy but not production-like. Neo4j is good local graph UX. Postgres-only is simpler but weaker graph UX. | Neo4j full profile plus NetworkX test fallback. |
| 17 | GNN | Do we build graph neural networks now? | GNN is cool but needs labels and compute. Graph rules are explainable and faster. | Graph rules/features first. PyG/GNN only as shadow research. |
| 18 | LLM role | What should GPT-5.5 do? | Data generation is high value. LLM judge is useful but secondary. LLM scorer is hard to govern. | Use LLM for scenarios, edge cases, notes, safe-reason drafts, evals. Not final scoring. |
| 19 | UI scope | Who gets the first UI? | Analyst UI proves review. SRE UI proves ops. Compliance UI proves audit. All at once is too much. | First UI: analyst queue plus operator health dashboard. |
| 20 | Model governance | Who approves model changes? | Manual file swap is risky. Registry with eval report is better. Full model committee is production. | No active model without pinned artifact and eval report. |
| 21 | Incident response | What if false positives spike? | Ignore is unsafe. Circuit breaker helps. Runbook/on-call is production. | Local: circuit breakers and manual override. Production: incident runbook. |

## What To Build Next

The local M1-M8 product spine is implemented. Do not add more local scaffolding
unless it closes a visible demo, ML, reliability, or blocker-truth gap.

Next local work, if continuing:

- add optional XGBoost/LightGBM champion comparison behind optional deps
- add graph-feature baseline before any GNN claim
- add optional LLM scenario-manifest expansion with duplicate detection
- add live public-data adapters only after terms, rate limits, and no-PII
  boundaries are explicit

Why this remains safe:

- no real PII
- no real money
- no real vendors by default
- no real SARs
- no real customer actions

## One-Sentence Decision

Build the local fraud operating system now with synthetic data and simulated
actions; treat production law, PII, vendors, RBAC, retention, fairness, and real
auto-actions as explicit blockers.
