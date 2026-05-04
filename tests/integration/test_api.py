from fastapi.testclient import TestClient

from fraud_v2.api.main import app, store
from fraud_v2.storage.sqlite_store import SQLiteStore


def test_api_generate_and_score(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = SQLiteStore(tmp_path / "api.sqlite")
    app.dependency_overrides[store] = lambda: db
    client = TestClient(app)

    generated = client.post("/v1/synthetic/generate?users=30")
    assert generated.status_code == 200
    assert generated.json()["events"] > 0

    response = client.post(
        "/v1/decisions/score",
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

    cases = client.get("/v1/review/cases")
    assert cases.status_code == 200

    app.dependency_overrides.clear()
