import json

import pytest

from fraud_v2.models.registry import JsonModelRegistry, ModelStatus


def _write_model_files(tmp_path, model_version: str = "baseline-test-001"):  # type: ignore[no-untyped-def]
    model_path = tmp_path / f"{model_version}.joblib"
    report_path = tmp_path / f"{model_version}-report.json"
    model_path.write_bytes(b"fake-model")
    report_path.write_text(
        json.dumps(
            {
                "model_version": model_version,
                "model_family": "sklearn_random_forest",
                "features": ["feature_a", "feature_b"],
                "threshold": 0.4,
                "average_precision": 0.9,
                "brier_score": 0.1,
                "cost_weighted_threshold": {"threshold": 0.45, "profit": 10.0},
            }
        ),
        encoding="utf-8",
    )
    return model_path, report_path


def test_model_registry_registers_hashed_shadow_model(tmp_path) -> None:  # type: ignore[no-untyped-def]
    model_path, report_path = _write_model_files(tmp_path)
    registry = JsonModelRegistry(tmp_path / "registry.json")

    model = registry.register_from_report(model_path, report_path, notes="local baseline")

    assert model.status == ModelStatus.SHADOW
    assert model.artifact_sha256
    assert model.report_sha256
    assert model.cost_weighted_threshold == 0.45
    assert registry.list_models()[0].notes == "local baseline"


def test_model_registry_promote_keeps_one_active_model(tmp_path) -> None:  # type: ignore[no-untyped-def]
    first_model, first_report = _write_model_files(tmp_path, "baseline-test-001")
    second_model, second_report = _write_model_files(tmp_path, "baseline-test-002")
    registry = JsonModelRegistry(tmp_path / "registry.json")
    registry.register_from_report(first_model, first_report, status=ModelStatus.ACTIVE)
    registry.register_from_report(second_model, second_report, status=ModelStatus.SHADOW)

    promoted = registry.promote("baseline-test-002")
    statuses = {model.model_version: model.status for model in registry.list_models()}

    assert promoted.status == ModelStatus.ACTIVE
    assert statuses == {
        "baseline-test-001": ModelStatus.SHADOW,
        "baseline-test-002": ModelStatus.ACTIVE,
    }


def test_model_registry_missing_model_fails(tmp_path) -> None:  # type: ignore[no-untyped-def]
    registry = JsonModelRegistry(tmp_path / "registry.json")

    with pytest.raises(KeyError, match="model version not found"):
        registry.promote("missing")
