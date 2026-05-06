param(
  [string]$ComposeProject = "fraud-v2",
  [string]$ComposeFile = "infra\docker-compose.yml",
  [string]$Database = "fraud_v2",
  [string]$DatabaseUser = "fraud",
  [string]$BackupDir = "data\local\postgres-backups",
  [string]$RestoreDatabase = "",
  [switch]$SkipRestore,
  [switch]$KeepRestoreDatabase
)

$ErrorActionPreference = "Stop"

function Invoke-FraudCompose {
  docker compose -p $ComposeProject -f $ComposeFile --profile full @args
}

function Assert-LastExitCode {
  param([string]$Message)

  if ($LASTEXITCODE -ne 0) {
    throw $Message
  }
}

function Invoke-PostgresScalar {
  param(
    [string]$TargetDatabase,
    [string]$Sql
  )

  $output = Invoke-FraudCompose exec -T postgres psql -U $DatabaseUser -d $TargetDatabase -At -c $Sql
  Assert-LastExitCode "Postgres scalar query failed for database '$TargetDatabase'."
  $value = $output |
    Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
    Select-Object -Last 1
  if ([string]::IsNullOrWhiteSpace($value)) {
    return "0"
  }
  return $value.Trim()
}

function Copy-PostgresFileFromContainer {
  param(
    [string]$ContainerPath,
    [string]$DestinationPath
  )

  $containerId = Invoke-FraudCompose ps -q postgres
  Assert-LastExitCode "Could not resolve Postgres container id."
  $containerId = ($containerId | Select-Object -Last 1).Trim()
  if ([string]::IsNullOrWhiteSpace($containerId)) {
    throw "Postgres container id was empty."
  }

  $previousErrorActionPreference = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    $copyOutput = & docker cp "${containerId}:$ContainerPath" $DestinationPath 2>&1
    $copyExitCode = $LASTEXITCODE
  }
  finally {
    $ErrorActionPreference = $previousErrorActionPreference
  }
  if ($copyExitCode -ne 0) {
    throw "docker cp failed for '$ContainerPath': $copyOutput"
  }
}

function Copy-PostgresFileToContainer {
  param(
    [string]$SourcePath,
    [string]$ContainerPath
  )

  $containerId = Invoke-FraudCompose ps -q postgres
  Assert-LastExitCode "Could not resolve Postgres container id."
  $containerId = ($containerId | Select-Object -Last 1).Trim()
  if ([string]::IsNullOrWhiteSpace($containerId)) {
    throw "Postgres container id was empty."
  }

  $previousErrorActionPreference = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    $copyOutput = & docker cp $SourcePath "${containerId}:$ContainerPath" 2>&1
    $copyExitCode = $LASTEXITCODE
  }
  finally {
    $ErrorActionPreference = $previousErrorActionPreference
  }
  if ($copyExitCode -ne 0) {
    throw "docker cp failed for '$SourcePath': $copyOutput"
  }
}

$timestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMdd_HHmmss")
if ([string]::IsNullOrWhiteSpace($RestoreDatabase)) {
  $RestoreDatabase = "fraud_v2_restore_$timestamp"
}

New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
$backupPath = Join-Path $BackupDir "fraud_v2-$timestamp.dump"
$manifestPath = Join-Path $BackupDir "postgres-backup-manifest-$timestamp.json"
$containerBackupPath = "/tmp/fraud_v2-$timestamp.dump"
$containerRestorePath = "/tmp/fraud_v2-restore-$timestamp.dump"

Invoke-FraudCompose exec -T postgres pg_dump -U $DatabaseUser -d $Database -Fc -f $containerBackupPath
Assert-LastExitCode "pg_dump failed for database '$Database'."

Copy-PostgresFileFromContainer -ContainerPath $containerBackupPath -DestinationPath $backupPath

$backupItem = Get-Item -LiteralPath $backupPath
$backupHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $backupPath).Hash.ToLowerInvariant()
$manifest = [ordered]@{
  schema_version = "postgres-backup-rehearsal-v1"
  created_at = (Get-Date).ToUniversalTime().ToString("o")
  compose_project = $ComposeProject
  database = $Database
  database_user = $DatabaseUser
  backup_format = "pg_dump_custom"
  backup_path = $backupPath
  manifest_path = $manifestPath
  bytes = $backupItem.Length
  sha256 = $backupHash
  restored = $false
  restore = $null
  verified = ($backupItem.Length -gt 0)
  local_only = $true
  not_managed_backup = $true
}

try {
  if (-not $SkipRestore) {
    Invoke-FraudCompose exec -T postgres createdb -U $DatabaseUser $RestoreDatabase
    Assert-LastExitCode "createdb failed for scratch restore database '$RestoreDatabase'."

    try {
      Copy-PostgresFileToContainer -SourcePath $backupPath -ContainerPath $containerRestorePath
      Invoke-FraudCompose exec -T postgres pg_restore -U $DatabaseUser -d $RestoreDatabase $containerRestorePath
      Assert-LastExitCode "pg_restore failed for scratch restore database '$RestoreDatabase'."

      $sourceEvents = [int](Invoke-PostgresScalar `
          -TargetDatabase $Database `
          -Sql "select count(*) from events;")
      $restoredEvents = [int](Invoke-PostgresScalar `
          -TargetDatabase $RestoreDatabase `
          -Sql "select count(*) from events;")
      $restoreVerified = $sourceEvents -eq $restoredEvents
      $manifest.restored = $true
      $manifest.restore = [ordered]@{
        database = $RestoreDatabase
        source_events = $sourceEvents
        restored_events = $restoredEvents
        verified = $restoreVerified
        kept = $KeepRestoreDatabase.IsPresent
      }
      $manifest.verified = ($manifest.verified -and $restoreVerified)
    }
    finally {
      if (-not $KeepRestoreDatabase) {
        Invoke-FraudCompose exec -T postgres dropdb -U $DatabaseUser --if-exists $RestoreDatabase | Out-Null
        Assert-LastExitCode "dropdb failed for scratch restore database '$RestoreDatabase'."
      }
    }
  }
}
finally {
  Invoke-FraudCompose exec -T postgres rm -f $containerBackupPath $containerRestorePath | Out-Null
}

$manifest | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
$manifest | ConvertTo-Json -Depth 10
