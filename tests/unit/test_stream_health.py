from __future__ import annotations

from datetime import UTC, datetime

from fraud_v2.domain.stream import StreamDeadLetter, StreamDeadLetterReason
from fraud_v2.observability.stream_health import (
    StreamHealthStatus,
    StreamHealthThresholds,
    build_stream_health_report,
    write_stream_health_artifacts,
)


def test_stream_health_report_is_healthy_for_zero_lag_and_no_dead_letters() -> None:
    report = build_stream_health_report(
        topic="fraud.events",
        group_id="fraud-v2-local",
        dead_letters=[],
        dead_letter_limit=100,
        lag_payload={
            "topic": "fraud.events",
            "group_id": "fraud-v2-local",
            "total_lag": 0,
            "partitions": [
                {
                    "topic": "fraud.events",
                    "partition": 0,
                    "low_watermark": 0,
                    "high_watermark": 1,
                    "committed_offset": 1,
                    "lag": 0,
                }
            ],
        },
        lag_source="unit",
        supervision_payload={
            "status": "completed",
            "batches_attempted": 1,
            "completed_batches": 1,
            "failed_batches": 0,
            "idle_batches": 0,
            "ingested": 1,
            "dead_lettered": 0,
            "dead_letter_published": 0,
            "dead_letter_publish_failed": 0,
        },
        supervision_source="unit",
        generated_at=datetime(2026, 5, 5, tzinfo=UTC),
    )

    assert report.status == StreamHealthStatus.HEALTHY
    assert report.health_score == 100
    assert report.alerts[0].code == "STREAM_HEALTH_OK"


def test_stream_health_report_flags_missing_lag_as_degraded() -> None:
    report = build_stream_health_report(
        topic="fraud.events",
        group_id="fraud-v2-local",
        dead_letters=[],
        dead_letter_limit=100,
    )

    assert report.status == StreamHealthStatus.DEGRADED
    assert report.alerts[0].code == "STREAM_LAG_NOT_CHECKED"


def test_stream_health_report_flags_critical_lag_and_dlq_publish_failure() -> None:
    report = build_stream_health_report(
        topic="fraud.events",
        group_id="fraud-v2-local",
        dead_letters=[
            StreamDeadLetter(
                source_topic="fraud.events",
                consumer_group="fraud-v2-local",
                reason=StreamDeadLetterReason.INVALID_EVENT,
                safe_error="schema validation failed",
            )
        ],
        dead_letter_limit=100,
        lag_payload={
            "topic": "fraud.events",
            "group_id": "fraud-v2-local",
            "total_lag": 2500,
            "partitions": [],
        },
        lag_source="unit",
        supervision_payload={
            "status": "completed",
            "failed_batches": 0,
            "dead_lettered": 1,
            "dead_letter_publish_failed": 1,
        },
        supervision_source="unit",
        thresholds=StreamHealthThresholds(critical_lag=1000),
    )

    assert report.status == StreamHealthStatus.CRITICAL
    assert {alert.code for alert in report.alerts} >= {
        "STREAM_LAG_CRITICAL",
        "STREAM_DLQ_PUBLISH_FAILED",
        "STREAM_DEAD_LETTERS_WARNING",
    }


def test_stream_health_artifacts_write_json_and_html(tmp_path) -> None:  # type: ignore[no-untyped-def]
    report = build_stream_health_report(
        topic="fraud.events",
        group_id="fraud-v2-local",
        dead_letters=[],
        dead_letter_limit=100,
        lag_payload={
            "topic": "fraud.events",
            "group_id": "fraud-v2-local",
            "total_lag": 0,
            "partitions": [],
        },
        lag_source="unit",
        generated_at=datetime(2026, 5, 5, tzinfo=UTC),
    )

    written = write_stream_health_artifacts(
        report,
        output_path=tmp_path / "stream-health.json",
        dashboard_path=tmp_path / "stream-health.html",
    )

    assert written.output_paths["report"].endswith("stream-health.json")
    assert written.output_paths["dashboard"].endswith("stream-health.html")
    assert "Stream Health" in (tmp_path / "stream-health.html").read_text(encoding="utf-8")
