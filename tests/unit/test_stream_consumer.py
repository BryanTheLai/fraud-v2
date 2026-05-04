from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from fraud_v2.domain.events import EventEnvelope
from fraud_v2.domain.stream import StreamDeadLetter
from fraud_v2.storage.sqlite_store import SQLiteStore
from fraud_v2.synthetic.generator import SyntheticFraudGenerator
from fraud_v2.workers.stream_consumer import StreamIngestionWorker, StreamMessage


@dataclass
class FakeMessage:
    raw_value: bytes | str | None
    error_value: object | None = None

    def value(self) -> bytes | str | None:
        return self.raw_value

    def error(self) -> object | None:
        return self.error_value


@dataclass
class FakeConsumer:
    messages: list[StreamMessage]
    subscriptions: list[list[str]] = field(default_factory=list)
    committed: list[StreamMessage] = field(default_factory=list)
    closed: bool = False

    def subscribe(self, topics: list[str]) -> None:
        self.subscriptions.append(topics)

    def poll(self, timeout: float) -> StreamMessage | None:
        if not self.messages:
            return None
        return self.messages.pop(0)

    def commit(
        self,
        message: StreamMessage | None = None,
        offsets: object | None = None,
        asynchronous: bool = True,
    ) -> object:
        if message is not None:
            self.committed.append(message)
        return None

    def close(self) -> None:
        self.closed = True


@dataclass
class FakeDeadLetterPublisher:
    published: list[tuple[str, StreamDeadLetter]] = field(default_factory=list)

    def publish(self, topic: str, dead_letter: StreamDeadLetter) -> None:
        self.published.append((topic, dead_letter))


class FailingDeadLetterPublisher:
    def publish(self, topic: str, dead_letter: StreamDeadLetter) -> None:
        raise RuntimeError(f"dlq publish failed: {topic}:{dead_letter.dead_letter_id}")


def test_stream_consumer_ingests_event_without_reenqueuing_outbox(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteStore(tmp_path / "fraud.sqlite")
    event = _event()
    consumer = FakeConsumer([FakeMessage(event.model_dump_json().encode("utf-8"))])

    report = StreamIngestionWorker(
        store=store,
        consumer=consumer,
        topic="fraud.events.smoke",
        group_id="test-group",
    ).run(max_messages=1)

    assert report.scanned == 1
    assert report.ingested == 1
    assert report.duplicates == 0
    assert report.failed == 0
    assert store.list_events()[0].idempotency_key == event.idempotency_key
    assert store.outbox_counts() == {}
    assert consumer.subscriptions == [["fraud.events.smoke"]]
    assert len(consumer.committed) == 1
    assert consumer.closed is True


def test_stream_consumer_commits_idempotent_duplicate(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteStore(tmp_path / "fraud.sqlite")
    event = _event()
    store.add_event(event, outbox_topic=None)
    consumer = FakeConsumer([FakeMessage(event.model_dump_json())])

    report = StreamIngestionWorker(
        store=store,
        consumer=consumer,
        topic="fraud.events",
        group_id="test-group",
    ).run(max_messages=1)

    assert report.scanned == 1
    assert report.ingested == 0
    assert report.duplicates == 1
    assert report.failed == 0
    assert len(consumer.committed) == 1
    assert len(store.list_events()) == 1


def test_stream_consumer_does_not_commit_idempotency_conflict(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteStore(tmp_path / "fraud.sqlite")
    event = _event()
    store.add_event(event, outbox_topic=None)
    conflicting_event = event.model_copy(update={"event_id": uuid4()})
    consumer = FakeConsumer([FakeMessage(conflicting_event.model_dump_json())])

    report = StreamIngestionWorker(
        store=store,
        consumer=consumer,
        topic="fraud.events",
        group_id="test-group",
    ).run(max_messages=1)

    assert report.scanned == 1
    assert report.ingested == 0
    assert report.conflicts == 1
    assert report.failed == 1
    assert report.dead_lettered == 1
    assert len(consumer.committed) == 1
    dead_letters = store.list_stream_dead_letters()
    assert len(dead_letters) == 1
    assert dead_letters[0].reason.value == "IDEMPOTENCY_CONFLICT"


def test_stream_consumer_reports_invalid_messages(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteStore(tmp_path / "fraud.sqlite")
    consumer = FakeConsumer([FakeMessage(b'{"not": "an event"}')])

    report = StreamIngestionWorker(
        store=store,
        consumer=consumer,
        topic="fraud.events",
        group_id="test-group",
    ).run(max_messages=1)

    assert report.scanned == 1
    assert report.invalid_messages == 1
    assert report.failed == 1
    assert report.dead_lettered == 1
    assert report.dead_letter_published == 0
    assert report.dead_letter_publish_failed == 0
    assert len(consumer.committed) == 1
    dead_letters = store.list_stream_dead_letters()
    assert len(dead_letters) == 1
    assert dead_letters[0].reason.value == "INVALID_EVENT"
    assert dead_letters[0].payload_hash is not None


def test_stream_consumer_publishes_dead_letters_when_configured(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteStore(tmp_path / "fraud.sqlite")
    consumer = FakeConsumer([FakeMessage(b'{"not": "an event"}')])
    publisher = FakeDeadLetterPublisher()

    report = StreamIngestionWorker(
        store=store,
        consumer=consumer,
        topic="fraud.events",
        group_id="test-group",
        dead_letter_publisher=publisher,
        dead_letter_topic="fraud.dead_letters.test",
    ).run(max_messages=1)

    assert report.dead_lettered == 1
    assert report.dead_letter_published == 1
    assert report.dead_letter_publish_failed == 0
    assert len(consumer.committed) == 1
    assert len(publisher.published) == 1
    assert publisher.published[0][0] == "fraud.dead_letters.test"
    assert publisher.published[0][1].reason.value == "INVALID_EVENT"


def test_stream_consumer_does_not_commit_when_dead_letter_publish_fails(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteStore(tmp_path / "fraud.sqlite")
    consumer = FakeConsumer([FakeMessage(b'{"not": "an event"}')])

    report = StreamIngestionWorker(
        store=store,
        consumer=consumer,
        topic="fraud.events",
        group_id="test-group",
        dead_letter_publisher=FailingDeadLetterPublisher(),
        dead_letter_topic="fraud.dead_letters.test",
    ).run(max_messages=1)

    assert report.dead_lettered == 1
    assert report.dead_letter_published == 0
    assert report.dead_letter_publish_failed == 1
    assert consumer.committed == []
    assert len(store.list_stream_dead_letters()) == 1


def _event() -> EventEnvelope:
    return (
        SyntheticFraudGenerator(seed=20260523)
        .generate(users=10)
        .events[0]
        .model_copy(update={"event_id": uuid4(), "idempotency_key": f"stream-test:{uuid4()}"})
    )
