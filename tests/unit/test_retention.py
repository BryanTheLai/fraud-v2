from datetime import UTC, datetime

from fraud_v2.domain.retention import RetentionPolicy
from fraud_v2.domain.stream import StreamDeadLetter, StreamDeadLetterReason
from fraud_v2.storage.sqlite_store import SQLiteStore
from fraud_v2.synthetic.generator import SyntheticFraudGenerator


def test_retention_report_counts_expired_local_records(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteStore(tmp_path / "retention.sqlite")
    dataset = SyntheticFraudGenerator().generate(users=10)
    store.add_events(dataset.events)

    report = store.retention_report(
        as_of=datetime(2026, 12, 1, tzinfo=UTC),
        policy=RetentionPolicy(
            event_days=90,
            decision_days=365,
            review_days=365,
            outbox_days=30,
            stream_dead_letter_days=30,
            audit_days=3650,
        ),
    )

    tables = {table.table: table for table in report.tables}
    assert tables["events"].expired_count == len(dataset.events)
    assert tables["events"].action == "report_only"
    assert tables["outbox_messages"].expired_count > 0
    assert tables["stream_dead_letters"].expired_count == 0
    assert tables["audit_entries"].expired_count == 0
    assert report.total_expired >= len(dataset.events)


def test_retention_prune_deletes_expired_records_without_breaking_audit(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteStore(tmp_path / "retention.sqlite")
    dataset = SyntheticFraudGenerator().generate(users=10)
    store.add_events(dataset.events)

    report = store.prune_retention(
        as_of=datetime(2026, 12, 1, tzinfo=UTC),
        policy=RetentionPolicy(
            event_days=90,
            decision_days=365,
            review_days=365,
            outbox_days=30,
            stream_dead_letter_days=30,
            audit_days=3650,
        ),
    )

    tables = {table.table: table for table in report.tables}
    assert tables["events"].action == "delete_expired"
    assert tables["events"].expired_count == len(dataset.events)
    assert tables["outbox_messages"].expired_count > 0
    assert tables["audit_entries"].action == "skipped_hash_chain"
    assert store.list_events() == []
    assert store.outbox_counts() == {}
    assert store.verify_audit_chain().valid is True


def test_retention_prune_deletes_expired_stream_dead_letters(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteStore(tmp_path / "retention.sqlite")
    store.save_stream_dead_letter(
        StreamDeadLetter(
            source_topic="fraud.events",
            consumer_group="test",
            reason=StreamDeadLetterReason.INVALID_EVENT,
            payload_hash="a" * 64,
            payload_preview="{bad}",
            safe_error="invalid event",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    )

    report = store.prune_retention(
        as_of=datetime(2026, 12, 1, tzinfo=UTC),
        policy=RetentionPolicy(stream_dead_letter_days=30),
    )

    tables = {table.table: table for table in report.tables}
    assert tables["stream_dead_letters"].expired_count == 1
    assert tables["stream_dead_letters"].action == "delete_expired"
    assert store.list_stream_dead_letters() == []
