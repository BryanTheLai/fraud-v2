from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from fraud_v2.models.dataset import build_training_dataset
from fraud_v2.models.thresholds import cost_weighted_threshold_report
from fraud_v2.synthetic.generator import load_events_jsonl


def benchmark_model_families(events_path: Path, output_path: Path) -> dict[str, Any]:
    events = load_events_jsonl(events_path)
    dataset = build_training_dataset(events)
    frame = dataset.frame
    if frame["label"].nunique() < 2:
        raise ValueError("benchmark needs at least one fraud and one legitimate label")

    stratify = frame[dataset.label_column]
    if int(stratify.value_counts().min()) < 2:
        stratify = None
    x_train, x_test, y_train, y_test = train_test_split(
        frame[dataset.feature_columns],
        frame[dataset.label_column],
        test_size=0.3,
        random_state=20260506,
        stratify=stratify,
    )
    labels = y_test.to_numpy()
    model_specs: list[tuple[str, Any]] = [
        (
            "sklearn_logistic_regression",
            make_pipeline(
                StandardScaler(),
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=20260506,
                ),
            ),
        ),
        (
            "sklearn_random_forest",
            RandomForestClassifier(
                n_estimators=120,
                random_state=20260506,
                class_weight="balanced",
                min_samples_leaf=2,
            ),
        ),
    ]
    rows: list[dict[str, str | float]] = []
    for family, model in model_specs:
        model.fit(x_train, y_train)
        probabilities = model.predict_proba(x_test)[:, 1]
        threshold_report = cost_weighted_threshold_report(labels, probabilities)
        best_profit = threshold_report["best_profit_threshold"]
        recall_at_1pct_fpr = threshold_report["best_recall_under_1pct_fpr"]
        rows.append(
            {
                "model_family": family,
                "average_precision": float(average_precision_score(labels, probabilities)),
                "brier_score": float(brier_score_loss(labels, probabilities)),
                "best_profit": float(best_profit["profit"]),
                "best_profit_threshold": float(best_profit["threshold"]),
                "recall_at_1pct_fpr": float(recall_at_1pct_fpr["recall"]),
                "recall_at_1pct_fpr_threshold": float(recall_at_1pct_fpr["threshold"]),
            }
        )
    winner = max(
        rows,
        key=lambda item: (
            _metric_value(item, "best_profit"),
            _metric_value(item, "average_precision"),
            -_metric_value(item, "brier_score"),
        ),
    )
    report = {
        "schema_version": "model-benchmark-report-v1",
        "rows": int(len(frame)),
        "features": dataset.feature_columns,
        "test_rows": int(len(labels)),
        "positive_test_rows": int(np.asarray(labels).sum()),
        "models": rows,
        "recommended_model_family": winner["model_family"],
        "recommendation": (
            "Use the winning lightweight tabular model as a shadow/ranking signal; keep the "
            "rules/graph policy as the final auditable guardrail until real labels exist."
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def _metric_value(row: dict[str, str | float], key: str) -> float:
    value = row[key]
    if isinstance(value, float):
        return value
    return float(value)
