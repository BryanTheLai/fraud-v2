from __future__ import annotations

import json
import platform
import sqlite3
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fraud_v2.decision.engine import DecisionEngine
from fraud_v2.domain.decisions import DecisionRequest
from fraud_v2.domain.entities import EntityRef
from fraud_v2.domain.enums import EntityType
from fraud_v2.storage.sqlite_store import SQLiteStore
from fraud_v2.synthetic.generator import SyntheticFraudGenerator


def run_load_benchmark(
    *,
    users: int,
    score_users: int,
    db_path: Path,
    output_path: Path,
    seed: int = 20260531,
    overwrite: bool = False,
) -> dict[str, Any]:
    reset_existing_db = db_path.exists()
    if reset_existing_db and not overwrite:
        raise FileExistsError(f"benchmark database already exists: {db_path}")

    generated_at = datetime.now(UTC)
    generation_started = time.perf_counter()
    dataset = SyntheticFraudGenerator(seed=seed).generate(users=users)
    generation_seconds = time.perf_counter() - generation_started

    store = SQLiteStore(db_path)
    if reset_existing_db:
        _clear_benchmark_database(db_path)
    load_started = time.perf_counter()
    inserted = store.add_events(dataset.events)
    load_seconds = time.perf_counter() - load_started

    events = store.list_events()
    as_of = max(event.occurred_at for event in events)
    engine = DecisionEngine(store)
    scoring_started = time.perf_counter()
    tier_counts: dict[str, int] = {}
    decisions_to_score = min(users, score_users)
    for index in range(decisions_to_score):
        decision = engine.score(
            DecisionRequest(
                target_entity=EntityRef(
                    entity_type=EntityType.USER,
                    entity_id=f"user_{index:05d}",
                ),
                as_of=as_of,
            )
        )
        tier_counts[decision.risk_tier.value] = tier_counts.get(decision.risk_tier.value, 0) + 1
    scoring_seconds = time.perf_counter() - scoring_started

    report: dict[str, Any] = {
        "generated_at": generated_at.isoformat(),
        "seed": seed,
        "users": users,
        "events": len(dataset.events),
        "inserted_events": inserted,
        "score_users": decisions_to_score,
        "generation_seconds": round(generation_seconds, 6),
        "load_seconds": round(load_seconds, 6),
        "score_seconds": round(scoring_seconds, 6),
        "load_events_per_second": _rate(inserted, load_seconds),
        "score_decisions_per_second": _rate(decisions_to_score, scoring_seconds),
        "risk_tiers": tier_counts,
        "db_path": str(db_path),
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "processor": platform.processor(),
            "machine": platform.machine(),
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def _rate(count: int, seconds: float) -> float:
    if seconds <= 0:
        return 0.0
    return round(count / seconds, 3)


def _clear_benchmark_database(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        for table in [
            "review_decisions",
            "review_cases",
            "decisions",
            "outbox_messages",
            "stream_dead_letters",
            "audit_entries",
            "events",
        ]:
            conn.execute(f"delete from {table}")
        conn.commit()
    finally:
        conn.close()
