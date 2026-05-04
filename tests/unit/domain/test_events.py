from datetime import UTC, datetime
from decimal import Decimal

import pytest

from fraud_v2.domain.entities import EntityRef
from fraud_v2.domain.enums import EntityType, EventType
from fraud_v2.domain.events import ApplicationSubmitted, DeviceObserved, EventEnvelope


def test_event_payload_type_must_match_envelope() -> None:
    with pytest.raises(ValueError, match="payload event_type must match"):
        EventEnvelope(
            event_type=EventType.DEVICE_OBSERVED,
            occurred_at=datetime(2026, 5, 1, tzinfo=UTC),
            idempotency_key="idem-123456",
            entity_refs=[EntityRef(entity_type=EntityType.USER, entity_id="user_1")],
            payload=ApplicationSubmitted(
                application_id="app_1",
                user_id="user_1",
                device_id="dev_1",
                requested_amount=Decimal("100"),
                declared_income=Decimal("50000"),
            ),
        )


def test_valid_device_event_round_trips_json() -> None:
    event = EventEnvelope(
        event_type=EventType.DEVICE_OBSERVED,
        occurred_at=datetime(2026, 5, 1, tzinfo=UTC),
        idempotency_key="idem-abcdef",
        entity_refs=[
            EntityRef(entity_type=EntityType.USER, entity_id="user_1"),
            EntityRef(entity_type=EntityType.DEVICE, entity_id="dev_1"),
        ],
        payload=DeviceObserved(
            user_id="user_1",
            device_id="dev_1",
            browser_fingerprint_hash="fp_1",
            ip_address="10.0.0.1",
            user_agent_family="chrome",
            timezone_offset_minutes=480,
        ),
    )
    parsed = EventEnvelope.model_validate_json(event.model_dump_json())
    assert parsed.event_id == event.event_id
    assert parsed.event_type == EventType.DEVICE_OBSERVED
