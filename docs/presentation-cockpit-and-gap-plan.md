---
project: fraud-v2
owner: Bryan
created_at: 2026-05-05
status: active-plan
---

# Presentation Cockpit And Blog Gap Plan

## Decision Rule

For every meaningful gap, separate:

- effort to build: mostly ignore; AI can produce code and docs cheaply.
- resource access: evaluate hard; vendor contracts, real PII, regulated data,
  money movement, enterprise APIs, legal approval, and hardware are real blockers.
- practical value: implement the version that makes the local demo more truthful
  and useful first.

## Current Continue/Pause Register

Date: 2026-05-05.

Implementation update:

- `/demo` cockpit exists with seeded scenario buttons, custom run controls, and
  local reset.
- `/dashboard/cases/{case_id}` exists with timeline, reasons, features, graph,
  and decision rail.
- `/dashboard/ops` exists as a human-readable metrics page; raw Prometheus
  remains at `/metrics`.
- `/dashboard/ml` exists and reads `data/models/baseline/baseline-report.json`.
- `fraud-v2 mlops-report` writes a local PSI/Kappa report and `/dashboard/ml`
  renders it when `data/local/mlops-report.json` exists.
- `/dashboard/signals` and `fraud-v2 signal-lab` show local camera metadata and
  public-KYB-style checks without external vendor calls.
- Yellow case rails can render a Break-the-Spell draft checklist; no real
  customer message is sent.
- Graph SVG now has a legend, node type markers, confirmed-fraud styling, and
  highlighted target/fraud edges.
- Feature vectors now include `declared_income_leading_digit` and
  `benford_declared_income_deviation` for the Instant Cash/Benford lane.
- Real KYC/KYB, PII, real money actions, real SAR filing, production auth, cloud
  deploy, and production GNN remain paused resource/legal blockers.

| Item | Still Vague Or Blocked | Main Options | Tradeoff | Decision |
|---|---|---|---|---|
| Demo cockpit | Exact UI route and flow are not built yet. | Keep plain dashboard; add `/demo`; replace dashboard. | Replacing dashboard risks churn. Separate `/demo` gives a presentation surface without losing current proof. | Continue: add `/demo`. |
| Old TNG RiskOps UI reuse | Source code not found locally. | Copy visual pattern; find old repo; rebuild from scratch. | Source reuse is fastest only if repo exists. Pattern reuse is enough. | Continue: reuse pattern, not code. |
| Analyst case detail | Current dashboard has rows but no full case file. | Row-only; drawer; case page. | Case page is best for presentation and evidence. | Continue: build case page. |
| UI-based simulation | Manual CLI/API is too hidden for demo. | CLI only; scenario buttons; customizable builder; raw JSON. | Buttons are presentable. Builder proves flexibility. Raw JSON is power-user only. | Continue: buttons plus advanced JSON/knobs. |
| Demo reset | Counters get messy after scoring. | No reset; CLI reset; UI reset; snapshots. | UI reset is best but must only touch local demo data. | Continue: CLI reset plus UI reset. |
| Graph visual | Current graph is truthful but flat. | Better SVG; Cytoscape.js; D3; Neo4j Browser. | Better SVG is low-risk. Cytoscape is better later. | Continue: improve SVG now; pause Cytoscape. |
| Graph ML | Blog implies GNN/message passing. | Rules only; graph features; node2vec; GraphSAGE/PyG. | True GNN is attractive but easy to fake without labels. Graph features are honest and useful. | Continue: graph features; pause production GNN. |
| Metrics UX | Raw Prometheus is machine-facing. | Keep raw only; add `/dashboard/ops`; rely on Grafana. | Raw stays required. Grafana needs full mode. Human ops page helps lite mode. | Continue: add `/dashboard/ops`. |
| ML dashboard | Model pieces exist but are not prominent. | Static report only; in-app ML dashboard; notebook. | In-app dashboard makes the ML project visible. Notebook is less demoable. | Continue: build ML dashboard. |
| Tabular ML | Current sklearn baseline exists. | Keep sklearn; add XGBoost/LightGBM optional; deep models. | XGBoost/LightGBM likely best practical next step; deep models need more data. | Continue: optional XGBoost/LightGBM; pause deep model as default. |
| Calibration and profit | Evaluations exist but not front-and-center. | Leave report; add charts; add threshold tuner. | Charts/tuner make the fraud economics real. | Continue. |
| Drift and PSI | Real production drift needs real reference/current data. | Static metric; drift simulator; ops alert. | Simulator is useful for demo but not a production monitoring claim. | Implemented local simulator/report; keep real production drift paused until real traffic. |
| Cohen's Kappa / IRR | Real IRR needs multiple analysts. | Ignore; simulate second reviewer; real analysts. | Real analysts unavailable. Simulation proves math only. | Implemented simulated reviewers; pause real analyst QA until real reviewers exist. |
| KYC/KYB | Real production access is not available in repo. | Mocks; sandbox adapters; public registries; real vendors. | Real vendors need accounts, billing, secrets, legal/privacy review. Public data is safe but incomplete. | Continue mocks/public/sandbox; pause production KYC/KYB. |
| Public KYB-like data | Live source choice and terms remain production questions. | Companies House; GLEIF; OFAC/OpenSanctions-style datasets. | Public data helps demo but is not a full vendor replacement. | Implemented local public-KYB-shaped demo; pause live calls. |
| Liveness/deepfake | No real vendor or real biometric pipeline. | Metadata only; EXIF upload; sandbox liveness; ML deepfake detector. | Metadata is cheap and visible but weak. Real liveness is vendor/legal heavy. | Implemented local metadata demo; pause real liveness. |
| Behavioral biometrics | Real client telemetry is privacy-sensitive. | Synthetic only; browser demo telemetry; real capture. | Browser demo is useful but must be clearly synthetic/local. | Continue synthetic + UI knobs; pause real capture. |
| Consortium data | Real shared fraud intel is enterprise/contractual. | Mock list; public sanctions/entity data; real consortium. | Public data is not consortium fraud intelligence. | Continue mock/public; pause real consortium. |
| Instant Cash story | Current app is broad; story needs a clear wedge. | ATO; instant cash; card testing; all-at-once. | Instant cash best matches blog's first-party fraud/economics. | Continue: make Instant Cash primary. |
| Benford's Law | Blog names it; app does not visibly show it. | Ignore; add synthetic income signal; add chart/test. | Easy and aligned with blog. | Continue. |
| Break-the-Spell | Blog names APP/BEC intervention. | Ignore; simulated prompt; real messaging. | Real messaging is external action; simulated prompt is safe. | Implemented simulated draft only; pause real messaging. |
| Compliance drafts | Drafts exist but UI not visible enough. | Keep CLI; add case export; real filing. | Real filing forbidden. UI export proves boundary. | Continue draft/export; pause real filing. |
| SAR/adverse action | Legal scope still blocked. | Draft-only; counsel-reviewed pilot; real filing. | Real filing requires legal authority. | Pause production; continue draft-only. |
| Real PII | Explicitly blocked. | Synthetic; redacted sample; real PII. | Real PII changes security/legal obligations. | Pause real PII; continue synthetic/redacted-only design. |
| Real money actions | Explicitly blocked. | Simulated actions; human-gated sandbox; real actions. | Real actions require rails and authority. | Pause real actions; continue simulation. |
| Production auth/RBAC | Local token is not production access control. | Keep token; OIDC/JWT; enterprise IAM. | OIDC is useful later but not needed for laptop demo. | Pause for now; keep role-shaped local auth. |
| Full cloud deployment | Local Docker exists, cloud target unknown. | Stay local; single VM; managed cloud/Kubernetes. | Cloud/IaC depends on target and budget. | Pause; keep local-first. |
| GitHub PR/push | No remote/auth previously configured. | Local commits only; configure origin/gh auth. | Needs operator login. | Pause until `gh auth login` and remote exist. |
| Synthetic data expansion | Current data is enough but narrow. | Deterministic generator; LLM edge cases; public datasets. | Deterministic base keeps tests stable. LLM adds breadth. | Continue: deterministic core plus LLM edge cases. |
| LLM role | Tempting to use as scorer. | Data generation; analyst note drafting; final risk scoring. | LLM scoring is non-deterministic and hard to govern. | Continue for data/eval/notes; pause final scoring. |
| Production claim | Tempting to call it production-ready. | Production-shaped local lab; regulated production system. | Truth matters. | Continue calling it local lab; pause production claims. |

## Old TNG RiskOps UI

The old TNG RiskOps Agent screenshots are reusable as a product pattern, not as
code unless the source repo is provided. A local search for `TNG RiskOps`,
`CASE-ATO`, `Decision rail`, and related strings did not find that code in this
GitHub folder.

What to reuse:

- Dense queue layout.
- Clear top-level summary cards.
- Primary case detail page.
- Right-side decision rail.
- Action ladder.
- Timeline-first case explanation.
- Plain operational visual style.
- Strong labels for state, score, next action, and evidence.

What not to copy blindly:

- ATO-only language. `fraud-v2` is broader: instant cash, synthetic identity,
  graph risk, first-party fraud, chargebacks, review, and model governance.
- Chat/WhatsApp-specific actions unless we build a simulated "Break the Spell"
  intervention.
- Freeze-account wording unless the action is simulated and clearly labeled.

Recommendation: implement the same information architecture with local
FastAPI-rendered HTML/CSS. Keep it plain, dense, and serious.

## Minimum Cockpit

Build `/demo` or make `/dashboard` into a cockpit.

| Surface | Possible Solutions | Tradeoffs | Recommendation |
|---|---|---|---|
| Main route | Keep `/dashboard` only; add `/demo`; replace `/dashboard` entirely | Keeping only dashboard is simple but cramped. Separate `/demo` is clearer for presentation. Replacing risks breaking current proof surface. | Add `/demo`, keep `/dashboard` as current analyst surface. |
| Scenario runner | Manual CLI; fixed UI buttons; editable scenario builder; raw JSON editor | CLI is reliable but not presentable. Buttons are fastest. Builder proves flexibility. JSON editor is powerful but intimidating. | Buttons plus an "advanced JSON" drawer. |
| Demo reset | Do nothing; CLI reset; UI reset button; seeded scenario snapshots | No reset makes demos messy. CLI reset is okay. UI reset is best for presentation but must be safe. | Add `fraud-v2 demo-reset` and a UI reset button that only touches local demo DB. |
| Decision display | Table row only; detail drawer; dedicated case page | Row is too shallow. Drawer is good for speed. Case page is best for screenshots. | Add decision/case detail page. |
| Evidence | Reasons only; graph only; timeline only; all together | Single evidence type under-explains. All together can be dense. | Use case page: reasons, feature values, graph, timeline, audit trace. |
| Actions | Read-only; simulated approve/review/block; analyst override; compliance export | Read-only is safe but weak. Simulated actions show workflow. Real actions are forbidden. | Simulated actions only, visibly labeled. |
| Article map | Docs only; in-app coverage map | Docs are useful but invisible in demo. | Add "Blog layer coverage" panel in `/demo`. |

## Graph Improvements

Current graph proves relationships but looks visually flat.

| Problem | Possible Solutions | Tradeoffs | Recommendation |
|---|---|---|---|
| Nodes look same | More colors; icons; grouped lanes; size by risk | Colors alone are weak. Icons/lane grouping make meaning faster. | Add entity-type icons, legend, and lane/group labels. |
| Fraud path unclear | Highlight shortest path; highlight only risky edges; fade background graph | Highlighting makes the story obvious. Too much fading can hide context. | Highlight target-to-risk-cluster path and keep rest muted. |
| Labels too small | Bigger text; tooltips; side detail panel | Bigger text may clutter. Tooltips need JS. Side panel scales better. | Bigger primary labels plus side evidence panel. |
| Edges unexplained | Edge labels; relationship table; edge badges | Labels clutter SVG. Table is readable. | Keep table, group it by relationship type, and show edge badges only for critical edges. |
| Static layout | Hand-rolled SVG; Cytoscape.js; D3; vis-network | SVG has zero dependency but limited interaction. Cytoscape is best for graph UI. D3 is flexible but more work. | Improve SVG now; add Cytoscape later if graph becomes the main demo. |

## Metrics Page

Keep `/metrics` raw for Prometheus. Add a human page.

| Surface | Possible Solutions | Tradeoffs | Recommendation |
|---|---|---|---|
| Raw metrics | Keep only raw; hide raw; keep raw plus friendly page | Raw is needed for Prometheus. Bad for humans. | Keep `/metrics`; add `/dashboard/ops`. |
| Ops summary | Text stats; cards; sparklines; Grafana only | Cards are fast. Sparklines help trend. Grafana is powerful but full-mode only. | Add cards now, link Grafana in full mode. |
| What to show | HTTP metrics only; fraud metrics only; full SRE + ML | HTTP-only is too generic. Fraud-only misses reliability. | Show decision count by tier, p95 latency, errors, review queue, DLQ, feature freshness, model version. |
| Alert meaning | Raw thresholds; plain action ladder | Raw thresholds are operator-unfriendly. | Add "healthy / watch / broken" labels with reason. |

## UI-Based Simulation

Manual simulation should become a first-class local feature.

| Scenario | Inputs | Expected Result | Build Now |
|---|---|---|---|
| Clean applicant | normal device, normal behavior, no chargeback, no bad graph | Green / Approve | Yes |
| Virtual camera | missing camera make/model, low entropy | Yellow / Review unless combined with stronger signals | Yes |
| Fraud ring neighbor | shared payee/device/IP near confirmed fraud | Yellow / Review | Yes |
| Confirmed fraud | chargeback plus confirmed fraud label | Red / Block | Yes |
| First-party instant cash | loan/payout attempt, repayment default label later | Yellow/Red depending history | Yes |
| APP/BEC intervention | transfer to risky beneficiary with unusual session | Yellow plus "Break the Spell" prompt | Simulated now |
| KYB suspicious company | stale company, bad sanctions/LEI/public registry signal | Review | Mock/public-data now |

Add scenario customization:

- amount
- device age
- IP/geo
- payee reuse
- camera metadata
- behavior entropy
- prior chargeback
- graph distance to confirmed fraud
- delayed label timing
- model/rule policy version

## Blog Gap Matrix

| Category | Blog Target | Current State | Possible Solutions | Tradeoffs | Recommendation |
|---|---|---|---|---|---|
| KYC/KYB gateway | Real identity/business verification | Mock boundaries only | Keep mocks; add sandbox vendor adapter; add public-data KYB; integrate real vendor | Mocks are safe. Sandbox proves wiring but not real verification. Real vendor needs account, billing, legal/privacy review. | Build adapter interfaces and public/sandbox demos. Do not use real production KYC/KYB by default. |
| Liveness/deepfake | Real liveness/deepfake defense | Simulated camera metadata | Keep synthetic signals; add image upload + EXIF scan; add vendor sandbox; add ML deepfake model | EXIF is cheap but weak. Vendor sandbox is realistic but external. Deepfake ML is heavy and easy to oversell. | Add EXIF/image metadata demo. Keep liveness vendor mocked. |
| Synthetic identity | Birth-to-credit and long-con surveillance | Synthetic labels and chargebacks | Add synthetic identity timeline; add credit-builder simulator; use public credit-like data if available | No real credit bureau data. Synthetic timeline is enough for local proof. | Build timeline simulator and case page. |
| Consortium data | Shared fraud intel | Mock/local signals | Keep mock; use OpenSanctions/OFAC for sanctions-like public data; vendor/consortium later | Public data is not consortium fraud intel. Real consortium requires contracts. | Add public sanctions/entity dataset connector; keep consortium mocked. |
| Real-time/Kappa | Unified stream processing and online/offline parity | Redpanda/outbox in full mode, SQLite lite | Keep current; add replay parity tests; add Feast-style interfaces; add Flink | Flink is resource/complexity heavy. Parity tests give most value. | Add parity test/report before Flink. |
| Feature freshness | Freshness metrics and circuit breakers | Feature freshness fields and metrics exist | Surface in UI; add stale-feature simulation; add breaker dashboard | UI makes it demoable. | Build `/dashboard/ops` freshness panel. |
| Graph/GNN | Heterogeneous graph and inductive GNN | NetworkX graph rules, Neo4j adapter | Better graph rules; node embeddings; PyG GraphSAGE; full GNN service | GNN needs labels and careful eval. Node embeddings are simpler ML proof. | Add graph-feature ML baseline first; defer PyG GNN to research mode. |
| Behavioral entropy | Real human interaction telemetry | Synthetic behavior events | Keep synthetic; add browser telemetry demo; add privacy-gated real collection | Real telemetry is privacy-sensitive. Synthetic is safe. | Add UI knobs and synthetic generator expansion. |
| Graph UI | Analyst spider-web explanation | Static SVG | Improved SVG; Cytoscape.js; Neo4j Browser link | SVG is lowest-risk. Cytoscape is best app UX. | Improve SVG now; plan Cytoscape if graph becomes central. |
| Action ops | Green/yellow/red with friction/block | Implemented as safe simulated decisions | Add decision rail; add action ladder; add simulated intervention; add real actions | Real actions forbidden. Simulated actions make demo real enough. | Build decision rail and action ladder. |
| Manual review | Analyst queue feeds labels | API/model exists, light UI | Queue table; case detail; analyst labels; IRR dashboard | Case detail gives biggest demo gain. IRR needs multiple reviewers or simulated reviewers. | Build case detail + simulated second reviewer for Kappa demo. |
| Compliance | Adverse reasons and SAR | Safe reasons and draft-only compliance | Keep drafts; add export; add reason quality checks; real filing | Real filings forbidden. | Add visible draft/export flow, clearly "human review only". |
| MLOps | PIT correctness, calibration, PSI, Kappa, Recall@1% FPR, profit | Training/eval pieces exist | Add ML dashboard; add threshold tuner; add drift simulator; add model registry UI | High demo value. Resource-light. | Build ML dashboard. Important for making this an ML project. |
| Instant Cash | First-party fraud, Benford, chargeback ratio, idempotency, Break the Spell | Payments/chargebacks/idempotency concepts exist partially | Add Benford feature; repayment/default labels; chargeback ratio; intervention UI | Very aligned with blog. Mostly local/synthetic. | Build now. |
| Production auth/RBAC | Real operator controls | Local token roles | Keep local; add OIDC later | OIDC not needed for laptop demo. | Keep local token; document production blocker. |

## KYC/KYB Reality

You probably do not have production KYC/KYB access unless you already created
vendor accounts, passed approval, configured billing, and stored credentials.
The repo intentionally has no real KYC/KYB credentials.

Free-ish paths:

- Stripe Identity: self-serve identity verification exists, with limited free
  initial verifications and test mode. Production use still involves Stripe
  account setup and handling real identity data.
- Persona, Onfido/Entrust, Sumsub: sandbox/test environments exist. They are
  useful for integration shape, not real verification.
- Companies House, GLEIF, OFAC: public datasets/APIs can support KYB-like or
  sanctions-like demos. They are not full KYC/KYB vendors.

Recommendation: add provider-shaped adapters but default to mock/public/sandbox.
Never require real vendor credentials for local startup.

## ML Project Emphasis

Make the product visibly ML-heavy without pretending an LLM is the fraud model.

Build now:

- model training report page
- precision/recall and Recall@1% FPR
- calibration/Brier chart
- profit curve and threshold selector
- score distribution, PSI drift, and simulated analyst Kappa
- feature importance
- graph-feature baseline
- shadow model comparison
- synthetic edge-case generator for training/eval

Defer:

- production GNN service
- real behavioral biometric capture
- real vendor-derived features
- real PII labels

Research lane:

- node2vec/GraphSAGE on synthetic graph
- LightGBM/XGBoost optional baseline
- LLM-generated scenario manifests with duplicate/coverage checks
- adversarial edge-case generation

## Recommended Build Order

1. `/demo` cockpit with scenario buttons, reset, and result panel.
2. Case detail page using TNG-style timeline, facts, missing data, decision rail.
3. Graph visual upgrade: legend, highlight path, grouped relationship table.
4. `/dashboard/ops` human metrics page, keep raw `/metrics`.
5. ML dashboard: training report, calibration, PSI, Kappa, profit curve, Recall@1% FPR.
6. Instant Cash expansion: Benford, repayment/default timeline, chargeback ratio,
   idempotency proof, Break-the-Spell simulated prompt.
7. Public-data adapters: local public-KYB-shaped connector exists; live
   OFAC/GLEIF/Companies House calls stay paused until terms, rate limits, and
   secrets/access are decided.
8. Optional sandbox adapters for Stripe Identity or Persona only if credentials
   are available and the integration is clearly marked as sandbox.
