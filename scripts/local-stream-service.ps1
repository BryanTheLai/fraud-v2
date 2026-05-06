param(
  [switch]$Once,
  [switch]$DryRun,
  [switch]$CheckLag,
  [switch]$PublishDeadLetters,
  [switch]$AllowCritical,
  [int]$LoopDelaySeconds = 30,
  [int]$BatchSize = 100,
  [int]$MaxBatches = 1,
  [int]$MaxEmptyPolls = 3,
  [string]$BootstrapServers = "localhost:19092",
  [string]$Topic = "fraud.events",
  [string]$GroupId = "fraud-v2-local",
  [string]$StoreBackend = "sqlite",
  [string]$DbPath = "data\local\fraud_v2.sqlite",
  [string]$PostgresDsn = "postgresql://fraud:fraud@localhost:5432/fraud_v2",
  [string]$DeadLetterTopic = "fraud.dead_letters",
  [string]$RunDir = "data\local\stream-service"
)

$ErrorActionPreference = "Stop"

function Invoke-FraudCli {
  param(
    [string[]]$Arguments
  )

  if ($DryRun) {
    Write-Host ("DRYRUN uv run fraud-v2 " + ($Arguments -join " "))
    return
  }

  & uv run fraud-v2 @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "fraud-v2 command failed with exit code ${LASTEXITCODE}: $($Arguments -join ' ')"
  }
}

function New-RunPath {
  param(
    [string]$Prefix,
    [string]$Timestamp,
    [string]$Extension
  )

  Join-Path $RunDir "$Prefix-$Timestamp.$Extension"
}

New-Item -ItemType Directory -Force $RunDir | Out-Null

do {
  $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
  $supervisorPath = New-RunPath -Prefix "stream-supervisor" -Timestamp $timestamp -Extension "json"
  $lagPath = New-RunPath -Prefix "stream-lag" -Timestamp $timestamp -Extension "json"
  $healthPath = New-RunPath -Prefix "stream-health" -Timestamp $timestamp -Extension "json"
  $dashboardPath = New-RunPath -Prefix "stream-health" -Timestamp $timestamp -Extension "html"

  $supervisorArgs = @(
    "stream-supervise",
    "--bootstrap-servers", $BootstrapServers,
    "--topic", $Topic,
    "--group-id", $GroupId,
    "--store-backend", $StoreBackend,
    "--db-path", $DbPath,
    "--postgres-dsn", $PostgresDsn,
    "--batch-size", "$BatchSize",
    "--max-batches", "$MaxBatches",
    "--max-empty-polls", "$MaxEmptyPolls",
    "--allow-unhealthy",
    "--output-path", $supervisorPath
  )
  if ($PublishDeadLetters) {
    $supervisorArgs += @("--publish-dead-letters", "--dead-letter-topic", $DeadLetterTopic)
  }
  Invoke-FraudCli -Arguments $supervisorArgs

  $lagWasWritten = $false
  if ($CheckLag) {
    $lagArgs = @(
      "stream-lag",
      "--bootstrap-servers", $BootstrapServers,
      "--topic", $Topic,
      "--group-id", $GroupId,
      "--output-path", $lagPath
    )
    try {
      Invoke-FraudCli -Arguments $lagArgs
      $lagWasWritten = -not $DryRun
    }
    catch {
      Write-Warning "stream-lag failed; stream-health will mark lag as not checked. $($_.Exception.Message)"
    }
  }

  $healthArgs = @(
    "stream-health",
    "--topic", $Topic,
    "--group-id", $GroupId,
    "--store-backend", $StoreBackend,
    "--db-path", $DbPath,
    "--postgres-dsn", $PostgresDsn,
    "--supervision-report-path", $supervisorPath,
    "--output-path", $healthPath,
    "--dashboard-path", $dashboardPath
  )
  if ($lagWasWritten -and (Test-Path $lagPath)) {
    $healthArgs += @("--lag-report-path", $lagPath)
  }
  if ($AllowCritical) {
    $healthArgs += @("--allow-critical")
  }
  Invoke-FraudCli -Arguments $healthArgs

  Write-Host "stream service iteration complete: $healthPath"
  if ($Once) {
    break
  }
  Start-Sleep -Seconds $LoopDelaySeconds
} while ($true)
