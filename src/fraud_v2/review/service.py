from __future__ import annotations

from uuid import UUID

from fraud_v2.domain.entities import EntityRef
from fraud_v2.domain.enums import (
    DecisionAction,
    EntityType,
    EventType,
    FraudTypology,
    LabelValue,
    ReviewOutcome,
)
from fraud_v2.domain.events import EventEnvelope, LabelCreated, ManualReviewDecided
from fraud_v2.domain.reviews import ReviewCase, ReviewDecision, ReviewDecisionRequest
from fraud_v2.storage.ports import FraudStore


class ReviewService:
    def __init__(self, store: FraudStore) -> None:
        self.store = store

    def ensure_case_for_decision(self, decision_id: UUID) -> ReviewCase | None:
        decision = self.store.get_decision(decision_id)
        if decision.action != DecisionAction.MANUAL_REVIEW:
            return None
        case = ReviewCase(
            decision_id=decision.decision_id,
            target_entity_id=decision.target_entity.entity_id,
            priority=decision.risk_score,
        )
        return self.store.save_review_case(case)

    def list_cases(self) -> list[ReviewCase]:
        return self.store.list_review_cases()

    def decide(self, case_id: UUID, request: ReviewDecisionRequest) -> ReviewDecision:
        case = self._case_by_id(case_id)
        decision = ReviewDecision(
            case_id=case_id,
            analyst_id=request.analyst_id,
            outcome=request.outcome,
            confidence=request.confidence,
            note=request.note,
        )
        saved = self.store.save_review_decision(decision)
        self._append_review_events(case, saved)
        return saved

    def _case_by_id(self, case_id: UUID) -> ReviewCase:
        for case in self.store.list_review_cases():
            if case.case_id == case_id:
                return case
        raise KeyError(f"review case not found: {case_id}")

    def _append_review_events(self, case: ReviewCase, decision: ReviewDecision) -> None:
        target = EntityRef(entity_type=EntityType.USER, entity_id=case.target_entity_id)
        self.store.add_event(
            EventEnvelope(
                event_type=EventType.MANUAL_REVIEW_DECIDED,
                occurred_at=decision.created_at,
                idempotency_key=f"review:{decision.review_decision_id}",
                entity_refs=[target],
                payload=ManualReviewDecided(
                    case_id=str(case.case_id),
                    decision_id=str(case.decision_id),
                    analyst_id=decision.analyst_id,
                    outcome=decision.outcome,
                    confidence=decision.confidence,
                    note=decision.note,
                ),
            )
        )
        label_value = _label_value(decision.outcome)
        if label_value is None:
            return
        self.store.add_event(
            EventEnvelope(
                event_type=EventType.LABEL_CREATED,
                occurred_at=decision.created_at,
                idempotency_key=f"label:{decision.review_decision_id}",
                entity_refs=[target],
                payload=LabelCreated(
                    target_entity=target,
                    label_value=label_value,
                    typology=FraudTypology.UNKNOWN,
                    label_available_at=decision.created_at,
                    source="manual_review",
                ),
            )
        )


def _label_value(outcome: ReviewOutcome) -> LabelValue | None:
    if outcome == ReviewOutcome.CONFIRMED_FRAUD:
        return LabelValue.FRAUD
    if outcome == ReviewOutcome.CONFIRMED_LEGITIMATE:
        return LabelValue.LEGITIMATE
    return None
