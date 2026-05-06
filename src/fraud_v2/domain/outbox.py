from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class OutboxStatus(StrEnum):
    PENDING = "PENDING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"
    DEAD_LETTER = "DEAD_LETTER"


class OutboxMessage(BaseModel):
    message_id: UUID = Field(default_factory=uuid4)
    event_id: UUID
    topic: str
    status: OutboxStatus = OutboxStatus.PENDING
    attempts: int = Field(default=0, ge=0)
    payload_json: str
    last_error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
