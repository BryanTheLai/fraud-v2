from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from fraud_v2.storage.ports import FraudStore
from fraud_v2.workers.stream_consumer import (
    StreamConsumer,
    StreamDeadLetterPublisher,
    StreamIngestionWorker,
)


class StreamConsumerFactory(Protocol):
    def create(self) -> StreamConsumer: ...


@dataclass(frozen=True)
class StreamSupervisionReport:
    topic: str
    group_id: str
    status: str
    batches_attempted: int
    completed_batches: int
    failed_batches: int
    idle_batches: int
    scanned: int
    ingested: int
    duplicates: int
    message_failures: int
    conflicts: int
    invalid_messages: int
    dead_lettered: int
    dead_letter_published: int
    dead_letter_publish_failed: int
    empty_polls: int
    last_error: str | None


@dataclass
class _StreamSupervisionTotals:
    batches_attempted: int = 0
    completed_batches: int = 0
    failed_batches: int = 0
    idle_batches: int = 0
    scanned: int = 0
    ingested: int = 0
    duplicates: int = 0
    message_failures: int = 0
    conflicts: int = 0
    invalid_messages: int = 0
    dead_lettered: int = 0
    dead_letter_published: int = 0
    dead_letter_publish_failed: int = 0
    empty_polls: int = 0
    last_error: str | None = None

    def to_report(self, *, topic: str, group_id: str, status: str) -> StreamSupervisionReport:
        return StreamSupervisionReport(
            topic=topic,
            group_id=group_id,
            status=status,
            batches_attempted=self.batches_attempted,
            completed_batches=self.completed_batches,
            failed_batches=self.failed_batches,
            idle_batches=self.idle_batches,
            scanned=self.scanned,
            ingested=self.ingested,
            duplicates=self.duplicates,
            message_failures=self.message_failures,
            conflicts=self.conflicts,
            invalid_messages=self.invalid_messages,
            dead_lettered=self.dead_lettered,
            dead_letter_published=self.dead_letter_published,
            dead_letter_publish_failed=self.dead_letter_publish_failed,
            empty_polls=self.empty_polls,
            last_error=self.last_error,
        )


@dataclass(frozen=True)
class StreamSupervisor:
    store: FraudStore
    consumer_factory: StreamConsumerFactory
    topic: str
    group_id: str = "fraud-v2-local"
    batch_size: int = 100
    max_empty_polls: int = 3
    poll_timeout_seconds: float = 1.0
    restart_backoff_seconds: float = 5.0
    idle_sleep_seconds: float = 1.0
    max_consecutive_failures: int = 3
    dead_letter_publisher: StreamDeadLetterPublisher | None = None
    dead_letter_topic: str = "fraud.dead_letters"
    sleeper: Callable[[float], None] = time.sleep

    def run(self, max_batches: int = 1) -> StreamSupervisionReport:
        totals = _StreamSupervisionTotals()
        status = "completed"
        consecutive_failures = 0

        for batch_index in range(max_batches):
            totals.batches_attempted += 1
            try:
                batch_report = StreamIngestionWorker(
                    store=self.store,
                    consumer=self.consumer_factory.create(),
                    topic=self.topic,
                    group_id=self.group_id,
                    dead_letter_publisher=self.dead_letter_publisher,
                    dead_letter_topic=self.dead_letter_topic,
                    poll_timeout_seconds=self.poll_timeout_seconds,
                    max_empty_polls=self.max_empty_polls,
                ).run(max_messages=self.batch_size)
            except RuntimeError as exc:
                totals.failed_batches += 1
                totals.last_error = f"{type(exc).__name__}: {exc}"[:500]
                consecutive_failures += 1
                if consecutive_failures >= self.max_consecutive_failures:
                    status = "failed"
                    break
                self.sleeper(self.restart_backoff_seconds)
                continue

            consecutive_failures = 0
            totals.completed_batches += 1
            totals.scanned += batch_report.scanned
            totals.ingested += batch_report.ingested
            totals.duplicates += batch_report.duplicates
            totals.message_failures += batch_report.failed
            totals.conflicts += batch_report.conflicts
            totals.invalid_messages += batch_report.invalid_messages
            totals.dead_lettered += batch_report.dead_lettered
            totals.dead_letter_published += batch_report.dead_letter_published
            totals.dead_letter_publish_failed += batch_report.dead_letter_publish_failed
            totals.empty_polls += batch_report.empty_polls
            if batch_report.scanned == 0:
                totals.idle_batches += 1
                if batch_index < max_batches - 1:
                    self.sleeper(self.idle_sleep_seconds)

        return totals.to_report(topic=self.topic, group_id=self.group_id, status=status)
