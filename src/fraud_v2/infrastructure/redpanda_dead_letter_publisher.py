from __future__ import annotations

from dataclasses import dataclass

from fraud_v2.domain.stream import StreamDeadLetter
from fraud_v2.infrastructure.optional_imports import optional_module


@dataclass(frozen=True)
class RedpandaDeadLetterPublisher:
    bootstrap_servers: str = "localhost:19092"

    def publish(self, topic: str, dead_letter: StreamDeadLetter) -> None:
        kafka = optional_module("confluent_kafka", "infra")
        producer = kafka.Producer({"bootstrap.servers": self.bootstrap_servers})
        producer.produce(
            topic,
            key=str(dead_letter.dead_letter_id).encode("utf-8"),
            value=dead_letter.model_dump_json().encode("utf-8"),
        )
        pending_messages = producer.flush(10)
        if pending_messages:
            raise TimeoutError(
                "redpanda dead-letter publish timed out "
                f"with {pending_messages} message(s) still queued"
            )
