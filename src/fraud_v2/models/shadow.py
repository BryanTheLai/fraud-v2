from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import joblib
import pandas as pd
from pydantic import BaseModel, Field

from fraud_v2.domain.entities import EntityRef
from fraud_v2.domain.enums import EntityType
from fraud_v2.domain.events import EventEnvelope
from fraud_v2.features.builder import FeatureBuilder
from fraud_v2.models.registry import JsonModelRegistry, ModelStatus, RegisteredModel
from fraud_v2.synthetic.generator import load_events_jsonl


class ShadowScore(BaseModel):
    shadow_score_id: UUID = Field(default_factory=uuid4)
    model_version: str
    model_status: ModelStatus
    target_entity: EntityRef
    as_of: datetime
    probability: float = Field(ge=0.0, le=1.0)
    threshold: float
    would_flag: bool
    feature_values: dict[str, float | int]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


def write_shadow_scores(
    events_path: Path,
    registry_path: Path,
    output_path: Path,
    status: ModelStatus = ModelStatus.ACTIVE,
) -> dict[str, Any]:
    events = load_events_jsonl(events_path)
    model_record = _select_model(JsonModelRegistry(registry_path).list_models(), status)
    scores = score_events_with_model(events, model_record)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps([score.model_dump(mode="json") for score in scores], indent=2, sort_keys=True),
        encoding="utf-8",
    )
    flagged = sum(1 for score in scores if score.would_flag)
    return {
        "model_version": model_record.model_version,
        "model_status": model_record.status.value,
        "rows": len(scores),
        "would_flag": flagged,
        "output": str(output_path),
    }


def score_events_with_model(
    events: list[EventEnvelope], model_record: RegisteredModel
) -> list[ShadowScore]:
    users = sorted(
        {
            ref.entity_id
            for event in events
            for ref in event.entity_refs
            if ref.entity_type == EntityType.USER
        }
    )
    as_of = max(event.occurred_at for event in events)
    builder = FeatureBuilder(events)
    rows: list[dict[str, float | int]] = []
    targets: list[EntityRef] = []
    for user_id in users:
        target = EntityRef(entity_type=EntityType.USER, entity_id=user_id)
        vector = builder.build(target, as_of)
        rows.append(
            {
                column: _number(vector.values.get(column, 0))
                for column in model_record.feature_columns
            }
        )
        targets.append(target)
    frame = pd.DataFrame(rows, columns=model_record.feature_columns)
    estimator = joblib.load(model_record.artifact_path)
    probabilities = estimator.predict_proba(frame)[:, 1]
    return [
        ShadowScore(
            model_version=model_record.model_version,
            model_status=model_record.status,
            target_entity=target,
            as_of=as_of,
            probability=float(probability),
            threshold=model_record.cost_weighted_threshold or model_record.threshold,
            would_flag=float(probability)
            >= (model_record.cost_weighted_threshold or model_record.threshold),
            feature_values=row,
        )
        for target, probability, row in zip(targets, probabilities, rows, strict=True)
    ]


def _select_model(models: list[RegisteredModel], status: ModelStatus) -> RegisteredModel:
    matching = [model for model in models if model.status == status]
    if not matching:
        raise KeyError(f"no registered model with status: {status.value}")
    return sorted(matching, key=lambda model: model.registered_at)[-1]


def _number(value: float | int | str | bool | object) -> float | int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int | float):
        return value
    return 0
