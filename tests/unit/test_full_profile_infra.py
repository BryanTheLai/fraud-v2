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
    assert "$cases = @(" in smoke_script
    assert "-UseBasicParsing" in smoke_script
    assert "/v1/synthetic/generate?users=30" in smoke_script
    assert "/v1/decisions/score" in smoke_script
    assert "/v1/review/cases" in smoke_script
    assert "fraud_decisions_total" in smoke_script
    assert 'up{job="fraud-v2-api", instance="api:8000"}' in smoke_script
