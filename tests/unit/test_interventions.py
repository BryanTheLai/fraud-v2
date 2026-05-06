from datetime import UTC, datetime

from fraud_v2.compliance.interventions import build_break_spell_draft
from fraud_v2.domain.decisions import DecisionResponse, FeatureVector
from fraud_v2.domain.entities import EntityRef
from fraud_v2.domain.enums import DecisionAction, EntityType, FeatureFreshnessStatus, RiskTier


def test_break_spell_draft_is_local_and_actionable() -> None:
    target = EntityRef(entity_type=EntityType.USER, entity_id="user_123")
    decision = DecisionResponse(
        target_entity=target,
        risk_score=55,
        risk_tier=RiskTier.YELLOW,
        action=DecisionAction.MANUAL_REVIEW,
        signals=[],
        feature_vector=FeatureVector(
            target_entity=target,
            as_of=datetime.now(UTC),
            values={"payment_amount_24h": 1000},
            freshness={"payment_amount_24h": FeatureFreshnessStatus.FRESH},
        ),
        policy_version="policy-test",
        safe_reasons=["Risky payee change pattern."],
    )

    draft = build_break_spell_draft(decision)

    assert draft.no_real_message_sent is True
    assert "Pause before continuing" in draft.message
    assert draft.risk_reasons == ["Risky payee change pattern."]
