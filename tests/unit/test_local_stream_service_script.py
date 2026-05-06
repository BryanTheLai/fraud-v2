from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_local_stream_service_script_runs_supervisor_and_health() -> None:
    script = (ROOT / "scripts" / "local-stream-service.ps1").read_text(encoding="utf-8")

    assert "param(" in script
    assert "[switch]$DryRun" in script
    assert "stream-supervise" in script
    assert "--output-path" in script
    assert "stream-health" in script
    assert "--supervision-report-path" in script
    assert "stream service iteration complete" in script


def test_local_stream_service_script_supports_lag_and_dlq_options() -> None:
    script = (ROOT / "scripts" / "local-stream-service.ps1").read_text(encoding="utf-8")

    assert "[switch]$CheckLag" in script
    assert "stream-lag" in script
    assert "--lag-report-path" in script
    assert "[switch]$PublishDeadLetters" in script
    assert "--publish-dead-letters" in script
    assert "--dead-letter-topic" in script
