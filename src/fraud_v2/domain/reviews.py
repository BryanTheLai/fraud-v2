from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from fraud_v2.domain.enums import ReviewOutcome


class ReviewCase(BaseModel):
    case_id: UUID = Field(default_factory=uuid4)
    decision_id: UUID
    target_entity_id: str
    priority: int = Field(ge=0, le=100)
    status: str = "open"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ReviewDecisionRequest(BaseModel):
    analyst_id: str
    outcome: ReviewOutcome
    confidence: float = Field(ge=0.0, le=1.0)
    note: str = Field(default="", max_length=2000)


class ReviewDecision(BaseModel):
    review_decision_id: UUID = Field(default_factory=uuid4)
    case_id: UUID
    analyst_id: str
    outcome: ReviewOutcome
    confidence: float
    note: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
