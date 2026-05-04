param(
  [switch]$KeepRunning,
  [int]$TimeoutSeconds = 180
)

$ErrorActionPreference = "Stop"

function Invoke-FraudCompose {
  docker compose -f infra\docker-compose.yml --profile full @args
}

function Wait-Http {
  param(
    [string]$Name,
    [string]$Uri,
    [int]$TimeoutSeconds
  )

  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  do {
    try {
      Invoke-RestMethod -Uri $Uri -TimeoutSec 5 | Out-Null
      Write-Host "$Name ready: $Uri"
      return
    }
    catch {
      Start-Sleep -Seconds 3
    }
  } while ((Get-Date) -lt $deadline)

  throw "$Name did not become ready before timeout: $Uri"
}

Invoke-FraudCompose config --quiet
Invoke-FraudCompose up -d --build

try {
  Wait-Http -Name "API" -Uri "http://127.0.0.1:8000/health/live" -TimeoutSeconds $TimeoutSeconds
  Wait-Http -Name "Prometheus" -Uri "http://127.0.0.1:9090/-/ready" -TimeoutSeconds $TimeoutSeconds
  Wait-Http -Name "Neo4j" -Uri "http://127.0.0.1:7474/" -TimeoutSeconds $TimeoutSeconds
  Invoke-FraudCompose ps
}
finally {
  if (-not $KeepRunning) {
    Invoke-FraudCompose down
  }
}
