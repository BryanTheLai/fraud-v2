from __future__ import annotations

import json

import pytest

from fraud_v2.compliance.evidence import (
    decrypt_evidence_payload,
    write_encrypted_decision_evidence,
)
from fraud_v2.decision.engine import DecisionEngine
from fraud_v2.domain.decisions import DecisionRequest
from fraud_v2.domain.entities import EntityRef
from fraud_v2.domain.enums import EntityType
from fraud_v2.storage.sqlite_store import SQLiteStore
from fraud_v2.synthetic.generator import SyntheticFraudGenerator


def test_encrypted_decision_evidence_round_trip(tmp_path) -> None:  # type: ignore[no-untyped-def]
    decision = _decision(tmp_path)
    output_path = tmp_path / "decision-evidence.enc.json"

    envelope = write_encrypted_decision_evidence(
        decision=decision,
        output_path=output_path,
        passphrase="local evidence passphrase",
    )
    decrypted = decrypt_evidence_payload(
        envelope=json.loads(output_path.read_text(encoding="utf-8")),
        passphrase="local evidence passphrase",
    )

    assert envelope["encryption"] == "AES-256-GCM"
    assert decrypted["decision"]["decision_id"] == str(decision.decision_id)
    assert decrypted["decision"]["safe_reasons"]
    assert decrypted["safety"]["regulatory_filing"] is False


def test_encrypted_decision_evidence_rejects_short_passphrase(tmp_path) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError, match="at least 12 bytes"):
        write_encrypted_decision_evidence(
            decision=_decision(tmp_path),
            output_path=tmp_path / "decision-evidence.enc.json",
            passphrase="short",
        )


def test_encrypted_decision_evidence_rejects_wrong_passphrase(tmp_path) -> None:  # type: ignore[no-untyped-def]
    decision = _decision(tmp_path)
    envelope = write_encrypted_decision_evidence(
        decision=decision,
        output_path=tmp_path / "decision-evidence.enc.json",
        passphrase="local evidence passphrase",
    )

    with pytest.raises(ValueError, match="decrypt failed"):
        decrypt_evidence_payload(envelope=envelope, passphrase="wrong evidence passphrase")


def _decision(tmp_path):  # type: ignore[no-untyped-def]
    store = SQLiteStore(tmp_path / "fraud.sqlite")
    dataset = SyntheticFraudGenerator(seed=32).generate(users=20)
    store.add_events(dataset.events)
    return DecisionEngine(store).score(
        DecisionRequest(
            target_entity=EntityRef(entity_type=EntityType.USER, entity_id="user_00000"),
            as_of=max(event.occurred_at for event in dataset.events),
            amount=1000,
        )
    )
