from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


class LlmProvider(Protocol):
    def generate_structured(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Generate one structured object that must still pass deterministic validation."""


@dataclass(frozen=True)
class LedgerEntry:
    content_hash: str
    schema_name: str
    model: str
    prompt_pack_version: str


class NoveltyLedger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def seen(self, payload: dict[str, Any]) -> bool:
        return self._hash(payload) in self._hashes()

    def append(
        self, payload: dict[str, Any], schema_name: str, model: str, prompt_pack_version: str
    ) -> None:
        entry = LedgerEntry(
            content_hash=self._hash(payload),
            schema_name=schema_name,
            model=model,
            prompt_pack_version=prompt_pack_version,
        )
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry.__dict__, sort_keys=True) + "\n")

    def _hashes(self) -> set[str]:
        if not self.path.exists():
            return set()
        hashes: set[str] = set()
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    hashes.add(str(json.loads(line)["content_hash"]))
        return hashes

    def _hash(self, payload: dict[str, Any]) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class OfflineStubProvider:
    """No-network provider for tests and local dry runs."""

    def generate_structured(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        return {
            "scenario_id": hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:12],
            "schema_title": schema.get("title", "unknown"),
            "narrative": (
                "offline stub scenario; replace with OpenAI or Azure provider when configured"
            ),
        }
