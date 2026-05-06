from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class RetentionPolicy(BaseModel):
    event_days: int = Field(default=90, ge=1)
    decision_days: int = Field(default=365, ge=1)
    review_days: int = Field(default=365, ge=1)
    outbox_days: int = Field(default=30, ge=1)
    stream_dead_letter_days: int = Field(default=30, ge=1)
    audit_days: int = Field(default=3650, ge=1)


class RetentionTableReport(BaseModel):
    table: str
    retention_days: int
    cutoff_at: datetime
    expired_count: int
    action: str = "report_only"


class RetentionReport(BaseModel):
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    as_of: datetime
    policy: RetentionPolicy
    tables: list[RetentionTableReport]
    total_expired: int = Field(ge=0)
