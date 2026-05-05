from __future__ import annotations

from datetime import UTC, datetime

from fraud_v2.operations.release_runbook import build_release_runbook, write_release_runbook


def test_release_runbook_contains_local_handoff_sections() -> None:
    runbook = build_release_runbook(
        version="0.44.0",
        branch="feature/test",
        latest_commit="abc1234",
        generated_at=datetime(2026, 5, 5, tzinfo=UTC),
    )

    assert "Version: `0.44.0`" in runbook
    assert "Branch: `feature/test`" in runbook
    assert "Required Verification" in runbook
    assert "Recovery Rehearsals" in runbook
    assert "GitHub Handoff" in runbook
    assert "Hard Limits" in runbook


def test_release_runbook_writes_markdown(tmp_path) -> None:  # type: ignore[no-untyped-def]
    version_path = tmp_path / "VERSION"
    output_path = tmp_path / "release-runbook.md"
    version_path.write_text("0.44.0\n", encoding="utf-8")

    runbook = write_release_runbook(
        output_path=output_path,
        version_path=version_path,
        generated_at=datetime(2026, 5, 5, tzinfo=UTC),
    )

    assert output_path.exists()
    assert output_path.read_text(encoding="utf-8") == runbook
    assert "0.44.0" in runbook
