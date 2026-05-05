from __future__ import annotations

import json

from fraud_v2.models.eval_dashboard import write_model_eval_dashboard


def test_model_eval_dashboard_writes_html_summary(tmp_path) -> None:  # type: ignore[no-untyped-def]
    report_path = tmp_path / "baseline-report.json"
    shadow_path = tmp_path / "shadow.json"
    output_path = tmp_path / "dashboard.html"
    report_path.write_text(
        json.dumps(
            {
                "model_version": "baseline-test",
                "model_family": "sklearn_random_forest",
                "rows": 12,
                "features": ["amount", "device_count"],
                "average_precision": 0.75,
                "brier_score": 0.12,
                "threshold": 0.4,
                "cost_weighted_threshold": {"threshold": 0.35},
                "recall_under_1pct_fpr_threshold": {"threshold": 0.8},
                "threshold_candidates": [
                    {"threshold": 0.35, "tp": 4, "fp": 1, "fn": 2, "profit": 1200}
                ],
                "feature_importances": [
                    {"feature": "device_count", "importance": 0.72},
                    {"feature": "amount", "importance": 0.28},
                ],
            }
        ),
        encoding="utf-8",
    )
    shadow_path.write_text(
        json.dumps(
            [
                {"would_flag": True},
                {"would_flag": False},
            ]
        ),
        encoding="utf-8",
    )

    summary = write_model_eval_dashboard(
        report_path=report_path,
        output_path=output_path,
        shadow_scores_path=shadow_path,
    )

    html = output_path.read_text(encoding="utf-8")
    assert summary["model_version"] == "baseline-test"
    assert summary["shadow_scores"]["flag_rate"] == 0.5
    assert "Model Eval Dashboard" in html
    assert "baseline-test" in html
    assert "device_count" in html
    assert "Feature Importance" in html
    assert "0.7200" in html


def test_model_eval_dashboard_handles_missing_shadow_scores(tmp_path) -> None:  # type: ignore[no-untyped-def]
    report_path = tmp_path / "baseline-report.json"
    report_path.write_text(
        json.dumps(
            {
                "model_version": "baseline-test",
                "model_family": "sklearn_random_forest",
                "rows": 12,
                "features": [],
                "average_precision": 0.75,
                "brier_score": 0.12,
                "threshold": 0.4,
                "threshold_candidates": [],
            }
        ),
        encoding="utf-8",
    )

    summary = write_model_eval_dashboard(
        report_path=report_path,
        output_path=tmp_path / "dashboard.html",
    )

    assert summary["shadow_scores"]["rows"] == 0
    assert summary["shadow_scores"]["flag_rate"] is None
