---
project: fraud-v2
owner: Bryan
created_at: 2026-05-04
updated_at: 2026-05-04
status: draft
source_task: TC-20260504-002
version: 1
---

# LLM Synthetic Data Lab

## Purpose

Use GPT-5.5/Azure/OpenAI capacity to generate breadth:

- fraud scenarios
- edge cases
- false-positive counterexamples
- malformed inputs
- analyst notes
- compliance-safe reason wording
- adversarial test cases
- simulation parameters

Do not use an LLM as the primary fraud scoring model in V1.

## Design Rule

LLM output is a proposal. Deterministic validators decide whether it enters the
dataset.

Pipeline:

```text
prompt pack
  -> structured LLM output
  -> JSON schema validation
  -> semantic validator
  -> novelty/dedupe check
  -> simulator expansion
  -> generated event stream
  -> data quality report
  -> accepted dataset manifest
```

## Provider Abstraction

Use an adapter so OpenAI and Azure OpenAI can be swapped:

```text
LlmProvider
  generate_structured(prompt, schema, metadata) -> LlmGenerationResult
  batch_generate(jsonl_file, schema, metadata) -> BatchJob
  get_batch_result(batch_id) -> BatchResult
```

Environment variables:

| Name | Required | Notes |
|---|---|---|
| `LLM_PROVIDER` | yes | `openai` or `azure_openai`. |
| `OPENAI_API_KEY` | if OpenAI | Standard OpenAI key. |
| `OPENAI_MODEL` | yes | Default local plan: GPT-5.5 if available. |
| `AZURE_OPENAI_ENDPOINT` | if Azure | Azure endpoint. |
| `AZURE_OPENAI_API_KEY` | if Azure key auth | Keep out of git. |
| `AZURE_OPENAI_DEPLOYMENT` | if Azure | Deployment name, not necessarily model name. |
| `LLM_BATCH_MODE` | no | `true` for async large generation. |

## Structured Output Schemas

### Scenario Spec

```json
{
  "scenario_id": "string",
  "typology": "SYNTHETIC_IDENTITY",
  "narrative": "string",
  "entities": [
    {
      "entity_role": "applicant",
      "traits": ["thin_file", "shared_device"]
    }
  ],
  "timeline": [
    {
      "relative_time": "T-3d",
      "event_type": "APPLICATION_SUBMITTED",
      "intent": "open account"
    }
  ],
  "risk_signals": ["device_reuse", "income_digit_anomaly"],
  "false_positive_counterexample": "string",
  "expected_label": "CONFIRMED_FRAUD",
  "label_available_after": "P14D"
}
```

### Edge Case Spec

```json
{
  "edge_case_id": "string",
  "target_contract": "DeviceObservedEvent",
  "mutation_type": "missing_required_field",
  "payload_delta": {},
  "expected_converter_result": "reject",
  "expected_safe_error_code": "missing_device_id"
}
```

### Analyst Note Spec

```json
{
  "case_id": "string",
  "analyst_persona": "senior_ato_reviewer",
  "visible_evidence": ["shared_device", "new_payee", "login_velocity"],
  "note": "string",
  "outcome": "CONFIRMED_FRAUD",
  "confidence": 0.87,
  "unsafe_reason_text_to_avoid": ["risk score only"]
}
```

## Append-Only Novelty Ledger

Bryan's idea:

- append generated cases to a file
- ask the LLM not to generate what already exists

Production-shaped version:

```text
data/synthetic/manifests/
  generation-manifest.jsonl
  coverage-ledger.json
  rejected-generations.jsonl
```

Each accepted generated item stores:

- `content_hash`
- `schema_name`
- `typology`
- `covered_features`
- `covered_rules`
- `covered_converter_errors`
- `covered_graph_patterns`
- `prompt_pack_version`
- `model`
- `provider`
- `created_at`
- `validator_version`

Do not paste the entire ledger into prompts after it grows. Use retrieval:

1. Load coverage summary.
2. Select nearest existing cases by typology/features.
3. Ask the LLM to generate cases that fill uncovered cells.
4. Reject duplicates by hash and semantic similarity.

## Coverage Matrix

The LLM generation target is a coverage matrix, not random volume.

| Dimension | Values |
|---|---|
| Typology | synthetic identity, ATO, card testing, first-party fraud, money mule, APP/BEC, deepfake, bust-out |
| Outcome | true fraud, false positive, legitimate, ambiguous, unreviewable |
| Event quality | valid, missing required, malformed, duplicate, stale, out-of-order |
| Graph pattern | one-hop fraud, two-hop fraud, shared device, shared address, supernode IP, mule chain |
| Action | approve, step-up, manual review, hold, block simulation, break-the-spell |
| Label delay | minutes, hours, days, weeks, months |
| Cost impact | low, medium, high, catastrophic |
| Customer context | new user, long-tenured user, traveler, shared household, business account |

## Prompt Packs

| Prompt Pack | Output | Used By |
|---|---|---|
| `typology_scenarios` | scenario specs | simulator |
| `false_positive_factory` | legitimate counterexamples | rules and model eval |
| `converter_fuzzer` | malformed payload specs | converter tests |
| `graph_ring_designer` | entity/edge pattern specs | graph generator |
| `analyst_notes` | review notes | UI and label loop |
| `safe_reasons` | reason-code wording candidates | compliance tests |
| `red_team_policy` | adversarial cases | decision and resilience tests |

## SVD And Latent Factor Ideas

SVD can help, but it is not the core fraud model.

Useful places:

- entity-merchant matrix embeddings
- user-device co-occurrence embeddings
- payee-transfer matrix embeddings
- graph adjacency compression for anomaly features
- clustering similar fraud rings for generation coverage

Bad places:

- replacing supervised fraud model
- direct production decision without explanation
- training on future labels or post-decision outcomes

Implementation plan:

1. Build sparse matrix from entity relationships at `as_of`.
2. Run truncated SVD on CPU.
3. Store embeddings as offline features.
4. Feed embeddings into XGBoost/LightGBM as secondary features.
5. Run ablation: baseline without SVD vs with SVD.

## Adjacent-Field Ideas To Import

| Field | Idea | Fraud V2 Use |
|---|---|---|
| Cybersecurity | kill chain and IOC correlation | Fraud attack timelines and indicator graph. |
| Spam/abuse | reputation systems and rate limits | Device/email/IP reputation. |
| Game anti-cheat | behavior entropy and hardware fingerprint drift | Bot/device-farm detection. |
| Epidemiology | contact tracing and transmission networks | Risk propagation through shared entities. |
| Manufacturing QA | statistical process control | PSI, score drift, false-positive spike detection. |
| Recommender systems | matrix factorization | Entity-payee-device embeddings. |
| Insurance claims | staged rings and investigator workflows | Graph case management. |
| Ad tech fraud | click farms and bot traffic | Velocity and behavior entropy features. |
| Credit risk | reject inference and delayed outcomes | Repayment/default label handling. |
| AML | suspicious activity narratives | SAR draft structure and mule networks. |

## Quality Gates For LLM Data

Generated data is accepted only if:

- JSON schema validates.
- All enum values are valid.
- Event timeline is possible.
- No real PII appears.
- No forbidden leakage fields appear.
- Idempotency keys are unique unless testing duplicates.
- Label availability is after the causal events.
- Scenario increases coverage or is a targeted duplicate test.
- Deterministic simulator can expand it into events.
- Data quality report passes thresholds.

## LLM Evaluation

Use evals for:

- schema adherence
- unsafe PII generation
- duplicate generation
- impossible timeline generation
- safe reason quality
- hallucinated vendor field detection
- analyst note consistency

LLM-generated artifacts must be versioned by:

- model
- prompt pack
- schema
- validator
- seed/temperature where applicable

## Why LLM Is Not The Primary Scorer

Fraud decisions need:

- stable thresholds
- calibration
- replay
- point-in-time correctness
- reason codes
- deterministic failure handling
- cost optimization
- auditability

Tabular models plus rules are better aligned with those needs. LLMs are useful
for synthetic breadth and review text, not as the decision authority.

