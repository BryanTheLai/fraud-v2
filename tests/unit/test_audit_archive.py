from __future__ import annotations

from fraud_v2.compliance.audit_archive import write_audit_archive
from fraud_v2.storage.sqlite_store import SQLiteStore
from fraud_v2.synthetic.generator import SyntheticFraudGenerator


def test_audit_archive_writes_entries_and_manifest(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteStore(tmp_path / "audit.sqlite")
    store.add_events(SyntheticFraudGenerator().generate(users=10).events[:2])

    manifest = write_audit_archive(
        store=store,
        output_dir=tmp_path / "archive",
    )

    entries_path = tmp_path / "archive" / "audit-entries.jsonl"
    manifest_path = tmp_path / "archive" / "audit-manifest.json"
    assert manifest["entries"] == 2
    assert manifest["first_sequence"] == 1
    assert manifest["last_sequence"] == 2
    assert manifest["chain_valid"] is True
    assert manifest["root_entry_hash"]
    assert manifest["archive_sha256"]
    assert entries_path.exists()
    assert manifest_path.exists()
    assert "event.ingested" in entries_path.read_text(encoding="utf-8")
