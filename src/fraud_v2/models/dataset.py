from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from fraud_v2.domain.entities import EntityRef
from fraud_v2.domain.enums import EntityType, LabelValue
from fraud_v2.domain.events import (
    ApplicationSubmitted,
    EventEnvelope,
    LabelCreated,
    PaymentAttempted,
)
from fraud_v2.features.builder import FeatureBuilder


@dataclass(frozen=True)
class TrainingDataset:
    frame: pd.DataFrame
    feature_columns: list[str]
    label_column: str = "label"


def build_training_dataset(events: list[EventEnvelope]) -> TrainingDataset:
    users = {
        ref.entity_id
        for event in events
        for ref in event.entity_refs
        if ref.entity_type == EntityType.USER
    }
    builder = FeatureBuilder(events)
    rows: list[dict[str, float | int | str]] = []
    max_time = max(event.occurred_at for event in events)
    fraud_users: set[str] = set()
    for event in events:
        if not isinstance(event.payload, LabelCreated):
            continue
        if event.payload.target_entity.entity_type != EntityType.USER:
            continue
        if event.payload.label_value == LabelValue.FRAUD:
            fraud_users.add(event.payload.target_entity.entity_id)
    for user_id in sorted(users):
        as_of = _first_score_time(events, user_id) or max_time
        vector = builder.build(EntityRef(entity_type=EntityType.USER, entity_id=user_id), as_of)
        row: dict[str, float | int | str] = {
            key: _number(value)
            for key, value in vector.values.items()
            if isinstance(value, bool | int | float)
        }
        row["user_id"] = user_id
        row["label"] = 1 if user_id in fraud_users else 0
        rows.append(row)
    frame = pd.DataFrame(rows).fillna(0)
    feature_columns = [column for column in frame.columns if column not in {"user_id", "label"}]
    return TrainingDataset(frame=frame, feature_columns=feature_columns)


def _number(value: bool | int | float | str) -> float | int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int | float):
        return value
    return 0


def _first_score_time(events: list[EventEnvelope], user_id: str) -> datetime | None:
    for event in sorted(events, key=lambda item: item.occurred_at):
        if isinstance(event.payload, ApplicationSubmitted) and event.payload.user_id == user_id:
            return event.occurred_at
        if isinstance(event.payload, PaymentAttempted) and event.payload.user_id == user_id:
            return event.occurred_at
    return None
