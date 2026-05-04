from __future__ import annotations

import hashlib
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from fraud_v2.domain.decisions import DecisionResponse
from fraud_v2.domain.errors import DecisionNotFound, DuplicatePayloadConflict
from fraud_v2.domain.events import EventEnvelope
from fraud_v2.domain.outbox import OutboxMessage, OutboxStatus
from fraud_v2.domain.reviews import ReviewCase, ReviewDecision


class SQLiteStore:
    def __init__(self, path: Path | str = Path("data/local/fraud_v2.sqlite")) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                create table if not exists events (
                  event_id text primary key,
                  event_type text not null,
                  occurred_at text not null,
                  idempotency_key text not null unique,
                  payload_hash text not null,
                  event_json text not null
                );
                create index if not exists ix_events_type_time on events(event_type, occurred_at);

                create table if not exists decisions (
                  decision_id text primary key,
                  target_entity_id text not null,
                  risk_score integer not null,
                  risk_tier text not null,
                  action text not null,
                  decision_json text not null
                );

                create table if not exists review_cases (
                  case_id text primary key,
                  decision_id text not null,
                  status text not null,
                  case_json text not null
                );

                create table if not exists review_decisions (
                  review_decision_id text primary key,
                  case_id text not null,
                  decision_json text not null
                );

                create table if not exists outbox_messages (
                  message_id text primary key,
                  event_id text not null unique,
                  topic text not null,
                  status text not null,
                  attempts integer not null,
                  payload_json text not null,
                  last_error text,
                  created_at text not null,
                  updated_at text not null
                );
                create index if not exists ix_outbox_status_created
                  on outbox_messages(status, created_at);
                """
            )

    def add_event(self, event: EventEnvelope, outbox_topic: str = "fraud.events") -> EventEnvelope:
        event_json = event.model_dump_json()
        payload_hash = hashlib.sha256(event_json.encode("utf-8")).hexdigest()
        with self._connect() as conn:
            existing = conn.execute(
                "select event_json, payload_hash from events where idempotency_key = ?",
                (event.idempotency_key,),
            ).fetchone()
            if existing:
                if existing["payload_hash"] != payload_hash:
                    raise DuplicatePayloadConflict(
                        f"idempotency key conflict: {event.idempotency_key}"
                    )
                return EventEnvelope.model_validate_json(str(existing["event_json"]))
            conn.execute(
                """
                insert into events(
                  event_id, event_type, occurred_at, idempotency_key, payload_hash, event_json
                )
                values (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(event.event_id),
                    event.event_type.value,
                    event.occurred_at.isoformat(),
                    event.idempotency_key,
                    payload_hash,
                    event_json,
                ),
            )
            self._enqueue_outbox(conn, event, event_json, outbox_topic)
        return event

    def add_events(self, events: list[EventEnvelope]) -> int:
        inserted = 0
        for event in events:
            self.add_event(event)
            inserted += 1
        return inserted

    def list_events(self) -> list[EventEnvelope]:
        with self._connect() as conn:
            rows = conn.execute("select event_json from events order by occurred_at asc").fetchall()
        return [EventEnvelope.model_validate_json(str(row["event_json"])) for row in rows]

    def list_outbox_messages(
        self,
        statuses: tuple[OutboxStatus, ...] = (OutboxStatus.PENDING, OutboxStatus.FAILED),
        limit: int = 100,
    ) -> list[OutboxMessage]:
        placeholders = ", ".join("?" for _ in statuses)
        params = [status.value for status in statuses]
        params.append(str(limit))
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                select * from outbox_messages
                where status in ({placeholders})
                order by created_at asc
                limit ?
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
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                update outbox_messages
                set status = ?, last_error = null, updated_at = ?
                where message_id = ?
                """,
                (OutboxStatus.PUBLISHED.value, now, str(message_id)),
            )
            row = conn.execute(
                "select * from outbox_messages where message_id = ?",
                (str(message_id),),
            ).fetchone()
        return self._outbox_from_row(row)

    def mark_outbox_failed(
        self, message_id: UUID, safe_error: str, max_attempts: int = 3
    ) -> OutboxMessage:
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            current = conn.execute(
                "select attempts from outbox_messages where message_id = ?",
                (str(message_id),),
            ).fetchone()
            attempts = int(current["attempts"]) + 1
            status = OutboxStatus.DEAD_LETTER if attempts >= max_attempts else OutboxStatus.FAILED
            conn.execute(
                """
                update outbox_messages
                set status = ?, attempts = ?, last_error = ?, updated_at = ?
                where message_id = ?
                """,
                (status.value, attempts, safe_error[:500], now, str(message_id)),
            )
            row = conn.execute(
                "select * from outbox_messages where message_id = ?",
                (str(message_id),),
            ).fetchone()
        return self._outbox_from_row(row)

    def save_decision(self, decision: DecisionResponse) -> DecisionResponse:
        with self._connect() as conn:
            conn.execute(
                """
                insert or replace into decisions(
                  decision_id, target_entity_id, risk_score, risk_tier, action, decision_json
                ) values (?, ?, ?, ?, ?, ?)
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
        return decision

    def get_decision(self, decision_id: UUID) -> DecisionResponse:
        with self._connect() as conn:
            row = conn.execute(
                "select decision_json from decisions where decision_id = ?",
                (str(decision_id),),
            ).fetchone()
        if not row:
            raise DecisionNotFound(str(decision_id))
        return DecisionResponse.model_validate_json(str(row["decision_json"]))

    def list_decisions(self) -> list[DecisionResponse]:
        with self._connect() as conn:
            rows = conn.execute("select decision_json from decisions").fetchall()
        return [DecisionResponse.model_validate_json(str(row["decision_json"])) for row in rows]

    def save_review_case(self, case: ReviewCase) -> ReviewCase:
        with self._connect() as conn:
            conn.execute(
                """
                insert or replace into review_cases(case_id, decision_id, status, case_json)
                values (?, ?, ?, ?)
                """,
                (str(case.case_id), str(case.decision_id), case.status, case.model_dump_json()),
            )
        return case

    def list_review_cases(self) -> list[ReviewCase]:
        with self._connect() as conn:
            rows = conn.execute("select case_json from review_cases order by case_id").fetchall()
        return [ReviewCase.model_validate_json(str(row["case_json"])) for row in rows]

    def save_review_decision(self, decision: ReviewDecision) -> ReviewDecision:
        with self._connect() as conn:
            conn.execute(
                """
                insert or replace into review_decisions(review_decision_id, case_id, decision_json)
                values (?, ?, ?)
                """,
                (
                    str(decision.review_decision_id),
                    str(decision.case_id),
                    decision.model_dump_json(),
                ),
            )
            conn.execute(
                "update review_cases set status = ? where case_id = ?",
                ("closed", str(decision.case_id)),
            )
        return decision

    def _enqueue_outbox(
        self, conn: sqlite3.Connection, event: EventEnvelope, event_json: str, topic: str
    ) -> None:
        now = datetime.now(UTC).isoformat()
        conn.execute(
            """
            insert or ignore into outbox_messages(
              message_id, event_id, topic, status, attempts, payload_json,
              last_error, created_at, updated_at
            )
            values (?, ?, ?, ?, ?, ?, null, ?, ?)
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

    def _outbox_from_row(self, row: sqlite3.Row | None) -> OutboxMessage:
        if row is None:
            raise KeyError("outbox message not found")
        return OutboxMessage(
            message_id=UUID(str(row["message_id"])),
            event_id=UUID(str(row["event_id"])),
            topic=str(row["topic"]),
            status=OutboxStatus(str(row["status"])),
            attempts=int(row["attempts"]),
            payload_json=str(row["payload_json"]),
            last_error=None if row["last_error"] is None else str(row["last_error"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
        )
