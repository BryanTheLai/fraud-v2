import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_grafana_dashboard_tracks_fraud_metrics() -> None:
    dashboard_path = ROOT / "infra" / "grafana" / "dashboards" / "fraud-v2-overview.json"
    dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))

    assert dashboard["uid"] == "fraud-v2-overview"
    assert dashboard["title"] == "Fraud V2 Overview"

    expressions = [
        target["expr"] for panel in dashboard["panels"] for target in panel.get("targets", [])
    ]
    assert any("fraud_decisions_total" in expression for expression in expressions)
    assert any("fraud_decision_latency_seconds_bucket" in expression for expression in expressions)
    assert any("fraud_events_ingested_total" in expression for expression in expressions)
    assert any('up{job="fraud-v2-api"}' in expression for expression in expressions)


def test_grafana_datasource_uid_matches_dashboard() -> None:
    datasource_path = ROOT / "infra" / "grafana" / "provisioning" / "datasources" / "prometheus.yml"
    datasource = datasource_path.read_text(encoding="utf-8")

    assert "uid: prometheus" in datasource
    assert "url: http://prometheus:9090" in datasource


def test_full_smoke_exercises_functional_api_and_observability() -> None:
    smoke_script = (ROOT / "scripts" / "full-smoke.ps1").read_text(encoding="utf-8")

    assert "$env:FRAUD_API_PORT" in smoke_script
    assert '$ApiBase = "http://127.0.0.1:$ApiPort"' in smoke_script
    assert '$ComposeProject = "fraud-v2-smoke"' in smoke_script
    assert "down --volumes --remove-orphans" in smoke_script
    assert "-UseBasicParsing" in smoke_script
    assert "/v1/synthetic/generate?users=30" in smoke_script
    assert "/v1/decisions/score" in smoke_script
    assert "ReviewCase" in smoke_script
    assert "/v1/review/cases/$reviewCaseId/decision" in smoke_script
    assert "CONFIRMED_FRAUD" in smoke_script
    assert "/v1/retention/prune?execute=false" in smoke_script
    assert "/v1/retention/prune?execute=true" in smoke_script
    assert "skipped_hash_chain" in smoke_script
    assert "/dashboard/graph?entity_id=user_00000" in smoke_script
    assert "fraud_decisions_total" in smoke_script
    assert 'up{job="fraud-v2-api", instance="api:8000"}' in smoke_script
    assert "FraudV2APIUnavailable" in smoke_script
    assert "PostgresEventStore" in smoke_script
    assert "pg_isready" in smoke_script
    assert "uv run --no-sync python -" in smoke_script
    assert "RedisFeatureCache" in smoke_script
    assert "redis-cli" in smoke_script
    assert "Neo4jGraphProjector" in smoke_script
    assert "cypher-shell" in smoke_script
    assert "RedpandaEventPublisher" in smoke_script
    assert "stream-consume" in smoke_script
    assert "stream-lag" in smoke_script
    assert "/v1/stream/dead-letters" in smoke_script
    assert "--publish-dead-letters" in smoke_script
    assert "redpanda_dlq=1" in smoke_script
    assert "rpk" in smoke_script


def test_prometheus_alert_rules_are_loaded_by_config() -> None:
    prometheus = (ROOT / "infra" / "prometheus.yml").read_text(encoding="utf-8")
    alerts = (ROOT / "infra" / "prometheus-alerts.yml").read_text(encoding="utf-8")

    assert "prometheus-alerts.yml" in prometheus
    assert "FraudV2APIUnavailable" in alerts
    assert "FraudV2DecisionLatencyP95High" in alerts
    assert "FraudV2HTTPServerErrors" in alerts


def test_docker_image_installs_full_profile_infra_extra() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "uv sync --frozen --no-dev --extra infra" in dockerfile


def test_redpanda_has_internal_and_host_listeners() -> None:
    compose = (ROOT / "infra" / "docker-compose.yml").read_text(encoding="utf-8")

    assert "internal://redpanda:9092" in compose
    assert "external://localhost:${FRAUD_REDPANDA_PORT:-19092}" in compose
    assert '"${FRAUD_REDPANDA_PORT:-19092}:19092"' in compose


def test_full_profile_api_uses_postgres_store_backend() -> None:
    compose = (ROOT / "infra" / "docker-compose.yml").read_text(encoding="utf-8")

    assert "FRAUD_STORE_BACKEND: postgres" in compose
    assert "FRAUD_POSTGRES_DSN: postgresql://fraud:fraud@postgres:5432/fraud_v2" in compose
