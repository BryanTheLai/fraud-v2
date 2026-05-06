from __future__ import annotations

from dataclasses import dataclass

from fraud_v2.domain.events import EventEnvelope
from fraud_v2.infrastructure.optional_imports import optional_module


@dataclass(frozen=True)
class RedpandaEventPublisher:
    bootstrap_servers: str = "localhost:19092"

    def publish(self, topic: str, event: EventEnvelope) -> None:
        kafka = optional_module("confluent_kafka", "infra")
        producer = kafka.Producer({"bootstrap.servers": self.bootstrap_servers})
        producer.produce(
            topic,
            key=event.idempotency_key.encode("utf-8"),
            value=event.model_dump_json().encode("utf-8"),
        )
        pending_messages = producer.flush(10)
        if pending_messages:
            raise TimeoutError(
                f"redpanda publish timed out with {pending_messages} message(s) still queued"
            )
