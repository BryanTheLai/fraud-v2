from __future__ import annotations

import json
import math
from pathlib import Path
from typing import TypedDict

from fraud_v2.decision.engine import DecisionEngine
from fraud_v2.domain.decisions import DecisionRequest
from fraud_v2.domain.entities import EntityRef
from fraud_v2.domain.enums import EntityType, LabelValue
from fraud_v2.domain.events import EventEnvelope, LabelCreated
from fraud_v2.storage.sqlite_store import SQLiteStore
from fraud_v2.synthetic.generator import load_events_jsonl


class MonitoringRow(TypedDict):
    user_id: str
    score: int
    tier: str
    label: int
    synthetic_group: str


def write_monitoring_report(
    events_path: Path, db_path: Path, output_path: Path
) -> dict[str, object]:
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
    rows: list[MonitoringRow] = []
    fraud_users = _fraud_users(events)
    for user_id in users:
        decision = engine.score(
            DecisionRequest(
                target_entity=EntityRef(entity_type=EntityType.USER, entity_id=user_id),
                as_of=as_of,
            )
        )
        rows.append(
            {
                "user_id": user_id,
                "score": decision.risk_score,
                "tier": decision.risk_tier.value,
                "label": 1 if user_id in fraud_users else 0,
                "synthetic_group": _synthetic_group(user_id),
            }
        )
    report = {
        "rows": len(rows),
        "score_summary": _score_summary([row["score"] for row in rows]),
        "psi_first_half_vs_second_half": _psi(
            [row["score"] for row in rows[: len(rows) // 2]],
            [row["score"] for row in rows[len(rows) // 2 :]],
        ),
        "confusion_proxy": _confusion(rows),
        "fairness_proxy": _fairness_proxy(rows),
        "fairness_note": (
            "Synthetic group is a hash bucket, not a protected class. "
            "This proves report mechanics only."
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _fraud_users(events: list[EventEnvelope]) -> set[str]:
    fraud_users: set[str] = set()
    for event in events:
        if not isinstance(event.payload, LabelCreated):
            continue
        if event.payload.label_value != LabelValue.FRAUD:
            continue
        if event.payload.target_entity.entity_type == EntityType.USER:
            fraud_users.add(event.payload.target_entity.entity_id)
    return fraud_users


def _score_summary(scores: list[int]) -> dict[str, float]:
    ordered = sorted(scores)
    return {
        "min": float(ordered[0]),
        "p50": float(ordered[len(ordered) // 2]),
        "max": float(ordered[-1]),
        "mean": sum(ordered) / len(ordered),
    }


def _psi(expected: list[int], actual: list[int]) -> float:
    bins = [(0, 20), (21, 50), (51, 79), (80, 100)]
    total = 0.0
    for low, high in bins:
        expected_pct = _bucket_pct(expected, low, high)
        actual_pct = _bucket_pct(actual, low, high)
        total += (actual_pct - expected_pct) * math.log(actual_pct / expected_pct)
    return total


def _bucket_pct(scores: list[int], low: int, high: int) -> float:
    if not scores:
        return 0.001
    count = sum(1 for score in scores if low <= score <= high)
    return max(count / len(scores), 0.001)


def _confusion(rows: list[MonitoringRow]) -> dict[str, int]:
    tp = sum(1 for row in rows if row["score"] >= 80 and row["label"] == 1)
    fp = sum(1 for row in rows if row["score"] >= 80 and row["label"] == 0)
    tn = sum(1 for row in rows if row["score"] < 80 and row["label"] == 0)
    fn = sum(1 for row in rows if row["score"] < 80 and row["label"] == 1)
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn}


def _fairness_proxy(rows: list[MonitoringRow]) -> dict[str, dict[str, float]]:
    groups = sorted({str(row["synthetic_group"]) for row in rows})
    output: dict[str, dict[str, float]] = {}
    for group in groups:
        group_rows = [row for row in rows if row["synthetic_group"] == group]
        red_rate = sum(1 for row in group_rows if row["score"] >= 80) / len(group_rows)
        fraud_rate = sum(1 for row in group_rows if row["label"] == 1) / len(group_rows)
        output[group] = {"red_rate": red_rate, "fraud_rate": fraud_rate}
    return output


def _synthetic_group(user_id: str) -> str:
    numeric = int(user_id.rsplit("_", 1)[-1])
    return f"group_{numeric % 3}"
