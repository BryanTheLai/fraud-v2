param(
  [switch]$KeepRunning,
  [int]$TimeoutSeconds = 180,
  [int]$ApiPort = 18000,
  [int]$PostgresPort = 15432,
  [int]$RedisPort = 16379,
  [int]$RedpandaPort = 19092,
  [int]$RedpandaAdminPort = 19644,
  [int]$Neo4jHttpPort = 17474,
  [int]$Neo4jBoltPort = 17687,
  [int]$PrometheusPort = 19090,
  [int]$GrafanaPort = 13000,
  [string]$ComposeProject = "fraud-v2-smoke"
)

$ErrorActionPreference = "Stop"

$env:FRAUD_API_PORT = "$ApiPort"
$env:FRAUD_POSTGRES_PORT = "$PostgresPort"
$env:FRAUD_REDIS_PORT = "$RedisPort"
$env:FRAUD_REDPANDA_PORT = "$RedpandaPort"
$env:FRAUD_REDPANDA_ADMIN_PORT = "$RedpandaAdminPort"
$env:FRAUD_NEO4J_HTTP_PORT = "$Neo4jHttpPort"
$env:FRAUD_NEO4J_BOLT_PORT = "$Neo4jBoltPort"
$env:FRAUD_PROMETHEUS_PORT = "$PrometheusPort"
$env:FRAUD_GRAFANA_PORT = "$GrafanaPort"

$ApiBase = "http://127.0.0.1:$ApiPort"
$PrometheusBase = "http://127.0.0.1:$PrometheusPort"
$GrafanaBase = "http://127.0.0.1:$GrafanaPort"
$Neo4jBase = "http://127.0.0.1:$Neo4jHttpPort"

function Invoke-FraudCompose {
  docker compose -p $ComposeProject -f infra\docker-compose.yml --profile full @args
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

function Assert-FraudCondition {
  param(
    [bool]$Condition,
    [string]$Message
  )

  if (-not $Condition) {
    throw $Message
  }
}

function Invoke-FraudApi {
  param(
    [string]$Method,
    [string]$Uri,
    [object]$Body = $null
  )

  $headers = @{ Authorization = "Bearer dev-token-change-me" }
  $parameters = @{
    Method = $Method
    Uri = $Uri
    Headers = $headers
    TimeoutSec = 10
  }
  if ($null -ne $Body) {
    $parameters.Body = ($Body | ConvertTo-Json -Depth 10)
    $parameters.ContentType = "application/json"
  }

  Invoke-RestMethod @parameters
}

function Wait-PrometheusQuery {
  param(
    [string]$Query,
    [int]$TimeoutSeconds
  )

  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  $encoded = [System.Uri]::EscapeDataString($Query)
  $uri = "$PrometheusBase/api/v1/query?query=$encoded"
  do {
    try {
      $result = Invoke-RestMethod -Uri $uri -TimeoutSec 5
      if ($result.status -eq "success" -and $result.data.result.Count -gt 0) {
        Write-Host "Prometheus query ready: $Query"
        return
      }
    }
    catch {
      Start-Sleep -Seconds 3
    }
    Start-Sleep -Seconds 3
  } while ((Get-Date) -lt $deadline)

  throw "Prometheus query did not return data before timeout: $Query"
}

Invoke-FraudCompose config --quiet
Invoke-FraudCompose up -d --build

try {
  Wait-Http -Name "API" -Uri "$ApiBase/health/live" -TimeoutSeconds $TimeoutSeconds
  Wait-Http -Name "Prometheus" -Uri "$PrometheusBase/-/ready" -TimeoutSeconds $TimeoutSeconds
  Wait-Http -Name "Grafana" -Uri "$GrafanaBase/api/health" -TimeoutSeconds $TimeoutSeconds
  Wait-Http -Name "Neo4j" -Uri "$Neo4jBase/" -TimeoutSeconds $TimeoutSeconds

  $generated = Invoke-FraudApi `
    -Method "Post" `
    -Uri "$ApiBase/v1/synthetic/generate?users=30"
  Assert-FraudCondition ($generated.events -gt 0) "Synthetic generation returned no events."

  $decision = Invoke-FraudApi `
    -Method "Post" `
    -Uri "$ApiBase/v1/decisions/score" `
    -Body @{
      target_entity = @{
        entity_type = "USER"
        entity_id = "user_00000"
      }
      as_of = "2026-05-10T00:00:00Z"
      amount = 1000
      context = @{}
    }
  Assert-FraudCondition ($decision.risk_score -ge 80) "Expected user_00000 to score as high risk."
  Assert-FraudCondition ($decision.risk_tier -eq "RED") "Expected user_00000 to land in RED tier."

  $cases = @(Invoke-FraudApi -Method "Get" -Uri "$ApiBase/v1/review/cases")
  Assert-FraudCondition ($cases.Count -gt 0) "Expected scoring to create at least one review case."

  $dashboard = Invoke-WebRequest -Uri "$ApiBase/dashboard" -TimeoutSec 10 -UseBasicParsing
  Assert-FraudCondition ($dashboard.Content -like "*Recent decisions*") "Dashboard missing recent decisions."
  Assert-FraudCondition ($dashboard.Content -like "*Open review queue*") "Dashboard missing review queue."
  Assert-FraudCondition ($dashboard.Content -like "*user_00000*") "Dashboard missing scored user."

  $metrics = Invoke-WebRequest -Uri "$ApiBase/metrics" -TimeoutSec 10 -UseBasicParsing
  Assert-FraudCondition ($metrics.Content -like "*fraud_decisions_total*") "Metrics missing decisions counter."
  Assert-FraudCondition ($metrics.Content -like "*fraud_events_ingested_total*") "Metrics missing events counter."

  $grafanaDashboard = Invoke-WebRequest `
    -Uri "$GrafanaBase/d/fraud-v2-overview/fraud-v2-overview" `
    -TimeoutSec 10 `
    -UseBasicParsing
  Assert-FraudCondition ($grafanaDashboard.StatusCode -eq 200) "Grafana dashboard did not load."

  Wait-PrometheusQuery -Query 'up{job="fraud-v2-api", instance="api:8000"}' -TimeoutSeconds $TimeoutSeconds

  Invoke-FraudCompose ps
}
finally {
  if (-not $KeepRunning) {
    Invoke-FraudCompose down
  }
}
