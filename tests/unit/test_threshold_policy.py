from __future__ import annotations

import pytest
from pydantic import ValidationError

from fraud_v2.decision.engine import DecisionEngine
from fraud_v2.domain.decisions import DecisionRequest
from fraud_v2.domain.entities import EntityRef
from fraud_v2.domain.enums import DecisionAction, EntityType, RiskTier
from fraud_v2.policy.thresholds import ThresholdPolicy, load_threshold_policy
from fraud_v2.storage.sqlite_store import SQLiteStore
from fraud_v2.synthetic.generator import SyntheticFraudGenerator


def test_threshold_policy_loads_from_json_file(tmp_path) -> None:  # type: ignore[no-untyped-def]
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(_strict_policy().model_dump_json(), encoding="utf-8")

    loaded = load_threshold_policy(policy_path)

    assert loaded.version == "strict-policy-test"
    assert loaded.red_min_score == 30


def test_threshold_policy_rejects_overlapping_bands() -> None:
    with pytest.raises(ValidationError, match="green_max_score must be lower"):
        ThresholdPolicy(
            version="bad-policy",
            green_max_score=80,
            red_min_score=20,
            degraded_min_score=21,
            high_request_amount_threshold=750,
            high_request_amount_severity=15,
            high_request_amount_reason="The requested amount is high for the local policy.",
        )


def test_decision_engine_uses_versioned_threshold_policy(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteStore(tmp_path / "fraud.sqlite")
    dataset = SyntheticFraudGenerator(seed=1).generate(users=50)
    store.add_events(dataset.events)
    early_as_of = dataset.events[20].occurred_at

    decision = DecisionEngine(store, policy=_strict_policy()).score(
        DecisionRequest(
            target_entity=EntityRef(entity_type=EntityType.USER, entity_id="user_00049"),
            as_of=early_as_of,
            amount=150,
        )
    )

    assert decision.policy_version == "strict-policy-test"
    assert decision.risk_score >= 30
    assert decision.risk_tier == RiskTier.RED
    assert decision.action == DecisionAction.BLOCK


def _strict_policy() -> ThresholdPolicy:
    return ThresholdPolicy(
        version="strict-policy-test",
        green_max_score=10,
        red_min_score=30,
        degraded_min_score=21,
        high_request_amount_threshold=100,
        high_request_amount_severity=35,
        high_request_amount_reason="The requested amount is high for the strict test policy.",
    )
