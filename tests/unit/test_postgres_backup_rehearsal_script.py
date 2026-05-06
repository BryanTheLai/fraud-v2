from __future__ import annotations

from pathlib import Path


def test_postgres_backup_rehearsal_uses_pg_dump_restore_and_manifest() -> None:
    script = Path("scripts/postgres-backup-rehearsal.ps1").read_text(encoding="utf-8")

    assert "pg_dump" in script
    assert "pg_restore" in script
    assert "Get-FileHash" in script
    assert "postgres-backup-rehearsal-v1" in script
    assert "not_managed_backup" in script
    assert "KeepRestoreDatabase" in script
    assert "Copy-PostgresFileToContainer" in script
    assert "$containerRestorePath" in script
    assert "pg_restore -U $DatabaseUser -d $RestoreDatabase $containerRestorePath" in script
    assert "pg_restore -U $DatabaseUser -d $RestoreDatabase $containerBackupPath" not in script


def test_full_smoke_runs_postgres_backup_rehearsal() -> None:
    smoke = Path("scripts/full-smoke.ps1").read_text(encoding="utf-8")

    assert "postgres-backup-rehearsal.ps1" in smoke
    assert "Postgres backup rehearsal failed" in smoke
    assert "postgresBackupManifest.verified" in smoke
    assert "postgresBackupManifest.restore.verified" in smoke
