from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class LocalTraceSpan(BaseModel):
    trace_id: str = Field(min_length=1, max_length=120)
    span_name: str = Field(min_length=1, max_length=120)
    started_at: datetime
    ended_at: datetime
    duration_ms: float = Field(ge=0)
    status_code: int | None = None
    attributes: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


def append_local_trace_span(
    *,
    path: Path,
    trace_id: str,
    span_name: str,
    started_at: datetime,
    ended_at: datetime,
    duration_ms: float,
    status_code: int | None = None,
    attributes: dict[str, str | int | float | bool | None] | None = None,
) -> LocalTraceSpan:
    span = LocalTraceSpan(
        trace_id=trace_id,
        span_name=span_name,
        started_at=started_at,
        ended_at=ended_at,
        duration_ms=round(duration_ms, 3),
        status_code=status_code,
        attributes=attributes or {},
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as trace_file:
        trace_file.write(span.model_dump_json())
        trace_file.write("\n")
    return span


def load_local_trace_spans(path: Path) -> list[LocalTraceSpan]:
    if not path.exists():
        return []
    spans: list[LocalTraceSpan] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.lstrip("\ufeff")
        if not line.strip():
            continue
        try:
            spans.append(LocalTraceSpan.model_validate_json(line))
        except ValueError as exc:
            raise ValueError(f"invalid trace JSONL at {path}:{line_number}") from exc
    return spans


def summarize_local_traces(
    *,
    trace_path: Path,
    output_path: Path,
    dashboard_path: Path | None = None,
) -> dict[str, Any]:
    spans = load_local_trace_spans(trace_path)
    durations = sorted(span.duration_ms for span in spans)
    by_span = Counter(span.span_name for span in spans)
    by_status = Counter(str(span.status_code) for span in spans if span.status_code is not None)
    report: dict[str, Any] = {
        "trace_path": str(trace_path),
        "generated_at": datetime.now(UTC).isoformat(),
        "total_spans": len(spans),
        "unique_traces": len({span.trace_id for span in spans}),
        "duration_ms": {
            "min": durations[0] if durations else None,
            "p50": _percentile(durations, 0.50),
            "p95": _percentile(durations, 0.95),
            "max": durations[-1] if durations else None,
        },
        "by_span": dict(sorted(by_span.items())),
        "by_status": dict(sorted(by_status.items())),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if dashboard_path is not None:
        dashboard_path.parent.mkdir(parents=True, exist_ok=True)
        dashboard_path.write_text(_html(report), encoding="utf-8")
        report["dashboard_path"] = str(dashboard_path)
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    index = round((len(values) - 1) * percentile)
    return values[index]


def _html(report: dict[str, Any]) -> str:
    duration = report["duration_ms"]
    span_rows = _rows(report["by_span"].items())
    status_rows = _rows(report["by_status"].items())
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>fraud-v2 local trace report</title>
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
    </style>
  </head>
  <body>
    <h1>Local Trace Report</h1>
    <p class="meta">{escape(str(report["trace_path"]))}</p>
    <section class="grid">
      {_metric("Spans", report["total_spans"])}
      {_metric("Traces", report["unique_traces"])}
      {_metric("P50 ms", _display(duration["p50"]))}
      {_metric("P95 ms", _display(duration["p95"]))}
      {_metric("Max ms", _display(duration["max"]))}
    </section>
    <h2>Spans</h2>
    <table><thead><tr><th>Name</th><th>Count</th></tr></thead><tbody>{span_rows}</tbody></table>
    <h2>Status Codes</h2>
    <table><thead><tr><th>Status</th><th>Count</th></tr></thead><tbody>{status_rows}</tbody></table>
  </body>
</html>
"""


def _rows(items: Iterable[tuple[str, Any]]) -> str:
    return "".join(
        f"<tr><td>{escape(str(key))}</td><td>{escape(str(value))}</td></tr>" for key, value in items
    )


def _metric(label: str, value: object) -> str:
    return (
        '<div class="metric">'
        f'<div class="label">{escape(label)}</div>'
        f'<div class="value">{escape(str(value))}</div>'
        "</div>"
    )


def _display(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)
