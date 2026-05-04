from __future__ import annotations

from datetime import timedelta

from fraud_v2.domain.decisions import FeatureVector
from fraud_v2.domain.entities import EntityRef
from fraud_v2.domain.enums import EntityType, EventType, FeatureFreshnessStatus, LabelValue
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
)


class FeatureBuilder:
    def __init__(self, events: list[EventEnvelope]) -> None:
        self.events = sorted(events, key=lambda event: event.occurred_at)

    def build(self, target: EntityRef, as_of) -> FeatureVector:  # type: ignore[no-untyped-def]
        user_id = target.entity_id
        events = [event for event in self.events if event.occurred_at <= as_of]
        user_events = [event for event in events if self._has_user(event, user_id)]
        latest_device = self._latest_device(user_events)
        device_events = [
            event for event in events if latest_device and self._has_device(event, latest_device)
        ]
        one_hour = as_of - timedelta(hours=1)
        three_minutes = as_of - timedelta(minutes=3)
        ten_minutes = as_of - timedelta(minutes=10)
        day = as_of - timedelta(days=1)

        failed_login_count_3m = sum(
            1
            for event in user_events
            if event.event_type == EventType.LOGIN_ATTEMPT
            and event.occurred_at >= three_minutes
            and isinstance(event.payload, LoginAttempt)
            and not event.payload.success
        )
        applications_per_device_1h = sum(
            1
            for event in device_events
            if event.event_type == EventType.APPLICATION_SUBMITTED and event.occurred_at >= one_hour
        )
        distinct_users_on_device_1h = len(
            {
                event.payload.user_id
                for event in device_events
                if event.occurred_at >= one_hour
                and isinstance(
                    event.payload, ApplicationSubmitted | DeviceObserved | PaymentAttempted
                )
            }
        )
        payment_attempt_count_10m = sum(
            1
            for event in user_events
            if event.event_type == EventType.PAYMENT_ATTEMPTED and event.occurred_at >= ten_minutes
        )
        payment_amount_24h = sum(
            float(event.payload.amount)
            for event in user_events
            if isinstance(event.payload, PaymentAttempted) and event.occurred_at >= day
        )
        chargebacks_total = sum(
            1 for event in user_events if isinstance(event.payload, ChargebackReceived)
        )
        confirmed_fraud_label = any(
            isinstance(event.payload, LabelCreated)
            and event.payload.label_value == LabelValue.FRAUD
            for event in user_events
        )
        virtual_camera_flag = any(
            isinstance(event.payload, CameraMetadataObserved)
            and (
                event.payload.camera_model is None
                or (event.payload.software_tag or "").lower()
                in {"snap camera", "obs virtual camera"}
            )
            for event in user_events
        )
        low_behavior_entropy = any(
            isinstance(event.payload, BehavioralSignalObserved)
            and (
                event.payload.keystroke_interval_ms_stddev < 5
                or event.payload.mouse_path_entropy < 0.5
            )
            for event in user_events
        )

        values: dict[str, float | int | str | bool] = {
            "failed_login_count_3m": failed_login_count_3m,
            "applications_per_device_1h": applications_per_device_1h,
            "distinct_users_on_device_1h": distinct_users_on_device_1h,
            "payment_attempt_count_10m": payment_attempt_count_10m,
            "payment_amount_24h": payment_amount_24h,
            "chargebacks_total": chargebacks_total,
            "confirmed_fraud_label": confirmed_fraud_label,
            "virtual_camera_flag": virtual_camera_flag,
            "low_behavior_entropy": low_behavior_entropy,
            "latest_device_known": latest_device is not None,
        }
        freshness = {name: FeatureFreshnessStatus.FRESH for name in values}
        if target.entity_type != EntityType.USER:
            freshness["target_entity_type"] = FeatureFreshnessStatus.DEGRADED
        return FeatureVector(
            target_entity=target,
            as_of=as_of,
            values=values,
            freshness=freshness,
            source_event_ids=[str(event.event_id) for event in user_events[-50:]],
        )

    def _latest_device(self, events: list[EventEnvelope]) -> str | None:
        for event in reversed(events):
            payload = event.payload
            if isinstance(
                payload,
                ApplicationSubmitted
                | DeviceObserved
                | LoginAttempt
                | BehavioralSignalObserved
                | PaymentAttempted
                | CameraMetadataObserved,
            ):
                return payload.device_id
        return None

    def _has_user(self, event: EventEnvelope, user_id: str) -> bool:
        return any(
            ref.entity_type == EntityType.USER and ref.entity_id == user_id
            for ref in event.entity_refs
        )

    def _has_device(self, event: EventEnvelope, device_id: str) -> bool:
        return any(
            ref.entity_type == EntityType.DEVICE and ref.entity_id == device_id
            for ref in event.entity_refs
        )
