from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class AuditEntry(BaseModel):
    sequence: int = Field(ge=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    actor: str = Field(min_length=1, max_length=160)
    action: str = Field(min_length=1, max_length=120)
    target_type: str = Field(min_length=1, max_length=80)
    target_id: str = Field(min_length=1, max_length=200)
    trace_id: str = Field(default="", max_length=120)
    payload_hash: str = Field(min_length=64, max_length=64)
    previous_hash: str = Field(default="", max_length=64)
    entry_hash: str = Field(min_length=64, max_length=64)


class AuditVerificationReport(BaseModel):
    valid: bool
    entries_checked: int
    failure_sequence: int | None = None
    failure_reason: str | None = None
