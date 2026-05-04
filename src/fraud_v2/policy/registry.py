from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from fraud_v2.policy.thresholds import ThresholdPolicy, load_threshold_policy


class PolicyStatus(StrEnum):
    CANDIDATE = "candidate"
    ACTIVE = "active"
    DISABLED = "disabled"


class RegisteredThresholdPolicy(BaseModel):
    version: str
    status: PolicyStatus
    source_path: str
    policy_sha256: str
    policy: ThresholdPolicy
    registered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    promoted_at: datetime | None = None
    notes: str = ""


class JsonThresholdPolicyRegistry:
    def __init__(self, path: Path) -> None:
        self.path = path

    def list_policies(self) -> list[RegisteredThresholdPolicy]:
        if not self.path.exists():
            return []
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return [RegisteredThresholdPolicy.model_validate(item) for item in data.get("policies", [])]

    def register(
        self,
        policy_path: Path,
        status: PolicyStatus = PolicyStatus.CANDIDATE,
        notes: str = "",
    ) -> RegisteredThresholdPolicy:
        policy = load_threshold_policy(policy_path)
        registered = RegisteredThresholdPolicy(
            version=policy.version,
            status=status,
            source_path=str(policy_path),
            policy_sha256=_sha256(policy_path),
            policy=policy,
            promoted_at=datetime.now(UTC) if status == PolicyStatus.ACTIVE else None,
            notes=notes,
        )
        policies = [
            existing for existing in self.list_policies() if existing.version != registered.version
        ]
        if status == PolicyStatus.ACTIVE:
            policies = [_demote_active(existing) for existing in policies]
        policies.append(registered)
        self._write(policies)
        return registered

    def promote(self, version: str) -> RegisteredThresholdPolicy:
        policies = self.list_policies()
        promoted: RegisteredThresholdPolicy | None = None
        output: list[RegisteredThresholdPolicy] = []
        for policy in policies:
            if policy.version == version:
                promoted = policy.model_copy(
                    update={"status": PolicyStatus.ACTIVE, "promoted_at": datetime.now(UTC)}
                )
                output.append(promoted)
            elif policy.status == PolicyStatus.ACTIVE:
                output.append(_demote_active(policy))
            else:
                output.append(policy)
        if promoted is None:
            raise KeyError(f"policy version not found: {version}")
        self._write(output)
        return promoted

    def _write(self, policies: list[RegisteredThresholdPolicy]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        ordered = sorted(policies, key=lambda item: (item.status.value, item.version))
        payload: dict[str, Any] = {
            "schema_version": "1.0",
            "updated_at": datetime.now(UTC).isoformat(),
            "policies": [policy.model_dump(mode="json") for policy in ordered],
        }
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_active_policy(policy: ThresholdPolicy, active_policy_path: Path) -> Path:
    active_policy_path.parent.mkdir(parents=True, exist_ok=True)
    active_policy_path.write_text(policy.model_dump_json(indent=2), encoding="utf-8")
    return active_policy_path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _demote_active(policy: RegisteredThresholdPolicy) -> RegisteredThresholdPolicy:
    return policy.model_copy(update={"status": PolicyStatus.CANDIDATE})
