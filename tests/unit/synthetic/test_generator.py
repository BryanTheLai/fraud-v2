from collections import Counter

from fraud_v2.domain.enums import EventType
from fraud_v2.domain.events import DeviceObserved, LabelCreated, LoginAttempt, PaymentAttempted
from fraud_v2.synthetic.generator import (
    BENIGN_CORPORATE_VIRTUAL_CAMERA_RANGE,
    BENIGN_DISPUTE_RANGE,
    BENIGN_PAYMENT_BURST_RANGE,
    BENIGN_TRAVEL_RECOVERY_RANGE,
    DEFAULT_SYNTHETIC_USERS,
    FRAUD_TYPOLOGIES,
    HOUSEHOLD_SHARED_DEVICE_RANGE,
    SyntheticFraudGenerator,
)


def test_synthetic_generator_is_deterministic() -> None:
    first = SyntheticFraudGenerator(seed=1).generate(users=20)
    second = SyntheticFraudGenerator(seed=1).generate(users=20)

    assert [event.event_id for event in first.events] == [event.event_id for event in second.events]


def test_synthetic_generator_covers_required_events() -> None:
    dataset = SyntheticFraudGenerator(seed=1).generate(users=50)
    event_types = {event.event_type for event in dataset.events}

    assert EventType.APPLICATION_SUBMITTED in event_types
    assert EventType.DEVICE_OBSERVED in event_types
    assert EventType.PAYMENT_ATTEMPTED in event_types
    assert EventType.LABEL_CREATED in event_types


def test_synthetic_generator_covers_plausible_edge_case_profiles() -> None:
    dataset = SyntheticFraudGenerator(seed=1).generate(users=DEFAULT_SYNTHETIC_USERS)
    labels = [
        event.payload.typology
        for event in dataset.events
        if isinstance(event.payload, LabelCreated)
    ]
    payment_attempts_by_user = Counter(
        event.payload.user_id
        for event in dataset.events
        if isinstance(event.payload, PaymentAttempted)
    )
    failed_logins_by_user = Counter(
        event.payload.user_id
        for event in dataset.events
        if isinstance(event.payload, LoginAttempt) and not event.payload.success
    )
    device_observations = Counter(
        event.payload.device_id
        for event in dataset.events
        if isinstance(event.payload, DeviceObserved)
    )

    assert len(dataset.events) >= 4500
    assert set(labels) >= set(FRAUD_TYPOLOGIES)
    assert any(count >= 3 for count in payment_attempts_by_user.values())
    assert device_observations["dev_household_shared_001"] == len(HOUSEHOLD_SHARED_DEVICE_RANGE)
    assert any(
        user_id in failed_logins_by_user
        for user_id in _users_from_range(BENIGN_TRAVEL_RECOVERY_RANGE)
    )
    assert any(
        payment_attempts_by_user[user_id] >= 3
        for user_id in _users_from_range(BENIGN_PAYMENT_BURST_RANGE)
    )
    assert any(
        getattr(event.payload, "user_id", "")
        in _users_from_range(BENIGN_CORPORATE_VIRTUAL_CAMERA_RANGE)
        and getattr(event.payload, "software_tag", None) == "OBS Virtual Camera"
        for event in dataset.events
    )
    assert any(
        getattr(event.payload, "user_id", "") in _users_from_range(BENIGN_DISPUTE_RANGE)
        and getattr(event.payload, "reason", None) == "customer_hardship_reversed"
        for event in dataset.events
    )
    assert any(
        device_id.startswith("dev_fraud_ring") and count >= 4
        for device_id, count in device_observations.items()
    )


def _users_from_range(values: range) -> set[str]:
    return {f"user_{index:05d}" for index in values}
