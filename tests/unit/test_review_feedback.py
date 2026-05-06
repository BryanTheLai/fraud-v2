from datetime import UTC, datetime
from pathlib import Path

from fraud_v2.domain.decisions import DecisionResponse, FeatureVector
from fraud_v2.domain.entities import EntityRef
from fraud_v2.domain.enums import (
    DecisionAction,
    EntityType,
    EventType,
    FeatureFreshnessStatus,
    LabelValue,
    ReviewOutcome,
    RiskTier,
)
from fraud_v2.domain.reviews import ReviewDecisionRequest
from fraud_v2.review.service import ReviewService
from fraud_v2.storage.sqlite_store import SQLiteStore


def test_confirmed_review_outcome_creates_review_and_label_events(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite")
    decision = _manual_review_decision("user_00042")
    store.save_decision(decision)
    case = ReviewService(store).ensure_case_for_decision(decision.decision_id)
    assert case is not None

    ReviewService(store).decide(
        case.case_id,
        ReviewDecisionRequest(
            analyst_id="analyst-1",
            outcome=ReviewOutcome.CONFIRMED_FRAUD,
            confidence=0.95,
            note="Synthetic fraud ring confirmed.",
        ),
    )

    events = store.list_events()
    review_events = [
        event for event in events if event.event_type == EventType.MANUAL_REVIEW_DECIDED
    ]
    label_events = [event for event in events if event.event_type == EventType.LABEL_CREATED]

    assert len(review_events) == 1
    assert len(label_events) == 1
    assert label_events[0].payload.label_value == LabelValue.FRAUD
    assert label_events[0].payload.source == "manual_review"
    assert store.list_review_cases()[0].status == "closed"


def test_non_final_review_outcome_does_not_create_training_label(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite")
    decision = _manual_review_decision("user_00043")
    store.save_decision(decision)
    case = ReviewService(store).ensure_case_for_decision(decision.decision_id)
    assert case is not None

    ReviewService(store).decide(
        case.case_id,
        ReviewDecisionRequest(
            analyst_id="analyst-1",
            outcome=ReviewOutcome.NEEDS_MORE_INFO,
            confidence=0.40,
            note="Waiting for more evidence.",
        ),
    )

    events = store.list_events()

    assert [event.event_type for event in events] == [EventType.MANUAL_REVIEW_DECIDED]
    assert store.list_review_cases()[0].status == "closed"


def _manual_review_decision(user_id: str) -> DecisionResponse:
    target = EntityRef(entity_type=EntityType.USER, entity_id=user_id)
    as_of = datetime(2026, 5, 5, tzinfo=UTC)
    return DecisionResponse(
        target_entity=target,
        risk_score=55,
        risk_tier=RiskTier.YELLOW,
        action=DecisionAction.MANUAL_REVIEW,
        signals=[],
        feature_vector=FeatureVector(
            target_entity=target,
            as_of=as_of,
            values={},
            freshness={"events": FeatureFreshnessStatus.FRESH},
        ),
        policy_version="test-policy",
        model_version="test-model",
        safe_reasons=["Manual review test."],
    )
