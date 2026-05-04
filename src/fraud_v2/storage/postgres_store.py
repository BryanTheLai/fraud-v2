from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from fraud_v2.domain.audit import AuditEntry, AuditVerificationReport
from fraud_v2.domain.decisions import DecisionResponse
from fraud_v2.domain.errors import DecisionNotFound, DuplicatePayloadConflict
from fraud_v2.domain.events import EventEnvelope
from fraud_v2.domain.outbox import OutboxMessage, OutboxStatus
from fraud_v2.domain.retention import RetentionPolicy, RetentionReport, RetentionTableReport
from fraud_v2.domain.reviews import ReviewCase, ReviewDecision
from fraud_v2.infrastructure.optional_imports import optional_module
from fraud_v2.observability.logging import get_trace_id
from fraud_v2.storage.sqlite_store import GENESIS_AUDIT_HASH


@dataclass(frozen=True)
class PostgresStore:
    dsn: str

    def __post_init__(self) -> None:
        self.init_schema()

    def init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                create table if not exists events (
                  event_id text primary key,
                  event_type text not null,
                  occurred_at timestamptz not null,
                  idempotency_key text not null unique,
                  payload_hash text not null,
                  event_json jsonb not null
                )
                """
            )
            conn.execute(
                "create index if not exists ix_events_type_time on events(event_type, occurred_at)"
            )
            conn.execute(
                """
                create table if not exists decisions (
                  decision_id text primary key,
                  target_entity_id text not null,
                  risk_score integer not null,
                  risk_tier text not null,
                  action text not null,
                  decision_json jsonb not null
                )
                """
            )
            conn.execute(
                """
                create table if not exists review_cases (
                  case_id text primary key,
                  decision_id text not null,
                  status text not null,
                  case_json jsonb not null
                )
                """
            )
            conn.execute(
                """
                create table if not exists review_decisions (
                  review_decision_id text primary key,
                  case_id text not null,
                  decision_json jsonb not null
                )
                """
            )
            conn.execute(
                """
                create table if not exists outbox_messages (
                  message_id text primary key,
                  event_id text not null unique,
                  topic text not null,
                  status text not null,
                  attempts integer not null,
                  payload_json jsonb not null,
                  last_error text,
                  created_at timestamptz not null,
                  updated_at timestamptz not null
                )
                """
            )
            conn.execute(
                """
                create index if not exists ix_outbox_status_created
                on outbox_messages(status, created_at)
                """
            )
            conn.execute(
                """
                create table if not exists audit_entries (
                  sequence integer primary key,
                  created_at timestamptz not null,
                  actor text not null,
                  action text not null,
                  target_type text not null,
                  target_id text not null,
                  trace_id text not null,
                  payload_hash text not null,
                  previous_hash text not null,
                  entry_hash text not null unique
                )
                """
            )
            conn.execute(
                """
                create index if not exists ix_audit_action_created
                on audit_entries(action, created_at)
                """
            )

    def add_event(self, event: EventEnvelope, outbox_topic: str = "fraud.events") -> EventEnvelope:
        event_json = event.model_dump_json()
        payload_hash = hashlib.sha256(event_json.encode("utf-8")).hexdigest()
        with self._connect() as conn:
            existing = conn.execute(
                """
                select event_json::text as event_json, payload_hash
                from events
                where idempotency_key = %s
                """,
                (event.idempotency_key,),
            ).fetchone()
            if existing:
                if str(existing["payload_hash"]) != payload_hash:
                    raise DuplicatePayloadConflict(
                        f"idempotency key conflict: {event.idempotency_key}"
                    )
                return EventEnvelope.model_validate_json(str(existing["event_json"]))
            conn.execute(
                """
                insert into events(
                  event_id, event_type, occurred_at, idempotency_key, payload_hash, event_json
                )
                values (%s, %s, %s, %s, %s, %s::jsonb)
                """,
                (
                    str(event.event_id),
                    event.event_type.value,
                    event.occurred_at,
                    event.idempotency_key,
                    payload_hash,
                    event_json,
                ),
            )
            self._enqueue_outbox(conn, event, event_json, outbox_topic)
            self._append_audit(
                conn,
                actor="local-system",
                action="event.ingested",
                target_type="event",
                target_id=str(event.event_id),
                payload={
                    "event_type": event.event_type.value,
                    "idempotency_key": event.idempotency_key,
                },
            )
        return event

    def add_events(self, events: list[EventEnvelope]) -> int:
        inserted = 0
        for event in events:
            self.add_event(event)
            inserted += 1
        return inserted

    def list_events(self) -> list[EventEnvelope]:
        with self._connect() as conn:
            rows = conn.execute(
                "select event_json::text as event_json from events order by occurred_at asc"
            ).fetchall()
        return [EventEnvelope.model_validate_json(str(row["event_json"])) for row in rows]

    def list_outbox_messages(
        self,
        statuses: tuple[OutboxStatus, ...] = (OutboxStatus.PENDING, OutboxStatus.FAILED),
        limit: int = 100,
    ) -> list[OutboxMessage]:
        placeholders = ", ".join("%s" for _ in statuses)
        params: list[object] = [status.value for status in statuses]
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                select message_id, event_id, topic, status, attempts,
                       payload_json::text as payload_json, last_error,
                       created_at, updated_at
                from outbox_messages
                where status in ({placeholders})
                order by created_at asc
                limit %s
                """,
                params,
            ).fetchall()
        return [self._outbox_from_row(row) for row in rows]

    def outbox_counts(self) -> dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute(
                "select status, count(*) as count from outbox_messages group by status"
            ).fetchall()
        return {str(row["status"]): int(row["count"]) for row in rows}

    def mark_outbox_published(self, message_id: UUID) -> OutboxMessage:
        now = datetime.now(UTC)
        with self._connect() as conn:
            conn.execute(
                """
                update outbox_messages
                set status = %s, last_error = null, updated_at = %s
                where message_id = %s
                """,
                (OutboxStatus.PUBLISHED.value, now, str(message_id)),
            )
            self._append_audit(
                conn,
                actor="local-system",
                action="outbox.published",
                target_type="outbox_message",
                target_id=str(message_id),
                payload={"status": OutboxStatus.PUBLISHED.value},
            )
            row = conn.execute(
                """
                select message_id, event_id, topic, status, attempts,
                       payload_json::text as payload_json, last_error,
                       created_at, updated_at
                from outbox_messages where message_id = %s
                """,
                (str(message_id),),
            ).fetchone()
        return self._outbox_from_row(row)

    def mark_outbox_failed(
        self, message_id: UUID, safe_error: str, max_attempts: int = 3
    ) -> OutboxMessage:
        now = datetime.now(UTC)
        with self._connect() as conn:
            current = conn.execute(
                "select attempts from outbox_messages where message_id = %s",
                (str(message_id),),
            ).fetchone()
            attempts = int(current["attempts"]) + 1
            status = OutboxStatus.DEAD_LETTER if attempts >= max_attempts else OutboxStatus.FAILED
            conn.execute(
                """
                update outbox_messages
                set status = %s, attempts = %s, last_error = %s, updated_at = %s
                where message_id = %s
                """,
                (status.value, attempts, safe_error[:500], now, str(message_id)),
            )
            self._append_audit(
                conn,
                actor="local-system",
                action="outbox.failed",
                target_type="outbox_message",
                target_id=str(message_id),
                payload={"status": status.value, "attempts": attempts},
            )
            row = conn.execute(
                """
                select message_id, event_id, topic, status, attempts,
                       payload_json::text as payload_json, last_error,
                       created_at, updated_at
                from outbox_messages where message_id = %s
                """,
                (str(message_id),),
            ).fetchone()
        return self._outbox_from_row(row)

    def save_decision(self, decision: DecisionResponse) -> DecisionResponse:
        with self._connect() as conn:
            conn.execute(
                """
                insert into decisions(
                  decision_id, target_entity_id, risk_score, risk_tier, action, decision_json
                )
                values (%s, %s, %s, %s, %s, %s::jsonb)
                on conflict (decision_id) do update set
                  target_entity_id = excluded.target_entity_id,
                  risk_score = excluded.risk_score,
                  risk_tier = excluded.risk_tier,
                  action = excluded.action,
                  decision_json = excluded.decision_json
                """,
                (
                    str(decision.decision_id),
                    decision.target_entity.entity_id,
                    decision.risk_score,
                    decision.risk_tier.value,
                    decision.action.value,
                    decision.model_dump_json(),
                ),
            )
            self._append_audit(
                conn,
                actor="local-system",
                action="decision.created",
                target_type="decision",
                target_id=str(decision.decision_id),
                payload={
                    "target_entity_id": decision.target_entity.entity_id,
                    "risk_score": decision.risk_score,
                    "risk_tier": decision.risk_tier.value,
                    "action": decision.action.value,
                    "policy_version": decision.policy_version,
                    "model_version": decision.model_version or "",
                },
            )
        return decision

    def get_decision(self, decision_id: UUID) -> DecisionResponse:
        with self._connect() as conn:
            row = conn.execute(
                "select decision_json::text as decision_json from decisions where decision_id = %s",
                (str(decision_id),),
            ).fetchone()
        if not row:
            raise DecisionNotFound(str(decision_id))
        return DecisionResponse.model_validate_json(str(row["decision_json"]))

    def list_decisions(self) -> list[DecisionResponse]:
        with self._connect() as conn:
            rows = conn.execute(
                "select decision_json::text as decision_json from decisions"
            ).fetchall()
        return [DecisionResponse.model_validate_json(str(row["decision_json"])) for row in rows]

    def save_review_case(self, case: ReviewCase) -> ReviewCase:
        with self._connect() as conn:
            conn.execute(
                """
                insert into review_cases(case_id, decision_id, status, case_json)
                values (%s, %s, %s, %s::jsonb)
                on conflict (case_id) do update set
                  decision_id = excluded.decision_id,
                  status = excluded.status,
                  case_json = excluded.case_json
                """,
                (str(case.case_id), str(case.decision_id), case.status, case.model_dump_json()),
            )
            self._append_audit(
                conn,
                actor="local-system",
                action="review.case_created",
                target_type="review_case",
                target_id=str(case.case_id),
                payload={
                    "decision_id": str(case.decision_id),
                    "target_entity_id": case.target_entity_id,
                    "priority": case.priority,
                    "status": case.status,
                },
            )
        return case

    def list_review_cases(self) -> list[ReviewCase]:
        with self._connect() as conn:
            rows = conn.execute(
                "select case_json::text as case_json from review_cases order by case_id"
            ).fetchall()
        return [ReviewCase.model_validate_json(str(row["case_json"])) for row in rows]

    def save_review_decision(self, decision: ReviewDecision) -> ReviewDecision:
        with self._connect() as conn:
            case_row = conn.execute(
                "select case_json::text as case_json from review_cases where case_id = %s",
                (str(decision.case_id),),
            ).fetchone()
            closed_case_json = None
            if case_row is not None:
                closed_case = ReviewCase.model_validate_json(str(case_row["case_json"])).model_copy(
                    update={"status": "closed"}
                )
                closed_case_json = closed_case.model_dump_json()
            conn.execute(
                """
                insert into review_decisions(review_decision_id, case_id, decision_json)
                values (%s, %s, %s::jsonb)
                on conflict (review_decision_id) do update set
                  case_id = excluded.case_id,
                  decision_json = excluded.decision_json
                """,
                (
                    str(decision.review_decision_id),
                    str(decision.case_id),
                    decision.model_dump_json(),
                ),
            )
            if closed_case_json is not None:
                conn.execute(
                    "update review_cases set status = %s, case_json = %s::jsonb where case_id = %s",
                    ("closed", closed_case_json, str(decision.case_id)),
                )
            self._append_audit(
                conn,
                actor=decision.analyst_id,
                action="review.decided",
                target_type="review_decision",
                target_id=str(decision.review_decision_id),
                payload={
                    "case_id": str(decision.case_id),
                    "outcome": decision.outcome.value,
                    "confidence": decision.confidence,
                },
            )
        return decision

    def list_audit_entries(self, limit: int = 100) -> list[AuditEntry]:
        with self._connect() as conn:
            rows = conn.execute(
                "select * from audit_entries order by sequence desc limit %s",
                (limit,),
            ).fetchall()
        return [self._audit_from_row(row) for row in reversed(rows)]

    def verify_audit_chain(self) -> AuditVerificationReport:
        with self._connect() as conn:
            rows = conn.execute("select * from audit_entries order by sequence asc").fetchall()
        previous_hash = GENESIS_AUDIT_HASH
        for row in rows:
            entry = self._audit_from_row(row)
            if entry.previous_hash != previous_hash:
                return AuditVerificationReport(
                    valid=False,
                    entries_checked=entry.sequence - 1,
                    failure_sequence=entry.sequence,
                    failure_reason="previous hash mismatch",
                )
            payload = self._audit_hash_payload(
                sequence=entry.sequence,
                created_at=entry.created_at.isoformat(),
                actor=entry.actor,
                action=entry.action,
                target_type=entry.target_type,
                target_id=entry.target_id,
                trace_id=entry.trace_id,
                payload_hash=entry.payload_hash,
                previous_hash=entry.previous_hash,
            )
            expected_hash = self._hash_json(payload)
            if entry.entry_hash != expected_hash:
                return AuditVerificationReport(
                    valid=False,
                    entries_checked=entry.sequence - 1,
                    failure_sequence=entry.sequence,
                    failure_reason="entry hash mismatch",
                )
            previous_hash = entry.entry_hash
        return AuditVerificationReport(valid=True, entries_checked=len(rows))

    def retention_report(
        self,
        as_of: datetime | None = None,
        policy: RetentionPolicy | None = None,
    ) -> RetentionReport:
        report_as_of = as_of or datetime.now(UTC)
        active_policy = policy or RetentionPolicy()
        tables = [
            self._retention_table_report(
                table="events",
                retention_days=active_policy.event_days,
                as_of=report_as_of,
                expired_count=self._count_events_before(
                    report_as_of - timedelta(days=active_policy.event_days)
                ),
            ),
            self._retention_table_report(
                table="decisions",
                retention_days=active_policy.decision_days,
                as_of=report_as_of,
                expired_count=self._count_decisions_before(
                    report_as_of - timedelta(days=active_policy.decision_days)
                ),
            ),
            self._retention_table_report(
                table="review_cases",
                retention_days=active_policy.review_days,
                as_of=report_as_of,
                expired_count=self._count_json_created_before(
                    table="review_cases",
                    json_column="case_json",
                    cutoff_at=report_as_of - timedelta(days=active_policy.review_days),
                ),
            ),
            self._retention_table_report(
                table="review_decisions",
                retention_days=active_policy.review_days,
                as_of=report_as_of,
                expired_count=self._count_json_created_before(
                    table="review_decisions",
                    json_column="decision_json",
                    cutoff_at=report_as_of - timedelta(days=active_policy.review_days),
                ),
            ),
            self._retention_table_report(
                table="outbox_messages",
                retention_days=active_policy.outbox_days,
                as_of=report_as_of,
                expired_count=self._count_iso_column_before(
                    table="outbox_messages",
                    column="created_at",
                    cutoff_at=report_as_of - timedelta(days=active_policy.outbox_days),
                ),
            ),
            self._retention_table_report(
                table="audit_entries",
                retention_days=active_policy.audit_days,
                as_of=report_as_of,
                expired_count=self._count_iso_column_before(
                    table="audit_entries",
                    column="created_at",
                    cutoff_at=report_as_of - timedelta(days=active_policy.audit_days),
                ),
            ),
        ]
        return RetentionReport(
            as_of=report_as_of,
            policy=active_policy,
            tables=tables,
            total_expired=sum(table.expired_count for table in tables),
        )

    def _connect(self) -> Any:
        psycopg = optional_module("psycopg", "infra")
        return psycopg.connect(self.dsn, row_factory=psycopg.rows.dict_row)

    def _enqueue_outbox(self, conn: Any, event: EventEnvelope, event_json: str, topic: str) -> None:
        now = datetime.now(UTC)
        conn.execute(
            """
            insert into outbox_messages(
              message_id, event_id, topic, status, attempts, payload_json,
              last_error, created_at, updated_at
            )
            values (%s, %s, %s, %s, %s, %s::jsonb, null, %s, %s)
            on conflict (event_id) do nothing
            """,
            (
                str(uuid4()),
                str(event.event_id),
                topic,
                OutboxStatus.PENDING.value,
                0,
                event_json,
                now,
                now,
            ),
        )

    def _append_audit(
        self,
        conn: Any,
        *,
        actor: str,
        action: str,
        target_type: str,
        target_id: str,
        payload: dict[str, Any],
    ) -> AuditEntry:
        now = datetime.now(UTC)
        previous = conn.execute(
            "select sequence, entry_hash from audit_entries order by sequence desc limit 1"
        ).fetchone()
        sequence = 1 if previous is None else int(previous["sequence"]) + 1
        previous_hash = GENESIS_AUDIT_HASH if previous is None else str(previous["entry_hash"])
        payload_hash = self._hash_json(payload)
        trace_id = get_trace_id()
        hash_payload = self._audit_hash_payload(
            sequence=sequence,
            created_at=now.isoformat(),
            actor=actor,
            action=action,
            target_type=target_type,
            target_id=target_id,
            trace_id=trace_id,
            payload_hash=payload_hash,
            previous_hash=previous_hash,
        )
        entry_hash = self._hash_json(hash_payload)
        conn.execute(
            """
            insert into audit_entries(
              sequence, created_at, actor, action, target_type, target_id,
              trace_id, payload_hash, previous_hash, entry_hash
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                sequence,
                now,
                actor,
                action,
                target_type,
                target_id,
                trace_id,
                payload_hash,
                previous_hash,
                entry_hash,
            ),
        )
        return AuditEntry(
            sequence=sequence,
            created_at=now,
            actor=actor,
            action=action,
            target_type=target_type,
            target_id=target_id,
            trace_id=trace_id,
            payload_hash=payload_hash,
            previous_hash=previous_hash,
            entry_hash=entry_hash,
        )

    def _audit_hash_payload(
        self,
        *,
        sequence: int,
        created_at: str,
        actor: str,
        action: str,
        target_type: str,
        target_id: str,
        trace_id: str,
        payload_hash: str,
        previous_hash: str,
    ) -> dict[str, str | int]:
        return {
            "sequence": sequence,
            "created_at": created_at,
            "actor": actor,
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "trace_id": trace_id,
            "payload_hash": payload_hash,
            "previous_hash": previous_hash,
        }

    def _hash_json(self, payload: dict[str, Any]) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _audit_from_row(self, row: Mapping[str, object]) -> AuditEntry:
        return AuditEntry(
            sequence=int(str(row["sequence"])),
            created_at=_parse_datetime(row["created_at"]),
            actor=str(row["actor"]),
            action=str(row["action"]),
            target_type=str(row["target_type"]),
            target_id=str(row["target_id"]),
            trace_id=str(row["trace_id"]),
            payload_hash=str(row["payload_hash"]),
            previous_hash=str(row["previous_hash"]),
            entry_hash=str(row["entry_hash"]),
        )

    def _retention_table_report(
        self,
        *,
        table: str,
        retention_days: int,
        as_of: datetime,
        expired_count: int,
    ) -> RetentionTableReport:
        return RetentionTableReport(
            table=table,
            retention_days=retention_days,
            cutoff_at=as_of - timedelta(days=retention_days),
            expired_count=expired_count,
        )

    def _count_events_before(self, cutoff_at: datetime) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "select count(*) as count from events where occurred_at < %s",
                (cutoff_at,),
            ).fetchone()
        return int(row["count"])

    def _count_decisions_before(self, cutoff_at: datetime) -> int:
        with self._connect() as conn:
            rows = conn.execute(
                "select decision_json::text as decision_json from decisions"
            ).fetchall()
        count = 0
        for row in rows:
            decision = DecisionResponse.model_validate_json(str(row["decision_json"]))
            if decision.created_at < cutoff_at:
                count += 1
        return count

    def _count_json_created_before(self, table: str, json_column: str, cutoff_at: datetime) -> int:
        if table not in {"review_cases", "review_decisions"}:
            raise ValueError(f"unsupported retention table: {table}")
        if json_column not in {"case_json", "decision_json"}:
            raise ValueError(f"unsupported retention column: {json_column}")
        with self._connect() as conn:
            rows = conn.execute(f"select {json_column}::text as payload from {table}").fetchall()
        count = 0
        for row in rows:
            payload = json.loads(str(row["payload"]))
            created_at = datetime.fromisoformat(str(payload["created_at"]))
            if created_at < cutoff_at:
                count += 1
        return count

    def _count_iso_column_before(self, table: str, column: str, cutoff_at: datetime) -> int:
        if table not in {"outbox_messages", "audit_entries"}:
            raise ValueError(f"unsupported retention table: {table}")
        if column != "created_at":
            raise ValueError(f"unsupported retention column: {column}")
        with self._connect() as conn:
            row = conn.execute(
                f"select count(*) as count from {table} where {column} < %s",
                (cutoff_at,),
            ).fetchone()
        return int(row["count"])

    def _outbox_from_row(self, row: Mapping[str, object] | None) -> OutboxMessage:
        if row is None:
            raise KeyError("outbox message not found")
        return OutboxMessage(
            message_id=UUID(str(row["message_id"])),
            event_id=UUID(str(row["event_id"])),
            topic=str(row["topic"]),
            status=OutboxStatus(str(row["status"])),
            attempts=int(str(row["attempts"])),
            payload_json=str(row["payload_json"]),
            last_error=None if row["last_error"] is None else str(row["last_error"]),
            created_at=_parse_datetime(row["created_at"]),
            updated_at=_parse_datetime(row["updated_at"]),
        )


class PostgresEventStore(PostgresStore):
    pass


def _parse_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))
