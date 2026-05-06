from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from enum import StrEnum
from html import escape
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from fraud_v2.domain.stream import StreamDeadLetter


class StreamHealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"


class StreamHealthSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class StreamHealthThresholds(BaseModel):
    warning_lag: int = Field(default=100, ge=1)
    critical_lag: int = Field(default=1000, ge=1)
    warning_dead_letters: int = Field(default=1, ge=1)
    critical_dead_letters: int = Field(default=10, ge=1)
    warning_failed_batches: int = Field(default=1, ge=1)
    critical_failed_batches: int = Field(default=3, ge=1)


class StreamHealthAlert(BaseModel):
    code: str
    severity: StreamHealthSeverity
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class StreamLagSnapshot(BaseModel):
    source: str
    checked: bool
    topic: str
    group_id: str
    total_lag: int | None = None
    partitions: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


class StreamSupervisionSnapshot(BaseModel):
    source: str
    loaded: bool
    status: str | None = None
    batches_attempted: int = 0
    completed_batches: int = 0
    failed_batches: int = 0
    idle_batches: int = 0
    ingested: int = 0
    dead_lettered: int = 0
    dead_letter_published: int = 0
    dead_letter_publish_failed: int = 0
    last_error: str | None = None


class StreamDeadLetterSnapshot(BaseModel):
    source: str
    sample_count: int
    limit: int
    by_reason: dict[str, int]
    latest_created_at: datetime | None = None


class StreamHealthReport(BaseModel):
    generated_at: datetime
    status: StreamHealthStatus
    health_score: int
    topic: str
    group_id: str
    thresholds: StreamHealthThresholds
    lag: StreamLagSnapshot
    supervision: StreamSupervisionSnapshot
    dead_letters: StreamDeadLetterSnapshot
    alerts: list[StreamHealthAlert]
    output_paths: dict[str, str] = Field(default_factory=dict)


def build_stream_health_report(
    *,
    topic: str,
    group_id: str,
    dead_letters: Sequence[StreamDeadLetter],
    dead_letter_limit: int,
    thresholds: StreamHealthThresholds | None = None,
    lag_payload: Mapping[str, Any] | None = None,
    lag_source: str = "not_checked",
    lag_error: str | None = None,
    supervision_payload: Mapping[str, Any] | None = None,
    supervision_source: str = "not_loaded",
    generated_at: datetime | None = None,
) -> StreamHealthReport:
    active_thresholds = thresholds or StreamHealthThresholds()
    lag = _lag_snapshot(
        topic=topic,
        group_id=group_id,
        source=lag_source,
        payload=lag_payload,
        error=lag_error,
    )
    supervision = _supervision_snapshot(
        source=supervision_source,
        payload=supervision_payload,
    )
    dead_letter_snapshot = _dead_letter_snapshot(
        dead_letters=dead_letters,
        limit=dead_letter_limit,
    )
    alerts = _alerts(
        thresholds=active_thresholds,
        lag=lag,
        supervision=supervision,
        dead_letters=dead_letter_snapshot,
    )
    status = _status(alerts)
    score = _health_score(alerts)
    return StreamHealthReport(
        generated_at=generated_at or datetime.now(UTC),
        status=status,
        health_score=score,
        topic=topic,
        group_id=group_id,
        thresholds=active_thresholds,
        lag=lag,
        supervision=supervision,
        dead_letters=dead_letter_snapshot,
        alerts=alerts,
    )


def load_json_mapping(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object in {path}")
    return payload


def write_stream_health_artifacts(
    report: StreamHealthReport,
    *,
    output_path: Path,
    dashboard_path: Path | None = None,
) -> StreamHealthReport:
    output_paths = {"report": str(output_path)}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_to_write = report.model_copy(update={"output_paths": output_paths})
    if dashboard_path is not None:
        dashboard_path.parent.mkdir(parents=True, exist_ok=True)
        output_paths["dashboard"] = str(dashboard_path)
        report_to_write = report.model_copy(update={"output_paths": output_paths})
        dashboard_path.write_text(_html(report_to_write), encoding="utf-8")
    output_path.write_text(report_to_write.model_dump_json(indent=2), encoding="utf-8")
    return report_to_write


def _lag_snapshot(
    *,
    topic: str,
    group_id: str,
    source: str,
    payload: Mapping[str, Any] | None,
    error: str | None,
) -> StreamLagSnapshot:
    if payload is None:
        return StreamLagSnapshot(
            source=source,
            checked=False,
            topic=topic,
            group_id=group_id,
            error=error,
        )
    partitions = payload.get("partitions", [])
    return StreamLagSnapshot(
        source=source,
        checked=True,
        topic=str(payload.get("topic", topic)),
        group_id=str(payload.get("group_id", group_id)),
        total_lag=_int_or_none(payload.get("total_lag")),
        partitions=[dict(partition) for partition in partitions if isinstance(partition, Mapping)],
        error=error,
    )


def _supervision_snapshot(
    *,
    source: str,
    payload: Mapping[str, Any] | None,
) -> StreamSupervisionSnapshot:
    if payload is None:
        return StreamSupervisionSnapshot(source=source, loaded=False)
    return StreamSupervisionSnapshot(
        source=source,
        loaded=True,
        status=_str_or_none(payload.get("status")),
        batches_attempted=_int_or_zero(payload.get("batches_attempted")),
        completed_batches=_int_or_zero(payload.get("completed_batches")),
        failed_batches=_int_or_zero(payload.get("failed_batches")),
        idle_batches=_int_or_zero(payload.get("idle_batches")),
        ingested=_int_or_zero(payload.get("ingested")),
        dead_lettered=_int_or_zero(payload.get("dead_lettered")),
        dead_letter_published=_int_or_zero(payload.get("dead_letter_published")),
        dead_letter_publish_failed=_int_or_zero(payload.get("dead_letter_publish_failed")),
        last_error=_str_or_none(payload.get("last_error")),
    )


def _dead_letter_snapshot(
    *,
    dead_letters: Sequence[StreamDeadLetter],
    limit: int,
) -> StreamDeadLetterSnapshot:
    by_reason = Counter(dead_letter.reason.value for dead_letter in dead_letters)
    latest_created_at = max((dead_letter.created_at for dead_letter in dead_letters), default=None)
    return StreamDeadLetterSnapshot(
        source="store",
        sample_count=len(dead_letters),
        limit=limit,
        by_reason=dict(sorted(by_reason.items())),
        latest_created_at=latest_created_at,
    )


def _alerts(
    *,
    thresholds: StreamHealthThresholds,
    lag: StreamLagSnapshot,
    supervision: StreamSupervisionSnapshot,
    dead_letters: StreamDeadLetterSnapshot,
) -> list[StreamHealthAlert]:
    alerts: list[StreamHealthAlert] = []
    if lag.error is not None:
        alerts.append(
            StreamHealthAlert(
                code="STREAM_LAG_CHECK_FAILED",
                severity=StreamHealthSeverity.WARNING,
                message="Stream lag could not be checked.",
                details={"error": lag.error},
            )
        )
    elif not lag.checked:
        alerts.append(
            StreamHealthAlert(
                code="STREAM_LAG_NOT_CHECKED",
                severity=StreamHealthSeverity.WARNING,
                message="Stream lag was not checked; use --live-lag or --lag-report-path.",
            )
        )
    elif lag.total_lag is None:
        alerts.append(
            StreamHealthAlert(
                code="STREAM_LAG_UNKNOWN",
                severity=StreamHealthSeverity.WARNING,
                message=(
                    "Stream lag is unknown because at least one partition has no committed offset."
                ),
            )
        )
    elif lag.total_lag >= thresholds.critical_lag:
        alerts.append(
            StreamHealthAlert(
                code="STREAM_LAG_CRITICAL",
                severity=StreamHealthSeverity.CRITICAL,
                message="Stream consumer lag is above the critical threshold.",
                details={"total_lag": lag.total_lag, "threshold": thresholds.critical_lag},
            )
        )
    elif lag.total_lag >= thresholds.warning_lag:
        alerts.append(
            StreamHealthAlert(
                code="STREAM_LAG_WARNING",
                severity=StreamHealthSeverity.WARNING,
                message="Stream consumer lag is above the warning threshold.",
                details={"total_lag": lag.total_lag, "threshold": thresholds.warning_lag},
            )
        )

    if supervision.loaded:
        alerts.extend(_supervision_alerts(thresholds, supervision))

    if dead_letters.sample_count >= thresholds.critical_dead_letters:
        alerts.append(
            StreamHealthAlert(
                code="STREAM_DEAD_LETTERS_CRITICAL",
                severity=StreamHealthSeverity.CRITICAL,
                message="Stored stream dead letters are above the critical threshold.",
                details={
                    "sample_count": dead_letters.sample_count,
                    "threshold": thresholds.critical_dead_letters,
                    "by_reason": dead_letters.by_reason,
                },
            )
        )
    elif dead_letters.sample_count >= thresholds.warning_dead_letters:
        alerts.append(
            StreamHealthAlert(
                code="STREAM_DEAD_LETTERS_WARNING",
                severity=StreamHealthSeverity.WARNING,
                message="Stored stream dead letters need operator review.",
                details={
                    "sample_count": dead_letters.sample_count,
                    "threshold": thresholds.warning_dead_letters,
                    "by_reason": dead_letters.by_reason,
                },
            )
        )

    if not alerts:
        alerts.append(
            StreamHealthAlert(
                code="STREAM_HEALTH_OK",
                severity=StreamHealthSeverity.INFO,
                message="No stream health warnings were detected.",
            )
        )
    return alerts


def _supervision_alerts(
    thresholds: StreamHealthThresholds,
    supervision: StreamSupervisionSnapshot,
) -> list[StreamHealthAlert]:
    alerts: list[StreamHealthAlert] = []
    if supervision.status == "failed":
        alerts.append(
            StreamHealthAlert(
                code="STREAM_SUPERVISOR_FAILED",
                severity=StreamHealthSeverity.CRITICAL,
                message="The last stream supervisor receipt ended in failed status.",
                details={"last_error": supervision.last_error},
            )
        )
    elif supervision.failed_batches >= thresholds.critical_failed_batches:
        alerts.append(
            StreamHealthAlert(
                code="STREAM_SUPERVISOR_FAILURES_CRITICAL",
                severity=StreamHealthSeverity.CRITICAL,
                message="Stream supervisor failed batches are above the critical threshold.",
                details={
                    "failed_batches": supervision.failed_batches,
                    "threshold": thresholds.critical_failed_batches,
                    "last_error": supervision.last_error,
                },
            )
        )
    elif supervision.failed_batches >= thresholds.warning_failed_batches:
        alerts.append(
            StreamHealthAlert(
                code="STREAM_SUPERVISOR_FAILURES_WARNING",
                severity=StreamHealthSeverity.WARNING,
                message="Stream supervisor reported failed batches.",
                details={
                    "failed_batches": supervision.failed_batches,
                    "threshold": thresholds.warning_failed_batches,
                    "last_error": supervision.last_error,
                },
            )
        )

    if supervision.dead_letter_publish_failed > 0:
        alerts.append(
            StreamHealthAlert(
                code="STREAM_DLQ_PUBLISH_FAILED",
                severity=StreamHealthSeverity.CRITICAL,
                message="Stream dead letters failed to publish to the DLQ topic.",
                details={"dead_letter_publish_failed": supervision.dead_letter_publish_failed},
            )
        )
    elif supervision.dead_lettered > 0:
        alerts.append(
            StreamHealthAlert(
                code="STREAM_SUPERVISOR_DEAD_LETTERED",
                severity=StreamHealthSeverity.WARNING,
                message="Stream supervisor recorded dead-lettered messages.",
                details={"dead_lettered": supervision.dead_lettered},
            )
        )
    return alerts


def _status(alerts: Sequence[StreamHealthAlert]) -> StreamHealthStatus:
    if any(alert.severity == StreamHealthSeverity.CRITICAL for alert in alerts):
        return StreamHealthStatus.CRITICAL
    if any(alert.severity == StreamHealthSeverity.WARNING for alert in alerts):
        return StreamHealthStatus.DEGRADED
    return StreamHealthStatus.HEALTHY


def _health_score(alerts: Sequence[StreamHealthAlert]) -> int:
    score = 100
    for alert in alerts:
        if alert.severity == StreamHealthSeverity.CRITICAL:
            score -= 45
        elif alert.severity == StreamHealthSeverity.WARNING:
            score -= 15
    return max(score, 0)


def _int_or_none(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.strip():
        return int(value)
    return None


def _int_or_zero(value: object) -> int:
    parsed = _int_or_none(value)
    return parsed if parsed is not None else 0


def _str_or_none(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _html(report: StreamHealthReport) -> str:
    alerts = "".join(_alert_row(alert) for alert in report.alerts)
    reasons = ", ".join(
        f"{escape(reason)}={count}" for reason, count in report.dead_letters.by_reason.items()
    )
    meta = (
        f"{escape(report.topic)} | {escape(report.group_id)} | "
        f"{escape(report.generated_at.isoformat())}"
    )
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>fraud-v2 stream health</title>
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
      .critical {{ color: #b42318; font-weight: 700; }}
      .warning {{ color: #a15c00; font-weight: 700; }}
      .info {{ color: #1f6feb; font-weight: 700; }}
    </style>
  </head>
  <body>
    <h1>Stream Health</h1>
    <p class="meta">{meta}</p>
    <section class="grid">
      {_metric("Status", report.status.value)}
      {_metric("Health Score", report.health_score)}
      {_metric("Total Lag", _display(report.lag.total_lag))}
      {_metric("Lag Source", report.lag.source)}
      {_metric("Dead Letters", report.dead_letters.sample_count)}
      {_metric("Supervisor Status", _display(report.supervision.status))}
      {_metric("Failed Batches", report.supervision.failed_batches)}
      {_metric("DLQ Publish Failed", report.supervision.dead_letter_publish_failed)}
    </section>
    <h2>Dead Letter Reasons</h2>
    <p>{reasons or "none"}</p>
    <h2>Alerts</h2>
    <table>
      <thead><tr><th>Severity</th><th>Code</th><th>Message</th></tr></thead>
      <tbody>{alerts}</tbody>
    </table>
  </body>
</html>
"""


def _metric(label: str, value: object) -> str:
    return (
        '<div class="metric">'
        f'<div class="label">{escape(label)}</div>'
        f'<div class="value">{escape(str(value))}</div>'
        "</div>"
    )


def _alert_row(alert: StreamHealthAlert) -> str:
    severity = alert.severity.value
    return (
        "<tr>"
        f'<td class="{escape(severity)}">{escape(severity)}</td>'
        f"<td>{escape(alert.code)}</td>"
        f"<td>{escape(alert.message)}</td>"
        "</tr>"
    )


def _display(value: object) -> str:
    if value is None:
        return "n/a"
    return str(value)
