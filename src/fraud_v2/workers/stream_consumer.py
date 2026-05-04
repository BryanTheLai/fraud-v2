from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, cast

from pydantic import ValidationError

from fraud_v2.domain.errors import DuplicatePayloadConflict
from fraud_v2.domain.events import EventEnvelope
from fraud_v2.infrastructure.optional_imports import optional_module
from fraud_v2.storage.ports import FraudStore


class StreamMessage(Protocol):
    def value(self) -> bytes | str | None: ...

    def error(self) -> object | None: ...


class StreamConsumer(Protocol):
    def subscribe(self, topics: list[str]) -> None: ...

    def poll(self, timeout: float) -> StreamMessage | None: ...

    def commit(
        self,
        message: StreamMessage | None = None,
        offsets: object | None = None,
        asynchronous: bool = True,
    ) -> object: ...

    def close(self) -> None: ...


@dataclass(frozen=True)
class StreamConsumeReport:
    topic: str
    group_id: str
    scanned: int
    ingested: int
    duplicates: int
    failed: int
    conflicts: int
    invalid_messages: int
    empty_polls: int


@dataclass(frozen=True)
class RedpandaConsumerFactory:
    bootstrap_servers: str = "localhost:19092"
    group_id: str = "fraud-v2-local"
    auto_offset_reset: str = "earliest"

    def create(self) -> StreamConsumer:
        kafka = optional_module("confluent_kafka", "infra")
        consumer = kafka.Consumer(
            {
                "bootstrap.servers": self.bootstrap_servers,
                "group.id": self.group_id,
                "auto.offset.reset": self.auto_offset_reset,
                "enable.auto.commit": False,
            }
        )
        return cast(StreamConsumer, consumer)


@dataclass(frozen=True)
class StreamIngestionWorker:
    store: FraudStore
    consumer: StreamConsumer
    topic: str
    group_id: str = "fraud-v2-local"
    poll_timeout_seconds: float = 1.0
    max_empty_polls: int = 3
    close_consumer: bool = True

    def run(self, max_messages: int = 100) -> StreamConsumeReport:
        self.consumer.subscribe([self.topic])
        known_idempotency_keys = {event.idempotency_key for event in self.store.list_events()}
        scanned = 0
        ingested = 0
        duplicates = 0
        failed = 0
        conflicts = 0
        invalid_messages = 0
        empty_polls = 0
        try:
            while scanned < max_messages and empty_polls < self.max_empty_polls:
                message = self.consumer.poll(self.poll_timeout_seconds)
                if message is None:
                    empty_polls += 1
                    continue
                empty_polls = 0
                scanned += 1
                if message.error() is not None:
                    failed += 1
                    continue
                raw_value = message.value()
                if raw_value is None:
                    failed += 1
                    invalid_messages += 1
                    continue
                try:
                    event = EventEnvelope.model_validate_json(_message_text(raw_value))
                    already_known = event.idempotency_key in known_idempotency_keys
                    self.store.add_event(event, outbox_topic=None)
                except DuplicatePayloadConflict:
                    conflicts += 1
                    failed += 1
                    continue
                except ValidationError:
                    invalid_messages += 1
                    failed += 1
                    continue
                self.consumer.commit(message=message, asynchronous=False)
                if already_known:
                    duplicates += 1
                else:
                    ingested += 1
                    known_idempotency_keys.add(event.idempotency_key)
        finally:
            if self.close_consumer:
                self.consumer.close()
        return StreamConsumeReport(
            topic=self.topic,
            group_id=self.group_id,
            scanned=scanned,
            ingested=ingested,
            duplicates=duplicates,
            failed=failed,
            conflicts=conflicts,
            invalid_messages=invalid_messages,
            empty_polls=empty_polls,
        )


def _message_text(raw_value: bytes | str) -> str:
    if isinstance(raw_value, bytes):
        return raw_value.decode("utf-8")
    return raw_value
