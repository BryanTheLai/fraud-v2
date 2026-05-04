from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fraud_v2.infrastructure.optional_imports import optional_module


@dataclass(frozen=True)
class StreamPartitionLag:
    topic: str
    partition: int
    low_watermark: int
    high_watermark: int
    committed_offset: int | None
    lag: int | None


@dataclass(frozen=True)
class StreamLagReport:
    topic: str
    group_id: str
    partitions: list[StreamPartitionLag]
    total_lag: int | None


@dataclass(frozen=True)
class RedpandaLagProbe:
    bootstrap_servers: str = "localhost:19092"

    def report(self, topic: str, group_id: str, timeout_seconds: float = 10.0) -> StreamLagReport:
        kafka = optional_module("confluent_kafka", "infra")
        consumer = kafka.Consumer(
            {
                "bootstrap.servers": self.bootstrap_servers,
                "group.id": group_id,
                "enable.auto.commit": False,
            }
        )
        try:
            metadata = consumer.list_topics(topic=topic, timeout=timeout_seconds)
            topic_metadata = metadata.topics.get(topic)
            if topic_metadata is None:
                raise RuntimeError(f"topic not found: {topic}")
            error = getattr(topic_metadata, "error", None)
            if error is not None:
                raise RuntimeError(f"topic metadata error for {topic}: {error}")
            partitions = [
                kafka.TopicPartition(topic, int(partition_id))
                for partition_id in sorted(topic_metadata.partitions)
            ]
            committed_offsets = _committed_offsets(
                consumer=consumer,
                partitions=partitions,
                timeout_seconds=timeout_seconds,
            )
            partition_lag: list[StreamPartitionLag] = []
            for partition in partitions:
                low, high = consumer.get_watermark_offsets(
                    partition,
                    timeout=timeout_seconds,
                    cached=False,
                )
                committed = committed_offsets.get(int(partition.partition))
                partition_lag.append(
                    StreamPartitionLag(
                        topic=topic,
                        partition=int(partition.partition),
                        low_watermark=int(low),
                        high_watermark=int(high),
                        committed_offset=committed,
                        lag=_lag_from_offsets(high_watermark=int(high), committed_offset=committed),
                    )
                )
            return StreamLagReport(
                topic=topic,
                group_id=group_id,
                partitions=partition_lag,
                total_lag=_total_lag(partition_lag),
            )
        finally:
            consumer.close()


def _committed_offsets(
    *,
    consumer: Any,
    partitions: list[Any],
    timeout_seconds: float,
) -> dict[int, int | None]:
    committed = consumer.committed(partitions, timeout=timeout_seconds)
    offsets: dict[int, int | None] = {}
    for partition in committed:
        offset = int(partition.offset)
        offsets[int(partition.partition)] = offset if offset >= 0 else None
    return offsets


def _lag_from_offsets(high_watermark: int, committed_offset: int | None) -> int | None:
    if committed_offset is None:
        return None
    return max(high_watermark - committed_offset, 0)


def _total_lag(partitions: list[StreamPartitionLag]) -> int | None:
    total = 0
    for partition in partitions:
        if partition.lag is None:
            return None
        total += partition.lag
    return total
