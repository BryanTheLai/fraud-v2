import pytest

from fraud_v2.connectors.mock_vendors import (
    MockConsortiumConnector,
    MockDeviceIntelConnector,
    MockKycConnector,
)
from fraud_v2.converters.raw_events import RawConversionError, RawEventConverter
from fraud_v2.domain.enums import EventType, PaymentRail


def test_application_converter_builds_canonical_event() -> None:
    event = RawEventConverter().application_submitted(
        {
            "application_id": "app_123",
            "user_id": "user_123",
            "device_id": "dev_123",
            "requested_amount": "500.00",
            "declared_income": "90000",
            "occurred_at": "2026-05-01T12:00:00+00:00",
        }
    )

    assert event.event_type == EventType.APPLICATION_SUBMITTED
    assert event.idempotency_key == "application:app_123"
    assert len(event.entity_refs) == 3


def test_payment_converter_rejects_bad_rail() -> None:
    with pytest.raises(RawConversionError, match="invalid payment payload"):
        RawEventConverter().payment_attempted(
            {
                "transaction_id": "txn_123",
                "user_id": "user_123",
                "device_id": "dev_123",
                "rail": "WIRE",
                "amount": "100.00",
                "payee_hash": "payee_123",
                "idempotency_key": "pay:txn_123",
            }
        )


def test_payment_converter_builds_canonical_event() -> None:
    event = RawEventConverter().payment_attempted(
        {
            "transaction_id": "txn_123",
            "user_id": "user_123",
            "device_id": "dev_123",
            "rail": PaymentRail.RTP.value,
            "amount": "100.00",
            "payee_hash": "payee_123",
            "idempotency_key": "pay:txn_123",
        }
    )

    assert event.event_type == EventType.PAYMENT_ATTEMPTED
    assert event.idempotency_key == "pay:txn_123"


def test_mock_connectors_emit_safe_synthetic_signals() -> None:
    kyc = MockKycConnector().screen("user_999", "synthetic_doc_reuse")
    device = MockDeviceIntelConnector().inspect("dev_emulator", "Android Emulator")
    consortium = MockConsortiumConnector().lookup("bad_payee")

    assert kyc.signals["synthetic_identity_hint"] is True
    assert device.signals["emulator_hint"] is True
    assert consortium.signals["known_bad_identifier"] is True
    assert "Mock" in kyc.safe_reason
