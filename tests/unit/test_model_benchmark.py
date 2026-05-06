from datetime import UTC, datetime
from decimal import Decimal

import pytest

from fraud_v2.domain.entities import EntityRef
from fraud_v2.domain.enums import EntityType, EventType, FraudTypology, LabelValue
from fraud_v2.domain.events import ApplicationSubmitted, EventEnvelope, LabelCreated
from fraud_v2.models.benchmark import benchmark_model_families
from fraud_v2.synthetic.generator import SyntheticFraudGenerator, write_events_jsonl


def test_model_benchmark_compares_lightweight_local_models(tmp_path) -> None:  # type: ignore[no-untyped-def]
    events_path = tmp_path / "events.jsonl"
    output_path = tmp_path / "benchmark.json"
    SyntheticFraudGenerator(seed=7).generate(users=80).write_jsonl(events_path)

    report = benchmark_model_families(events_path=events_path, output_path=output_path)

    assert output_path.exists()
    assert report["rows"] == 80
    assert {row["model_family"] for row in report["models"]} >= {
        "sklearn_logistic_regression",
        "sklearn_random_forest",
    }
    assert report["recommended_model_family"] in {
        "sklearn_logistic_regression",
        "sklearn_random_forest",
    }
    assert all(0 <= row["average_precision"] <= 1 for row in report["models"])


def test_model_benchmark_fails_fast_when_a_class_has_one_row(tmp_path) -> None:  # type: ignore[no-untyped-def]
    events_path = tmp_path / "events.jsonl"
    output_path = tmp_path / "benchmark.json"
    write_events_jsonl(
        [
            _application_event("user_00001"),
            _application_event("user_00002"),
            _application_event("user_00003"),
            _fraud_label("user_00001"),
        ],
        events_path,
    )

    with pytest.raises(ValueError, match="at least two rows per class"):
        benchmark_model_families(events_path=events_path, output_path=output_path)


def _application_event(user_id: str) -> EventEnvelope:
    index = int(user_id.rsplit("_", 1)[-1])
    payload = ApplicationSubmitted(
        application_id=f"app_{index:05d}",
        user_id=user_id,
        device_id=f"dev_{index:05d}",
        requested_amount=Decimal("250"),
        declared_income=Decimal("50000"),
    )
    return EventEnvelope(
        event_type=EventType.APPLICATION_SUBMITTED,
        occurred_at=datetime(2026, 5, 1, 12, index, tzinfo=UTC),
        idempotency_key=f"application:app_{index:05d}",
        entity_refs=[
            EntityRef(entity_type=EntityType.USER, entity_id=user_id),
            EntityRef(entity_type=EntityType.DEVICE, entity_id=f"dev_{index:05d}"),
            EntityRef(entity_type=EntityType.APPLICATION, entity_id=f"app_{index:05d}"),
        ],
        payload=payload,
    )


def _fraud_label(user_id: str) -> EventEnvelope:
    payload = LabelCreated(
        target_entity=EntityRef(entity_type=EntityType.USER, entity_id=user_id),
        label_value=LabelValue.FRAUD,
        typology=FraudTypology.SYNTHETIC_IDENTITY,
        label_available_at=datetime(2026, 5, 2, 12, tzinfo=UTC),
        source="unit_test",
    )
    return EventEnvelope(
        event_type=EventType.LABEL_CREATED,
        occurred_at=datetime(2026, 5, 2, 12, tzinfo=UTC),
        idempotency_key=f"label:{user_id}",
        entity_refs=[EntityRef(entity_type=EntityType.USER, entity_id=user_id)],
        payload=payload,
    )
