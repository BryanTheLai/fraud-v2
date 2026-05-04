from __future__ import annotations

import json
import random
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from fraud_v2.domain.entities import EntityRef
from fraud_v2.domain.enums import EntityType, EventType, FraudTypology, LabelValue, PaymentRail
from fraud_v2.domain.events import (
    ApplicationSubmitted,
    BehavioralSignalObserved,
    CameraMetadataObserved,
    ChargebackReceived,
    DeviceObserved,
    EventEnvelope,
    LabelCreated,
    LoginAttempt,
    PaymentAttempted,
    PaymentSettled,
)


class SyntheticDataset:
    def __init__(self, events: list[EventEnvelope]) -> None:
        self.events = events

    def write_jsonl(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for event in self.events:
                handle.write(event.model_dump_json() + "\n")


class SyntheticFraudGenerator:
    def __init__(self, seed: int = 20260505) -> None:
        self.rng = random.Random(seed)
        self.base_time = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)

    def generate(self, users: int = 120, fraud_rate: float = 0.12) -> SyntheticDataset:
        events: list[EventEnvelope] = []
        shared_bad_device = "dev_fraud_ring_001"
        shared_bad_ip = "10.10.0.99"
        fraud_users = max(1, int(users * fraud_rate))

        for index in range(users):
            user_id = f"user_{index:05d}"
            is_fraud = index < fraud_users
            typology = self._typology(index) if is_fraud else FraudTypology.UNKNOWN
            device_id = shared_bad_device if is_fraud and index % 3 == 0 else f"dev_{index:05d}"
            ip_address = (
                shared_bad_ip
                if is_fraud and index % 3 == 0
                else f"10.0.{index // 255}.{index % 255}"
            )
            app_time = self.base_time + timedelta(minutes=index * 2)
            requested = Decimal(str(self.rng.choice([50, 100, 250, 500, 1000, 1500])))
            income = Decimal(str(self.rng.choice([18000, 32000, 55000, 90000, 150000])))

            events.extend(
                [
                    self._event(
                        EventType.DEVICE_OBSERVED,
                        app_time - timedelta(minutes=15),
                        f"device:{user_id}:{device_id}",
                        [self._user(user_id), self._device(device_id), self._ip(ip_address)],
                        DeviceObserved(
                            user_id=user_id,
                            device_id=device_id,
                            browser_fingerprint_hash=(
                                "fp_shared_bad"
                                if is_fraud and index % 3 == 0
                                else f"fp_{index:05d}"
                            ),
                            ip_address=ip_address,
                            user_agent_family=self.rng.choice(["chrome", "edge", "firefox"]),
                            timezone_offset_minutes=self.rng.choice([-480, -300, 0, 480]),
                            emulator_flag=is_fraud and typology == FraudTypology.ACCOUNT_TAKEOVER,
                        ),
                    ),
                    self._event(
                        EventType.CAMERA_METADATA_OBSERVED,
                        app_time - timedelta(minutes=12),
                        f"camera:{user_id}:{device_id}",
                        [self._user(user_id), self._device(device_id)],
                        CameraMetadataObserved(
                            user_id=user_id,
                            device_id=device_id,
                            camera_make=None if is_fraud and index % 4 == 0 else "Canon",
                            camera_model=None if is_fraud and index % 4 == 0 else "EOS-Mock",
                            software_tag=(
                                "Snap Camera"
                                if is_fraud and typology == FraudTypology.DEEPFAKE_LIVENESS
                                else None
                            ),
                        ),
                    ),
                    self._event(
                        EventType.BEHAVIORAL_SIGNAL_OBSERVED,
                        app_time - timedelta(minutes=10),
                        f"behavior:{user_id}:{device_id}",
                        [self._user(user_id), self._device(device_id)],
                        BehavioralSignalObserved(
                            user_id=user_id,
                            session_id=f"sess_{index:05d}",
                            device_id=device_id,
                            keystroke_interval_ms_stddev=(
                                0.0 if is_fraud and index % 5 == 0 else self.rng.uniform(35, 180)
                            ),
                            mouse_path_entropy=(
                                0.1 if is_fraud and index % 5 == 0 else self.rng.uniform(1.5, 5.0)
                            ),
                            session_duration_seconds=self.rng.uniform(20, 600),
                        ),
                    ),
                    self._event(
                        EventType.APPLICATION_SUBMITTED,
                        app_time,
                        f"application:{user_id}",
                        [self._user(user_id), self._device(device_id), self._application(index)],
                        ApplicationSubmitted(
                            application_id=f"app_{index:05d}",
                            user_id=user_id,
                            device_id=device_id,
                            requested_amount=requested,
                            declared_income=income,
                        ),
                    ),
                ]
            )

            if is_fraud and typology == FraudTypology.ACCOUNT_TAKEOVER:
                events.extend(self._failed_logins(user_id, device_id, ip_address, app_time))

            transaction_id = f"txn_{index:05d}"
            rail = self.rng.choice(list(PaymentRail))
            events.append(
                self._event(
                    EventType.PAYMENT_ATTEMPTED,
                    app_time + timedelta(minutes=5),
                    f"payment:{transaction_id}",
                    [
                        self._user(user_id),
                        self._device(device_id),
                        self._transaction(transaction_id),
                    ],
                    PaymentAttempted(
                        transaction_id=transaction_id,
                        user_id=user_id,
                        device_id=device_id,
                        rail=rail,
                        amount=requested,
                        payee_hash=(
                            "payee_mule_001"
                            if is_fraud and typology == FraudTypology.MONEY_MULE
                            else f"payee_{index % 50:03d}"
                        ),
                        idempotency_key=f"pay:{transaction_id}",
                    ),
                )
            )

            if not is_fraud or typology not in {FraudTypology.CARD_TESTING, FraudTypology.APP_SCAM}:
                events.append(
                    self._event(
                        EventType.PAYMENT_SETTLED,
                        app_time + timedelta(minutes=10),
                        f"settled:{transaction_id}",
                        [self._user(user_id), self._transaction(transaction_id)],
                        PaymentSettled(
                            transaction_id=transaction_id,
                            user_id=user_id,
                            amount=requested,
                            rail=rail,
                        ),
                    )
                )

            if is_fraud:
                events.extend(
                    self._fraud_outcome(
                        user_id, transaction_id, requested, rail, typology, app_time
                    )
                )

        return SyntheticDataset(sorted(events, key=lambda event: event.occurred_at))

    def _failed_logins(
        self, user_id: str, device_id: str, ip_address: str, app_time: datetime
    ) -> list[EventEnvelope]:
        return [
            self._event(
                EventType.LOGIN_ATTEMPT,
                app_time - timedelta(minutes=3, seconds=offset),
                f"login:{user_id}:{offset}",
                [self._user(user_id), self._device(device_id), self._ip(ip_address)],
                LoginAttempt(
                    user_id=user_id,
                    device_id=device_id,
                    ip_address=ip_address,
                    success=False,
                    failure_reason="bad_password",
                ),
            )
            for offset in range(6)
        ]

    def _fraud_outcome(
        self,
        user_id: str,
        transaction_id: str,
        amount: Decimal,
        rail: PaymentRail,
        typology: FraudTypology,
        app_time: datetime,
    ) -> list[EventEnvelope]:
        label_time = app_time + timedelta(days=7)
        return [
            self._event(
                EventType.CHARGEBACK_RECEIVED,
                label_time,
                f"chargeback:{transaction_id}",
                [self._user(user_id), self._transaction(transaction_id)],
                ChargebackReceived(
                    transaction_id=transaction_id,
                    user_id=user_id,
                    amount=amount,
                    reason=typology.value.lower(),
                ),
            ),
            self._event(
                EventType.LABEL_CREATED,
                label_time + timedelta(minutes=1),
                f"label:{user_id}",
                [self._user(user_id)],
                LabelCreated(
                    target_entity=self._user(user_id),
                    label_value=LabelValue.FRAUD,
                    typology=typology,
                    label_available_at=label_time,
                    source="synthetic_ground_truth",
                ),
            ),
        ]

    def _event(
        self,
        event_type: EventType,
        occurred_at: datetime,
        idempotency_key: str,
        entity_refs: list[EntityRef],
        payload: Any,
    ) -> EventEnvelope:
        event_id = uuid5(NAMESPACE_URL, f"fraud-v2:{idempotency_key}:{occurred_at.isoformat()}")
        return EventEnvelope(
            event_id=event_id,
            event_type=event_type,
            occurred_at=occurred_at,
            idempotency_key=idempotency_key,
            entity_refs=entity_refs,
            payload=payload,
        )

    def _typology(self, index: int) -> FraudTypology:
        typologies = [
            FraudTypology.SYNTHETIC_IDENTITY,
            FraudTypology.ACCOUNT_TAKEOVER,
            FraudTypology.CARD_TESTING,
            FraudTypology.FIRST_PARTY_FRAUD,
            FraudTypology.MONEY_MULE,
            FraudTypology.APP_SCAM,
            FraudTypology.DEEPFAKE_LIVENESS,
        ]
        return typologies[index % len(typologies)]

    def _user(self, user_id: str) -> EntityRef:
        return EntityRef(entity_type=EntityType.USER, entity_id=user_id)

    def _device(self, device_id: str) -> EntityRef:
        return EntityRef(entity_type=EntityType.DEVICE, entity_id=device_id)

    def _ip(self, ip_address: str) -> EntityRef:
        return EntityRef(entity_type=EntityType.IP_ADDRESS, entity_id=ip_address)

    def _transaction(self, transaction_id: str) -> EntityRef:
        return EntityRef(entity_type=EntityType.TRANSACTION, entity_id=transaction_id)

    def _application(self, index: int) -> EntityRef:
        return EntityRef(entity_type=EntityType.APPLICATION, entity_id=f"app_{index:05d}")


def load_events_jsonl(path: Path) -> list[EventEnvelope]:
    events: list[EventEnvelope] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                events.append(EventEnvelope.model_validate_json(line))
    return events


def write_events_jsonl(events: Iterable[EventEnvelope], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for event in events:
            payload = json.loads(event.model_dump_json())
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
