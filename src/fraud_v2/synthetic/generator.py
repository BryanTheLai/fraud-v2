from __future__ import annotations

import json
import random
from collections.abc import Iterable
from dataclasses import dataclass
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

DEFAULT_SYNTHETIC_USERS = 720
FRAUD_TYPOLOGIES: tuple[FraudTypology, ...] = (
    FraudTypology.SYNTHETIC_IDENTITY,
    FraudTypology.ACCOUNT_TAKEOVER,
    FraudTypology.CARD_TESTING,
    FraudTypology.FIRST_PARTY_FRAUD,
    FraudTypology.MONEY_MULE,
    FraudTypology.APP_SCAM,
    FraudTypology.BEC,
    FraudTypology.DEEPFAKE_LIVENESS,
    FraudTypology.BUST_OUT,
)
HOUSEHOLD_SHARED_DEVICE_RANGE = range(520, 536)
BENIGN_CORPORATE_VIRTUAL_CAMERA_RANGE = range(560, 572)
BENIGN_TRAVEL_RECOVERY_RANGE = range(580, 592)
BENIGN_PAYMENT_BURST_RANGE = range(600, 612)
BENIGN_DISPUTE_RANGE = range(620, 628)


@dataclass(frozen=True)
class SyntheticUserProfile:
    user_id: str
    index: int
    is_fraud: bool
    typology: FraudTypology
    device_id: str
    ip_address: str
    fingerprint_hash: str
    requested_amount: Decimal
    declared_income: Decimal
    payee_hash: str
    camera_make: str | None
    camera_model: str | None
    software_tag: str | None
    low_behavior_entropy: bool
    emulator_flag: bool
    payment_attempts: int
    settles_payment: bool
    chargeback_delay_days: int


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

    def generate(
        self,
        users: int = DEFAULT_SYNTHETIC_USERS,
        fraud_rate: float = 0.12,
    ) -> SyntheticDataset:
        events: list[EventEnvelope] = []
        fraud_users = max(1, int(users * fraud_rate))

        for index in range(users):
            profile = self._profile(index, fraud_users)
            app_time = self.base_time + timedelta(minutes=index * 2)

            events.extend(
                [
                    self._event(
                        EventType.DEVICE_OBSERVED,
                        app_time - timedelta(minutes=15),
                        f"device:{profile.user_id}:{profile.device_id}",
                        [
                            self._user(profile.user_id),
                            self._device(profile.device_id),
                            self._ip(profile.ip_address),
                        ],
                        DeviceObserved(
                            user_id=profile.user_id,
                            device_id=profile.device_id,
                            browser_fingerprint_hash=profile.fingerprint_hash,
                            ip_address=profile.ip_address,
                            user_agent_family=self._user_agent(profile),
                            timezone_offset_minutes=self.rng.choice([-480, -300, 0, 480]),
                            emulator_flag=profile.emulator_flag,
                        ),
                    ),
                    self._event(
                        EventType.CAMERA_METADATA_OBSERVED,
                        app_time - timedelta(minutes=12),
                        f"camera:{profile.user_id}:{profile.device_id}",
                        [self._user(profile.user_id), self._device(profile.device_id)],
                        CameraMetadataObserved(
                            user_id=profile.user_id,
                            device_id=profile.device_id,
                            camera_make=profile.camera_make,
                            camera_model=profile.camera_model,
                            software_tag=profile.software_tag,
                        ),
                    ),
                    self._event(
                        EventType.BEHAVIORAL_SIGNAL_OBSERVED,
                        app_time - timedelta(minutes=10),
                        f"behavior:{profile.user_id}:{profile.device_id}",
                        [self._user(profile.user_id), self._device(profile.device_id)],
                        BehavioralSignalObserved(
                            user_id=profile.user_id,
                            session_id=f"sess_{index:05d}",
                            device_id=profile.device_id,
                            keystroke_interval_ms_stddev=(
                                0.0 if profile.low_behavior_entropy else self.rng.uniform(35, 180)
                            ),
                            mouse_path_entropy=(
                                0.1 if profile.low_behavior_entropy else self.rng.uniform(1.5, 5.0)
                            ),
                            session_duration_seconds=self.rng.uniform(20, 600),
                        ),
                    ),
                    self._event(
                        EventType.APPLICATION_SUBMITTED,
                        app_time,
                        f"application:{profile.user_id}",
                        [
                            self._user(profile.user_id),
                            self._device(profile.device_id),
                            self._application(index),
                        ],
                        ApplicationSubmitted(
                            application_id=f"app_{index:05d}",
                            user_id=profile.user_id,
                            device_id=profile.device_id,
                            requested_amount=profile.requested_amount,
                            declared_income=profile.declared_income,
                        ),
                    ),
                ]
            )

            if profile.typology == FraudTypology.ACCOUNT_TAKEOVER:
                events.extend(self._failed_logins(profile, app_time))

            payments = self._payment_events(profile, app_time)
            events.extend(payments)
            if profile.is_fraud and payments:
                first_payment = payments[0].payload
                if isinstance(first_payment, PaymentAttempted):
                    events.extend(self._fraud_outcome(profile, first_payment, app_time))
            if not profile.is_fraud and profile.index in BENIGN_TRAVEL_RECOVERY_RANGE:
                events.extend(self._benign_recovery_logins(profile, app_time))
            if not profile.is_fraud and profile.index in BENIGN_DISPUTE_RANGE and payments:
                first_payment = payments[0].payload
                if isinstance(first_payment, PaymentAttempted):
                    events.extend(self._benign_dispute_outcome(profile, first_payment, app_time))

        return SyntheticDataset(sorted(events, key=lambda event: event.occurred_at))

    def _profile(self, index: int, fraud_users: int) -> SyntheticUserProfile:
        user_id = f"user_{index:05d}"
        is_fraud = index < fraud_users
        typology = self._typology(index) if is_fraud else FraudTypology.UNKNOWN
        device_id = self._device_id(index=index, is_fraud=is_fraud, typology=typology)
        requested = self._requested_amount(is_fraud=is_fraud, typology=typology)
        return SyntheticUserProfile(
            user_id=user_id,
            index=index,
            is_fraud=is_fraud,
            typology=typology,
            device_id=device_id,
            ip_address=self._ip_address(index=index, is_fraud=is_fraud, typology=typology),
            fingerprint_hash=self._fingerprint(index=index, device_id=device_id),
            requested_amount=requested,
            declared_income=self._declared_income(is_fraud=is_fraud, typology=typology),
            payee_hash=self._payee_hash(index=index, is_fraud=is_fraud, typology=typology),
            camera_make=self._camera_make(is_fraud=is_fraud, typology=typology, index=index),
            camera_model=self._camera_model(is_fraud=is_fraud, typology=typology, index=index),
            software_tag=self._software_tag(
                typology=typology,
                index=index,
                is_fraud=is_fraud,
            ),
            low_behavior_entropy=is_fraud
            and typology
            in {
                FraudTypology.ACCOUNT_TAKEOVER,
                FraudTypology.DEEPFAKE_LIVENESS,
                FraudTypology.CARD_TESTING,
            },
            emulator_flag=is_fraud
            and typology in {FraudTypology.ACCOUNT_TAKEOVER, FraudTypology.CARD_TESTING},
            payment_attempts=self._payment_attempt_count(
                index=index,
                is_fraud=is_fraud,
                typology=typology,
            ),
            settles_payment=typology
            not in {FraudTypology.CARD_TESTING, FraudTypology.APP_SCAM, FraudTypology.BUST_OUT},
            chargeback_delay_days=1
            if typology == FraudTypology.CARD_TESTING
            else 14
            if typology == FraudTypology.BUST_OUT
            else 7,
        )

    def _failed_logins(
        self, profile: SyntheticUserProfile, app_time: datetime
    ) -> list[EventEnvelope]:
        return [
            self._event(
                EventType.LOGIN_ATTEMPT,
                app_time - timedelta(minutes=3, seconds=offset),
                f"login:{profile.user_id}:{offset}",
                [
                    self._user(profile.user_id),
                    self._device(profile.device_id),
                    self._ip(profile.ip_address),
                ],
                LoginAttempt(
                    user_id=profile.user_id,
                    device_id=profile.device_id,
                    ip_address=profile.ip_address,
                    success=False,
                    failure_reason="bad_password",
                ),
            )
            for offset in range(6)
        ]

    def _benign_recovery_logins(
        self, profile: SyntheticUserProfile, app_time: datetime
    ) -> list[EventEnvelope]:
        attempts: list[EventEnvelope] = []
        for offset in range(2):
            attempts.append(
                self._event(
                    EventType.LOGIN_ATTEMPT,
                    app_time - timedelta(minutes=2, seconds=offset * 20),
                    f"login-recovery:{profile.user_id}:failed:{offset}",
                    [
                        self._user(profile.user_id),
                        self._device(profile.device_id),
                        self._ip(profile.ip_address),
                    ],
                    LoginAttempt(
                        user_id=profile.user_id,
                        device_id=profile.device_id,
                        ip_address=profile.ip_address,
                        success=False,
                        failure_reason="forgot_password",
                    ),
                )
            )
        attempts.append(
            self._event(
                EventType.LOGIN_ATTEMPT,
                app_time - timedelta(minutes=1),
                f"login-recovery:{profile.user_id}:success",
                [
                    self._user(profile.user_id),
                    self._device(profile.device_id),
                    self._ip(profile.ip_address),
                ],
                LoginAttempt(
                    user_id=profile.user_id,
                    device_id=profile.device_id,
                    ip_address=profile.ip_address,
                    success=True,
                ),
            )
        )
        return attempts

    def _payment_events(
        self, profile: SyntheticUserProfile, app_time: datetime
    ) -> list[EventEnvelope]:
        events: list[EventEnvelope] = []
        rail = self._payment_rail(profile.typology)
        for attempt in range(profile.payment_attempts):
            transaction_id = f"txn_{profile.index:05d}_{attempt:02d}"
            amount = self._payment_amount(profile, attempt)
            occurred_at = app_time + timedelta(minutes=5, seconds=attempt * 70)
            events.append(
                self._event(
                    EventType.PAYMENT_ATTEMPTED,
                    occurred_at,
                    f"payment:{transaction_id}",
                    [
                        self._user(profile.user_id),
                        self._device(profile.device_id),
                        self._transaction(transaction_id),
                    ],
                    PaymentAttempted(
                        transaction_id=transaction_id,
                        user_id=profile.user_id,
                        device_id=profile.device_id,
                        rail=rail,
                        amount=amount,
                        payee_hash=profile.payee_hash,
                        idempotency_key=f"pay:{transaction_id}",
                    ),
                )
            )
            if profile.settles_payment and attempt == 0:
                events.append(
                    self._event(
                        EventType.PAYMENT_SETTLED,
                        occurred_at + timedelta(minutes=5),
                        f"settled:{transaction_id}",
                        [self._user(profile.user_id), self._transaction(transaction_id)],
                        PaymentSettled(
                            transaction_id=transaction_id,
                            user_id=profile.user_id,
                            amount=amount,
                            rail=rail,
                        ),
                    )
                )
        return events

    def _fraud_outcome(
        self, profile: SyntheticUserProfile, payment: PaymentAttempted, app_time: datetime
    ) -> list[EventEnvelope]:
        label_time = app_time + timedelta(days=profile.chargeback_delay_days)
        return [
            self._event(
                EventType.CHARGEBACK_RECEIVED,
                label_time,
                f"chargeback:{payment.transaction_id}",
                [self._user(profile.user_id), self._transaction(payment.transaction_id)],
                ChargebackReceived(
                    transaction_id=payment.transaction_id,
                    user_id=profile.user_id,
                    amount=payment.amount,
                    reason=profile.typology.value.lower(),
                ),
            ),
            self._event(
                EventType.LABEL_CREATED,
                label_time + timedelta(minutes=1),
                f"label:{profile.user_id}",
                [self._user(profile.user_id)],
                LabelCreated(
                    target_entity=self._user(profile.user_id),
                    label_value=LabelValue.FRAUD,
                    typology=profile.typology,
                    label_available_at=label_time,
                    source="synthetic_ground_truth",
                ),
            ),
        ]

    def _benign_dispute_outcome(
        self, profile: SyntheticUserProfile, payment: PaymentAttempted, app_time: datetime
    ) -> list[EventEnvelope]:
        label_time = app_time + timedelta(days=5)
        return [
            self._event(
                EventType.CHARGEBACK_RECEIVED,
                label_time,
                f"benign-dispute:{payment.transaction_id}",
                [self._user(profile.user_id), self._transaction(payment.transaction_id)],
                ChargebackReceived(
                    transaction_id=payment.transaction_id,
                    user_id=profile.user_id,
                    amount=payment.amount,
                    reason="customer_hardship_reversed",
                ),
            ),
            self._event(
                EventType.LABEL_CREATED,
                label_time + timedelta(minutes=1),
                f"legit-label:{profile.user_id}",
                [self._user(profile.user_id)],
                LabelCreated(
                    target_entity=self._user(profile.user_id),
                    label_value=LabelValue.LEGITIMATE,
                    typology=FraudTypology.UNKNOWN,
                    label_available_at=label_time,
                    source="synthetic_false_positive_control",
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
        return FRAUD_TYPOLOGIES[index % len(FRAUD_TYPOLOGIES)]

    def _device_id(self, *, index: int, is_fraud: bool, typology: FraudTypology) -> str:
        if is_fraud and typology in {FraudTypology.MONEY_MULE, FraudTypology.SYNTHETIC_IDENTITY}:
            return f"dev_fraud_ring_{index % 4:03d}"
        if is_fraud and typology == FraudTypology.CARD_TESTING:
            return f"dev_card_testing_{index % 3:03d}"
        if not is_fraud and index in HOUSEHOLD_SHARED_DEVICE_RANGE:
            return "dev_household_shared_001"
        return f"dev_{index:05d}"

    def _ip_address(self, *, index: int, is_fraud: bool, typology: FraudTypology) -> str:
        if is_fraud and typology in {FraudTypology.MONEY_MULE, FraudTypology.SYNTHETIC_IDENTITY}:
            return f"10.10.{index % 3}.99"
        if is_fraud and typology == FraudTypology.ACCOUNT_TAKEOVER:
            return "198.51.100.77"
        if not is_fraud and index in HOUSEHOLD_SHARED_DEVICE_RANGE:
            return "10.0.88.12"
        if not is_fraud and index in BENIGN_TRAVEL_RECOVERY_RANGE:
            return f"203.0.113.{index % 200}"
        return f"10.0.{index // 255}.{index % 255}"

    def _fingerprint(self, *, index: int, device_id: str) -> str:
        if device_id.startswith("dev_fraud_ring"):
            return f"fp_ring_{device_id[-3:]}"
        if device_id.startswith("dev_card_testing"):
            return f"fp_card_{device_id[-3:]}"
        if device_id == "dev_household_shared_001":
            return "fp_household_shared"
        return f"fp_{index:05d}"

    def _requested_amount(self, *, is_fraud: bool, typology: FraudTypology) -> Decimal:
        if typology == FraudTypology.FIRST_PARTY_FRAUD:
            return Decimal(str(self.rng.choice([1000, 1500, 2000])))
        if typology == FraudTypology.BUST_OUT:
            return Decimal(str(self.rng.choice([1500, 2000, 2500])))
        if typology in {FraudTypology.CARD_TESTING, FraudTypology.APP_SCAM, FraudTypology.BEC}:
            return Decimal(str(self.rng.choice([50, 100, 250, 500])))
        if is_fraud:
            return Decimal(str(self.rng.choice([500, 1000, 1500])))
        return Decimal(str(self.rng.choice([50, 100, 250, 500, 750])))

    def _declared_income(self, *, is_fraud: bool, typology: FraudTypology) -> Decimal:
        if typology in {FraudTypology.SYNTHETIC_IDENTITY, FraudTypology.BUST_OUT}:
            return Decimal(str(self.rng.choice([90000, 99000, 150000, 199000])))
        if typology == FraudTypology.FIRST_PARTY_FRAUD:
            return Decimal(str(self.rng.choice([32000, 55000, 90000])))
        if is_fraud:
            return Decimal(str(self.rng.choice([18000, 32000, 55000, 90000])))
        return Decimal(str(self.rng.choice([18000, 24000, 32000, 42000, 55000, 75000])))

    def _payee_hash(self, *, index: int, is_fraud: bool, typology: FraudTypology) -> str:
        if typology == FraudTypology.MONEY_MULE:
            return f"payee_mule_{index % 5:03d}"
        if typology in {FraudTypology.APP_SCAM, FraudTypology.BEC}:
            return f"payee_scam_{index % 4:03d}"
        if typology == FraudTypology.CARD_TESTING:
            return f"payee_card_test_{index % 3:03d}"
        if is_fraud and typology == FraudTypology.BUST_OUT:
            return "payee_bustout_cashout"
        return f"payee_{index % 80:03d}"

    def _camera_make(self, *, is_fraud: bool, typology: FraudTypology, index: int) -> str | None:
        if not is_fraud and index in BENIGN_CORPORATE_VIRTUAL_CAMERA_RANGE:
            return "Logitech"
        if is_fraud and typology in {FraudTypology.DEEPFAKE_LIVENESS, FraudTypology.MONEY_MULE}:
            return None
        if is_fraud and index % 9 == 0:
            return None
        return self.rng.choice(["Canon", "Logitech", "Sony", "Apple"])

    def _camera_model(self, *, is_fraud: bool, typology: FraudTypology, index: int) -> str | None:
        if not is_fraud and index in BENIGN_CORPORATE_VIRTUAL_CAMERA_RANGE:
            return "C920"
        if is_fraud and typology in {FraudTypology.DEEPFAKE_LIVENESS, FraudTypology.MONEY_MULE}:
            return None
        if is_fraud and index % 9 == 0:
            return None
        return self.rng.choice(["EOS-Mock", "C920", "FaceTime-HD", "ZV-Mock"])

    def _software_tag(
        self,
        *,
        typology: FraudTypology,
        index: int = -1,
        is_fraud: bool = True,
    ) -> str | None:
        if not is_fraud and index in BENIGN_CORPORATE_VIRTUAL_CAMERA_RANGE:
            return "OBS Virtual Camera"
        if typology == FraudTypology.DEEPFAKE_LIVENESS:
            return self.rng.choice(["Snap Camera", "OBS Virtual Camera"])
        return None

    def _payment_attempt_count(
        self,
        *,
        index: int,
        is_fraud: bool,
        typology: FraudTypology,
    ) -> int:
        if not is_fraud and index in BENIGN_PAYMENT_BURST_RANGE:
            return 3
        if typology == FraudTypology.CARD_TESTING:
            return 5
        if typology in {FraudTypology.APP_SCAM, FraudTypology.BEC}:
            return 3
        if typology == FraudTypology.BUST_OUT:
            return 4
        return 1

    def _payment_rail(self, typology: FraudTypology) -> PaymentRail:
        if typology in {FraudTypology.APP_SCAM, FraudTypology.BEC, FraudTypology.MONEY_MULE}:
            return PaymentRail.RTP
        if typology == FraudTypology.CARD_TESTING:
            return PaymentRail.DEBIT_CARD
        return self.rng.choice(list(PaymentRail))

    def _payment_amount(self, profile: SyntheticUserProfile, attempt: int) -> Decimal:
        if profile.typology == FraudTypology.CARD_TESTING:
            return Decimal(str([5, 8, 12, 18, 25][attempt]))
        if profile.typology in {FraudTypology.APP_SCAM, FraudTypology.BEC}:
            return profile.requested_amount + Decimal(str(attempt * 50))
        if profile.typology == FraudTypology.BUST_OUT:
            return profile.requested_amount + Decimal(str(attempt * 250))
        return profile.requested_amount

    def _user_agent(self, profile: SyntheticUserProfile) -> str:
        if profile.typology == FraudTypology.ACCOUNT_TAKEOVER:
            return "headless_chrome"
        if profile.typology == FraudTypology.CARD_TESTING:
            return "mobile_webview"
        return self.rng.choice(["chrome", "edge", "firefox", "safari"])

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
