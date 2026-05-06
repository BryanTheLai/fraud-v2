from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

from fraud_v2.synthetic.generator import DEFAULT_SYNTHETIC_USERS


def write_release_runbook(
    *,
    output_path: Path,
    version_path: Path = Path("VERSION"),
    generated_at: datetime | None = None,
) -> str:
    version = version_path.read_text(encoding="utf-8").strip()
    branch = _git(["branch", "--show-current"]) or "unknown"
    latest_commit = _git(["rev-parse", "--short", "HEAD"]) or "unknown"
    runbook = build_release_runbook(
        version=version,
        branch=branch,
        latest_commit=latest_commit,
        generated_at=generated_at or datetime.now(UTC),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(runbook, encoding="utf-8")
    return runbook


def build_release_runbook(
    *,
    version: str,
    branch: str,
    latest_commit: str,
    generated_at: datetime,
) -> str:
    return f"""# Fraud V2 Local Release Runbook

Generated: {generated_at.isoformat()}

## Release

- Version: `{version}`
- Branch: `{branch}`
- Latest commit: `{latest_commit}`
- Boundary: local synthetic fraud lab, not regulated production

## Local Lite Mode

```powershell
uv sync --extra dev
uv run fraud-v2 generate `
  --users {DEFAULT_SYNTHETIC_USERS} `
  --output data\\synthetic\\tiny\\events.jsonl
uv run fraud-v2 load data\\synthetic\\tiny\\events.jsonl --db-path data\\local\\fraud_v2.sqlite
uv run fraud-v2 score user_00000 --db-path data\\local\\fraud_v2.sqlite
uv run uvicorn fraud_v2.api.main:app --host 127.0.0.1 --port 8000
```

## Full Docker Mode

```powershell
docker compose -f infra\\docker-compose.yml --profile full up -d --build
powershell -ExecutionPolicy Bypass -File scripts\\full-smoke.ps1 -TimeoutSeconds 240
```

## Required Verification

```powershell
uv run ruff format --check .
uv run ruff check .
uv run fraud-v2 secrets-scan --root .
uv run mypy src
uv run pytest -q
uv run fraud-v2 capacity-profile `
  --profile smoke `
  --users 50 `
  --score-users 5 `
  --min-load-events-per-second 0.1 `
  --min-score-decisions-per-second 0.1 `
  --output-dir data\\local\\ci-capacity `
  --overwrite `
  --fail-on-target-miss
docker compose -f infra\\docker-compose.yml --profile full config --quiet
docker build -t fraud-v2:local .
powershell -ExecutionPolicy Bypass -File scripts\\full-smoke.ps1 -TimeoutSeconds 240
```

## Recovery Rehearsals

```powershell
uv run fraud-v2 sqlite-backup `
  --db-path data\\local\\fraud_v2.sqlite `
  --output-dir data\\local\\backups\\sqlite
uv run fraud-v2 sqlite-restore `
  data\\local\\backups\\sqlite\\fraud_v2.sqlite.bak `
  --restore-path data\\local\\fraud_v2-restored.sqlite
powershell -ExecutionPolicy Bypass -File scripts\\postgres-backup-rehearsal.ps1
```

## GitHub Handoff

```powershell
powershell -ExecutionPolicy Bypass -File scripts\\github-handoff.ps1
gh auth login
git remote add origin <repo-url>
powershell -ExecutionPolicy Bypass -File scripts\\github-handoff.ps1 -Execute
```

## Hard Limits

- Synthetic data only unless explicit governance approves real redacted data.
- Mock KYC, banking, liveness, consortium, SAR, and payment vendor boundaries only.
- No real compliance filings.
- No real production deployment target yet.
- No cloud backups, KMS/HSM, WORM storage, PITR, on-call routing, or managed stream monitor.
"""


def _git(args: list[str]) -> str | None:
    result = subprocess.run(
        ["git", *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()
