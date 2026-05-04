from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split

from fraud_v2.models.dataset import build_training_dataset
from fraud_v2.models.thresholds import cost_weighted_threshold_report
from fraud_v2.synthetic.generator import load_events_jsonl


def train_baseline(events_path: Path, output_dir: Path) -> dict[str, Any]:
    events = load_events_jsonl(events_path)
    dataset = build_training_dataset(events)
    frame = dataset.frame
    if frame["label"].nunique() < 2:
        raise ValueError("training data needs at least one fraud and one legitimate label")
    x_train, x_test, y_train, y_test = train_test_split(
        frame[dataset.feature_columns],
        frame[dataset.label_column],
        test_size=0.3,
        random_state=20260505,
        stratify=frame[dataset.label_column],
    )
    model = RandomForestClassifier(
        n_estimators=150,
        random_state=20260505,
        class_weight="balanced",
        min_samples_leaf=2,
    )
    model.fit(x_train, y_train)
    probabilities = model.predict_proba(x_test)[:, 1]
    threshold, best_f1 = _best_threshold(y_test.to_numpy(), probabilities)
    cost_report = cost_weighted_threshold_report(y_test.to_numpy(), probabilities)
    predictions = (probabilities >= threshold).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, predictions, average="binary", zero_division=0
    )
    report = {
        "model_family": "sklearn_random_forest",
        "model_version": "baseline-20260505-001",
        "rows": int(len(frame)),
        "features": dataset.feature_columns,
        "average_precision": float(average_precision_score(y_test, probabilities)),
        "brier_score": float(brier_score_loss(y_test, probabilities)),
        "precision_at_threshold": float(precision),
        "recall_at_threshold": float(recall),
        "f1_at_threshold": float(f1),
        "best_f1": float(best_f1),
        "threshold": float(threshold),
        "cost_weighted_threshold": cost_report["best_profit_threshold"],
        "recall_under_1pct_fpr_threshold": cost_report["best_recall_under_1pct_fpr"],
        "threshold_candidates": cost_report["candidates"],
        "cost_assumptions": cost_report["cost_assumptions"],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output_dir / "baseline.joblib")
    (output_dir / "baseline-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _best_threshold(labels: np.ndarray, probabilities: np.ndarray) -> tuple[float, float]:
    best_threshold = 0.5
    best_f1 = -1.0
    for threshold in np.linspace(0.05, 0.95, 19):
        predictions = (probabilities >= threshold).astype(int)
        _, _, f1, _ = precision_recall_fscore_support(
            labels, predictions, average="binary", zero_division=0
        )
        if float(f1) > best_f1:
            best_threshold = float(threshold)
            best_f1 = float(f1)
    return best_threshold, best_f1
