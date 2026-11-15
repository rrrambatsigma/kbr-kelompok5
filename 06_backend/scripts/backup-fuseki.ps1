param(
    [string]$DataDir = "",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

$backendDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

if ($DataDir -eq "") {
    $DataDir = Join-Path $backendDir "fuseki-data"
}

if ($OutputDir -eq "") {
    $OutputDir = Join-Path $backendDir "backups"
}

if (-not (Test-Path $DataDir)) {
    throw "Folder data Fuseki tidak ditemukan: $DataDir"
}

$fusekiRunning = Get-NetTCPConnection -State Listen -LocalPort 3030 -ErrorAction SilentlyContinue
if ($fusekiRunning) {
    Write-Warning "Fuseki masih berjalan. Hentikan dulu agar backup konsisten."
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$target = Join-Path $OutputDir "fuseki-data-$timestamp.zip"

Write-Host "Membuat backup $DataDir -> $target ..."
Compress-Archive -Path (Join-Path $DataDir "*") -DestinationPath $target -Force

Write-Host "Backup selesai: $target"
