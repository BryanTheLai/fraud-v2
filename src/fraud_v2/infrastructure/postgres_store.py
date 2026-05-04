from __future__ import annotations

import hashlib
from dataclasses import dataclass

from fraud_v2.domain.errors import DuplicatePayloadConflict
from fraud_v2.domain.events import EventEnvelope
from fraud_v2.infrastructure.optional_imports import optional_module


@dataclass(frozen=True)
class PostgresEventStore:
    dsn: str

    def init_schema(self) -> None:
        psycopg = optional_module("psycopg", "infra")
        with psycopg.connect(self.dsn) as conn:
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

    def add_event(self, event: EventEnvelope) -> EventEnvelope:
        psycopg = optional_module("psycopg", "infra")
        event_json = event.model_dump_json()
        payload_hash = hashlib.sha256(event_json.encode("utf-8")).hexdigest()
        with psycopg.connect(self.dsn) as conn:
            existing = conn.execute(
                "select event_json::text, payload_hash from events where idempotency_key = %s",
                (event.idempotency_key,),
            ).fetchone()
            if existing:
                if existing[1] != payload_hash:
                    raise DuplicatePayloadConflict(
                        f"idempotency key conflict: {event.idempotency_key}"
                    )
                return EventEnvelope.model_validate_json(existing[0])
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
        return event

    def list_events(self) -> list[EventEnvelope]:
        psycopg = optional_module("psycopg", "infra")
        with psycopg.connect(self.dsn) as conn:
            rows = conn.execute(
                "select event_json::text from events order by occurred_at asc"
            ).fetchall()
        return [EventEnvelope.model_validate_json(row[0]) for row in rows]
