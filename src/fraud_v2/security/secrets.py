from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

SKIP_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "data",
    "node_modules",
}
TEXT_SUFFIXES = {
    "",
    ".cfg",
    ".css",
    ".env",
    ".html",
    ".ini",
    ".json",
    ".jsonl",
    ".md",
    ".ps1",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
KNOWN_LOCAL_VALUES = {
    "dev-token-change-me",
    "fraud-local-password",
    "local-jwt-secret-for-fraud-v2-tests-32b",
    "replace-with-local-only-secret-32b-min",
    "replace-with-local-review-passphrase",
}


@dataclass(frozen=True)
class SecretPattern:
    code: str
    description: str
    regex: re.Pattern[str]
    group: str = "secret"


PATTERNS = [
    SecretPattern(
        code="OPENAI_API_KEY",
        description="OpenAI API key",
        regex=re.compile(r"(?P<secret>sk-[A-Za-z0-9_-]{32,})"),
    ),
    SecretPattern(
        code="AZURE_OPENAI_API_KEY",
        description="Azure/OpenAI-style API key assignment",
        regex=re.compile(
            r"(?i)(?:AZURE_OPENAI_API_KEY|OPENAI_API_KEY)\s*[:=]\s*[\"']?(?P<secret>[A-Za-z0-9_\-]{24,})"
        ),
    ),
    SecretPattern(
        code="GITHUB_TOKEN",
        description="GitHub token",
        regex=re.compile(r"(?P<secret>gh[pousr]_[A-Za-z0-9_]{30,})"),
    ),
    SecretPattern(
        code="AWS_ACCESS_KEY_ID",
        description="AWS access key id",
        regex=re.compile(r"(?P<secret>AKIA[0-9A-Z]{16})"),
    ),
    SecretPattern(
        code="PRIVATE_KEY",
        description="Private key material",
        regex=re.compile(r"(?P<secret>-----BEGIN [A-Z ]*PRIVATE KEY-----)"),
    ),
    SecretPattern(
        code="HIGH_ENTROPY_ASSIGNMENT",
        description="High entropy credential-like assignment",
        regex=re.compile(
            r"(?i)(?:secret|token|password|api[_-]?key)\s*[:=]\s*[\"']?(?P<secret>[A-Za-z0-9+/=_\-]{32,})"
        ),
    ),
]


class SecretFinding(BaseModel):
    path: str
    line: int
    code: str
    description: str
    evidence: str
    masked_secret: str


class SecretScanReport(BaseModel):
    root: str
    scanned_files: int
    findings: list[SecretFinding] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.findings


def scan_secrets(root: Path) -> SecretScanReport:
    scanned_files = 0
    findings: list[SecretFinding] = []
    for path in _candidate_files(root):
        scanned_files += 1
        findings.extend(_scan_file(root=root, path=path))
    return SecretScanReport(root=str(root), scanned_files=scanned_files, findings=findings)


def report_payload(report: SecretScanReport) -> dict[str, Any]:
    return {
        "root": report.root,
        "scanned_files": report.scanned_files,
        "passed": report.passed,
        "findings": [finding.model_dump(mode="json") for finding in report.findings],
    }


def _candidate_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if path.stat().st_size > 2_000_000:
            continue
        files.append(path)
    return sorted(files)


def _scan_file(*, root: Path, path: Path) -> list[SecretFinding]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return []
    findings: list[SecretFinding] = []
    relative_path = str(path.relative_to(root))
    for line_number, line in enumerate(lines, start=1):
        for pattern in PATTERNS:
            for match in pattern.regex.finditer(line):
                secret = match.group(pattern.group).strip().strip("\"'")
                if _is_allowed_local_value(secret):
                    continue
                if pattern.code == "HIGH_ENTROPY_ASSIGNMENT" and _entropy(secret) < 3.5:
                    continue
                findings.append(
                    SecretFinding(
                        path=relative_path,
                        line=line_number,
                        code=pattern.code,
                        description=pattern.description,
                        evidence=_safe_evidence(line),
                        masked_secret=_mask(secret),
                    )
                )
    return findings


def _is_allowed_local_value(secret: str) -> bool:
    if secret in KNOWN_LOCAL_VALUES:
        return True
    lowered = secret.lower()
    return (
        "example" in lowered
        or "placeholder" in lowered
        or "replace-with" in lowered
        or "change-me" in lowered
    )


def _entropy(value: str) -> float:
    if not value:
        return 0.0
    counts = {character: value.count(character) for character in set(value)}
    length = len(value)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


def _safe_evidence(line: str) -> str:
    cleaned = line.strip()
    if len(cleaned) <= 160:
        return cleaned
    return f"{cleaned[:157]}..."


def _mask(secret: str) -> str:
    if len(secret) <= 8:
        return "***"
    return f"{secret[:4]}...{secret[-4:]}"
