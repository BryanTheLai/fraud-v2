from __future__ import annotations

from datetime import UTC, datetime

from fraud_v2.operations.readiness import (
    build_readiness_report,
    render_readiness_html,
    write_readiness_report,
)


def test_readiness_report_contains_capabilities_and_blockers() -> None:
    report = build_readiness_report(
        version="0.45.0",
        generated_at=datetime(2026, 5, 5, tzinfo=UTC),
    )

    assert report["schema_version"] == "fraud-v2-readiness-v1"
    assert report["version"] == "0.45.0"
    assert report["regulated_production_ready"] is False
    assert "SQLite backup/restore" in report["implemented_capabilities"]
    assert "simulation workbench UI and CLI" in report["implemented_capabilities"]
    assert "Instant Cash cockpit" in report["implemented_capabilities"]
    assert "model family benchmark" in report["implemented_capabilities"]
    assert "model feature importance reporting" in report["implemented_capabilities"]
    assert "real verified labels" in report["production_blockers"]
    assert "GitHub CLI authentication" not in report["production_blockers"]
    assert report["summary"]["checks"] == len(report["checks"])


def test_readiness_report_writes_json_and_html(tmp_path) -> None:  # type: ignore[no-untyped-def]
    version_path = tmp_path / "VERSION"
    output_path = tmp_path / "readiness.json"
    dashboard_path = tmp_path / "readiness.html"
    version_path.write_text("0.45.0\n", encoding="utf-8")

    report = write_readiness_report(
        output_path=output_path,
        dashboard_path=dashboard_path,
        version_path=version_path,
        generated_at=datetime(2026, 5, 5, tzinfo=UTC),
    )

    assert output_path.exists()
    assert dashboard_path.exists()
    assert report["artifacts"]["dashboard_path"] == str(dashboard_path)


def test_readiness_html_escapes_report_values() -> None:
    html = render_readiness_html(
        {
            "status": "blocked",
            "version": "<version>",
            "branch": "<branch>",
            "checks": [{"name": "x", "status": "pass", "detail": "<ok>"}],
            "implemented_capabilities": ["<capability>"],
            "production_blockers": ["<blocker>"],
        }
    )

    assert "&lt;version&gt;" in html
    assert "&lt;capability&gt;" in html
