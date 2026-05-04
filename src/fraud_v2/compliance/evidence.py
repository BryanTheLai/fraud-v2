from __future__ import annotations

import base64
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from fraud_v2.domain.decisions import DecisionResponse

EVIDENCE_SCHEMA_VERSION = "1.0"
EVIDENCE_PASSPHRASE_ENV = "FRAUD_EVIDENCE_PASSPHRASE"


def build_decision_evidence_payload(decision: DecisionResponse) -> dict[str, Any]:
    return {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "evidence_type": "decision",
        "exported_at": datetime.now(UTC).isoformat(),
        "decision": {
            "decision_id": str(decision.decision_id),
            "target_entity": decision.target_entity.model_dump(mode="json"),
            "created_at": decision.created_at.isoformat(),
            "risk_score": decision.risk_score,
            "risk_tier": decision.risk_tier.value,
            "action": decision.action.value,
            "policy_version": decision.policy_version,
            "model_version": decision.model_version,
            "degraded": decision.degraded,
            "reasoning_trace_id": str(decision.reasoning_trace_id),
            "safe_reasons": decision.safe_reasons,
            "signals": [signal.model_dump(mode="json") for signal in decision.signals],
            "feature_vector": decision.feature_vector.model_dump(mode="json"),
        },
        "safety": {
            "contains_real_pii": False,
            "regulatory_filing": False,
            "legal_disclaimer": (
                "Local encrypted evidence export for human review only; not a regulatory filing."
            ),
        },
    }


def write_encrypted_decision_evidence(
    *,
    decision: DecisionResponse,
    output_path: Path,
    passphrase: str,
) -> dict[str, Any]:
    payload = build_decision_evidence_payload(decision)
    envelope = encrypt_evidence_payload(
        payload=payload,
        passphrase=passphrase,
        aad=str(decision.decision_id),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(envelope, indent=2, sort_keys=True), encoding="utf-8")
    return envelope


def encrypt_evidence_payload(
    *,
    payload: dict[str, Any],
    passphrase: str,
    aad: str,
) -> dict[str, Any]:
    if len(passphrase.encode("utf-8")) < 12:
        raise ValueError("evidence passphrase must be at least 12 bytes")
    salt = os.urandom(16)
    nonce = os.urandom(12)
    key = _derive_key(passphrase=passphrase, salt=salt)
    plaintext = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, aad.encode("utf-8"))
    return {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "encryption": "AES-256-GCM",
        "kdf": "scrypt",
        "kdf_params": {"n": 2**14, "r": 8, "p": 1, "salt_bytes": 16},
        "aad": aad,
        "salt_b64": base64.b64encode(salt).decode("ascii"),
        "nonce_b64": base64.b64encode(nonce).decode("ascii"),
        "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
    }


def decrypt_evidence_payload(*, envelope: dict[str, Any], passphrase: str) -> dict[str, Any]:
    if envelope.get("encryption") != "AES-256-GCM" or envelope.get("kdf") != "scrypt":
        raise ValueError("unsupported evidence envelope")
    salt = base64.b64decode(str(envelope["salt_b64"]).encode("ascii"), validate=True)
    nonce = base64.b64decode(str(envelope["nonce_b64"]).encode("ascii"), validate=True)
    ciphertext = base64.b64decode(
        str(envelope["ciphertext_b64"]).encode("ascii"),
        validate=True,
    )
    key = _derive_key(passphrase=passphrase, salt=salt)
    try:
        plaintext = AESGCM(key).decrypt(
            nonce,
            ciphertext,
            str(envelope["aad"]).encode("utf-8"),
        )
    except InvalidTag as exc:
        raise ValueError("evidence decrypt failed") from exc
    return json.loads(plaintext.decode("utf-8"))


def _derive_key(*, passphrase: str, salt: bytes) -> bytes:
    return Scrypt(
        salt=salt,
        length=32,
        n=2**14,
        r=8,
        p=1,
    ).derive(passphrase.encode("utf-8"))
