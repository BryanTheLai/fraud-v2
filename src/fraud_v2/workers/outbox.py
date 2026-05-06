from __future__ import annotations

from dataclasses import dataclass, field

from fraud_v2.domain.events import EventEnvelope
from fraud_v2.domain.outbox import OutboxStatus
from fraud_v2.infrastructure.ports import EventPublisher
from fraud_v2.storage.sqlite_store import SQLiteStore


@dataclass(frozen=True)
class OutboxRunReport:
    scanned: int
    published: int
    failed: int
    dead_lettered: int


@dataclass
class DryRunEventPublisher:
    published: list[tuple[str, str]] = field(default_factory=list)

    def publish(self, topic: str, event: EventEnvelope) -> None:
        self.published.append((topic, event.idempotency_key))


@dataclass(frozen=True)
class OutboxWorker:
    store: SQLiteStore
    publisher: EventPublisher
    batch_size: int = 100
    max_attempts: int = 3

    def run_once(self) -> OutboxRunReport:
        messages = self.store.list_outbox_messages(limit=self.batch_size)
        published = 0
        failed = 0
        dead_lettered = 0
        for message in messages:
            event = EventEnvelope.model_validate_json(message.payload_json)
            try:
                self.publisher.publish(message.topic, event)
            except RuntimeError as exc:
                updated = self.store.mark_outbox_failed(
                    message.message_id,
                    safe_error=f"{type(exc).__name__}: {exc}",
                    max_attempts=self.max_attempts,
                )
                if updated.status == OutboxStatus.DEAD_LETTER:
                    dead_lettered += 1
                else:
                    failed += 1
                continue
            self.store.mark_outbox_published(message.message_id)
            published += 1
        return OutboxRunReport(
            scanned=len(messages),
            published=published,
            failed=failed,
            dead_lettered=dead_lettered,
        )
