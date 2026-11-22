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

$fusekiRunning = Get-NetTCPConnection -State Listen -LocalPort 3030 -ErrorAction SilentlyContinue
if ($fusekiRunning) {
    Write-Warning "Fuseki masih berjalan. Hentikan dulu agar backup konsisten."
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"

$targets = @(
    @{ Label = "ontology"; Path = $DataDir },
    @{ Label = "kasus"; Path = (Join-Path $backendDir "fuseki-data-kasus") }
)

$backedUp = 0

foreach ($target in $targets) {
    if (-not (Test-Path $target.Path)) {
        Write-Host "Lewati $($target.Label): $($target.Path) tidak ada."
        continue
    }

    $zip = Join-Path $OutputDir "fuseki-$($target.Label)-$timestamp.zip"
    Write-Host "Membuat backup $($target.Path) -> $zip ..."
    Compress-Archive -Path (Join-Path $target.Path "*") -DestinationPath $zip -Force
    $backedUp++
}

if ($backedUp -eq 0) {
    throw "Tidak ada dataset yang bisa dibackup."
}

Write-Host "Backup selesai: $backedUp dataset."
