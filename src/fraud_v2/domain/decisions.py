from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from fraud_v2.domain.entities import EntityRef
from fraud_v2.domain.enums import DecisionAction, FeatureFreshnessStatus, RiskTier


class RiskSignal(BaseModel):
    code: str
    severity: int = Field(ge=0, le=100)
    safe_reason: str
    source: str


class FeatureVector(BaseModel):
    target_entity: EntityRef
    as_of: datetime
    values: dict[str, float | int | str | bool]
    freshness: dict[str, FeatureFreshnessStatus]
    source_event_ids: list[str] = Field(default_factory=list)


class DecisionRequest(BaseModel):
    target_entity: EntityRef
    as_of: datetime = Field(default_factory=lambda: datetime.now(UTC))
    amount: float = Field(default=0.0, ge=0)
    context: dict[str, str | float | int | bool] = Field(default_factory=dict)


class DecisionResponse(BaseModel):
    decision_id: UUID = Field(default_factory=uuid4)
    target_entity: EntityRef
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    risk_score: int = Field(ge=0, le=100)
    risk_tier: RiskTier
    action: DecisionAction
    signals: list[RiskSignal]
    feature_vector: FeatureVector
    policy_version: str
    model_version: str | None = None
    degraded: bool = False
    safe_reasons: list[str]
    reasoning_trace_id: UUID = Field(default_factory=uuid4)
