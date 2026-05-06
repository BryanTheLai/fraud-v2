from __future__ import annotations

import pytest

from fraud_v2.policy.registry import (
    JsonThresholdPolicyRegistry,
    PolicyStatus,
    write_active_policy,
)
from fraud_v2.policy.thresholds import ThresholdPolicy, load_threshold_policy


def test_policy_registry_registers_hashed_candidate(tmp_path) -> None:  # type: ignore[no-untyped-def]
    policy_path = _write_policy(tmp_path, "policy-a")
    registry = JsonThresholdPolicyRegistry(tmp_path / "registry.json")

    registered = registry.register(policy_path, notes="strict local test")

    assert registered.version == "policy-a"
    assert registered.status == PolicyStatus.CANDIDATE
    assert registered.policy_sha256
    assert registry.list_policies()[0].notes == "strict local test"


def test_policy_registry_promote_keeps_one_active_policy(tmp_path) -> None:  # type: ignore[no-untyped-def]
    first_path = _write_policy(tmp_path, "policy-a")
    second_path = _write_policy(tmp_path, "policy-b")
    registry = JsonThresholdPolicyRegistry(tmp_path / "registry.json")
    registry.register(first_path, status=PolicyStatus.ACTIVE)
    registry.register(second_path, status=PolicyStatus.CANDIDATE)

    promoted = registry.promote("policy-b")
    statuses = {policy.version: policy.status for policy in registry.list_policies()}

    assert promoted.status == PolicyStatus.ACTIVE
    assert statuses == {
        "policy-a": PolicyStatus.CANDIDATE,
        "policy-b": PolicyStatus.ACTIVE,
    }


def test_policy_registry_writes_active_policy_file(tmp_path) -> None:  # type: ignore[no-untyped-def]
    policy_path = _write_policy(tmp_path, "policy-a")
    registry = JsonThresholdPolicyRegistry(tmp_path / "registry.json")
    registered = registry.register(policy_path, status=PolicyStatus.ACTIVE)
    active_path = tmp_path / "active.json"

    write_active_policy(registered.policy, active_path)

    assert load_threshold_policy(active_path).version == "policy-a"


def test_policy_registry_missing_policy_fails(tmp_path) -> None:  # type: ignore[no-untyped-def]
    registry = JsonThresholdPolicyRegistry(tmp_path / "registry.json")

    with pytest.raises(KeyError, match="policy version not found"):
        registry.promote("missing")


def _write_policy(tmp_path, version: str):  # type: ignore[no-untyped-def]
    policy = ThresholdPolicy(
        version=version,
        green_max_score=20,
        red_min_score=80,
        degraded_min_score=21,
        high_request_amount_threshold=750,
        high_request_amount_severity=15,
        high_request_amount_reason="The requested amount is high for the test policy.",
    )
    path = tmp_path / f"{version}.json"
    path.write_text(policy.model_dump_json(), encoding="utf-8")
    return path
