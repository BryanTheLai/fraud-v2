from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol, cast

from pydantic import ValidationError

from fraud_v2.domain.errors import DuplicatePayloadConflict
from fraud_v2.domain.events import EventEnvelope
from fraud_v2.domain.stream import StreamDeadLetter, StreamDeadLetterReason
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


class StreamDeadLetterPublisher(Protocol):
    def publish(self, topic: str, dead_letter: StreamDeadLetter) -> None: ...


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
    dead_lettered: int
    dead_letter_published: int
    dead_letter_publish_failed: int
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
    dead_letter_publisher: StreamDeadLetterPublisher | None = None
    dead_letter_topic: str = "fraud.dead_letters"
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
        dead_lettered = 0
        dead_letter_published = 0
        dead_letter_publish_failed = 0
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
                    published = self._dead_letter(
                        reason=StreamDeadLetterReason.MESSAGE_ERROR,
                        raw_value=message.value(),
                        safe_error=f"stream message error: {message.error()}",
                    )
                    dead_lettered += 1
                    if published:
                        dead_letter_published += int(self.dead_letter_publisher is not None)
                        self.consumer.commit(message=message, asynchronous=False)
                    else:
                        dead_letter_publish_failed += 1
                    continue
                raw_value = message.value()
                if raw_value is None:
                    failed += 1
                    invalid_messages += 1
                    published = self._dead_letter(
                        reason=StreamDeadLetterReason.EMPTY_PAYLOAD,
                        raw_value=None,
                        safe_error="stream message had no payload",
                    )
                    dead_lettered += 1
                    if published:
                        dead_letter_published += int(self.dead_letter_publisher is not None)
                        self.consumer.commit(message=message, asynchronous=False)
                    else:
                        dead_letter_publish_failed += 1
                    continue
                try:
                    event = EventEnvelope.model_validate_json(_message_text(raw_value))
                    already_known = event.idempotency_key in known_idempotency_keys
                    self.store.add_event(event, outbox_topic=None)
                except DuplicatePayloadConflict as exc:
                    conflicts += 1
                    failed += 1
                    published = self._dead_letter(
                        reason=StreamDeadLetterReason.IDEMPOTENCY_CONFLICT,
                        raw_value=raw_value,
                        safe_error=str(exc),
                    )
                    dead_lettered += 1
                    if published:
                        dead_letter_published += int(self.dead_letter_publisher is not None)
                        self.consumer.commit(message=message, asynchronous=False)
                    else:
                        dead_letter_publish_failed += 1
                    continue
                except ValidationError as exc:
                    invalid_messages += 1
                    failed += 1
                    published = self._dead_letter(
                        reason=StreamDeadLetterReason.INVALID_EVENT,
                        raw_value=raw_value,
                        safe_error=str(exc).splitlines()[0],
                    )
                    dead_lettered += 1
                    if published:
                        dead_letter_published += int(self.dead_letter_publisher is not None)
                        self.consumer.commit(message=message, asynchronous=False)
                    else:
                        dead_letter_publish_failed += 1
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
            dead_lettered=dead_lettered,
            dead_letter_published=dead_letter_published,
            dead_letter_publish_failed=dead_letter_publish_failed,
            empty_polls=empty_polls,
        )

    def _dead_letter(
        self,
        *,
        reason: StreamDeadLetterReason,
        raw_value: bytes | str | None,
        safe_error: str,
    ) -> bool:
        dead_letter = StreamDeadLetter(
            source_topic=self.topic,
            consumer_group=self.group_id,
            reason=reason,
            payload_hash=_payload_hash(raw_value),
            payload_preview=_payload_preview(raw_value),
            safe_error=safe_error[:500],
        )
        saved = self.store.save_stream_dead_letter(dead_letter)
        if self.dead_letter_publisher is None:
            return True
        try:
            self.dead_letter_publisher.publish(self.dead_letter_topic, saved)
        except RuntimeError:
            return False
        return True


def _message_text(raw_value: bytes | str) -> str:
    if isinstance(raw_value, bytes):
        return raw_value.decode("utf-8")
    return raw_value


def _payload_hash(raw_value: bytes | str | None) -> str | None:
    if raw_value is None:
        return None
    raw_bytes = raw_value.encode("utf-8") if isinstance(raw_value, str) else raw_value
    return hashlib.sha256(raw_bytes).hexdigest()


def _payload_preview(raw_value: bytes | str | None) -> str:
    if raw_value is None:
        return ""
    if isinstance(raw_value, bytes):
        text = raw_value.decode("utf-8", errors="replace")
    else:
        text = raw_value
    return text.replace("\r", " ").replace("\n", " ")[:500]
