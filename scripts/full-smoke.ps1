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

function Wait-ComposeCommand {
  param(
    [string]$Name,
    [string[]]$Arguments,
    [int]$TimeoutSeconds
  )

  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  do {
    $output = & docker compose -p $ComposeProject -f infra\docker-compose.yml --profile full @Arguments 2>&1
    if ($LASTEXITCODE -eq 0) {
      Write-Host "$Name ready"
      return
    }
    Start-Sleep -Seconds 3
  } while ((Get-Date) -lt $deadline)

  throw "$Name did not become ready before timeout: $output"
}

Invoke-FraudCompose config --quiet
Invoke-FraudCompose down --volumes --remove-orphans
Invoke-FraudCompose up -d --build

try {
  Wait-Http -Name "API" -Uri "$ApiBase/health/live" -TimeoutSeconds $TimeoutSeconds
  Wait-Http -Name "Prometheus" -Uri "$PrometheusBase/-/ready" -TimeoutSeconds $TimeoutSeconds
  Wait-Http -Name "Grafana" -Uri "$GrafanaBase/api/health" -TimeoutSeconds $TimeoutSeconds
  Wait-Http -Name "Neo4j" -Uri "$Neo4jBase/" -TimeoutSeconds $TimeoutSeconds
  Wait-ComposeCommand `
    -Name "Postgres" `
    -Arguments @("exec", "-T", "postgres", "pg_isready", "-U", "fraud", "-d", "fraud_v2") `
    -TimeoutSeconds $TimeoutSeconds
  Wait-ComposeCommand `
    -Name "Redis" `
    -Arguments @("exec", "-T", "redis", "redis-cli", "ping") `
    -TimeoutSeconds $TimeoutSeconds
  Wait-ComposeCommand `
    -Name "Redpanda" `
    -Arguments @("exec", "-T", "redpanda", "rpk", "cluster", "info") `
    -TimeoutSeconds $TimeoutSeconds
  Wait-ComposeCommand `
    -Name "Neo4j Bolt" `
    -Arguments @("exec", "-T", "neo4j", "cypher-shell", "-u", "neo4j", "-p", "fraud-local-password", "RETURN 1") `
    -TimeoutSeconds $TimeoutSeconds

  $generated = Invoke-FraudApi `
    -Method "Post" `
    -Uri "$ApiBase/v1/synthetic/generate?users=30"
  Assert-FraudCondition ($generated.events -gt 0) "Synthetic generation returned no events."

  $principal = Invoke-FraudApi -Method "Get" -Uri "$ApiBase/v1/auth/whoami"
  Assert-FraudCondition ($principal.roles -contains "admin") "Expected dev token to include admin role."
  Assert-FraudCondition ($principal.roles -contains "system") "Expected dev token to include system role."

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

  $reviewCaseSmoke = @'
from uuid import uuid4

from fraud_v2.domain.reviews import ReviewCase
from fraud_v2.storage.postgres_store import PostgresStore

store = PostgresStore("postgresql://fraud:fraud@postgres:5432/fraud_v2")
case = store.save_review_case(
    ReviewCase(
        decision_id=uuid4(),
        target_entity_id="user_smoke_review",
        priority=50,
    )
)
print(case.case_id)
'@
  $reviewCaseResult = $reviewCaseSmoke | docker compose `
    -p $ComposeProject `
    -f infra\docker-compose.yml `
    --profile full `
    exec -T api uv run --no-sync python - 2>&1
  Assert-FraudCondition ($LASTEXITCODE -eq 0) "Review case seed failed: $reviewCaseResult"
  $reviewCaseOutput = ($reviewCaseResult -join "`n").Trim()
  $reviewCaseId = ($reviewCaseOutput -split "`n")[-1].Trim()
  Assert-FraudCondition (-not [string]::IsNullOrWhiteSpace($reviewCaseId)) "Review case seed did not return a case id."

  $reviewDecision = Invoke-FraudApi `
    -Method "Post" `
    -Uri "$ApiBase/v1/review/cases/$reviewCaseId/decision" `
    -Body @{
      analyst_id = "analyst_smoke"
      outcome = "CONFIRMED_FRAUD"
      confidence = 0.98
      note = "full-smoke synthetic review decision"
    }
  Assert-FraudCondition ("$($reviewDecision.case_id)" -eq $reviewCaseId) "Review decision case id mismatch."
  Assert-FraudCondition ($reviewDecision.outcome -eq "CONFIRMED_FRAUD") "Review decision outcome mismatch."
  $reviewCases = @(Invoke-FraudApi -Method "Get" -Uri "$ApiBase/v1/review/cases")
  $closedReviewCase = $reviewCases |
    Where-Object { "$($_.case_id)" -eq $reviewCaseId } |
    Select-Object -First 1
  Assert-FraudCondition ($null -ne $closedReviewCase) "Review case missing after review decision."
  Assert-FraudCondition ($closedReviewCase.status -eq "closed") "Review case did not close after review decision."

  $audit = @(Invoke-FraudApi -Method "Get" -Uri "$ApiBase/v1/audit/entries")
  Assert-FraudCondition ($audit.Count -gt 0) "Expected audit entries after scoring."
  $auditVerify = Invoke-FraudApi -Method "Get" -Uri "$ApiBase/v1/audit/verify"
  Assert-FraudCondition ($auditVerify.valid -eq $true) "Expected audit hash chain to verify."
  $retention = Invoke-FraudApi -Method "Get" -Uri "$ApiBase/v1/retention/report"
  Assert-FraudCondition ($retention.total_expired -ge 0) "Expected retention report to load."

  $postgresSmoke = @'
from fraud_v2.infrastructure.postgres_store import PostgresEventStore
from fraud_v2.synthetic.generator import SyntheticFraudGenerator
from datetime import UTC, datetime
from uuid import uuid4

store = PostgresEventStore("postgresql://fraud:fraud@postgres:5432/fraud_v2")
store.init_schema()
base_event = SyntheticFraudGenerator(seed=20260520).generate(users=10).events[0]
event = base_event.model_copy(
    update={
        "event_id": uuid4(),
        "idempotency_key": f"postgres-smoke:{uuid4()}",
        "occurred_at": datetime.now(UTC),
    }
)
store.add_event(event)
events = store.list_events()
assert any(str(existing.event_id) == str(event.event_id) for existing in events)
print(f"postgres_events={len(events)}")
'@
  $postgresResult = $postgresSmoke | docker compose `
    -p $ComposeProject `
    -f infra\docker-compose.yml `
    --profile full `
    exec -T api uv run --no-sync python - 2>&1
  Assert-FraudCondition ($LASTEXITCODE -eq 0) "Postgres adapter smoke failed: $postgresResult"
  Write-Host ($postgresResult -join "`n")
  Assert-FraudCondition (($postgresResult -join "`n") -like "*postgres_events=*") "Postgres adapter smoke did not print event count."

  $redisSmoke = @'
from fraud_v2.domain.entities import EntityRef
from fraud_v2.domain.enums import EntityType
from fraud_v2.features.builder import FeatureBuilder
from fraud_v2.infrastructure.redis_feature_cache import RedisFeatureCache
from fraud_v2.synthetic.generator import SyntheticFraudGenerator

events = SyntheticFraudGenerator().generate(users=10).events
target = EntityRef(entity_type=EntityType.USER, entity_id="user_00000")
vector = FeatureBuilder(events).build(target, max(event.occurred_at for event in events))
cache = RedisFeatureCache("redis://redis:6379/0")
cache.put(vector)
loaded = cache.get(target)
assert loaded is not None
assert loaded.target_entity == target
print(f"redis_feature_cache={loaded.target_entity.entity_id}")
'@
  $redisResult = $redisSmoke | docker compose `
    -p $ComposeProject `
    -f infra\docker-compose.yml `
    --profile full `
    exec -T api uv run --no-sync python - 2>&1
  Assert-FraudCondition ($LASTEXITCODE -eq 0) "Redis adapter smoke failed: $redisResult"
  Write-Host ($redisResult -join "`n")
  Assert-FraudCondition (($redisResult -join "`n") -like "*redis_feature_cache=*") "Redis adapter smoke did not print feature cache proof."

  $neo4jSmoke = @'
from fraud_v2.infrastructure.neo4j_projector import Neo4jGraphProjector
from fraud_v2.synthetic.generator import SyntheticFraudGenerator

events = SyntheticFraudGenerator().generate(users=10).events
edges = Neo4jGraphProjector(
    uri="bolt://neo4j:7687",
    user="neo4j",
    password="fraud-local-password",
).project(events)
assert edges > 0
print(f"neo4j_edges={edges}")
'@
  $neo4jResult = $neo4jSmoke | docker compose `
    -p $ComposeProject `
    -f infra\docker-compose.yml `
    --profile full `
    exec -T api uv run --no-sync python - 2>&1
  Assert-FraudCondition ($LASTEXITCODE -eq 0) "Neo4j adapter smoke failed: $neo4jResult"
  Write-Host ($neo4jResult -join "`n")
  Assert-FraudCondition (($neo4jResult -join "`n") -like "*neo4j_edges=*") "Neo4j adapter smoke did not print edge count."

  $redpandaSmoke = @'
from fraud_v2.infrastructure.redpanda_publisher import RedpandaEventPublisher
from fraud_v2.synthetic.generator import SyntheticFraudGenerator

event = SyntheticFraudGenerator().generate(users=10).events[0]
RedpandaEventPublisher("redpanda:9092").publish("fraud.events.smoke", event)
print("redpanda_publish=1")
'@
  $redpandaResult = $redpandaSmoke | docker compose `
    -p $ComposeProject `
    -f infra\docker-compose.yml `
    --profile full `
    exec -T api uv run --no-sync python - 2>&1
  Assert-FraudCondition ($LASTEXITCODE -eq 0) "Redpanda adapter smoke failed: $redpandaResult"
  Write-Host ($redpandaResult -join "`n")
  Assert-FraudCondition (($redpandaResult -join "`n") -like "*redpanda_publish=1*") "Redpanda adapter smoke did not print publish proof."

  $dashboard = Invoke-WebRequest -Uri "$ApiBase/dashboard" -TimeoutSec 10 -UseBasicParsing
  Assert-FraudCondition ($dashboard.Content -like "*Recent decisions*") "Dashboard missing recent decisions."
  Assert-FraudCondition ($dashboard.Content -like "*Open review queue*") "Dashboard missing review queue."
  Assert-FraudCondition ($dashboard.Content -like "*user_00000*") "Dashboard missing scored user."
  Assert-FraudCondition ($dashboard.Content -like "*Graph evidence*") "Dashboard missing graph evidence link."

  $graphDashboard = Invoke-WebRequest `
    -Uri "$ApiBase/dashboard/graph?entity_id=user_00000" `
    -TimeoutSec 10 `
    -UseBasicParsing
  Assert-FraudCondition ($graphDashboard.Content -like "*<svg*") "Graph evidence dashboard missing SVG."
  Assert-FraudCondition ($graphDashboard.Content -like "*USED_DEVICE*") "Graph evidence dashboard missing relationship details."

  $metrics = Invoke-WebRequest -Uri "$ApiBase/metrics" -TimeoutSec 10 -UseBasicParsing
  Assert-FraudCondition ($metrics.Content -like "*fraud_decisions_total*") "Metrics missing decisions counter."
  Assert-FraudCondition ($metrics.Content -like "*fraud_events_ingested_total*") "Metrics missing events counter."

  $grafanaDashboard = Invoke-WebRequest `
    -Uri "$GrafanaBase/d/fraud-v2-overview/fraud-v2-overview" `
    -TimeoutSec 10 `
    -UseBasicParsing
  Assert-FraudCondition ($grafanaDashboard.StatusCode -eq 200) "Grafana dashboard did not load."

  Wait-PrometheusQuery -Query 'up{job="fraud-v2-api", instance="api:8000"}' -TimeoutSeconds $TimeoutSeconds
  $rules = Invoke-RestMethod -Uri "$PrometheusBase/api/v1/rules" -TimeoutSec 10
  $rulesJson = $rules.data.groups | ConvertTo-Json -Depth 20
  Assert-FraudCondition ($rulesJson -like "*FraudV2APIUnavailable*") "Prometheus alert rules did not load."

  $retentionDryRun = Invoke-FraudApi `
    -Method "Post" `
    -Uri "$ApiBase/v1/retention/prune?execute=false&as_of=2026-12-01T00:00:00Z"
  $dryRunActions = @($retentionDryRun.tables | ForEach-Object { $_.action })
  Assert-FraudCondition ($dryRunActions -contains "dry_run") "Retention prune dry run did not mark dry_run actions."

  $retentionPrune = Invoke-FraudApi `
    -Method "Post" `
    -Uri "$ApiBase/v1/retention/prune?execute=true&as_of=2026-12-01T00:00:00Z"
  $retentionActions = @($retentionPrune.tables | ForEach-Object { $_.action })
  Assert-FraudCondition ($retentionActions -contains "delete_expired") "Retention prune did not delete expired rows."
  Assert-FraudCondition ($retentionActions -contains "skipped_hash_chain") "Retention prune should preserve audit hash chain."
  Assert-FraudCondition ($retentionPrune.total_expired -gt 0) "Retention prune did not report expired rows."
  $auditVerifyAfterPrune = Invoke-FraudApi -Method "Get" -Uri "$ApiBase/v1/audit/verify"
  Assert-FraudCondition ($auditVerifyAfterPrune.valid -eq $true) "Expected audit hash chain to verify after retention prune."

  Invoke-FraudCompose ps
}
finally {
  if (-not $KeepRunning) {
    Invoke-FraudCompose down --volumes --remove-orphans
  }
}
