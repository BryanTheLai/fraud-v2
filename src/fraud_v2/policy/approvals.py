from __future__ import annotations

import base64
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from pydantic import BaseModel, Field

SIGNATURE_ALGORITHM = "ed25519"


class PolicyApproval(BaseModel):
    policy_version: str
    policy_sha256: str
    approver_id: str
    approver_role: str
    approved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    notes: str = ""
    signature_algorithm: str = SIGNATURE_ALGORITHM
    public_key_pem: str
    signature_b64: str


class PolicyApprovalStatus(BaseModel):
    policy_version: str
    policy_sha256: str
    required_approvals: int
    verified_approvals: int
    invalid_approvals: int
    verified_approvers: list[str]
    approved: bool


class JsonPolicyApprovalStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def list_approvals(self) -> list[PolicyApproval]:
        if not self.path.exists():
            return []
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return [PolicyApproval.model_validate(item) for item in data.get("approvals", [])]

    def add(self, approval: PolicyApproval) -> PolicyApproval:
        if not verify_policy_approval(approval):
            raise ValueError("policy approval signature is invalid")
        approvals = [
            existing
            for existing in self.list_approvals()
            if not (
                existing.policy_version == approval.policy_version
                and existing.policy_sha256 == approval.policy_sha256
                and existing.approver_id == approval.approver_id
            )
        ]
        approvals.append(approval)
        self._write(approvals)
        return approval

    def status(
        self,
        *,
        policy_version: str,
        policy_sha256: str,
        required_approvals: int = 2,
    ) -> PolicyApprovalStatus:
        verified_by_approver: dict[str, PolicyApproval] = {}
        invalid_approvals = 0
        for approval in self.list_approvals():
            if approval.policy_version != policy_version or approval.policy_sha256 != policy_sha256:
                continue
            if verify_policy_approval(approval):
                verified_by_approver[approval.approver_id] = approval
            else:
                invalid_approvals += 1
        verified_approvers = sorted(verified_by_approver)
        return PolicyApprovalStatus(
            policy_version=policy_version,
            policy_sha256=policy_sha256,
            required_approvals=required_approvals,
            verified_approvals=len(verified_approvers),
            invalid_approvals=invalid_approvals,
            verified_approvers=verified_approvers,
            approved=len(verified_approvers) >= required_approvals,
        )

    def _write(self, approvals: list[PolicyApproval]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        ordered = sorted(
            approvals,
            key=lambda item: (item.policy_version, item.policy_sha256, item.approver_id),
        )
        payload: dict[str, Any] = {
            "schema_version": "1.0",
            "updated_at": datetime.now(UTC).isoformat(),
            "approvals": [approval.model_dump(mode="json") for approval in ordered],
        }
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def generate_policy_signing_keypair(
    *,
    private_key_path: Path,
    public_key_path: Path,
    overwrite: bool = False,
) -> dict[str, str]:
    if not overwrite:
        existing = [path for path in [private_key_path, public_key_path] if path.exists()]
        if existing:
            raise FileExistsError(f"refusing to overwrite existing key file: {existing[0]}")
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    private_key_path.parent.mkdir(parents=True, exist_ok=True)
    public_key_path.parent.mkdir(parents=True, exist_ok=True)
    private_key_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    public_key_path.write_bytes(
        public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    return {
        "private_key_path": str(private_key_path),
        "public_key_path": str(public_key_path),
        "signature_algorithm": SIGNATURE_ALGORITHM,
    }


def create_policy_approval(
    *,
    policy_version: str,
    policy_sha256: str,
    approver_id: str,
    approver_role: str,
    private_key_path: Path,
    notes: str = "",
) -> PolicyApproval:
    private_key = _load_private_key(private_key_path)
    approved_at = datetime.now(UTC)
    unsigned = PolicyApproval(
        policy_version=policy_version,
        policy_sha256=policy_sha256,
        approver_id=approver_id,
        approver_role=approver_role,
        approved_at=approved_at,
        notes=notes,
        public_key_pem=_public_key_pem(private_key.public_key()),
        signature_b64="",
    )
    signature = private_key.sign(_approval_payload(unsigned))
    return unsigned.model_copy(
        update={"signature_b64": base64.b64encode(signature).decode("ascii")}
    )


def verify_policy_approval(approval: PolicyApproval) -> bool:
    if approval.signature_algorithm != SIGNATURE_ALGORITHM:
        return False
    try:
        public_key = _load_public_key(approval.public_key_pem.encode("utf-8"))
        signature = base64.b64decode(approval.signature_b64.encode("ascii"), validate=True)
        public_key.verify(signature, _approval_payload(approval))
    except (InvalidSignature, ValueError):
        return False
    return True


def _approval_payload(approval: PolicyApproval) -> bytes:
    payload = {
        "approved_at": approval.approved_at.astimezone(UTC).isoformat(),
        "approver_id": approval.approver_id,
        "approver_role": approval.approver_role,
        "notes": approval.notes,
        "policy_sha256": approval.policy_sha256,
        "policy_version": approval.policy_version,
        "signature_algorithm": approval.signature_algorithm,
    }
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _load_private_key(path: Path) -> Ed25519PrivateKey:
    key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("policy approval private key must be Ed25519")
    return key


def _load_public_key(public_key_pem: bytes) -> Ed25519PublicKey:
    key = serialization.load_pem_public_key(public_key_pem)
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError("policy approval public key must be Ed25519")
    return key


def _public_key_pem(public_key: Ed25519PublicKey) -> str:
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
