from __future__ import annotations

import json
from pathlib import Path

from fraud_v2.decision.engine import DecisionEngine
from fraud_v2.domain.decisions import DecisionRequest
from fraud_v2.domain.entities import EntityRef
from fraud_v2.domain.enums import EntityType
from fraud_v2.storage.sqlite_store import SQLiteStore
from fraud_v2.synthetic.generator import load_events_jsonl


def run_replay(events_path: Path, db_path: Path, report_path: Path) -> dict[str, int | str]:
    events = load_events_jsonl(events_path)
    store = SQLiteStore(db_path)
    store.add_events(events)
    users = sorted(
        {
            ref.entity_id
            for event in events
            for ref in event.entity_refs
            if ref.entity_type == EntityType.USER
        }
    )
    as_of = max(event.occurred_at for event in events)
    engine = DecisionEngine(store)
    decisions = [
        engine.score(
            DecisionRequest(
                target_entity=EntityRef(entity_type=EntityType.USER, entity_id=user_id),
                as_of=as_of,
            )
        )
        for user_id in users
    ]
    report: dict[str, int | str] = {
        "events": len(events),
        "users": len(users),
        "decisions": len(decisions),
        "green": sum(1 for decision in decisions if decision.risk_tier.value == "GREEN"),
        "yellow": sum(1 for decision in decisions if decision.risk_tier.value == "YELLOW"),
        "red": sum(1 for decision in decisions if decision.risk_tier.value == "RED"),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
