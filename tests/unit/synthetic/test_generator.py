from fraud_v2.domain.enums import EventType
from fraud_v2.synthetic.generator import SyntheticFraudGenerator


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
