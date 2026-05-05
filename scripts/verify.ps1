param(
  [switch]$Full,
  [switch]$SkipDockerBuild,
  [switch]$SkipFullSmoke,
  [int]$TimeoutSeconds = 240
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

function Invoke-VerifyStep {
  param(
    [string]$Name,
    [scriptblock]$Command
  )

  Write-Host ""
  Write-Host ">>> $Name"
  & $Command
  if ($LASTEXITCODE -ne 0) {
    throw "Verification step failed: $Name"
  }
}

Invoke-VerifyStep "ruff format" { uv run ruff format --check . }
Invoke-VerifyStep "ruff check" { uv run ruff check . }
Invoke-VerifyStep "secrets scan" { uv run fraud-v2 secrets-scan --root . }
Invoke-VerifyStep "mypy" { uv run mypy src }
Invoke-VerifyStep "pytest" { uv run pytest -q }
Invoke-VerifyStep "pytest collect" { uv run pytest --collect-only -q }
Invoke-VerifyStep "local doctor" {
  uv run fraud-v2 local-doctor `
    --output-path data\local\local-doctor-smoke.json `
    --dashboard-path data\local\local-doctor-smoke.html
}
Invoke-VerifyStep "readiness report" {
  uv run fraud-v2 readiness-report `
    --output-path data\local\readiness-report-smoke.json `
    --dashboard-path data\local\readiness-report-smoke.html
}
Invoke-VerifyStep "release runbook" {
  uv run fraud-v2 release-runbook --output-path data\local\release-runbook-smoke.md
}
Invoke-VerifyStep "simulation workbench" {
  uv run fraud-v2 simulate-risk `
    --amount 1000 `
    --virtual-camera `
    --one-hop-from-fraud `
    --app-bec-pattern
}
Invoke-VerifyStep "model benchmark" {
  uv run fraud-v2 model-benchmark `
    --events-path data\synthetic\tiny\events.jsonl `
    --output-path data\models\benchmark-report.json
}
Invoke-VerifyStep "capacity profile" {
  uv run fraud-v2 capacity-profile `
    --profile smoke `
    --users 50 `
    --score-users 5 `
    --min-load-events-per-second 0.1 `
    --min-score-decisions-per-second 0.1 `
    --output-dir data\local\ci-capacity `
    --overwrite `
    --fail-on-target-miss
}

if ($Full) {
  Invoke-VerifyStep "docker compose config" {
    docker compose -f infra\docker-compose.yml --profile full config --quiet
  }
  if (-not $SkipDockerBuild) {
    Invoke-VerifyStep "docker build" { docker build -t fraud-v2:local . }
  }
  if (-not $SkipFullSmoke) {
    Invoke-VerifyStep "full smoke" {
      powershell -ExecutionPolicy Bypass -File scripts\full-smoke.ps1 -TimeoutSeconds $TimeoutSeconds
    }
  }
}

Write-Host ""
Write-Host "verification complete"
