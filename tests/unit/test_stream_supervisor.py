from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from fraud_v2.storage.sqlite_store import SQLiteStore
from fraud_v2.synthetic.generator import SyntheticFraudGenerator
from fraud_v2.workers.stream_consumer import StreamConsumer, StreamMessage
from fraud_v2.workers.stream_supervisor import StreamSupervisor


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
class FakeConsumerFactory:
    consumers: list[StreamConsumer] = field(default_factory=list)
    failures_before_success: int = 0
    created: int = 0

    def create(self) -> StreamConsumer:
        self.created += 1
        if self.failures_before_success > 0:
            self.failures_before_success -= 1
            raise RuntimeError("temporary stream outage")
        return self.consumers.pop(0)


@dataclass
class SleepRecorder:
    calls: list[float] = field(default_factory=list)

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


def test_stream_supervisor_aggregates_successful_batches(tmp_path) -> None:  # type: ignore[no-untyped-def]
    event = _event()
    first_consumer = FakeConsumer([FakeMessage(event.model_dump_json())])
    second_consumer = FakeConsumer([])
    sleep = SleepRecorder()
    report = StreamSupervisor(
        store=SQLiteStore(tmp_path / "fraud.sqlite"),
        consumer_factory=FakeConsumerFactory([first_consumer, second_consumer]),
        topic="fraud.events",
        group_id="supervisor-test",
        batch_size=1,
        max_empty_polls=1,
        idle_sleep_seconds=0.5,
        sleeper=sleep,
    ).run(max_batches=2)

    assert report.status == "completed"
    assert report.batches_attempted == 2
    assert report.completed_batches == 2
    assert report.failed_batches == 0
    assert report.idle_batches == 1
    assert report.scanned == 1
    assert report.ingested == 1
    assert report.empty_polls == 1
    assert first_consumer.closed is True
    assert second_consumer.closed is True
    assert sleep.calls == []


def test_stream_supervisor_backs_off_and_recovers(tmp_path) -> None:  # type: ignore[no-untyped-def]
    event = _event()
    sleep = SleepRecorder()
    factory = FakeConsumerFactory(
        consumers=[FakeConsumer([FakeMessage(event.model_dump_json())])],
        failures_before_success=1,
    )

    report = StreamSupervisor(
        store=SQLiteStore(tmp_path / "fraud.sqlite"),
        consumer_factory=factory,
        topic="fraud.events",
        group_id="supervisor-test",
        restart_backoff_seconds=0.25,
        sleeper=sleep,
    ).run(max_batches=2)

    assert report.status == "completed"
    assert report.failed_batches == 1
    assert report.completed_batches == 1
    assert report.ingested == 1
    assert report.last_error == "RuntimeError: temporary stream outage"
    assert sleep.calls == [0.25]


def test_stream_supervisor_fails_after_consecutive_failures(tmp_path) -> None:  # type: ignore[no-untyped-def]
    sleep = SleepRecorder()
    report = StreamSupervisor(
        store=SQLiteStore(tmp_path / "fraud.sqlite"),
        consumer_factory=FakeConsumerFactory(failures_before_success=2),
        topic="fraud.events",
        group_id="supervisor-test",
        restart_backoff_seconds=0.1,
        max_consecutive_failures=2,
        sleeper=sleep,
    ).run(max_batches=3)

    assert report.status == "failed"
    assert report.batches_attempted == 2
    assert report.failed_batches == 2
    assert report.completed_batches == 0
    assert report.last_error == "RuntimeError: temporary stream outage"
    assert sleep.calls == [0.1]


def _event():  # type: ignore[no-untyped-def]
    return (
        SyntheticFraudGenerator(seed=20260529)
        .generate(users=10)
        .events[0]
        .model_copy(update={"event_id": uuid4(), "idempotency_key": f"supervisor:{uuid4()}"})
    )
