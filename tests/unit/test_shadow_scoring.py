import json

import joblib
import numpy as np

from fraud_v2.models.registry import JsonModelRegistry, ModelStatus
from fraud_v2.models.shadow import write_shadow_scores
from fraud_v2.synthetic.generator import SyntheticFraudGenerator


class DummyEstimator:
    def predict_proba(self, frame):  # type: ignore[no-untyped-def]
        probabilities = np.linspace(0.1, 0.9, len(frame))
        return np.column_stack([1.0 - probabilities, probabilities])


def test_write_shadow_scores_from_registered_active_model(tmp_path) -> None:  # type: ignore[no-untyped-def]
    events_path = tmp_path / "events.jsonl"
    model_path = tmp_path / "model.joblib"
    report_path = tmp_path / "report.json"
    registry_path = tmp_path / "registry.json"
    output_path = tmp_path / "shadow.json"
    SyntheticFraudGenerator(seed=1).generate(users=10).write_jsonl(events_path)
    joblib.dump(DummyEstimator(), model_path)
    report_path.write_text(
        json.dumps(
            {
                "model_version": "shadow-test-001",
                "model_family": "dummy",
                "features": ["failed_login_count_3m", "payment_amount_24h"],
                "threshold": 0.5,
                "cost_weighted_threshold": {"threshold": 0.5},
            }
        ),
        encoding="utf-8",
    )
    registry = JsonModelRegistry(registry_path)
    registry.register_from_report(model_path, report_path, status=ModelStatus.ACTIVE)

    report = write_shadow_scores(events_path, registry_path, output_path)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["rows"] == 10
    assert report["would_flag"] == 5
    assert payload[0]["model_version"] == "shadow-test-001"
    assert payload[0]["model_status"] == "active"
    assert "feature_values" in payload[0]
