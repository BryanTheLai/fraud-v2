from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

from fraud_v2 import __version__

GIB = 1024**3


@dataclass(frozen=True)
class CommandProbe:
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    category: str
    status: str
    detail: str
    required_for: list[str]
    remediation: str


CommandRunner = Callable[[list[str]], CommandProbe]
CommandFinder = Callable[[str], str | None]


REQUIRED_REPO_FILES = [
    Path("AGENTS.md"),
    Path("startup/PROMPT.md"),
    Path("pyproject.toml"),
    Path("README.md"),
]


def write_local_doctor_report(
    *,
    output_path: Path,
    dashboard_path: Path | None = None,
    generated_at: datetime | None = None,
    root_path: Path = Path("."),
    command_runner: CommandRunner | None = None,
    command_finder: CommandFinder | None = None,
    disk_free_bytes: int | None = None,
    memory_total_bytes: int | None = None,
) -> dict[str, Any]:
    report = build_local_doctor_report(
        generated_at=generated_at or datetime.now(UTC),
        root_path=root_path,
        command_runner=command_runner or _run_command,
        command_finder=command_finder or shutil.which,
        disk_free_bytes=disk_free_bytes,
        memory_total_bytes=memory_total_bytes,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    if dashboard_path is not None:
        dashboard_path.parent.mkdir(parents=True, exist_ok=True)
        dashboard_path.write_text(render_local_doctor_html(report), encoding="utf-8")
        report["artifacts"]["dashboard_path"] = str(dashboard_path)
        output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def build_local_doctor_report(
    *,
    generated_at: datetime,
    root_path: Path = Path("."),
    command_runner: CommandRunner | None = None,
    command_finder: CommandFinder | None = None,
    disk_free_bytes: int | None = None,
    memory_total_bytes: int | None = None,
) -> dict[str, Any]:
    root_path = root_path.resolve()
    resolved_runner = command_runner or _run_command
    resolved_finder = command_finder or shutil.which
    checks = [
        _python_check(),
        _package_check(),
        _repo_files_check(root_path),
        _disk_check(root_path, disk_free_bytes=disk_free_bytes),
        _memory_check(memory_total_bytes=memory_total_bytes),
        _tool_check("uv", ["lite", "full"], command_finder=resolved_finder),
        _tool_check("git", ["lite", "github"], command_finder=resolved_finder),
        _docker_check(command_runner=resolved_runner, command_finder=resolved_finder),
        _docker_compose_check(command_runner=resolved_runner, command_finder=resolved_finder),
        _path_check("docker_compose_file", root_path / "infra/docker-compose.yml", ["full"]),
        _path_check("full_smoke_script", root_path / "scripts/full-smoke.ps1", ["full"]),
        _gpu_check(command_runner=resolved_runner, command_finder=resolved_finder),
        _tool_check("gh", ["github"], command_finder=resolved_finder),
        _origin_remote_check(command_runner=resolved_runner),
        _gh_auth_check(command_runner=resolved_runner, command_finder=resolved_finder),
        _path_check("github_handoff_script", root_path / "scripts/github-handoff.ps1", ["github"]),
    ]
    lite_ready = _scope_ready(checks, "lite")
    full_profile_ready = lite_ready and _scope_ready(checks, "full")
    github_handoff_ready = _scope_ready(checks, "github")
    warning_count = sum(1 for check in checks if check.status == "warn")
    blocked_count = sum(1 for check in checks if check.status == "blocked")
    if not lite_ready:
        status = "blocked"
    elif not full_profile_ready or not github_handoff_ready or warning_count:
        status = "warn"
    else:
        status = "ready"

    return {
        "schema_version": "fraud-v2-local-doctor-v1",
        "generated_at": generated_at.isoformat(),
        "version": __version__,
        "status": status,
        "lite_ready": lite_ready,
        "full_profile_ready": full_profile_ready,
        "github_handoff_ready": github_handoff_ready,
        "gpu_required": False,
        "production_claim": False,
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python": platform.python_version(),
        },
        "checks": [asdict(check) for check in checks],
        "summary": {
            "checks": len(checks),
            "blocked": blocked_count,
            "warnings": warning_count,
            "passed": sum(1 for check in checks if check.status == "pass"),
        },
        "artifacts": {},
    }


def render_local_doctor_html(report: dict[str, Any]) -> str:
    check_rows = [
        _row(
            check["name"],
            check["category"],
            check["status"],
            ", ".join(check["required_for"]),
            check["detail"],
            check["remediation"],
        )
        for check in report["checks"]
    ]
    rows = "\n".join(check_rows)
    status = escape(str(report["status"]))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Fraud V2 Local Doctor</title>
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
  <h1>Fraud V2 Local Doctor</h1>
  <p>Status: <strong class="{status}">{status}</strong></p>
  <p>Version: {escape(str(report["version"]))}</p>
  <p>Lite ready: {escape(str(report["lite_ready"]))} |
     Full profile ready: {escape(str(report["full_profile_ready"]))} |
     GitHub handoff ready: {escape(str(report["github_handoff_ready"]))}</p>
  <h2>Checks</h2>
  <table>
    <tr>
      <th>Name</th><th>Category</th><th>Status</th><th>Scope</th>
      <th>Detail</th><th>Remediation</th>
    </tr>
    {rows}
  </table>
  <p>GPU is optional. This report is a local runability check, not a regulated
     production readiness claim.</p>
</body>
</html>
"""


def _row(
    name: str,
    category: str,
    status: str,
    required_for: str,
    detail: str,
    remediation: str,
) -> str:
    return (
        "<tr>"
        f"<td>{escape(name)}</td>"
        f"<td>{escape(category)}</td>"
        f'<td class="{escape(status)}">{escape(status)}</td>'
        f"<td>{escape(required_for)}</td>"
        f"<td>{escape(detail)}</td>"
        f"<td>{escape(remediation)}</td>"
        "</tr>"
    )


def _python_check() -> DoctorCheck:
    version = sys.version_info
    status = "pass" if version >= (3, 12) else "blocked"
    return DoctorCheck(
        name="python_version",
        category="runtime",
        status=status,
        detail=f"Python {platform.python_version()} at {sys.executable}",
        required_for=["lite", "full"],
        remediation="Install Python 3.12 or newer.",
    )


def _package_check() -> DoctorCheck:
    return DoctorCheck(
        name="fraud_v2_package",
        category="runtime",
        status="pass",
        detail=f"fraud-v2 package import succeeded at version {__version__}",
        required_for=["lite", "full"],
        remediation="Run `uv sync --extra dev --extra infra --extra llm`.",
    )


def _repo_files_check(root_path: Path) -> DoctorCheck:
    missing = [str(path) for path in REQUIRED_REPO_FILES if not (root_path / path).exists()]
    return DoctorCheck(
        name="repo_contract_files",
        category="repo",
        status="pass" if not missing else "blocked",
        detail="all required repo contract files exist"
        if not missing
        else f"missing: {', '.join(missing)}",
        required_for=["lite", "full"],
        remediation="Run from the fraud-v2 repo root.",
    )


def _disk_check(root_path: Path, *, disk_free_bytes: int | None) -> DoctorCheck:
    free = disk_free_bytes if disk_free_bytes is not None else shutil.disk_usage(root_path).free
    free_gib = free / GIB
    if free_gib >= 10:
        status = "pass"
    elif free_gib >= 2:
        status = "warn"
    else:
        status = "blocked"
    return DoctorCheck(
        name="disk_free",
        category="hardware",
        status=status,
        detail=f"{free_gib:.1f} GiB free at {root_path}",
        required_for=["lite", "full"],
        remediation="Keep at least 10 GiB free for Docker images and smoke artifacts.",
    )


def _memory_check(*, memory_total_bytes: int | None) -> DoctorCheck:
    total = memory_total_bytes if memory_total_bytes is not None else _total_memory_bytes()
    if total is None:
        return DoctorCheck(
            name="system_memory",
            category="hardware",
            status="warn",
            detail="total system memory could not be detected",
            required_for=["lite", "full"],
            remediation="Use at least 8 GiB RAM for full-profile Docker runs.",
        )
    total_gib = total / GIB
    if total_gib >= 8:
        status = "pass"
    elif total_gib >= 4:
        status = "warn"
    else:
        status = "blocked"
    return DoctorCheck(
        name="system_memory",
        category="hardware",
        status=status,
        detail=f"{total_gib:.1f} GiB RAM detected",
        required_for=["lite", "full"],
        remediation="Use at least 8 GiB RAM for full-profile Docker runs.",
    )


def _tool_check(
    tool: str,
    required_for: list[str],
    *,
    command_finder: CommandFinder,
) -> DoctorCheck:
    path = command_finder(tool)
    return DoctorCheck(
        name=f"{tool}_command",
        category="tooling",
        status="pass" if path else "blocked",
        detail=path or f"{tool} was not found on PATH",
        required_for=required_for,
        remediation=f"Install {tool} and make sure it is available on PATH.",
    )


def _docker_check(*, command_runner: CommandRunner, command_finder: CommandFinder) -> DoctorCheck:
    if not command_finder("docker"):
        return DoctorCheck(
            name="docker_engine",
            category="tooling",
            status="blocked",
            detail="docker was not found on PATH",
            required_for=["full"],
            remediation="Install Docker Desktop and start the Docker engine.",
        )
    result = command_runner(["docker", "info", "--format", "{{json .ServerVersion}}"])
    return DoctorCheck(
        name="docker_engine",
        category="tooling",
        status="pass" if result.returncode == 0 else "blocked",
        detail=result.stdout.strip() or result.stderr.strip() or "docker info returned no output",
        required_for=["full"],
        remediation="Start Docker Desktop, then rerun the doctor.",
    )


def _docker_compose_check(
    *,
    command_runner: CommandRunner,
    command_finder: CommandFinder,
) -> DoctorCheck:
    if not command_finder("docker"):
        return DoctorCheck(
            name="docker_compose",
            category="tooling",
            status="blocked",
            detail="docker was not found on PATH",
            required_for=["full"],
            remediation="Install Docker Desktop with Compose v2.",
        )
    result = command_runner(["docker", "compose", "version"])
    return DoctorCheck(
        name="docker_compose",
        category="tooling",
        status="pass" if result.returncode == 0 else "blocked",
        detail=result.stdout.strip()
        or result.stderr.strip()
        or "docker compose returned no output",
        required_for=["full"],
        remediation="Install or repair Docker Compose v2.",
    )


def _gpu_check(*, command_runner: CommandRunner, command_finder: CommandFinder) -> DoctorCheck:
    if not command_finder("nvidia-smi"):
        return DoctorCheck(
            name="nvidia_gpu",
            category="optional_gpu",
            status="warn",
            detail="nvidia-smi was not found; CPU mode is supported",
            required_for=["optional_gpu"],
            remediation="Install NVIDIA drivers/CUDA only if you want GPU experiments.",
        )
    result = command_runner(
        [
            "nvidia-smi",
            "--query-gpu=name,memory.total,driver_version",
            "--format=csv,noheader",
        ]
    )
    return DoctorCheck(
        name="nvidia_gpu",
        category="optional_gpu",
        status="pass" if result.returncode == 0 else "warn",
        detail=result.stdout.strip() or result.stderr.strip() or "nvidia-smi returned no GPU rows",
        required_for=["optional_gpu"],
        remediation="GPU is optional; repair NVIDIA drivers only for GPU experiments.",
    )


def _origin_remote_check(*, command_runner: CommandRunner) -> DoctorCheck:
    result = command_runner(["git", "remote", "get-url", "origin"])
    return DoctorCheck(
        name="origin_remote",
        category="github",
        status="pass" if result.returncode == 0 and result.stdout.strip() else "blocked",
        detail=result.stdout.strip() or result.stderr.strip() or "origin remote is not configured",
        required_for=["github"],
        remediation="Run `git remote add origin <repo-url>`.",
    )


def _gh_auth_check(
    *,
    command_runner: CommandRunner,
    command_finder: CommandFinder,
) -> DoctorCheck:
    if not command_finder("gh"):
        return DoctorCheck(
            name="github_auth",
            category="github",
            status="blocked",
            detail="gh was not found on PATH",
            required_for=["github"],
            remediation="Install GitHub CLI, then run `gh auth login`.",
        )
    result = command_runner(["gh", "auth", "status"])
    return DoctorCheck(
        name="github_auth",
        category="github",
        status="pass" if result.returncode == 0 else "blocked",
        detail=result.stdout.strip() or result.stderr.strip() or "gh auth status failed",
        required_for=["github"],
        remediation="Run `gh auth login`.",
    )


def _path_check(name: str, path: Path, required_for: list[str]) -> DoctorCheck:
    return DoctorCheck(
        name=name,
        category="repo",
        status="pass" if path.exists() else "blocked",
        detail=str(path) if path.exists() else f"missing {path}",
        required_for=required_for,
        remediation="Restore the missing repo file.",
    )


def _scope_ready(checks: list[DoctorCheck], scope: str) -> bool:
    return not any(check.status == "blocked" and scope in check.required_for for check in checks)


def _run_command(command: list[str]) -> CommandProbe:
    try:
        result = subprocess.run(command, capture_output=True, check=False, text=True, timeout=12)
    except FileNotFoundError as exc:
        return CommandProbe(returncode=127, stdout="", stderr=str(exc))
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return CommandProbe(returncode=124, stdout=stdout, stderr=stderr or "command timed out")
    return CommandProbe(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)


def _total_memory_bytes() -> int | None:
    if platform.system() == "Windows":
        return _windows_total_memory_bytes()
    page_size = getattr(os, "sysconf", lambda _name: None)("SC_PAGE_SIZE")
    page_count = getattr(os, "sysconf", lambda _name: None)("SC_PHYS_PAGES")
    if isinstance(page_size, int) and isinstance(page_count, int):
        return page_size * page_count
    return None


def _windows_total_memory_bytes() -> int | None:
    try:
        import ctypes
        from ctypes import wintypes
    except ImportError:
        return None

    class MemoryStatusEx(ctypes.Structure):
        _fields_ = [
            ("dwLength", wintypes.DWORD),
            ("dwMemoryLoad", wintypes.DWORD),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    memory_status = MemoryStatusEx()
    memory_status.dwLength = ctypes.sizeof(MemoryStatusEx)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory_status)):
        return None
    return int(memory_status.ullTotalPhys)
