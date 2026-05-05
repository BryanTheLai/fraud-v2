from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ReadinessCheck:
    name: str
    status: str
    detail: str


IMPLEMENTED_CAPABILITIES = [
    "domain contracts",
    "synthetic data",
    "SQLite lite storage",
    "SQLite backup/restore",
    "Postgres full-profile storage",
    "Postgres backup rehearsal",
    "rules and graph decisions",
    "analyst review workflow",
    "compliance drafts",
    "encrypted evidence export",
    "model registry and shadow scoring",
    "model feature importance reporting",
    "MLOps drift and analyst Kappa report",
    "signal lab for metadata and public-KYB-style checks",
    "simulation workbench UI and CLI",
    "Break-the-Spell intervention drafts",
    "capacity profile receipts",
    "stream ingestion and supervision",
    "stream health and DLQ proof",
    "audit hash chain and archive",
    "secrets scan",
    "GitHub handoff script",
    "release runbook",
    "local doctor",
    "verification and cleanup scripts",
]

PRODUCTION_BLOCKERS = [
    "real fraud wedge and action authority",
    "real verified labels",
    "vendor and legal approvals",
    "real PII security design",
    "production deployment target",
    "real traffic SLO and capacity model",
    "GitHub CLI authentication",
]


def write_readiness_report(
    *,
    output_path: Path,
    dashboard_path: Path | None = None,
    version_path: Path = Path("VERSION"),
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    report = build_readiness_report(
        version=version_path.read_text(encoding="utf-8").strip(),
        generated_at=generated_at or datetime.now(UTC),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    if dashboard_path is not None:
        dashboard_path.parent.mkdir(parents=True, exist_ok=True)
        dashboard_path.write_text(render_readiness_html(report), encoding="utf-8")
        report["artifacts"]["dashboard_path"] = str(dashboard_path)
        output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def build_readiness_report(*, version: str, generated_at: datetime) -> dict[str, Any]:
    branch = _git(["branch", "--show-current"]) or "unknown"
    latest_commit = _git(["rev-parse", "--short", "HEAD"]) or "unknown"
    dirty = bool(_git(["status", "--porcelain"]))
    remote_url = _git(["remote", "get-url", "origin"])
    gh_auth = _command_succeeds(["gh", "auth", "status"])
    checks = [
        ReadinessCheck(
            "worktree_clean",
            "pass" if not dirty else "warn",
            "clean" if not dirty else "uncommitted local changes exist",
        ),
        ReadinessCheck(
            "origin_remote",
            "pass" if remote_url else "blocked",
            remote_url or "origin remote is not configured",
        ),
        ReadinessCheck(
            "github_auth",
            "pass" if gh_auth else "blocked",
            "gh auth status succeeded" if gh_auth else "gh auth status failed",
        ),
        _file_check("pr_draft", Path(".github/PULL_REQUEST_DRAFT.md")),
        _file_check("release_runbook_cli", Path("src/fraud_v2/operations/release_runbook.py")),
        _file_check("full_smoke", Path("scripts/full-smoke.ps1")),
        _file_check("github_handoff", Path("scripts/github-handoff.ps1")),
        _file_check("postgres_backup_rehearsal", Path("scripts/postgres-backup-rehearsal.ps1")),
    ]
    blocker_count = sum(1 for check in checks if check.status == "blocked")
    warning_count = sum(1 for check in checks if check.status == "warn")
    status = "blocked" if blocker_count else "warn" if warning_count else "ready"
    return {
        "schema_version": "fraud-v2-readiness-v1",
        "generated_at": generated_at.isoformat(),
        "version": version,
        "branch": branch,
        "latest_commit": latest_commit,
        "status": status,
        "local_product_ready": blocker_count == 0
        or all(
            check.name in {"origin_remote", "github_auth"} or check.status == "pass"
            for check in checks
        ),
        "regulated_production_ready": False,
        "implemented_capabilities": IMPLEMENTED_CAPABILITIES,
        "production_blockers": PRODUCTION_BLOCKERS,
        "checks": [asdict(check) for check in checks],
        "summary": {
            "checks": len(checks),
            "blocked": blocker_count,
            "warnings": warning_count,
            "implemented_capabilities": len(IMPLEMENTED_CAPABILITIES),
            "production_blockers": len(PRODUCTION_BLOCKERS),
        },
        "artifacts": {},
    }


def render_readiness_html(report: dict[str, Any]) -> str:
    check_rows = [
        _row(check["name"], check["status"], check["detail"]) for check in report["checks"]
    ]
    checks = "\n".join(check_rows)
    capabilities = "\n".join(
        f"<li>{escape(capability)}</li>" for capability in report["implemented_capabilities"]
    )
    blockers = "\n".join(f"<li>{escape(blocker)}</li>" for blocker in report["production_blockers"])
    status = escape(str(report["status"]))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Fraud V2 Readiness</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #111827; }}
    h1, h2 {{ margin-bottom: 8px; }}
    table {{ border-collapse: collapse; width: 100%; margin: 16px 0 28px; }}
    th, td {{ border: 1px solid #d1d5db; padding: 8px; text-align: left; }}
    th {{ background: #f3f4f6; }}
    .pass {{ color: #166534; }}
    .warn {{ color: #9a3412; }}
    .blocked {{ color: #991b1b; }}
  </style>
</head>
<body>
  <h1>Fraud V2 Readiness</h1>
  <p>Status: <strong class="{status}">{status}</strong></p>
  <p>Version: {escape(str(report["version"]))} | Branch: {escape(str(report["branch"]))}</p>
  <h2>Checks</h2>
  <table>
    <tr><th>Name</th><th>Status</th><th>Detail</th></tr>
    {checks}
  </table>
  <h2>Implemented Capabilities</h2>
  <ul>{capabilities}</ul>
  <h2>Production Blockers</h2>
  <ul>{blockers}</ul>
  <p>Local synthetic lab readiness is not regulated production readiness.</p>
</body>
</html>
"""


def _row(name: str, status: str, detail: str) -> str:
    return (
        "<tr>"
        f"<td>{escape(name)}</td>"
        f'<td class="{escape(status)}">{escape(status)}</td>'
        f"<td>{escape(detail)}</td>"
        "</tr>"
    )


def _file_check(name: str, path: Path) -> ReadinessCheck:
    return ReadinessCheck(
        name=name,
        status="pass" if path.exists() else "blocked",
        detail=str(path) if path.exists() else f"missing {path}",
    )


def _git(args: list[str]) -> str | None:
    result = subprocess.run(["git", *args], check=False, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def _command_succeeds(command: list[str]) -> bool:
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    return result.returncode == 0
