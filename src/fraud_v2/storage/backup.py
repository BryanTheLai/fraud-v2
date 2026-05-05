from __future__ import annotations

import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def write_sqlite_backup(
    *,
    db_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    if not db_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {db_path}")
    output_dir.mkdir(parents=True, exist_ok=True)
    backup_path = output_dir / f"{db_path.stem}.sqlite.bak"
    manifest_path = output_dir / "sqlite-backup-manifest.json"
    shutil.copy2(db_path, backup_path)
    source_sha256 = _sha256(db_path)
    backup_sha256 = _sha256(backup_path)
    manifest = {
        "schema_version": "sqlite-backup-v1",
        "created_at": datetime.now(UTC).isoformat(),
        "source_path": str(db_path),
        "backup_path": str(backup_path),
        "manifest_path": str(manifest_path),
        "source_sha256": source_sha256,
        "backup_sha256": backup_sha256,
        "bytes": backup_path.stat().st_size,
        "verified": source_sha256 == backup_sha256,
        "local_only": True,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def restore_sqlite_backup(
    *,
    backup_path: Path,
    restore_path: Path,
    overwrite: bool = False,
) -> dict[str, Any]:
    if not backup_path.exists():
        raise FileNotFoundError(f"SQLite backup not found: {backup_path}")
    if restore_path.exists() and not overwrite:
        raise FileExistsError(f"restore path already exists: {restore_path}")
    restore_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup_path, restore_path)
    backup_sha256 = _sha256(backup_path)
    restore_sha256 = _sha256(restore_path)
    return {
        "schema_version": "sqlite-restore-v1",
        "restored_at": datetime.now(UTC).isoformat(),
        "backup_path": str(backup_path),
        "restore_path": str(restore_path),
        "backup_sha256": backup_sha256,
        "restore_sha256": restore_sha256,
        "bytes": restore_path.stat().st_size,
        "verified": backup_sha256 == restore_sha256,
        "overwrote_existing": overwrite,
        "local_only": True,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
