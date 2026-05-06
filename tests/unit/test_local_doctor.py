from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fraud_v2.operations.local_doctor import (
    CommandProbe,
    build_local_doctor_report,
    render_local_doctor_html,
    write_local_doctor_report,
)


def test_local_doctor_marks_gpu_optional_and_scopes_github_blockers(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _write_required_repo_files(tmp_path)

    report = build_local_doctor_report(
        generated_at=datetime(2026, 5, 5, tzinfo=UTC),
        root_path=tmp_path,
        command_runner=_fake_runner,
        command_finder=_fake_finder_without_gpu,
        disk_free_bytes=20 * 1024**3,
        memory_total_bytes=16 * 1024**3,
    )

    assert report["schema_version"] == "fraud-v2-local-doctor-v1"
    assert report["lite_ready"] is True
    assert report["full_profile_ready"] is True
    assert report["github_handoff_ready"] is True
    assert report["production_claim"] is False
    gpu_check = _check(report, "nvidia_gpu")
    assert gpu_check["status"] == "warn"
    assert gpu_check["required_for"] == ["optional_gpu"]


def test_local_doctor_blocks_full_profile_when_docker_engine_fails(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _write_required_repo_files(tmp_path)

    def runner(command: list[str]) -> CommandProbe:
        if command[:2] == ["docker", "info"]:
            return CommandProbe(1, "", "Docker engine is not running")
        return _fake_runner(command)

    report = build_local_doctor_report(
        generated_at=datetime(2026, 5, 5, tzinfo=UTC),
        root_path=tmp_path,
        command_runner=runner,
        command_finder=_fake_finder_without_gpu,
        disk_free_bytes=20 * 1024**3,
        memory_total_bytes=16 * 1024**3,
    )

    assert report["lite_ready"] is True
    assert report["full_profile_ready"] is False
    assert _check(report, "docker_engine")["status"] == "blocked"


def test_local_doctor_writes_json_and_html(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _write_required_repo_files(tmp_path)
    output_path = tmp_path / "doctor.json"
    dashboard_path = tmp_path / "doctor.html"

    report = write_local_doctor_report(
        output_path=output_path,
        dashboard_path=dashboard_path,
        root_path=tmp_path,
        generated_at=datetime(2026, 5, 5, tzinfo=UTC),
        command_runner=_fake_runner,
        command_finder=_fake_finder_without_gpu,
        disk_free_bytes=20 * 1024**3,
        memory_total_bytes=16 * 1024**3,
    )

    assert output_path.exists()
    assert dashboard_path.exists()
    assert report["artifacts"]["dashboard_path"] == str(dashboard_path)


def test_local_doctor_html_escapes_report_values() -> None:
    html = render_local_doctor_html(
        {
            "status": "warn",
            "version": "<version>",
            "lite_ready": True,
            "full_profile_ready": False,
            "github_handoff_ready": False,
            "checks": [
                {
                    "name": "<name>",
                    "category": "repo",
                    "status": "pass",
                    "required_for": ["lite"],
                    "detail": "<detail>",
                    "remediation": "<fix>",
                }
            ],
        }
    )

    assert "&lt;version&gt;" in html
    assert "&lt;detail&gt;" in html


def _check(report: dict, name: str) -> dict:  # type: ignore[type-arg]
    return next(check for check in report["checks"] if check["name"] == name)


def _write_required_repo_files(root: Path) -> None:
    for path in [
        "AGENTS.md",
        "startup/PROMPT.md",
        "pyproject.toml",
        "README.md",
        "infra/docker-compose.yml",
        "scripts/full-smoke.ps1",
        "scripts/github-handoff.ps1",
    ]:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("placeholder", encoding="utf-8")


def _fake_finder_without_gpu(command: str) -> str | None:
    if command == "nvidia-smi":
        return None
    return f"C:\\fake\\{command}.exe"


def _fake_runner(command: list[str]) -> CommandProbe:
    if command[:3] == ["docker", "info", "--format"]:
        return CommandProbe(0, "26.1.1", "")
    if command[:3] == ["docker", "compose", "version"]:
        return CommandProbe(0, "Docker Compose version v2.29.0", "")
    if command[:4] == ["git", "remote", "get-url", "origin"]:
        return CommandProbe(0, "https://github.com/example/fraud-v2.git", "")
    if command[:3] == ["gh", "auth", "status"]:
        return CommandProbe(0, "Logged in to github.com", "")
    return CommandProbe(0, "", "")
