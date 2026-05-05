from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_verify_script_runs_core_gate_and_optional_full_smoke() -> None:
    script = (ROOT / "scripts" / "verify.ps1").read_text(encoding="utf-8")

    assert "[switch]$Full" in script
    assert "uv run ruff format --check ." in script
    assert "uv run ruff check ." in script
    assert "uv run fraud-v2 secrets-scan --root ." in script
    assert "uv run mypy src" in script
    assert "uv run pytest -q" in script
    assert "uv run fraud-v2 local-doctor" in script
    assert "uv run fraud-v2 readiness-report" in script
    assert "uv run fraud-v2 capacity-profile" in script
    assert "docker build -t fraud-v2:local ." in script
    assert "scripts\\full-smoke.ps1" in script


def test_clean_local_script_is_repo_scoped_and_keeps_venv_by_default() -> None:
    script = (ROOT / "scripts" / "clean-local.ps1").read_text(encoding="utf-8")

    assert "[switch]$DryRun" in script
    assert "[switch]$IncludeVenv" in script
    assert "[switch]$IncludePublicData" in script
    assert "[switch]$Strict" in script
    assert "Refusing to remove repo root" in script
    assert "$RepoPrefix" in script
    assert "StartsWith($RepoPrefix" in script
    assert "data\\local" in script
    assert "if ($IncludePublicData)" in script
    assert "__pycache__" in script
    assert "Remove-Item -LiteralPath $fullPath -Recurse -Force" in script
    assert "Remove-DirectoryBestEffort" in script
    assert "Sort-Object { $_.FullName.Length } -Descending" in script
    assert "skipped locked or unavailable path" in script
    assert "if ($IncludeVenv)" in script


def test_test_script_delegates_to_verify_script() -> None:
    script = (ROOT / "scripts" / "test.ps1").read_text(encoding="utf-8")

    assert "verify.ps1" in script
    assert "powershell -ExecutionPolicy Bypass -File $verify" in script
