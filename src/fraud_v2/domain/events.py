from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from fraud_v2.domain.entities import EntityRef
from fraud_v2.domain.enums import EventType, FraudTypology, LabelValue, PaymentRail, ReviewOutcome


class ApplicationSubmitted(BaseModel):
    event_type: Literal[EventType.APPLICATION_SUBMITTED] = EventType.APPLICATION_SUBMITTED
    application_id: str
    user_id: str
    device_id: str
    requested_amount: Decimal = Field(gt=0)
    declared_income: Decimal = Field(gt=0)
    product: str = "instant_cash"
    channel: str = "web"


class DeviceObserved(BaseModel):
    event_type: Literal[EventType.DEVICE_OBSERVED] = EventType.DEVICE_OBSERVED
    user_id: str
    device_id: str
    browser_fingerprint_hash: str
    ip_address: str
    user_agent_family: str
    timezone_offset_minutes: int
    emulator_flag: bool = False


class CameraMetadataObserved(BaseModel):
    event_type: Literal[EventType.CAMERA_METADATA_OBSERVED] = EventType.CAMERA_METADATA_OBSERVED
    user_id: str
    device_id: str
    camera_make: str | None = None
    camera_model: str | None = None
    software_tag: str | None = None


class LoginAttempt(BaseModel):
    event_type: Literal[EventType.LOGIN_ATTEMPT] = EventType.LOGIN_ATTEMPT
    user_id: str
    device_id: str
    ip_address: str
    success: bool
    failure_reason: str | None = None


class BehavioralSignalObserved(BaseModel):
    event_type: Literal[EventType.BEHAVIORAL_SIGNAL_OBSERVED] = EventType.BEHAVIORAL_SIGNAL_OBSERVED
    user_id: str
    session_id: str
    device_id: str
    keystroke_interval_ms_stddev: float = Field(ge=0)
    mouse_path_entropy: float = Field(ge=0)
    session_duration_seconds: float = Field(ge=0)


class PaymentAttempted(BaseModel):
    event_type: Literal[EventType.PAYMENT_ATTEMPTED] = EventType.PAYMENT_ATTEMPTED
    transaction_id: str
    user_id: str
    device_id: str
    rail: PaymentRail
    amount: Decimal = Field(gt=0)
    payee_hash: str
    idempotency_key: str


class PaymentSettled(BaseModel):
    event_type: Literal[EventType.PAYMENT_SETTLED] = EventType.PAYMENT_SETTLED
    transaction_id: str
    user_id: str
    amount: Decimal = Field(gt=0)
    rail: PaymentRail


class ChargebackReceived(BaseModel):
    event_type: Literal[EventType.CHARGEBACK_RECEIVED] = EventType.CHARGEBACK_RECEIVED
    transaction_id: str
    user_id: str
    amount: Decimal = Field(gt=0)
    reason: str


class ManualReviewDecided(BaseModel):
    event_type: Literal[EventType.MANUAL_REVIEW_DECIDED] = EventType.MANUAL_REVIEW_DECIDED
    case_id: str
    decision_id: str
    analyst_id: str
    outcome: ReviewOutcome
    confidence: float = Field(ge=0.0, le=1.0)
    note: str = Field(default="", max_length=2000)


class LabelCreated(BaseModel):
    event_type: Literal[EventType.LABEL_CREATED] = EventType.LABEL_CREATED
    target_entity: EntityRef
    label_value: LabelValue
    typology: FraudTypology = FraudTypology.UNKNOWN
    label_available_at: datetime
    source: str


CanonicalPayload = Annotated[
    ApplicationSubmitted
    | DeviceObserved
    | CameraMetadataObserved
    | LoginAttempt
    | BehavioralSignalObserved
    | PaymentAttempted
    | PaymentSettled
    | ChargebackReceived
    | ManualReviewDecided
    | LabelCreated,
    Field(discriminator="event_type"),
]


class EventEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID = Field(default_factory=uuid4)
    event_type: EventType
    occurred_at: datetime
    received_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    schema_version: str = "1.0"
    idempotency_key: str = Field(min_length=8, max_length=240)
    entity_refs: list[EntityRef]
    payload: CanonicalPayload

    @model_validator(mode="after")
    def payload_type_matches_envelope(self) -> EventEnvelope:
        if self.payload.event_type != self.event_type:
            raise ValueError("payload event_type must match envelope event_type")
        return self
