# Kumo.ai Secret Sauce: Algorithmic Brief

Date: 2026-05-06
Audience: fraud-v2 research
Status: public-source research, not proprietary source-code access

## TL;DR

Short version:

> Kumo's trick is that they do not flatten tables into features. They compile a
> predictive query into labels and timestamps, turn the relational DB into a
> temporal heterogeneous graph, sample the relevant neighborhood around the
> target entity, encode arbitrary rows/columns with schema-agnostic encoders,
> run a Relational Graph Transformer over the subgraph, then use in-context
> learning or fine-tuning to predict. The "feature engineering automation" is
> learned joins, learned group-bys, learned recency windows, and learned
> multi-hop graph traversal. Their moat seems less like one model and more like
> the whole stack: PQL label generation + temporal graph sampler + feature store
> + relational transformer + context label generation + model planner.

> For our fraud-v2 work, this is exactly relevant because fraud/payment data is
> multi-table, graphy, temporal, and label-delayed. But we should not depend on
> Kumo as the primary scorer yet. We should benchmark it offline against our
> rules, graph features, and sklearn/LightGBM baselines once our synthetic or
> public delayed-label data is shaped correctly.

Kumo's secret sauce is not "AutoML for CSVs." It is closer to:

```text
relational warehouse
  -> predictive query
  -> temporal heterogeneous graph
  -> schema-agnostic row/cell encoders
  -> entity-centered temporal subgraph sampling
  -> Relational Graph Transformer
  -> in-context learning or fine-tuned prediction head
  -> prediction + evaluation + explanations
```

The point is to avoid flattening relational data into one giant feature table.
Instead, Kumo treats the database itself as the model input. Rows become nodes.
Foreign keys become typed edges. Timestamps enforce what was knowable at
prediction time. The model learns the joins, group-bys, rolling windows, graph
neighborhoods, and multi-hop patterns that data scientists normally hand-code.

For fraud-v2, the correct posture is:

- Use Kumo as an offline challenger, not the primary decision engine.
- Copy the mental model immediately: model fraud as a temporal heterogeneous
  graph.
- Keep deterministic local rules, graph features, and sklearn/LightGBM baselines
  until Kumo beats them on delayed-label fraud splits.
- Do not route live payment/fraud decisions through Kumo without explicit vendor,
  security, latency, PII, and legal approval.

## Source Map

Primary sources:

- [KumoRFM: A Foundation Model for In-Context Learning on Relational Data](https://kumo.ai/research/kumo_relational_foundation_model.pdf)
- [KumoRFM-2: Scaling Foundation Models for Relational Learning](https://arxiv.org/abs/2604.12596)
- [Position: Relational Deep Learning - Graph Representation Learning on Relational Databases](https://proceedings.mlr.press/v235/fey24a.html)
- [Large Scale Graph Learning / Kumo distributed training backend](https://kumo.ai/docs/how-distributed-training-works/)
- [Large-Scale Training of Graph Transformers - and How the Kumo Training Backend Works](https://kumo.ai/research/Kumo-backend-works/)
- [Smarter Adaptive Graph Sampling for More Accurate Graph Learning](https://kumo.ai/research/adaptive-graph-sampling/)
- [Relational Graph Transformer paper](https://openreview.net/pdf?id=hvqyDwRKYi)
- [Kumo SDK trainer docs](https://kumo-ai.github.io/kumo-sdk/docs/modules/trainer.html)
- [Kumo Model Planner docs](https://kumo.ai/docs/model-planner/)
- [KumoRFM GitHub](https://github.com/kumo-ai/kumo-rfm)

Local fraud-v2 context:

- [AGENTS.md](../AGENTS.md)
- [Data strategy](data-strategy.md)
- [Solution tradeoffs](solution-tradeoffs.md)
- [Current feature builder](../src/fraud_v2/features/builder.py)
- [Current graph service](../src/fraud_v2/graph/service.py)
- [Current sklearn baseline](../src/fraud_v2/models/train.py)

## What They Are Really Doing

### 1. Predictive Query Language as task compiler

Kumo starts with a predictive query, not a hand-built feature table.

Example shape:

```sql
PREDICT COUNT(chargebacks.*, 0, 30)
FOR EACH users.user_id
```

That query defines:

- the target entity, such as `user`, `transaction`, `merchant`, or `payee`
- the prediction timestamp
- the future label window
- filters
- task type: binary classification, multiclass, regression, forecasting, or link prediction
- which historical snapshots can be used as context

The important part: the label definition is independent of one fixed row. If the
query says "chargeback in the next 30 days," Kumo can generate many historical
training/context examples by moving the prediction timestamp backward and asking
the same question at many valid times.

This matters for fraud because fraud labels are delayed. A normal tabular
pipeline often leaks future chargebacks/defaults into the features. Kumo's PQL
design is intentionally time-bounded so it can generate labels forward and input
subgraphs backward.

### 2. Relational database becomes a temporal heterogeneous graph

This is the Relational Deep Learning core:

```text
table              -> node type
row                -> node
primary/foreign key -> typed edge
timestamp          -> temporal ordering
column value       -> node/cell attribute
```

For payments/fraud:

```text
users          -> USER nodes
devices        -> DEVICE nodes
payment_attempts -> PAYMENT_ATTEMPT nodes
transactions   -> TRANSACTION nodes
payees         -> PAYEE nodes
bank_accounts  -> BANK_ACCOUNT nodes
chargebacks    -> CHARGEBACK nodes
labels         -> LABEL nodes or task table rows
reviews        -> REVIEW nodes

USER --USED_DEVICE--> DEVICE
USER --INITIATED--> PAYMENT_ATTEMPT
PAYMENT_ATTEMPT --TO_PAYEE--> PAYEE
PAYMENT_ATTEMPT --ON_RAIL--> ACH / CARD / RTP
TRANSACTION --RESULTED_IN--> CHARGEBACK
USER --HAS_LABEL--> LABEL
```

This preserves signal that flattening destroys, not limited to:

- multi-hop fraud rings
- shared devices or payees
- sequential behavior before a chargeback
- account/payee reuse
- temporal bursts
- sparse links where one weird relationship is more important than aggregate averages

### 3. Schema-agnostic row and cell encoding

KumoRFM claims a table-invariant encoder. The problem it solves: every database
has different tables, different column counts, and different semantic column
types. A normal neural net expects fixed-width vectors.

The public KumoRFM paper describes a row-level representation pipeline:

1. Encode each cell according to semantic type.
2. Project all cell representations to a common hidden dimension.
3. Use attention over the table's two-dimensional cell grid.
4. Produce a fixed-dimensional row embedding.

Column treatment:

| Column type | Likely encoding behavior |
|---|---|
| numeric | normalize/project |
| categorical | embedding table |
| multicategorical | embed and pool |
| timestamp | temporal/periodic/relative-time encoding |
| text | language/text encoder or embedding |
| precomputed embedding | projection |
| hashed IDs | opaque categorical/identifier treatment |

The key product claim: the same model can ingest arbitrary tables without
hand-writing a feature vector per schema.

This is one reason Kumo is more interesting than "LLM over CSV." Serialized CSV
throws away relational structure or forces a language model to infer it from
text. Kumo makes the relational graph first-class.

### 4. Temporal neighbor sampling

Graph models cannot load a whole enterprise graph into GPU memory. The model
needs a small local subgraph around the target entity.

Kumo's public backend docs describe the production trick:

```text
target entity + timestamp
  -> graph sampler in RAM expands neighborhoods
  -> feature store on SSD fetches attributes
  -> GPU trainer/inference receives constructed subgraph
```

Sampling controls:

- hop depth
- fanout per hop
- fanout per edge type
- metapaths
- temporal constraints
- recency weighting
- static vs temporal sampling

For fraud this is critical. If we predict at time `T`, the model must not see:

- a chargeback filed after `T`
- a manual review after `T`
- a device link first observed after `T`
- a label available after `T`

Kumo's pitch is that the sampler enforces this during neighborhood construction,
not as an afterthought in feature SQL.

### 5. Adaptive metapath-aware sampling

Plain GraphSAGE samples a fixed number of neighbors per hop. That is efficient,
but rigid. In heterogeneous relational graphs, a missing neighbor is not just
"one less sample." It may mean a missing semantic path.

Kumo's adaptive metapath-aware sampling article says the sampler tries to fill
missing sample budget with nodes from the same metapath or structurally related
children when a planned sample path is sparse.

Fraud example:

```text
USER -> PAYMENT_ATTEMPT -> PAYEE -> PAYMENT_ATTEMPT -> OTHER_USER
```

If one payee has too few historical attempts, a dumb sampler underuses budget.
A metapath-aware sampler can spend the budget on equivalent or nearby semantic
paths instead of random irrelevant neighbors.

Why this matters:

- fraud graphs are sparse for new users
- high-degree payees/devices can explode neighborhoods
- useful signal is often in specific paths, not random neighbors
- fixed fanout can over-sample noisy relationships and under-sample rare risky ones

### 6. Relational Graph Transformer instead of plain R-GCN

R-GCN is relation-specific message passing. It is useful but relatively rigid:
messages are transformed by relation type and aggregated.

Kumo's public material describes a Relational Graph Transformer:

- self-attention over the entity-centered subgraph
- node type positional encoding
- hop/distance encoding
- time encoding
- subgraph/tree/local-structure encoding
- attention over cross-table relationships

In normal terms:

```text
R-GCN:
  "For each edge type, pass messages with relation-specific weights."

Relational Graph Transformer:
  "Turn the local relational neighborhood into a structured token set,
   attach type/time/hop/topology signals, and let attention decide which
   facts matter for this target prediction."
```

For fraud:

- The model can attend differently to the same payee relationship depending on recency.
- It can distinguish a one-hop shared device from a four-hop shared-risk cluster.
- It can learn that a chargeback path matters more than a benign household-shared-device path.
- It can use relationship type and temporal order together.

### 7. In-context learning over relational subgraphs

KumoRFM is not only a trained GNN. It is a relational foundation model that tries
to generalize to new tasks by generating context examples at prediction time.

Public KumoRFM material says it dynamically creates context labels from
historical snapshots. The context examples are not text examples. They are
labeled relational subgraphs:

```text
context example 1: (entity e1, timestamp t1, subgraph G<=t1, label y1)
context example 2: (entity e2, timestamp t2, subgraph G<=t2, label y2)
...
test example:      (entity e*, timestamp t*, subgraph G<=t*)
```

Then an ICL module uses those context representations plus labels to predict the
test example.

This is the foundation-model part:

- It has learned general relational patterns during pretraining.
- At inference, it adapts to a new task using context labels generated from the
  user's own database.
- For repeated/production tasks, Kumo can fine-tune instead of relying only on
  in-context inference.

### 8. KumoRFM-2: hierarchical attention across four axes

KumoRFM-2, published as an arXiv paper in April 2026, says it scales relational
foundation modeling by pretraining across four axes:

- row dimension
- column dimension
- foreign-key dimension
- cross-sample/context dimension

The important change from the first public KumoRFM framing: the architecture is
more explicitly hierarchical. It first reasons within tables across rows and
columns, then enriches those representations through foreign-key graph attention
and cross-sample/context attention.

Why this matters:

- Full attention over every cell, every row, every table, and every context
  example is too expensive.
- Hierarchical attention gives the model a way to scale while still preserving
  relational structure.
- It also lets context labels condition processing earlier in the pipeline.

### 9. Fine-tuning and model planning

Kumo's SDK docs expose the supervised path:

```python
graph = kumoai.Graph(...)
pquery = kumoai.PredictiveQuery(graph=graph, query=...)
model_plan = pquery.suggest_model_plan()
trainer = kumoai.Trainer(model_plan)
training_table = pquery.generate_training_table()
training_job = trainer.fit(graph=graph, training_table=training_table)
prediction_table = pquery.generate_prediction_table()
prediction_job = trainer.predict(graph=graph, prediction_table=prediction_table)
```

The Model Planner docs say Kumo can search across GNN families and
hyperparameters, including architecture, neighborhood sampling, layer
connectivity, embedding size, and aggregation methods.

For fraud-v2, fine-tuning is the path that would matter if we had real labels.
Zero-shot is great for exploration. Production fraud would need:

- delayed-label split
- calibration
- threshold tuning
- false-positive cost model
- recall at fixed FPR
- latency and train/serve skew evidence
- model governance

## Why This Automates Feature Engineering

Manual fraud feature engineering usually looks like this:

```sql
-- examples only
COUNT(payments WHERE user_id = X AND created_at > T - interval '10 minutes')
COUNT(DISTINCT users WHERE device_id = latest_device AND created_at > T - interval '1 hour')
SUM(amount WHERE payee = P AND created_at > T - interval '7 days')
MIN(graph_distance(user, confirmed_fraud_user))
COUNT(chargebacks WHERE bank_account = B AND label_available_at < T)
```

Kumo's approach replaces those hand-written features with learnable operations:

| Manual feature idea | Kumo/RDL analog |
|---|---|
| SQL joins | graph edges from PK/FK links |
| rolling counts | temporal neighbor aggregation |
| recency features | time encodings + temporal sampler |
| graph distance | hop encoding + subgraph attention |
| entity type handling | node/edge type encodings |
| repeated historical labels | context labels / dynamic task table |
| feature table generation | predictive query + graph sampler |
| per-task model build | in-context learning or model planner |

The honest phrasing: Kumo does not remove the need to understand the data. It
removes much of the mechanical feature engineering. You still need a clean
schema, correct timestamps, valid labels, and a well-defined prediction target.

## What Is Probably Proprietary / Not Public

Public sources do not fully reveal:

- exact model sizes
- exact pretraining data corpus
- exact pretraining objectives and sampling schedule
- exact KumoRFM-2 production architecture used in hosted service
- exact feature normalization and semantic type inference edge cases
- exact context selection/ranking algorithm
- exact explainability implementation details in production
- exact latency/throughput under fraud-specific workloads
- exact online serving path for customer deployments
- exact guardrails for PII, data residency, and tenant isolation beyond public claims

So the right language is:

> Based on public papers and docs, their moat appears to be the combination of
> relational foundation modeling, temporal graph sampling infrastructure,
> schema-agnostic encoding, and production graph-transformer serving. We do not
> have source-code-level evidence of the proprietary implementation.

## Why This Is Hard To Rebuild

Building the model architecture is only one part. The harder production pieces:

1. **Task compilation**
   - Convert user predictive queries into valid labels and prediction tables.
   - Avoid time leakage by construction.

2. **Schema inference**
   - Detect table keys, foreign keys, timestamp columns, semantic column types.
   - Keep overrides simple enough for real data teams.

3. **Online graph sampling**
   - Build fresh neighborhoods per training example.
   - Respect per-edge type fanouts and timestamps.
   - Avoid exploding high-degree nodes.

4. **Feature storage**
   - Do not fit all node features in GPU memory.
   - Fetch features fast enough to keep GPUs saturated.

5. **Temporal correctness**
   - Every hop must be filtered by prediction time.
   - This is easy to get wrong in SQL/Spark pipelines.

6. **Transfer across schemas**
   - The model has to work when table names, column names, widths, and domains change.

7. **Context generation**
   - Historical labels have to be generated fast enough for in-context prediction.
   - KumoRFM claims large-scale dynamic context-label generation.

8. **Enterprise UX**
   - Data scientists need PQL, UI, SDK codegen, model planner, batch prediction,
     explanations, evaluation, and online serving.

The secret sauce is the productized stack, not one isolated equation.

## Comparison With Other Approaches

### Versus ydata-profiling

YData profiling explains the dataset. It does not learn predictive relational
representations.

Use YData for:

- schema/missingness/cardinality
- distribution summaries
- data-quality gates
- leakage checks

Use Kumo for:

- predictive tasks over connected tables
- graph/temporal relational signal
- challenger scoring

### Versus sklearn/XGBoost/LightGBM

Gradient boosting is still strong when:

- the data is mostly single-table
- features are already well engineered
- interpretability and operational control matter
- labels are limited
- local CPU-only operation matters

Kumo has the biggest advantage when:

- many tables matter
- graph relationships matter
- feature engineering is repeatedly rebuilt
- fraud rings/mules/shared devices/payees matter
- timestamps and delayed labels are central

### Versus R-GCN

R-GCN is a good research baseline. Kumo's public approach is broader:

- schema-agnostic cell/row encoding
- temporal heterogeneous graph construction
- graph transformer attention
- in-context learning
- online sampling backend
- model planner
- enterprise connectors

### Versus "LLM on CSV"

LLM-on-CSV can summarize data and maybe generate hypotheses. It is weak as the
primary predictive model because it serializes structured data into text and
forces the model to infer relationships indirectly.

Kumo's model operates directly on the relational structure.

## fraud-v2 Mapping

Current fraud-v2 components:

- [FeatureBuilder](../src/fraud_v2/features/builder.py): hand-coded velocity,
  payment, chargeback, virtual camera, behavior, Benford-style features.
- [GraphService](../src/fraud_v2/graph/service.py): NetworkX graph over users,
  devices, IPs, transactions, payees, confirmed fraud labels.
- [train_baseline](../src/fraud_v2/models/train.py): sklearn random forest over
  the built feature table.
- [data strategy](data-strategy.md): delayed labels, graph relationships,
  PaySim/public data, no real PII.

How Kumo would map:

| fraud-v2 object | Kumo/RDL representation |
|---|---|
| event JSONL | event/fact tables |
| user/device/payment/payee refs | graph nodes |
| idempotency keys | integrity fields, not prediction target |
| `occurred_at` | timestamp for temporal sampling |
| chargebacks/defaults/labels | delayed target labels |
| manual reviews | label/review table, but watch leakage |
| graph rings | multi-hop graph neighborhoods |
| FeatureBuilder outputs | baseline comparator, not required by Kumo |

First predictive queries worth testing:

```text
1. Will USER receive a fraud label within 30 days?
2. Will PAYMENT_ATTEMPT result in chargeback/default within 30 days?
3. Will PAYEE become connected to a confirmed fraud cluster within 14 days?
4. Will USER require manual review at application time?
5. Will ACH attempt return unauthorized/NSF/admin failure?
```



## Due Diligence Questions For Kumo

Ask Kumo:

1. What exact deployment path supports fraud-style online scoring?
2. What is p50/p95/p99 latency for one target entity with a 2-hop or 4-hop graph?
3. How do they prove no temporal leakage for delayed fraud labels?
4. Can we inspect generated training tables / context labels?
5. Can we export explanations at cell, edge, and path level?
6. How do they handle high-degree supernodes like shared IPs, merchants, payees,
   corporate devices, or payment processors?
7. How are timestamps chosen when multiple event tables have different time semantics?
8. What happens if a key relationship is missing or inferred incorrectly?
9. What data leaves our environment in KumoRFM vs full platform vs VPC/private cloud?
10. Can Kumo run a benchmark on our synthetic fraud-v2 schema without real PII?
11. What are the limits for context size, row count, prediction batch size, and explanations?
12. What is the recommended metric suite for imbalanced fraud: PR-AUC, recall at
    1 percent FPR, cost-weighted profit, calibration, chargeback recovery?

## Recommended fraud-v2 Next Step

Build `fraud-v2` in this order:

1. Add notebook-free profiler and fraud data-quality report.
2. Add payment/ACH return-code and retry-success dashboard.
3. Export canonical event JSONL to relational tables:
   - users
   - devices
   - payment_attempts
   - transactions
   - payees
   - chargebacks
   - labels
   - reviews
4. Define delayed-label splits.
5. Train/score:
   - current rules
   - current graph features
   - sklearn baseline
   - optional LightGBM/XGBoost
   - Kumo offline challenger
6. Compare with:
   - PR-AUC
   - recall at fixed FPR
   - cost-weighted threshold
   - false-positive cases
   - leakage audit
   - explanation quality

## Bottom Line

Kumo's secret sauce is a productized relational foundation model stack:

- predictive query as label/task compiler
- temporal heterogeneous graph representation
- schema-agnostic row/cell encoders
- temporal and metapath-aware graph sampling
- Relational Graph Transformer attention
- in-context learning over dynamically generated labeled subgraphs
- optional fine-tuning and model planning
- production graph sampler + feature store + GPU trainer/serving path

That is highly relevant to fraud/payment data. It is also exactly why we should
not fake it locally. The honest local path is to make fraud-v2's data shape and
delayed-label evaluation strong enough that Kumo can be tested as a real
challenger instead of treated as magic.
