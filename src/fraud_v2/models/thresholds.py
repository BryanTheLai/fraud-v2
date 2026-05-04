from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class CostAssumptions:
    fraud_loss: float = 500.0
    false_positive_cost: float = 50.0
    manual_review_cost: float = 5.0
    compute_cost_per_score: float = 0.001
    recovery_rate_on_missed_fraud: float = 0.10


def cost_weighted_threshold_report(
    labels: np.ndarray,
    probabilities: np.ndarray,
    assumptions: CostAssumptions = CostAssumptions(),
) -> dict[str, Any]:
    candidates: list[dict[str, float | int]] = []
    for threshold in np.linspace(0.05, 0.95, 19):
        predictions = (probabilities >= threshold).astype(int)
        tp = int(((predictions == 1) & (labels == 1)).sum())
        fp = int(((predictions == 1) & (labels == 0)).sum())
        tn = int(((predictions == 0) & (labels == 0)).sum())
        fn = int(((predictions == 0) & (labels == 1)).sum())
        fpr = fp / max(fp + tn, 1)
        recall = tp / max(tp + fn, 1)
        profit = (
            tp * assumptions.fraud_loss
            - fp * assumptions.false_positive_cost
            - fn * assumptions.fraud_loss * (1.0 - assumptions.recovery_rate_on_missed_fraud)
            - len(labels) * assumptions.compute_cost_per_score
        )
        candidates.append(
            {
                "threshold": float(threshold),
                "profit": float(profit),
                "tp": tp,
                "fp": fp,
                "tn": tn,
                "fn": fn,
                "fpr": float(fpr),
                "recall": float(recall),
            }
        )
    best_by_profit = max(candidates, key=lambda item: float(item["profit"]))
    guardrail_candidates = [item for item in candidates if float(item["fpr"]) <= 0.01]
    best_at_1pct_fpr = (
        max(guardrail_candidates, key=lambda item: float(item["recall"]))
        if guardrail_candidates
        else min(candidates, key=lambda item: float(item["fpr"]))
    )
    return {
        "cost_assumptions": assumptions.__dict__,
        "best_profit_threshold": best_by_profit,
        "best_recall_under_1pct_fpr": best_at_1pct_fpr,
        "candidates": candidates,
    }
