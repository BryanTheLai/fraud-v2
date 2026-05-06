import pytest

from fraud_v2.domain.stream import StreamDeadLetter, StreamDeadLetterReason
from fraud_v2.infrastructure import (
    neo4j_projector as neo4j_projector_module,
)
from fraud_v2.infrastructure import (
    redpanda_dead_letter_publisher as dead_letter_module,
)
from fraud_v2.infrastructure import (
    redpanda_publisher as publisher_module,
)
from fraud_v2.infrastructure.neo4j_projector import Neo4jGraphProjector
from fraud_v2.infrastructure.optional_imports import optional_module
from fraud_v2.infrastructure.redpanda_dead_letter_publisher import RedpandaDeadLetterPublisher
from fraud_v2.infrastructure.redpanda_publisher import RedpandaEventPublisher
from fraud_v2.public_data.registry import describe_public_dataset
from fraud_v2.synthetic.generator import SyntheticFraudGenerator


def test_optional_module_error_names_extra() -> None:
    with pytest.raises(RuntimeError, match="uv sync --extra infra"):
        optional_module("not_a_real_module_for_fraud_v2", "infra")


def test_public_dataset_registry_describes_known_dataset() -> None:
    dataset = describe_public_dataset("paysim")

    assert dataset.name == "paysim"
    assert "fraud" in dataset.purpose.lower()


class _TimedOutProducer:
    def produce(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        pass

    def flush(self, timeout: int) -> int:
        assert timeout == 10
        return 1


class _TimedOutKafka:
    def Producer(self, config):  # type: ignore[no-untyped-def]
        assert "bootstrap.servers" in config
        return _TimedOutProducer()


def test_redpanda_event_publisher_fails_when_flush_leaves_messages(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    event = SyntheticFraudGenerator(seed=7).generate(users=1).events[0]
    monkeypatch.setattr(publisher_module, "optional_module", lambda *_args: _TimedOutKafka())

    with pytest.raises(TimeoutError, match="still queued"):
        RedpandaEventPublisher().publish("fraud.events", event)


def test_redpanda_dead_letter_publisher_fails_when_flush_leaves_messages(
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    dead_letter = StreamDeadLetter(
        source_topic="fraud.events",
        consumer_group="fraud-v2-test",
        reason=StreamDeadLetterReason.INVALID_EVENT,
        safe_error="invalid local test payload",
    )
    monkeypatch.setattr(dead_letter_module, "optional_module", lambda *_args: _TimedOutKafka())

    with pytest.raises(TimeoutError, match="dead-letter publish timed out"):
        RedpandaDeadLetterPublisher().publish("fraud.dead_letters", dead_letter)


def test_neo4j_projector_closes_driver_when_projection_fails(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    events = SyntheticFraudGenerator(seed=7).generate(users=1).events[:1]
    driver = _ClosingDriver()

    class FakeGraphDatabase:
        @staticmethod
        def driver(*args, **kwargs):  # type: ignore[no-untyped-def]
            return driver

    class FakeNeo4j:
        GraphDatabase = FakeGraphDatabase

    monkeypatch.setattr(neo4j_projector_module, "optional_module", lambda *_args: FakeNeo4j)

    with pytest.raises(RuntimeError, match="cypher failed"):
        Neo4jGraphProjector().project(events)

    assert driver.closed is True


class _FailingSession:
    def __enter__(self):  # type: ignore[no-untyped-def]
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:  # type: ignore[no-untyped-def]
        return False

    def run(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        raise RuntimeError("cypher failed")


class _ClosingDriver:
    def __init__(self) -> None:
        self.closed = False

    def session(self) -> _FailingSession:
        return _FailingSession()

    def close(self) -> None:
        self.closed = True
