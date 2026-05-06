from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any


def write_model_eval_dashboard(
    *,
    report_path: Path,
    output_path: Path,
    shadow_scores_path: Path | None = None,
) -> dict[str, Any]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    shadow_summary = _shadow_summary(shadow_scores_path)
    summary = {
        "model_version": str(report["model_version"]),
        "model_family": str(report["model_family"]),
        "rows": int(report["rows"]),
        "features": len(report.get("features", [])),
        "average_precision": float(report["average_precision"]),
        "brier_score": float(report["brier_score"]),
        "threshold": float(report["threshold"]),
        "cost_weighted_threshold": _threshold_value(report.get("cost_weighted_threshold")),
        "recall_under_1pct_fpr_threshold": _threshold_value(
            report.get("recall_under_1pct_fpr_threshold")
        ),
        "shadow_scores": shadow_summary,
        "output_path": str(output_path),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_html(report, summary), encoding="utf-8")
    return summary


def _shadow_summary(shadow_scores_path: Path | None) -> dict[str, int | float | None | str]:
    if shadow_scores_path is None or not shadow_scores_path.exists():
        return {
            "path": None,
            "rows": 0,
            "would_flag": 0,
            "flag_rate": None,
        }
    scores = json.loads(shadow_scores_path.read_text(encoding="utf-8"))
    rows = len(scores)
    would_flag = sum(1 for score in scores if bool(score.get("would_flag")))
    return {
        "path": str(shadow_scores_path),
        "rows": rows,
        "would_flag": would_flag,
        "flag_rate": round(would_flag / rows, 6) if rows else None,
    }


def _threshold_value(raw_value: object) -> float | None:
    if not isinstance(raw_value, dict):
        return None
    threshold = raw_value.get("threshold")
    return float(threshold) if threshold is not None else None


def _html(report: dict[str, Any], summary: dict[str, Any]) -> str:
    features = report.get("features", [])
    candidates = report.get("threshold_candidates", [])[:10]
    feature_importances = report.get("feature_importances", [])[:12]
    model_version = escape(str(summary["model_version"]))
    model_family = escape(str(summary["model_family"]))
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>fraud-v2 model eval dashboard</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 32px; color: #172026; }}
      h1 {{ margin-bottom: 4px; }}
      .meta {{ color: #52616b; margin-top: 0; }}
      .grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 12px;
        margin: 24px 0;
      }}
      .metric {{ border: 1px solid #d8dee4; border-radius: 6px; padding: 12px; }}
      .label {{ color: #52616b; font-size: 12px; text-transform: uppercase; }}
      .value {{ font-size: 22px; font-weight: 700; margin-top: 4px; }}
      table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
      th, td {{ border-bottom: 1px solid #d8dee4; padding: 8px; text-align: left; }}
      th {{ background: #f6f8fa; }}
      code {{ background: #f6f8fa; padding: 2px 4px; border-radius: 4px; }}
    </style>
  </head>
  <body>
    <h1>Model Eval Dashboard</h1>
    <p class="meta">{model_version} | {model_family}</p>
    <section class="grid">
      {_metric("Rows", summary["rows"])}
      {_metric("Features", summary["features"])}
      {_metric("Average Precision", _fmt(summary["average_precision"]))}
      {_metric("Brier Score", _fmt(summary["brier_score"]))}
      {_metric("Model Threshold", _fmt(summary["threshold"]))}
      {_metric("Cost Threshold", _fmt(summary["cost_weighted_threshold"]))}
      {_metric("Shadow Rows", summary["shadow_scores"]["rows"])}
      {_metric("Shadow Flag Rate", _fmt(summary["shadow_scores"]["flag_rate"]))}
    </section>
    <h2>Feature Columns</h2>
    <p>{", ".join(f"<code>{escape(str(feature))}</code>" for feature in features)}</p>
    <h2>Feature Importance</h2>
    {_feature_importance_table(feature_importances)}
    <h2>Top Threshold Candidates</h2>
    <table>
      <thead><tr><th>Threshold</th><th>TP</th><th>FP</th><th>FN</th><th>Profit</th></tr></thead>
      <tbody>{"".join(_candidate_row(candidate) for candidate in candidates)}</tbody>
    </table>
  </body>
</html>
"""


def _feature_importance_table(feature_importances: list[dict[str, Any]]) -> str:
    if not feature_importances:
        return "<p>No feature importance values found in the model report.</p>"
    rows = "".join(
        "<tr>"
        f"<td>{escape(str(item.get('feature', '')))}</td>"
        f"<td>{escape(_fmt(item.get('importance')))}</td>"
        "</tr>"
        for item in feature_importances
    )
    return (
        "<table><thead><tr><th>Feature</th><th>Importance</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )


def _metric(label: str, value: object) -> str:
    return (
        '<div class="metric">'
        f'<div class="label">{escape(label)}</div>'
        f'<div class="value">{escape(str(value))}</div>'
        "</div>"
    )


def _candidate_row(candidate: dict[str, Any]) -> str:
    return (
        "<tr>"
        f"<td>{escape(_fmt(candidate.get('threshold')))}</td>"
        f"<td>{escape(str(candidate.get('tp', '')))}</td>"
        f"<td>{escape(str(candidate.get('fp', '')))}</td>"
        f"<td>{escape(str(candidate.get('fn', '')))}</td>"
        f"<td>{escape(_fmt(candidate.get('profit')))}</td>"
        "</tr>"
    )


def _fmt(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, int | float):
        return f"{value:.4f}"
    return str(value)
