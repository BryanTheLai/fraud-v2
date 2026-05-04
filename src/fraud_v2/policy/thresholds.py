from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from fraud_v2.domain.enums import DecisionAction, RiskTier


class ThresholdPolicy(BaseModel):
    version: str = Field(min_length=6)
    green_max_score: int = Field(ge=0, le=100)
    red_min_score: int = Field(ge=0, le=100)
    degraded_min_score: int = Field(ge=0, le=100)
    high_request_amount_threshold: float = Field(ge=0)
    high_request_amount_severity: int = Field(ge=0, le=100)
    high_request_amount_reason: str = Field(min_length=10, max_length=300)

    @model_validator(mode="after")
    def validate_threshold_order(self) -> ThresholdPolicy:
        if self.green_max_score >= self.red_min_score:
            raise ValueError("green_max_score must be lower than red_min_score")
        return self

    def tier_action(self, score: int, degraded: bool) -> tuple[RiskTier, DecisionAction]:
        if degraded:
            return RiskTier.YELLOW, DecisionAction.MANUAL_REVIEW
        if score <= self.green_max_score:
            return RiskTier.GREEN, DecisionAction.APPROVE
        if score < self.red_min_score:
            return RiskTier.YELLOW, DecisionAction.MANUAL_REVIEW
        return RiskTier.RED, DecisionAction.BLOCK


def default_threshold_policy() -> ThresholdPolicy:
    return ThresholdPolicy(
        version="local-policy-20260505-002",
        green_max_score=20,
        red_min_score=80,
        degraded_min_score=21,
        high_request_amount_threshold=750,
        high_request_amount_severity=15,
        high_request_amount_reason="The requested amount is high for the local policy.",
    )


def load_threshold_policy(path: Path | None = None) -> ThresholdPolicy:
    if path is None:
        return default_threshold_policy()
    return ThresholdPolicy.model_validate_json(path.read_text(encoding="utf-8"))
