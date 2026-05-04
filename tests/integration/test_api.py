from fastapi.testclient import TestClient

from fraud_v2.api.main import app, store
from fraud_v2.config.settings import Settings, get_settings
from fraud_v2.storage.sqlite_store import SQLiteStore


def test_api_generate_and_score(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = SQLiteStore(tmp_path / "api.sqlite")
    app.dependency_overrides[store] = lambda: db
    client = TestClient(app)
    headers = {"Authorization": "Bearer dev-token-change-me"}

    generated = client.post("/v1/synthetic/generate?users=30", headers=headers)
    assert generated.status_code == 200
    assert generated.json()["events"] > 0

    response = client.post(
        "/v1/decisions/score",
        headers=headers,
        json={
            "target_entity": {"entity_type": "USER", "entity_id": "user_00000"},
            "as_of": "2026-05-10T00:00:00Z",
            "amount": 1000,
            "context": {},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["risk_score"] >= 80

    cases = client.get("/v1/review/cases", headers=headers)
    assert cases.status_code == 200
    audit = client.get("/v1/audit/entries", headers=headers)
    assert audit.status_code == 200
    assert any(entry["action"] == "decision.created" for entry in audit.json())
    audit_verify = client.get("/v1/audit/verify", headers=headers)
    assert audit_verify.status_code == 200
    assert audit_verify.json()["valid"] is True
    retention = client.get("/v1/retention/report", headers=headers)
    assert retention.status_code == 200
    assert retention.json()["policy"]["event_days"] == 90
    whoami = client.get("/v1/auth/whoami", headers=headers)
    assert whoami.status_code == 200
    assert whoami.json()["roles"] == ["admin", "analyst", "system"]
    dashboard = client.get("/dashboard")
    assert dashboard.status_code == 200
    assert "Recent decisions" in dashboard.text
    assert "Open review queue" in dashboard.text
    assert "user_00000" in dashboard.text

    app.dependency_overrides.clear()


def test_api_rejects_missing_token(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = SQLiteStore(tmp_path / "api.sqlite")
    app.dependency_overrides[store] = lambda: db
    client = TestClient(app)

    response = client.post("/v1/synthetic/generate?users=30")

    assert response.status_code == 401
    app.dependency_overrides.clear()


def test_api_adds_trace_header_and_request_metrics(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = SQLiteStore(tmp_path / "api.sqlite")
    app.dependency_overrides[store] = lambda: db
    client = TestClient(app)

    response = client.get("/health/live", headers={"X-Request-ID": "trace-test-001"})
    assert response.status_code == 200
    assert response.headers["X-Trace-ID"] == "trace-test-001"

    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "fraud_http_requests_total" in metrics.text
    assert 'route="/health/live"' in metrics.text

    app.dependency_overrides.clear()


def test_role_tokens_enforce_api_boundaries(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = SQLiteStore(tmp_path / "api.sqlite")
    app.dependency_overrides[store] = lambda: db
    app.dependency_overrides[get_settings] = lambda: Settings(
        api_token="",
        api_tokens="analyst:analyst-token,system:system-token,admin:admin-token",
    )
    client = TestClient(app)

    analyst_headers = {"Authorization": "Bearer analyst-token"}
    system_headers = {"Authorization": "Bearer system-token"}

    analyst_generate = client.post("/v1/synthetic/generate?users=30", headers=analyst_headers)
    assert analyst_generate.status_code == 403

    system_generate = client.post("/v1/synthetic/generate?users=30", headers=system_headers)
    assert system_generate.status_code == 200

    analyst_cases = client.get("/v1/review/cases", headers=analyst_headers)
    assert analyst_cases.status_code == 200

    system_cases = client.get("/v1/review/cases", headers=system_headers)
    assert system_cases.status_code == 403

    analyst_audit = client.get("/v1/audit/entries", headers=analyst_headers)
    assert analyst_audit.status_code == 403

    analyst_retention = client.get("/v1/retention/report", headers=analyst_headers)
    assert analyst_retention.status_code == 403

    app.dependency_overrides.clear()
