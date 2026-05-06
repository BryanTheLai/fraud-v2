from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fraud_v2.domain.audit import AuditEntry
from fraud_v2.storage.ports import FraudStore


def write_audit_archive(
    *,
    store: FraudStore,
    output_dir: Path,
    limit: int = 10000,
) -> dict[str, Any]:
    entries = store.list_audit_entries(limit=limit)
    verification = store.verify_audit_chain()
    output_dir.mkdir(parents=True, exist_ok=True)
    entries_path = output_dir / "audit-entries.jsonl"
    manifest_path = output_dir / "audit-manifest.json"
    entries_payload = _entries_payload(entries)
    entries_path.write_text(entries_payload, encoding="utf-8")
    manifest = {
        "schema_version": "audit-archive-v1",
        "created_at": datetime.now(UTC).isoformat(),
        "entries_path": str(entries_path),
        "manifest_path": str(manifest_path),
        "entries": len(entries),
        "limit": limit,
        "first_sequence": entries[0].sequence if entries else None,
        "last_sequence": entries[-1].sequence if entries else None,
        "root_entry_hash": entries[-1].entry_hash if entries else None,
        "archive_sha256": hashlib.sha256(entries_payload.encode("utf-8")).hexdigest(),
        "chain_valid": verification.valid,
        "chain_entries_checked": verification.entries_checked,
        "chain_failure_sequence": verification.failure_sequence,
        "chain_failure_reason": verification.failure_reason,
        "local_only": True,
        "not_worm_storage": True,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def _entries_payload(entries: list[AuditEntry]) -> str:
    if not entries:
        return ""
    return "\n".join(entry.model_dump_json() for entry in entries) + "\n"
