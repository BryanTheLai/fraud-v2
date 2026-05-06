from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from pydantic import ValidationError

from fraud_v2.domain.entities import EntityRef
from fraud_v2.domain.enums import EntityType, EventType, PaymentRail
from fraud_v2.domain.events import ApplicationSubmitted, EventEnvelope, PaymentAttempted


class RawConversionError(ValueError):
    """Raised when a raw payload cannot become a canonical event."""


class RawEventConverter:
    def application_submitted(self, raw: Mapping[str, Any]) -> EventEnvelope:
        try:
            payload = ApplicationSubmitted(
                application_id=str(raw["application_id"]),
                user_id=str(raw["user_id"]),
                device_id=str(raw["device_id"]),
                requested_amount=Decimal(str(raw["requested_amount"])),
                declared_income=Decimal(str(raw["declared_income"])),
                product=str(raw.get("product", "instant_cash")),
                channel=str(raw.get("channel", "web")),
            )
            occurred_at = _occurred_at(raw)
            idempotency_key = str(
                raw.get("idempotency_key", f"application:{payload.application_id}")
            )
            return EventEnvelope(
                event_type=EventType.APPLICATION_SUBMITTED,
                occurred_at=occurred_at,
                idempotency_key=idempotency_key,
                entity_refs=[
                    EntityRef(entity_type=EntityType.USER, entity_id=payload.user_id),
                    EntityRef(entity_type=EntityType.DEVICE, entity_id=payload.device_id),
                    EntityRef(entity_type=EntityType.APPLICATION, entity_id=payload.application_id),
                ],
                payload=payload,
            )
        except (KeyError, ValidationError, ValueError) as exc:
            raise RawConversionError(f"invalid application payload: {exc}") from exc

    def payment_attempted(self, raw: Mapping[str, Any]) -> EventEnvelope:
        try:
            payload = PaymentAttempted(
                transaction_id=str(raw["transaction_id"]),
                user_id=str(raw["user_id"]),
                device_id=str(raw["device_id"]),
                rail=PaymentRail(str(raw["rail"])),
                amount=Decimal(str(raw["amount"])),
                payee_hash=str(raw["payee_hash"]),
                idempotency_key=str(raw["idempotency_key"]),
            )
            occurred_at = _occurred_at(raw)
            return EventEnvelope(
                event_type=EventType.PAYMENT_ATTEMPTED,
                occurred_at=occurred_at,
                idempotency_key=payload.idempotency_key,
                entity_refs=[
                    EntityRef(entity_type=EntityType.USER, entity_id=payload.user_id),
                    EntityRef(entity_type=EntityType.DEVICE, entity_id=payload.device_id),
                    EntityRef(entity_type=EntityType.TRANSACTION, entity_id=payload.transaction_id),
                ],
                payload=payload,
            )
        except (KeyError, ValidationError, ValueError) as exc:
            raise RawConversionError(f"invalid payment payload: {exc}") from exc


def _occurred_at(raw: Mapping[str, Any]) -> datetime:
    value = raw.get("occurred_at")
    if value is None:
        return datetime.now(UTC)
    if isinstance(value, datetime):
        return _normalize_utc(value)
    return _normalize_utc(datetime.fromisoformat(str(value).replace("Z", "+00:00")))


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
