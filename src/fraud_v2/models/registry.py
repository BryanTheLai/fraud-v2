from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ModelStatus(StrEnum):
    CANDIDATE = "candidate"
    SHADOW = "shadow"
    ACTIVE = "active"
    DISABLED = "disabled"


class RegisteredModel(BaseModel):
    model_version: str
    model_family: str
    status: ModelStatus
    artifact_path: str
    report_path: str
    artifact_sha256: str
    report_sha256: str
    feature_columns: list[str]
    threshold: float
    cost_weighted_threshold: float | None = None
    average_precision: float | None = None
    brier_score: float | None = None
    registered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    notes: str = ""


class JsonModelRegistry:
    def __init__(self, path: Path) -> None:
        self.path = path

    def list_models(self) -> list[RegisteredModel]:
        if not self.path.exists():
            return []
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return [RegisteredModel.model_validate(item) for item in data.get("models", [])]

    def register_from_report(
        self,
        artifact_path: Path,
        report_path: Path,
        status: ModelStatus = ModelStatus.SHADOW,
        notes: str = "",
    ) -> RegisteredModel:
        if not artifact_path.exists():
            raise FileNotFoundError(f"model artifact not found: {artifact_path}")
        if not report_path.exists():
            raise FileNotFoundError(f"model report not found: {report_path}")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        model = RegisteredModel(
            model_version=str(report["model_version"]),
            model_family=str(report["model_family"]),
            status=status,
            artifact_path=str(artifact_path),
            report_path=str(report_path),
            artifact_sha256=_sha256(artifact_path),
            report_sha256=_sha256(report_path),
            feature_columns=[str(column) for column in report.get("features", [])],
            threshold=float(report["threshold"]),
            cost_weighted_threshold=_cost_threshold(report),
            average_precision=_optional_float(report, "average_precision"),
            brier_score=_optional_float(report, "brier_score"),
            notes=notes,
        )
        models = [
            existing
            for existing in self.list_models()
            if existing.model_version != model.model_version
        ]
        if model.status == ModelStatus.ACTIVE:
            models = [_demote_active(existing) for existing in models]
        models.append(model)
        self._write(models)
        return model

    def promote(self, model_version: str) -> RegisteredModel:
        models = self.list_models()
        promoted: RegisteredModel | None = None
        output: list[RegisteredModel] = []
        for model in models:
            if model.model_version == model_version:
                promoted = model.model_copy(update={"status": ModelStatus.ACTIVE})
                output.append(promoted)
            elif model.status == ModelStatus.ACTIVE:
                output.append(_demote_active(model))
            else:
                output.append(model)
        if promoted is None:
            raise KeyError(f"model version not found: {model_version}")
        self._write(output)
        return promoted

    def set_status(self, model_version: str, status: ModelStatus) -> RegisteredModel:
        models = self.list_models()
        updated: RegisteredModel | None = None
        output: list[RegisteredModel] = []
        for model in models:
            if model.model_version == model_version:
                updated = model.model_copy(update={"status": status})
                output.append(updated)
            elif status == ModelStatus.ACTIVE and model.status == ModelStatus.ACTIVE:
                output.append(_demote_active(model))
            else:
                output.append(model)
        if updated is None:
            raise KeyError(f"model version not found: {model_version}")
        self._write(output)
        return updated

    def _write(self, models: list[RegisteredModel]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        ordered = sorted(models, key=lambda item: (item.status.value, item.model_version))
        payload: dict[str, Any] = {
            "schema_version": "1.0",
            "updated_at": datetime.now(UTC).isoformat(),
            "models": [model.model_dump(mode="json") for model in ordered],
        }
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _optional_float(report: dict[str, Any], key: str) -> float | None:
    value = report.get(key)
    if value is None:
        return None
    return float(value)


def _cost_threshold(report: dict[str, Any]) -> float | None:
    value = report.get("cost_weighted_threshold")
    if not isinstance(value, dict):
        return None
    threshold = value.get("threshold")
    if threshold is None:
        return None
    return float(threshold)


def _demote_active(model: RegisteredModel) -> RegisteredModel:
    return model.model_copy(update={"status": ModelStatus.SHADOW})
