---
project: fraud-v2
owner: Bryan
created_at: 2026-05-04
updated_at: 2026-05-06
status: current
source_task: TC-20260504-002
version: 1
---

# Data Strategy

## Goal

Fraud V2 needs data that exercises the whole system:

- identity/application
- device/session
- camera metadata
- behavior telemetry
- payment/transaction
- repayment/default/chargeback
- graph relationships
- manual review
- decision traces
- delayed labels
- edge cases and false positives

No single public dataset covers all of this. The local build must use a hybrid
data plan.

## Data Sources

| Source | Can We Get It? | Auth/Access | Covers | Misses | Use |
|---|---|---|---|---|---|
| Deterministic simulator | yes | none | Full local schema, labels, graph, delayed outcomes. | Real-world messiness unless modeled. | Primary V1 data. |
| GPT-5.5/Azure/OpenAI synthetic generation | yes, assuming tokens and endpoint access | API credentials | Rare scenarios, edge cases, analyst notes, malformed payloads, false-positive stories. | Must validate; not statistical truth. | Scenario expansion and fuzzing. |
| IEEE-CIS/Vesta fraud dataset | likely, via Kaggle or mirrors | Kaggle/account depending source | Ecommerce transaction and identity-like fields with fraud label. | No full graph, no manual review, anonymized fields. | Benchmark tabular models. |
| PaySim | yes, public synthetic dataset | Kaggle/GitHub/paper | Mobile money transfer fraud and high-volume synthetic transactions. | No identity/KYC graph depth. | Payment behavior benchmark and generator inspiration. |
| BankSim | yes, public synthetic dataset | Kaggle/paper | Bank payment simulator and fraud scenarios. | Older dataset; not identity/device-heavy. | Simulator inspiration and benchmark. |
| Elliptic Bitcoin | yes, public crypto graph dataset | Kaggle/provider page | Labeled transaction graph for illicit/licit classification. | Crypto-specific, not instant-cash KYC. | Graph ML benchmark. |
| Real KYC/device/payment vendor data | no for local V1 | contracts/secrets | Production signal. | Not available and high-risk. | Mock only until approved. |
| Real customer data | no | legal/security approval | Best production evidence. | PII, compliance, breach risk. | Explicitly out of local V1. |

## Recommendation

Use four data streams:

1. `simulated_core`: deterministic local simulator that covers every domain
   contract and label.
2. `llm_scenarios`: GPT-generated scenario specs and edge cases that are fed
   into the simulator, not trusted directly.
3. `public_benchmarks`: IEEE-CIS, PaySim, BankSim, Elliptic where available.
4. `manual_review_labels`: analyst outcomes created inside the local UI.

## Synthetic Data Generator Shape

The simulator should generate:

| Object | Fields | Notes |
|---|---|---|
| `SyntheticPerson` | stable ID, age band, income band, address cluster, phone/email hashes | No real PII. |
| `SyntheticApplication` | product, requested amount, declared income, submitted_at, channel | Primary scoring target for instant cash. |
| `SyntheticDevice` | device ID, browser fingerprint, user agent family, timezone, emulator flag | Shared devices create graph risk. |
| `SyntheticSession` | login attempts, session age, IP, geo, behavior signals | Drives ATO and automation features. |
| `SyntheticCameraMetadata` | camera make/model/software tags, missing EXIF flags | Deepfake/virtual camera signal only. |
| `SyntheticPaymentInstrument` | card/bank/payment token hash, rail, account age | No real PAN/account numbers. |
| `SyntheticTransaction` | amount, merchant/payee, rail, status, created_at | Drives payment risk. |
| `SyntheticRepayment` | due date, paid date, amount, status | Drives first-party fraud/default labels. |
| `SyntheticDispute` | chargeback/default/fraud report, reported_at | Delayed label source. |
| `SyntheticReview` | analyst ID, outcome, confidence, notes | Label loop and IRR. |
| `SyntheticGraphRing` | shared devices/cards/addresses/IPs, mule paths | Graph fraud clusters. |

## Fraud Typologies To Generate

| Typology | Required Signals | Label Delay | False Positive Counterexample |
|---|---|---:|---|
| Synthetic identity | impossible timeline, document reuse, thin file, shared identifiers | weeks/months | immigrant/new-to-credit legitimate thin file |
| Account takeover | new device, geo velocity, failed logins, payee change | minutes/days | user traveling with new phone |
| Card testing | many low-value attempts, high decline ratio, many cards per device/IP | minutes/hours | QA/test card environment |
| First-party fraud | good onboarding, cash-out, no repayment/default | days/weeks | temporary hardship or bank error |
| Money mule | receives from risky users, forwards quickly, shared device/address | days/weeks | family/shared household transfers |
| APP/BEC scam | urgent payee change, message pattern, unusual beneficiary | minutes/hours | legitimate emergency payment |
| Deepfake/liveness bypass | virtual camera metadata, impossible camera fields, device mismatch | minutes/days | privacy tool or corporate virtual camera |
| Bust-out | long clean history, rising limits, sudden max utilization | months/years | legitimate business seasonality |

## Dataset Generation Phases

### Phase 1: Local Golden/Demo Dataset

Size:

- 720 users
- 4,703 events
- all nine local fraud typologies
- 16 benign shared-household users as false-positive pressure
- 12 benign corporate virtual-camera users
- 12 benign account-recovery users with failed-login bursts
- 12 benign payment-burst users
- 8 legitimate dispute/chargeback controls
- payment bursts, virtual-camera metadata, ATO failed-login bursts, and delayed
  labels

Purpose:

- unit tests
- golden decision traces
- human-readable debugging
- default cockpit/dashboard visualization

### Phase 2: Larger Local Dataset

Size:

- 10,000 users
- about 60,000 to 100,000 events
- 1,000 labeled risky cases
- 100 graph rings

Purpose:

- UI demo
- local model training
- feature freshness tests
- replay tests

### Phase 3: Stress Dataset

Size:

- 100,000 users
- 1,000,000 events
- generated in chunks

Purpose:

- throughput tests
- Redpanda lag
- Neo4j query guards
- batch training speed

This must be optional on Bryan's laptop.

## Public Benchmark Plan

| Dataset | First Task | Model Use | Caveat |
|---|---|---|---|
| IEEE-CIS | Load transaction and identity CSVs into benchmark format. | Tabular baseline benchmark. | Kaggle access may require account; features are anonymized. |
| PaySim | Load mobile money transactions. | Payment fraud and class imbalance tests. | Synthetic and mobile-money-specific. |
| BankSim | Load bank payment transactions. | Simulator validation and retail/payment fraud tests. | Older and not identity-heavy. |
| Elliptic | Load graph edges/features. | Graph ML and graph feature benchmark. | Crypto-specific and not local product truth. |

## What If Data Is Not Available?

| Missing Input | Why It May Be Missing | Alternative |
|---|---|---|
| Kaggle IEEE-CIS | Requires Kaggle account/API token or accepted terms. | Use simulator and PaySim first. Add Kaggle loader behind optional command. |
| Real KYC outputs | Vendor contract and secret required. | Mock KYC adapter with documented status taxonomy. |
| Device fingerprint | Requires client SDK and privacy review. | Synthetic device IDs plus browser fingerprint hashes. |
| Camera metadata | Real images are PII/biometric-adjacent. | Synthetic metadata payloads and a few generated non-PII test files later. |
| Consortium blacklist | Contractual and sensitive. | Local mock list seeded from synthetic bad entities. |
| SAR outcomes | Legal/compliance-controlled. | SAR draft status only; no final SAR label unless manually simulated. |
| Real chargebacks/defaults | Business data required. | Simulate delayed repayment/default/dispute events. |

## Data Quality Gates

Every generated dataset must produce a report:

- row counts by event type
- fraud rate by typology
- label delay distribution
- missing-field distribution
- duplicate idempotency key count
- graph component size distribution
- supernode count
- feature leakage scan
- PSI against prior baseline
- synthetic-data provenance

## Leakage Rules

Forbidden in training features:

- `is_fraud`
- `review_outcome`
- labels before `label_available_at`
- future chargeback/default fields
- decision action from a later policy
- LLM-generated explanation text unless explicitly in an NLP experiment

Allowed:

- event-time features available at `as_of`
- historical counts before `as_of`
- prior confirmed labels only if available before `as_of`
- graph relationships known before `as_of`

## Data File Layout

```text
data/
  synthetic/
    manifests/
      generation-manifest.jsonl
      coverage-ledger.json
    tiny/
      events.jsonl
      entities.jsonl
      labels.jsonl
    demo/
      events.parquet
      entities.parquet
      labels.parquet
    stress/
      part-000.parquet
  public/
    ieee-cis/
    paysim/
    banksim/
    elliptic/
  offline/
    features.duckdb
    feature_snapshots/
  models/
```

## Minimum Viable Input Set

M1 can start with only:

- `APPLICATION_SUBMITTED`
- `DEVICE_OBSERVED`
- `LOGIN_ATTEMPT`
- `BEHAVIORAL_SIGNAL_OBSERVED`
- `PAYMENT_ATTEMPTED`
- `PAYMENT_SETTLED`
- `CHARGEBACK_RECEIVED`
- `MANUAL_REVIEW_DECIDED`
- `LABEL_CREATED`

That is enough to prove:

- event contracts
- graph edges
- velocity features
- decision rules
- delayed labels
- ML training dataset assembly
