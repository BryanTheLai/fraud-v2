param(
  [switch]$DryRun,
  [switch]$IncludeVenv,
  [switch]$IncludePublicData,
  [switch]$Strict
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$RepoPrefix = $Root.TrimEnd([char[]]@("\", "/")) + "\"

function Assert-UnderRepo {
  param([string]$Path)

  $resolved = (Resolve-Path -LiteralPath $Path -ErrorAction SilentlyContinue)
  if ($null -eq $resolved) {
    return $null
  }
  $fullPath = $resolved.Path
  if ($fullPath -eq $Root) {
    throw "Refusing to remove repo root."
  }
  if (-not $fullPath.StartsWith($RepoPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to remove path outside repo: $fullPath"
  }
  $fullPath
}

function Remove-LocalPath {
  param([string]$Path)

  $fullPath = Assert-UnderRepo -Path $Path
  if ($null -eq $fullPath) {
    return
  }
  if ($DryRun) {
    Write-Host "would remove $fullPath"
    return
  }
  try {
    Remove-Item -LiteralPath $fullPath -Recurse -Force
    Write-Host "removed $fullPath"
  }
  catch {
    if ($Strict) {
      throw
    }
    if (Test-Path -LiteralPath $fullPath -PathType Container) {
      Remove-DirectoryBestEffort -Path $fullPath
      return
    }
    Write-Warning "skipped locked or unavailable path: $fullPath"
  }
}

function Remove-DirectoryBestEffort {
  param([string]$Path)

  Get-ChildItem -LiteralPath $Path -Force -Recurse |
    Sort-Object { $_.FullName.Length } -Descending |
    ForEach-Object {
      $item = $_
      try {
        Remove-Item -LiteralPath $item.FullName -Recurse -Force
        Write-Host "removed $($item.FullName)"
      }
      catch {
        Write-Warning "skipped locked or unavailable path: $($item.FullName)"
      }
    }
  try {
    Remove-Item -LiteralPath $Path -Force
    Write-Host "removed $Path"
  }
  catch {
    Write-Warning "skipped locked or unavailable path: $Path"
  }
}

$paths = @(
  ".mypy_cache",
  ".pytest_cache",
  ".ruff_cache",
  "data\local",
  "data\models",
  "data\offline",
  "data\synthetic\manifests",
  "data\synthetic\demo",
  "data\synthetic\stress"
)

if ($IncludePublicData) {
  $paths += "data\public"
}

foreach ($path in $paths) {
  Remove-LocalPath -Path (Join-Path $Root $path)
}

$pycacheRoots = @("src", "tests")
foreach ($pycacheRoot in $pycacheRoots) {
  $fullPycacheRoot = Join-Path $Root $pycacheRoot
  if (Test-Path -LiteralPath $fullPycacheRoot) {
    Get-ChildItem -LiteralPath $fullPycacheRoot -Recurse -Directory -Filter "__pycache__" |
      ForEach-Object { Remove-LocalPath -Path $_.FullName }
  }
}

if ($IncludeVenv) {
  Remove-LocalPath -Path (Join-Path $Root ".venv")
}

Write-Host "local cleanup complete"
