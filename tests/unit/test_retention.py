from datetime import UTC, datetime

from fraud_v2.domain.retention import RetentionPolicy
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
            audit_days=3650,
        ),
    )

    tables = {table.table: table for table in report.tables}
    assert tables["events"].expired_count == len(dataset.events)
    assert tables["events"].action == "report_only"
    assert tables["outbox_messages"].expired_count > 0
    assert tables["audit_entries"].expired_count == 0
    assert report.total_expired >= len(dataset.events)
