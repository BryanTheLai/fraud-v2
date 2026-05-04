from fraud_v2.infrastructure.redpanda_lag import (
    StreamPartitionLag,
    _lag_from_offsets,
    _total_lag,
)


def test_lag_from_offsets_returns_unknown_without_commit() -> None:
    assert _lag_from_offsets(high_watermark=10, committed_offset=None) is None


def test_lag_from_offsets_never_goes_negative() -> None:
    assert _lag_from_offsets(high_watermark=10, committed_offset=12) == 0


def test_total_lag_sums_known_partitions() -> None:
    partitions = [
        StreamPartitionLag(
            topic="fraud.events",
            partition=0,
            low_watermark=0,
            high_watermark=10,
            committed_offset=7,
            lag=3,
        ),
        StreamPartitionLag(
            topic="fraud.events",
            partition=1,
            low_watermark=0,
            high_watermark=4,
            committed_offset=2,
            lag=2,
        ),
    ]

    assert _total_lag(partitions) == 5


def test_total_lag_is_unknown_when_any_partition_is_unknown() -> None:
    partitions = [
        StreamPartitionLag(
            topic="fraud.events",
            partition=0,
            low_watermark=0,
            high_watermark=10,
            committed_offset=None,
            lag=None,
        )
    ]

    assert _total_lag(partitions) is None
