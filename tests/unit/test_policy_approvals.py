from __future__ import annotations

import pytest

from fraud_v2.policy.approvals import (
    JsonPolicyApprovalStore,
    create_policy_approval,
    generate_policy_signing_keypair,
    verify_policy_approval,
)
from fraud_v2.policy.registry import JsonThresholdPolicyRegistry
from fraud_v2.policy.thresholds import ThresholdPolicy


def test_policy_approval_store_counts_distinct_verified_approvers(tmp_path) -> None:  # type: ignore[no-untyped-def]
    registered = _registered_policy(tmp_path)
    first_key = _keypair(tmp_path, "first")
    second_key = _keypair(tmp_path, "second")
    store = JsonPolicyApprovalStore(tmp_path / "approvals.json")

    first = store.add(
        create_policy_approval(
            policy_version=registered.version,
            policy_sha256=registered.policy_sha256,
            approver_id="alice",
            approver_role="risk",
            private_key_path=first_key,
            notes="looks right",
        )
    )
    store.add(
        create_policy_approval(
            policy_version=registered.version,
            policy_sha256=registered.policy_sha256,
            approver_id="alice",
            approver_role="risk",
            private_key_path=first_key,
            notes="replacement approval",
        )
    )

    one_approver = store.status(
        policy_version=registered.version,
        policy_sha256=registered.policy_sha256,
        required_approvals=2,
    )
    store.add(
        create_policy_approval(
            policy_version=registered.version,
            policy_sha256=registered.policy_sha256,
            approver_id="bob",
            approver_role="compliance",
            private_key_path=second_key,
        )
    )
    two_approvers = store.status(
        policy_version=registered.version,
        policy_sha256=registered.policy_sha256,
        required_approvals=2,
    )

    assert verify_policy_approval(first) is True
    assert one_approver.approved is False
    assert one_approver.verified_approvals == 1
    assert two_approvers.approved is True
    assert two_approvers.verified_approvers == ["alice", "bob"]


def test_policy_approval_rejects_tampered_payload(tmp_path) -> None:  # type: ignore[no-untyped-def]
    registered = _registered_policy(tmp_path)
    private_key = _keypair(tmp_path, "approver")
    approval = create_policy_approval(
        policy_version=registered.version,
        policy_sha256=registered.policy_sha256,
        approver_id="alice",
        approver_role="risk",
        private_key_path=private_key,
    )
    tampered = approval.model_copy(update={"policy_sha256": "0" * 64})

    assert verify_policy_approval(tampered) is False
    with pytest.raises(ValueError, match="signature is invalid"):
        JsonPolicyApprovalStore(tmp_path / "approvals.json").add(tampered)


def test_policy_keygen_refuses_to_overwrite_existing_keys(tmp_path) -> None:  # type: ignore[no-untyped-def]
    private_key = tmp_path / "policy.pem"
    public_key = tmp_path / "policy.pub.pem"
    generate_policy_signing_keypair(
        private_key_path=private_key,
        public_key_path=public_key,
    )

    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        generate_policy_signing_keypair(
            private_key_path=private_key,
            public_key_path=public_key,
        )


def _registered_policy(tmp_path):  # type: ignore[no-untyped-def]
    policy = ThresholdPolicy(
        version="approval-policy",
        green_max_score=20,
        red_min_score=80,
        degraded_min_score=21,
        high_request_amount_threshold=750,
        high_request_amount_severity=15,
        high_request_amount_reason="The requested amount is high for the approval test.",
    )
    policy_path = tmp_path / "approval-policy.json"
    policy_path.write_text(policy.model_dump_json(), encoding="utf-8")
    return JsonThresholdPolicyRegistry(tmp_path / "registry.json").register(policy_path)


def _keypair(tmp_path, name: str):  # type: ignore[no-untyped-def]
    private_key = tmp_path / f"{name}.pem"
    public_key = tmp_path / f"{name}.pub.pem"
    generate_policy_signing_keypair(
        private_key_path=private_key,
        public_key_path=public_key,
    )
    return private_key
