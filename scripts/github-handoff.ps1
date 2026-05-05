param(
  [string]$RemoteName = "origin",
  [string]$Base = "main",
  [string]$Title = "feat: implement local fraud-v2 platform",
  [string]$BodyFile = ".github\PULL_REQUEST_DRAFT.md",
  [switch]$Execute
)

$ErrorActionPreference = "Stop"

function Invoke-NativeCheck {
  param(
    [string]$FilePath,
    [string[]]$Arguments
  )

  $previousErrorActionPreference = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    $output = & $FilePath @Arguments 2>&1
    $exitCode = $LASTEXITCODE
  }
  finally {
    $ErrorActionPreference = $previousErrorActionPreference
  }
  [pscustomobject]@{
    ExitCode = $exitCode
    Output = ($output -join "`n").Trim()
  }
}

function Invoke-RequiredNative {
  param(
    [string]$FilePath,
    [string[]]$Arguments,
    [string]$FailureMessage
  )

  $result = Invoke-NativeCheck -FilePath $FilePath -Arguments $Arguments
  if ($result.ExitCode -ne 0) {
    throw "$FailureMessage`n$result"
  }
  $result.Output
}

$branch = Invoke-RequiredNative `
  -FilePath "git" `
  -Arguments @("branch", "--show-current") `
  -FailureMessage "Could not read current git branch."

$dirty = Invoke-RequiredNative `
  -FilePath "git" `
  -Arguments @("status", "--porcelain") `
  -FailureMessage "Could not read git status."

$remoteResult = Invoke-NativeCheck -FilePath "git" -Arguments @("remote", "get-url", $RemoteName)
$authResult = Invoke-NativeCheck -FilePath "gh" -Arguments @("auth", "status")
$bodyExists = Test-Path -LiteralPath $BodyFile
$remoteConfigured = $remoteResult.ExitCode -eq 0 -and -not [string]::IsNullOrWhiteSpace($remoteResult.Output)
$ghAuthenticated = $authResult.ExitCode -eq 0
$worktreeClean = [string]::IsNullOrWhiteSpace($dirty)
$ready = $remoteConfigured -and $ghAuthenticated -and $bodyExists -and $worktreeClean

$pushCommand = "git push -u $RemoteName $branch"
$prCommand = "gh pr create --base $Base --title `"$Title`" --body-file $BodyFile"
$report = [ordered]@{
  schema_version = "github-handoff-v1"
  branch = $branch
  remote_name = $RemoteName
  remote_configured = $remoteConfigured
  remote_url = if ($remoteConfigured) { $remoteResult.Output } else { $null }
  gh_authenticated = $ghAuthenticated
  body_file = $BodyFile
  body_file_exists = $bodyExists
  worktree_clean = $worktreeClean
  execute = $Execute.IsPresent
  ready = $ready
  next_commands = @(
    "gh auth login",
    "git remote add $RemoteName <repo-url>",
    $pushCommand,
    $prCommand
  )
}

if (-not $Execute) {
  $report | ConvertTo-Json -Depth 10
  exit 0
}

if (-not $ready) {
  $report | ConvertTo-Json -Depth 10
  exit 2
}

Invoke-RequiredNative `
  -FilePath "git" `
  -Arguments @("push", "-u", $RemoteName, $branch) `
  -FailureMessage "git push failed." | Out-Host

Invoke-RequiredNative `
  -FilePath "gh" `
  -Arguments @("pr", "create", "--base", $Base, "--title", $Title, "--body-file", $BodyFile) `
  -FailureMessage "gh pr create failed." | Out-Host

$report.ready = $true
$report.pushed = $true
$report.pr_requested = $true
$report | ConvertTo-Json -Depth 10
