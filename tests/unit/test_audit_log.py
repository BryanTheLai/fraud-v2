from datetime import UTC, datetime

from fraud_v2.decision.engine import DecisionEngine
from fraud_v2.domain.decisions import DecisionRequest
from fraud_v2.domain.entities import EntityRef
from fraud_v2.domain.enums import EntityType
from fraud_v2.observability.logging import reset_trace_id, set_trace_id
from fraud_v2.storage.sqlite_store import SQLiteStore
from fraud_v2.synthetic.generator import SyntheticFraudGenerator


def test_sqlite_audit_log_is_hash_chained(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteStore(tmp_path / "audit.sqlite")
    events = SyntheticFraudGenerator().generate(users=10).events
    store.add_events(events)

    token = set_trace_id("audit-trace-001")
    try:
        DecisionEngine(store).score(
            DecisionRequest(
                target_entity=EntityRef(entity_type=EntityType.USER, entity_id="user_00000"),
                as_of=datetime(2026, 5, 10, tzinfo=UTC),
                amount=1000,
            )
        )
    finally:
        reset_trace_id(token)

    entries = store.list_audit_entries(limit=1000)
    assert entries[0].sequence == 1
    assert any(entry.action == "event.ingested" for entry in entries)
    decision_entry = next(entry for entry in entries if entry.action == "decision.created")
    assert decision_entry.trace_id == "audit-trace-001"
    assert decision_entry.previous_hash
    assert decision_entry.entry_hash != decision_entry.previous_hash

    report = store.verify_audit_chain()
    assert report.valid is True
    assert report.entries_checked == len(entries)


def test_sqlite_audit_chain_detects_tampering(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteStore(tmp_path / "audit.sqlite")
    event = SyntheticFraudGenerator().generate(users=10).events[0]
    store.add_event(event)

    with store._connect() as conn:  # noqa: SLF001
        conn.execute(
            "update audit_entries set action = ? where sequence = 1",
            ("event.tampered",),
        )

    report = store.verify_audit_chain()
    assert report.valid is False
    assert report.failure_sequence == 1
    assert report.failure_reason == "entry hash mismatch"
