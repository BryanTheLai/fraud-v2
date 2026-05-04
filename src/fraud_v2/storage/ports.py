from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from fraud_v2.domain.audit import AuditEntry, AuditVerificationReport
from fraud_v2.domain.decisions import DecisionResponse
from fraud_v2.domain.events import EventEnvelope
from fraud_v2.domain.outbox import OutboxMessage, OutboxStatus
from fraud_v2.domain.retention import RetentionPolicy, RetentionReport
from fraud_v2.domain.reviews import ReviewCase, ReviewDecision


class FraudStore(Protocol):
    def add_event(
        self, event: EventEnvelope, outbox_topic: str = "fraud.events"
    ) -> EventEnvelope: ...

    def add_events(self, events: list[EventEnvelope]) -> int: ...

    def list_events(self) -> list[EventEnvelope]: ...

    def list_outbox_messages(
        self,
        statuses: tuple[OutboxStatus, ...] = (OutboxStatus.PENDING, OutboxStatus.FAILED),
        limit: int = 100,
    ) -> list[OutboxMessage]: ...

    def outbox_counts(self) -> dict[str, int]: ...

    def mark_outbox_published(self, message_id: UUID) -> OutboxMessage: ...

    def mark_outbox_failed(
        self, message_id: UUID, safe_error: str, max_attempts: int = 3
    ) -> OutboxMessage: ...

    def save_decision(self, decision: DecisionResponse) -> DecisionResponse: ...

    def get_decision(self, decision_id: UUID) -> DecisionResponse: ...

    def list_decisions(self) -> list[DecisionResponse]: ...

    def save_review_case(self, case: ReviewCase) -> ReviewCase: ...

    def list_review_cases(self) -> list[ReviewCase]: ...

    def save_review_decision(self, decision: ReviewDecision) -> ReviewDecision: ...

    def list_audit_entries(self, limit: int = 100) -> list[AuditEntry]: ...

    def verify_audit_chain(self) -> AuditVerificationReport: ...

    def retention_report(
        self,
        as_of: datetime | None = None,
        policy: RetentionPolicy | None = None,
    ) -> RetentionReport: ...

    def prune_retention(
        self,
        as_of: datetime | None = None,
        policy: RetentionPolicy | None = None,
    ) -> RetentionReport: ...
