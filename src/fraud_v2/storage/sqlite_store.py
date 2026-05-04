from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from uuid import UUID

from fraud_v2.domain.decisions import DecisionResponse
from fraud_v2.domain.errors import DecisionNotFound, DuplicatePayloadConflict
from fraud_v2.domain.events import EventEnvelope
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
                """
            )

    def add_event(self, event: EventEnvelope) -> EventEnvelope:
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
