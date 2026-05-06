from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class StreamDeadLetterReason(StrEnum):
    MESSAGE_ERROR = "MESSAGE_ERROR"
    EMPTY_PAYLOAD = "EMPTY_PAYLOAD"
    INVALID_EVENT = "INVALID_EVENT"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"


class StreamDeadLetter(BaseModel):
    dead_letter_id: UUID = Field(default_factory=uuid4)
    source_topic: str
    consumer_group: str
    reason: StreamDeadLetterReason
    payload_hash: str | None = None
    payload_preview: str = Field(default="", max_length=500)
    safe_error: str = Field(max_length=500)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
