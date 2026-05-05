from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fraud_v2.observability.traces import (
    append_local_trace_span,
    load_local_trace_spans,
    summarize_local_traces,
)


def test_append_and_summarize_local_trace_spans(tmp_path) -> None:  # type: ignore[no-untyped-def]
    trace_path = tmp_path / "traces.jsonl"
    started_at = datetime(2026, 5, 5, tzinfo=UTC)

    append_local_trace_span(
        path=trace_path,
        trace_id="trace-001",
        span_name="http.request",
        started_at=started_at,
        ended_at=started_at + timedelta(milliseconds=12),
        duration_ms=12.4,
        status_code=200,
        attributes={"method": "GET", "route": "/health/live"},
    )
    append_local_trace_span(
        path=trace_path,
        trace_id="trace-002",
        span_name="http.request",
        started_at=started_at,
        ended_at=started_at + timedelta(milliseconds=31),
        duration_ms=31.2,
        status_code=500,
        attributes={"method": "POST", "route": "/v1/decisions/score"},
    )

    spans = load_local_trace_spans(trace_path)
    report = summarize_local_traces(
        trace_path=trace_path,
        output_path=tmp_path / "trace-report.json",
        dashboard_path=tmp_path / "trace-report.html",
    )

    assert len(spans) == 2
    assert report["total_spans"] == 2
    assert report["unique_traces"] == 2
    assert report["by_span"] == {"http.request": 2}
    assert report["by_status"] == {"200": 1, "500": 1}
    assert "Local Trace Report" in (tmp_path / "trace-report.html").read_text(encoding="utf-8")


def test_load_local_trace_spans_tolerates_windows_bom(tmp_path) -> None:  # type: ignore[no-untyped-def]
    trace_path = tmp_path / "traces.jsonl"
    trace_path.write_text(
        '\ufeff{"trace_id":"trace-bom","span_name":"http.request",'
        '"started_at":"2026-05-05T00:00:00Z",'
        '"ended_at":"2026-05-05T00:00:00.010Z",'
        '"duration_ms":10.0,"status_code":200,"attributes":{}}\n',
        encoding="utf-8",
    )

    spans = load_local_trace_spans(trace_path)

    assert spans[0].trace_id == "trace-bom"
