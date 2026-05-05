from __future__ import annotations

import pytest

from fraud_v2.storage.backup import restore_sqlite_backup, write_sqlite_backup
from fraud_v2.storage.sqlite_store import SQLiteStore
from fraud_v2.synthetic.generator import SyntheticFraudGenerator


def test_sqlite_backup_and_restore_round_trip(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_path = tmp_path / "fraud.sqlite"
    SQLiteStore(db_path).add_events(SyntheticFraudGenerator().generate(users=10).events[:2])

    manifest = write_sqlite_backup(db_path=db_path, output_dir=tmp_path / "backup")
    restore = restore_sqlite_backup(
        backup_path=tmp_path / "backup" / "fraud.sqlite.bak",
        restore_path=tmp_path / "restored.sqlite",
    )

    assert manifest["verified"] is True
    assert manifest["bytes"] > 0
    assert restore["verified"] is True
    assert SQLiteStore(tmp_path / "restored.sqlite").list_events()


def test_sqlite_restore_requires_overwrite(tmp_path) -> None:  # type: ignore[no-untyped-def]
    backup_path = tmp_path / "backup.sqlite"
    restore_path = tmp_path / "restore.sqlite"
    backup_path.write_bytes(b"backup")
    restore_path.write_bytes(b"existing")

    with pytest.raises(FileExistsError):
        restore_sqlite_backup(
            backup_path=backup_path,
            restore_path=restore_path,
        )

    report = restore_sqlite_backup(
        backup_path=backup_path,
        restore_path=restore_path,
        overwrite=True,
    )

    assert report["verified"] is True
    assert report["overwrote_existing"] is True
