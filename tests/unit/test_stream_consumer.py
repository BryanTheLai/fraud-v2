from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from fraud_v2.domain.events import EventEnvelope
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
    assert consumer.committed == []


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
    assert consumer.committed == []


def _event() -> EventEnvelope:
    return (
        SyntheticFraudGenerator(seed=20260523)
        .generate(users=10)
        .events[0]
        .model_copy(update={"event_id": uuid4(), "idempotency_key": f"stream-test:{uuid4()}"})
    )
