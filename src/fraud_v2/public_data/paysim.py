from __future__ import annotations

import csv
import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from fraud_v2.domain.entities import EntityRef
from fraud_v2.domain.enums import EntityType, EventType, FraudTypology, LabelValue, PaymentRail
from fraud_v2.domain.events import (
    ChargebackReceived,
    EventEnvelope,
    LabelCreated,
    PaymentAttempted,
    PaymentSettled,
)

PAYSIM_REQUIRED_COLUMNS = {
    "step",
    "type",
    "amount",
    "nameOrig",
    "nameDest",
    "isFraud",
}


@dataclass(frozen=True)
class PaySimConversionReport:
    dataset: str
    input_path: str
    output_path: str
    rows: int
    events: int
    fraud_rows: int
    legitimate_rows: int
    skipped_rows: int


def convert_paysim_csv(
    *,
    input_path: Path,
    output_path: Path,
    limit_rows: int | None = None,
    base_time: datetime = datetime(2026, 1, 1, tzinfo=UTC),
) -> PaySimConversionReport:
    rows = 0
    fraud_rows = 0
    legitimate_rows = 0
    skipped_rows = 0
    events: list[EventEnvelope] = []

    with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        _validate_columns(reader.fieldnames)
        for row_index, row in enumerate(reader):
            if limit_rows is not None and rows >= limit_rows:
                break
            rows += 1
            try:
                converted = _convert_row(row=row, row_index=row_index, base_time=base_time)
            except ValueError:
                skipped_rows += 1
                continue
            events.extend(converted)
            if _is_fraud(row):
                fraud_rows += 1
            else:
                legitimate_rows += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as output:
        for event in sorted(events, key=lambda item: item.occurred_at):
            payload = json.loads(event.model_dump_json())
            output.write(json.dumps(payload, sort_keys=True) + "\n")

    return PaySimConversionReport(
        dataset="paysim",
        input_path=str(input_path),
        output_path=str(output_path),
        rows=rows,
        events=len(events),
        fraud_rows=fraud_rows,
        legitimate_rows=legitimate_rows,
        skipped_rows=skipped_rows,
    )


def _validate_columns(fieldnames: Sequence[str] | None) -> None:
    columns = set(fieldnames or [])
    missing = sorted(PAYSIM_REQUIRED_COLUMNS - columns)
    if missing:
        raise ValueError(f"PaySim CSV missing required columns: {', '.join(missing)}")


def _convert_row(
    *,
    row: dict[str, str],
    row_index: int,
    base_time: datetime,
) -> list[EventEnvelope]:
    amount = _decimal(row["amount"])
    if amount <= 0:
        raise ValueError("PaySim amount must be positive")
    transaction_id = f"paysim_txn_{row_index:08d}"
    user_id = f"paysim_user_{_stable_hash(row['nameOrig'])[:16]}"
    payee_hash = _stable_hash(row["nameDest"])
    occurred_at = base_time + timedelta(hours=int(float(row["step"])))
    rail = _rail(row["type"])
    attempted = _event(
        event_type=EventType.PAYMENT_ATTEMPTED,
        occurred_at=occurred_at,
        idempotency_key=f"paysim:payment_attempted:{row_index}",
        entity_refs=[_user(user_id), _transaction(transaction_id)],
        payload=PaymentAttempted(
            transaction_id=transaction_id,
            user_id=user_id,
            device_id=f"paysim_device_{_stable_hash(row['nameOrig'])[:12]}",
            rail=rail,
            amount=amount,
            payee_hash=payee_hash,
            idempotency_key=f"paysim:payment:{row_index}",
        ),
    )
    output = [attempted]
    if _is_fraud(row):
        output.extend(
            [
                _event(
                    event_type=EventType.CHARGEBACK_RECEIVED,
                    occurred_at=occurred_at + timedelta(days=1),
                    idempotency_key=f"paysim:chargeback:{row_index}",
                    entity_refs=[_user(user_id), _transaction(transaction_id)],
                    payload=ChargebackReceived(
                        transaction_id=transaction_id,
                        user_id=user_id,
                        amount=amount,
                        reason="paysim_fraud_label",
                    ),
                ),
                _event(
                    event_type=EventType.LABEL_CREATED,
                    occurred_at=occurred_at + timedelta(days=1, minutes=1),
                    idempotency_key=f"paysim:label:{row_index}",
                    entity_refs=[_user(user_id)],
                    payload=LabelCreated(
                        target_entity=_user(user_id),
                        label_value=LabelValue.FRAUD,
                        typology=FraudTypology.UNKNOWN,
                        label_available_at=occurred_at + timedelta(days=1),
                        source="paysim_public_dataset",
                    ),
                ),
            ]
        )
    else:
        output.append(
            _event(
                event_type=EventType.PAYMENT_SETTLED,
                occurred_at=occurred_at + timedelta(minutes=10),
                idempotency_key=f"paysim:payment_settled:{row_index}",
                entity_refs=[_user(user_id), _transaction(transaction_id)],
                payload=PaymentSettled(
                    transaction_id=transaction_id,
                    user_id=user_id,
                    amount=amount,
                    rail=rail,
                ),
            )
        )
    return output


def _event(
    *,
    event_type: EventType,
    occurred_at: datetime,
    idempotency_key: str,
    entity_refs: list[EntityRef],
    payload: Any,
) -> EventEnvelope:
    return EventEnvelope(
        event_id=uuid5(NAMESPACE_URL, f"fraud-v2:{idempotency_key}:{occurred_at.isoformat()}"),
        event_type=event_type,
        occurred_at=occurred_at,
        idempotency_key=idempotency_key,
        entity_refs=entity_refs,
        payload=payload,
    )


def _decimal(raw_value: str) -> Decimal:
    try:
        return Decimal(raw_value)
    except InvalidOperation as exc:
        raise ValueError(f"invalid PaySim amount: {raw_value}") from exc


def _is_fraud(row: dict[str, str]) -> bool:
    return row["isFraud"].strip() == "1"


def _rail(raw_type: str) -> PaymentRail:
    match raw_type.strip().upper():
        case "CASH_OUT" | "TRANSFER":
            return PaymentRail.RTP
        case "DEBIT":
            return PaymentRail.DEBIT_CARD
        case "PAYMENT":
            return PaymentRail.PUSH_TO_CARD
        case _:
            return PaymentRail.ACH


def _stable_hash(raw_value: str) -> str:
    return hashlib.sha256(raw_value.strip().encode("utf-8")).hexdigest()


def _user(user_id: str) -> EntityRef:
    return EntityRef(entity_type=EntityType.USER, entity_id=user_id)


def _transaction(transaction_id: str) -> EntityRef:
    return EntityRef(entity_type=EntityType.TRANSACTION, entity_id=transaction_id)
