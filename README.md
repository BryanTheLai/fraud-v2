# fraud-v2

Local-first, Python-heavy fraud decision platform spec based on the BryansLab
Fraud Detection V2 article.

Start here:

- [Plan Index](docs/plan-index.md)
- [Spec Plan](docs/spec-plan.md)
- [Setup](docs/setup.md)
- [Vagueness Register](docs/vagueness-register.md)
- [Blockers And Vague Decisions](docs/blockers-and-vague-decisions.md)
- [Solution Tradeoffs](docs/solution-tradeoffs.md)
- [Dependency Map](docs/dependency-map.md)
- [Data Strategy](docs/data-strategy.md)
- [LLM Synthetic Data Lab](docs/llm-synthetic-data-lab.md)
- [Local Production Profile](docs/local-production-profile.md)
- [Production Readiness](docs/production-readiness.md)
- [Code Factory Dashboard](factory/dashboard.md)

Current state: local MVP plus full-profile adapter layer implemented. It runs in
lite mode with synthetic data, SQLite storage, rules/graph scoring, baseline
model training, FastAPI endpoints, dashboard, metrics, tests, CI workflow, and
Docker Compose scaffolding. Analyst review outcomes feed canonical review and
label events for replay/training. Full mode uses Postgres as the primary app
store and includes Redis, Redpanda, Neo4j, Prometheus, and a provisioned Grafana
dashboard. Stream ingestion now has bounded consume, supervised consume,
dead-letter, DLQ publishing, and lag-inspection CLIs for local reliability work.

## Run Lite Mode

```powershell
uv sync --extra dev
uv run fraud-v2 generate --users 120 --output data/synthetic/tiny/events.jsonl
uv run fraud-v2 load data/synthetic/tiny/events.jsonl --db-path data/local/fraud_v2.sqlite
uv run fraud-v2 score user_00000 --db-path data/local/fraud_v2.sqlite
uv run uvicorn fraud_v2.api.main:app --host 127.0.0.1 --port 8000
```

Local URLs:

- API docs: `http://127.0.0.1:8000/docs`
- Analyst dashboard: `http://127.0.0.1:8000/dashboard`
- Graph evidence: `http://127.0.0.1:8000/dashboard/graph?entity_id=user_00000`
- Metrics: `http://127.0.0.1:8000/metrics`

Every API response includes `X-Trace-ID`. Pass `X-Request-ID` to force a known
trace ID during local debugging.

Protected `/v1/*` endpoints require `Authorization: Bearer dev-token-change-me`
by default. Override `FRAUD_API_TOKEN` locally instead of committing secrets.
For local role testing, set `FRAUD_API_TOKENS` with comma-separated
`role:token` pairs, such as:

```text
FRAUD_API_TOKENS=admin:local-admin-token,analyst:local-analyst-token,system:local-system-token
```

Roles are intentionally small:

- `system`: ingest/generate/score.
- `analyst`: read decisions, graph, and review queue.
- `admin`: all local actions.

JWT/OIDC-shaped local auth is available without an external provider:

```powershell
$env:FRAUD_AUTH_MODE="jwt"
$env:FRAUD_JWT_SECRET="replace-with-local-only-secret-32b-min"
uv run fraud-v2 auth-token --secret $env:FRAUD_JWT_SECRET --subject local-admin
```

Use the printed token as `Authorization: Bearer <token>`. JWT mode validates
issuer, audience, expiry, subject, and role claims. It is still local auth, not
a replacement for a production OIDC provider.

JWKS/OIDC-shaped verification is also available for asymmetric JWTs:

```powershell
$env:FRAUD_AUTH_MODE="jwt"
$env:FRAUD_JWT_ALGORITHMS="RS256"
$env:FRAUD_JWT_JWKS_PATH="C:\path\to\jwks.json"
```

Use `FRAUD_JWT_JWKS_URL` for a direct JWKS endpoint or
`FRAUD_JWT_OIDC_DISCOVERY_URL` for an OIDC discovery document. HS algorithms are
rejected whenever JWKS verification is configured.

Admin-only audit endpoints:

- `GET /v1/audit/entries`
- `GET /v1/audit/verify`
- `GET /v1/retention/report`
- `POST /v1/retention/prune?execute=false`
- `GET /v1/stream/dead-letters`

The audit log is hash-chained in SQLite. This is tamper-evident for local
development, not a substitute for production WORM storage.

## Run Full Local Infra

```powershell
docker compose -f infra\docker-compose.yml --profile full up -d
docker compose -f infra\docker-compose.yml --profile full ps
```

The full profile starts the API container plus Postgres, Redis, Redpanda, Neo4j,
Prometheus, and Grafana. The API uses `FRAUD_STORE_BACKEND=postgres` in this
profile. Lite mode still defaults to SQLite.

Grafana opens at `http://127.0.0.1:3000/d/fraud-v2-overview/fraud-v2-overview`
with anonymous local viewer access enabled by the Docker profile.
Prometheus also loads local alert rules from `infra/prometheus-alerts.yml`.

Full-profile smoke:

```powershell
.\scripts\full-smoke.ps1
.\scripts\full-smoke.ps1 -KeepRunning
```

The smoke resets only the isolated smoke Compose project, builds the API image
with full-profile infra extras, starts the full profile, generates synthetic
events through the protected API, scores `user_00000`, submits a synthetic
review decision, verifies retention prune dry-run and execute paths, checks the
dashboard, verifies Prometheus metrics, checks graph evidence rendering, loads
Grafana, verifies the Postgres adapter inside the Docker network, verifies
Redis and Neo4j adapters, publishes a Redpanda event, consumes it back into
Postgres through the stream worker, proves zero consumer lag, runs the
supervised stream worker path, verifies invalid-record DLQ publishing, then
shuts the stack down unless `-KeepRunning` is set.

`full-smoke.ps1` uses high host ports by default, for example API `18000`,
Grafana `13000`, Prometheus `19090`, and Neo4j HTTP `17474`, so it can run while
a normal dev API is already listening on `8000`. It also uses a separate Docker
Compose project name, `fraud-v2-smoke`, to avoid disturbing a manually started
full stack.

## Reports

```powershell
uv run fraud-v2 replay --events-path data/synthetic/tiny/events.jsonl
uv run fraud-v2 monitor --events-path data/synthetic/tiny/events.jsonl
uv run fraud-v2 llm-stub
uv run fraud-v2 llm-generate --provider offline
uv run fraud-v2 outbox-drain --db-path data/local/fraud_v2.sqlite --dry-run
uv run fraud-v2 stream-consume --bootstrap-servers localhost:19092 --topic fraud.events --max-messages 10
uv run fraud-v2 stream-supervise --bootstrap-servers localhost:19092 --topic fraud.events --group-id fraud-v2-local --max-batches 3 --batch-size 100
uv run fraud-v2 stream-consume --bootstrap-servers localhost:19092 --topic fraud.events --max-messages 10 --publish-dead-letters --dead-letter-topic fraud.dead_letters --allow-errors
uv run fraud-v2 stream-lag --bootstrap-servers localhost:19092 --topic fraud.events --group-id fraud-v2-local
uv run fraud-v2 stream-dead-letters --db-path data/local/fraud_v2.sqlite
uv run fraud-v2 compliance-draft <decision-id> --db-path data/local/fraud_v2.sqlite
uv run fraud-v2 retention-report --db-path data/local/fraud_v2.sqlite
uv run fraud-v2 retention-prune --db-path data/local/fraud_v2.sqlite
uv run fraud-v2 retention-prune --db-path data/local/fraud_v2.sqlite --execute
uv run fraud-v2 policy-show
uv run fraud-v2 policy-register data/policies/strict.json --status candidate
uv run fraud-v2 policy-promote strict-policy-test
uv run fraud-v2 model-register --status shadow
uv run fraud-v2 model-promote baseline-20260505-001
uv run fraud-v2 shadow-score --status active
uv run fraud-v2 public-dataset paysim
```

OpenAI/Azure-backed synthetic scenario generation is available through
`llm-generate --provider openai` or `--provider azure`, but the repo defaults to
`offline` so local tests never require credentials or network calls.

## Quality Gate

```powershell
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest -q
```
