from __future__ import annotations

import json
import math
from collections import Counter
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Literal, TypedDict

from fraud_v2.decision.engine import DecisionEngine
from fraud_v2.domain.decisions import DecisionRequest
from fraud_v2.domain.entities import EntityRef
from fraud_v2.domain.enums import EntityType, LabelValue, ReviewOutcome
from fraud_v2.domain.events import EventEnvelope, LabelCreated
from fraud_v2.storage.sqlite_store import SQLiteStore
from fraud_v2.synthetic.generator import load_events_jsonl

DriftStatus = Literal["stable", "watch", "drift"]
KappaStatus = Literal["strong", "usable", "watch"]


class MlOpsScoreRow(TypedDict):
    user_id: str
    score: int
    label: int
    reviewer_a: str
    reviewer_b: str


def write_mlops_report(
    *,
    events_path: Path,
    db_path: Path,
    output_path: Path,
    simulate_score_shift_points: int = 12,
) -> dict[str, object]:
    events = load_events_jsonl(events_path)
    store = SQLiteStore(db_path)
    store.add_events(events)
    rows = _score_rows(events=events, store=store)
    midpoint = len(rows) // 2
    reference_scores = [row["score"] for row in rows[:midpoint]]
    current_scores = [
        _shift_score(row["score"], simulate_score_shift_points) for row in rows[midpoint:]
    ]
    score_psi = population_stability_index(reference_scores, current_scores)
    kappa = cohen_kappa(
        [row["reviewer_a"] for row in rows],
        [row["reviewer_b"] for row in rows],
    )
    report = {
        "rows": len(rows),
        "simulation": {
            "current_score_shift_points": simulate_score_shift_points,
            "note": "Current population shift is synthetic and local-only.",
        },
        "score_drift": {
            "psi": score_psi,
            "status": psi_status(score_psi),
            "reference_distribution": _band_distribution(reference_scores),
            "current_distribution": _band_distribution(current_scores),
        },
        "analyst_consistency": {
            "cohens_kappa": kappa,
            "status": kappa_status(kappa),
            "reviewer_a_distribution": _counter_dict(row["reviewer_a"] for row in rows),
            "reviewer_b_distribution": _counter_dict(row["reviewer_b"] for row in rows),
            "note": "Reviewer labels are deterministic simulations, not real analyst QA.",
        },
        "confusion_at_red": _confusion_at_red(rows),
        "operating_notes": [
            "PSI below 0.10 is stable, 0.10-0.25 is watch, above 0.25 is drift.",
            "Kappa below 0.60 needs review of analyst guidance or queue routing.",
            "Use real analyst labels only after privacy, access control, and QA policy exist.",
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def population_stability_index(
    expected: Sequence[int | float],
    actual: Sequence[int | float],
    bins: list[tuple[float, float]] | None = None,
) -> float:
    if bins is None:
        bins = [(0, 20), (21, 50), (51, 79), (80, 100)]
    total = 0.0
    for low, high in bins:
        expected_pct = _bucket_pct(expected, low, high)
        actual_pct = _bucket_pct(actual, low, high)
        total += (actual_pct - expected_pct) * math.log(actual_pct / expected_pct)
    return round(total, 6)


def cohen_kappa(labels_a: list[str], labels_b: list[str]) -> float:
    if len(labels_a) != len(labels_b):
        raise ValueError("label lists must have the same length")
    if not labels_a:
        return 0.0
    categories = set(labels_a) | set(labels_b)
    observed = sum(a == b for a, b in zip(labels_a, labels_b, strict=True)) / len(labels_a)
    expected = sum(
        (labels_a.count(category) / len(labels_a)) * (labels_b.count(category) / len(labels_b))
        for category in categories
    )
    if expected == 1.0:
        return 1.0 if observed == 1.0 else 0.0
    return round((observed - expected) / (1.0 - expected), 6)


def psi_status(value: float) -> DriftStatus:
    if value < 0.10:
        return "stable"
    if value < 0.25:
        return "watch"
    return "drift"


def kappa_status(value: float) -> KappaStatus:
    if value >= 0.80:
        return "strong"
    if value >= 0.60:
        return "usable"
    return "watch"


def _score_rows(*, events: list[EventEnvelope], store: SQLiteStore) -> list[MlOpsScoreRow]:
    users = sorted(
        {
            ref.entity_id
            for event in events
            for ref in event.entity_refs
            if ref.entity_type == EntityType.USER
        }
    )
    as_of = max(event.occurred_at for event in events)
    fraud_users = _fraud_users(events)
    engine = DecisionEngine(store)
    rows: list[MlOpsScoreRow] = []
    for user_id in users:
        decision = engine.score(
            DecisionRequest(
                target_entity=EntityRef(entity_type=EntityType.USER, entity_id=user_id),
                as_of=as_of,
            )
        )
        score = decision.risk_score
        label = 1 if user_id in fraud_users else 0
        rows.append(
            {
                "user_id": user_id,
                "score": score,
                "label": label,
                "reviewer_a": _reviewer_a(score),
                "reviewer_b": _reviewer_b(user_id=user_id, score=score, label=label),
            }
        )
    return rows


def _fraud_users(events: list[EventEnvelope]) -> set[str]:
    users: set[str] = set()
    for event in events:
        payload = event.payload
        if not isinstance(payload, LabelCreated):
            continue
        if payload.label_value != LabelValue.FRAUD:
            continue
        if payload.target_entity.entity_type == EntityType.USER:
            users.add(payload.target_entity.entity_id)
    return users


def _reviewer_a(score: int) -> str:
    if score >= 80:
        return ReviewOutcome.CONFIRMED_FRAUD.value
    if score <= 20:
        return ReviewOutcome.CONFIRMED_LEGITIMATE.value
    return ReviewOutcome.NEEDS_MORE_INFO.value


def _reviewer_b(*, user_id: str, score: int, label: int) -> str:
    user_index = int(user_id.rsplit("_", 1)[-1])
    if score >= 90 or (score >= 75 and label == 1):
        return ReviewOutcome.CONFIRMED_FRAUD.value
    if score <= 25 or (score < 40 and user_index % 5 == 0):
        return ReviewOutcome.CONFIRMED_LEGITIMATE.value
    if user_index % 11 == 0:
        return ReviewOutcome.ESCALATED.value
    return ReviewOutcome.NEEDS_MORE_INFO.value


def _shift_score(score: int, shift: int) -> int:
    return max(0, min(100, score + shift))


def _bucket_pct(scores: Sequence[int | float], low: float, high: float) -> float:
    if not scores:
        return 0.001
    count = sum(1 for score in scores if low <= score <= high)
    return max(count / len(scores), 0.001)


def _band_distribution(scores: list[int]) -> dict[str, int]:
    return {
        "green_0_20": sum(0 <= score <= 20 for score in scores),
        "low_yellow_21_50": sum(21 <= score <= 50 for score in scores),
        "high_yellow_51_79": sum(51 <= score <= 79 for score in scores),
        "red_80_100": sum(80 <= score <= 100 for score in scores),
    }


def _confusion_at_red(rows: list[MlOpsScoreRow]) -> dict[str, int]:
    return {
        "tp": sum(row["score"] >= 80 and row["label"] == 1 for row in rows),
        "fp": sum(row["score"] >= 80 and row["label"] == 0 for row in rows),
        "tn": sum(row["score"] < 80 and row["label"] == 0 for row in rows),
        "fn": sum(row["score"] < 80 and row["label"] == 1 for row in rows),
    }


def _counter_dict(values: Iterable[str]) -> dict[str, int]:
    return dict(Counter(values))
