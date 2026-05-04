from __future__ import annotations

from uuid import UUID

from fraud_v2.domain.enums import DecisionAction
from fraud_v2.domain.reviews import ReviewCase, ReviewDecision, ReviewDecisionRequest
from fraud_v2.storage.sqlite_store import SQLiteStore


class ReviewService:
    def __init__(self, store: SQLiteStore) -> None:
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
        decision = ReviewDecision(
            case_id=case_id,
            analyst_id=request.analyst_id,
            outcome=request.outcome,
            confidence=request.confidence,
            note=request.note,
        )
        return self.store.save_review_decision(decision)
