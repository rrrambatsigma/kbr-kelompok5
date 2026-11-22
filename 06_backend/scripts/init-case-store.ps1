param(
    [string]$FusekiJar = "E:\apache-jena-fuseki-6.2.0\apache-jena-fuseki-6.2.0\fuseki-server.jar",
    [string]$DataDir = ""
)

$ErrorActionPreference = "Stop"

$backendDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$configDir = Join-Path $backendDir "fuseki-config"
$vocabFile = Join-Path $configDir "case-vocab.ttl"

if ($DataDir -eq "") {
    $DataDir = Join-Path $backendDir "fuseki-data-kasus"
}

if (-not (Test-Path $FusekiJar)) {
    throw "fuseki-server.jar tidak ditemukan di '$FusekiJar'."
}

if (-not (Test-Path $vocabFile)) {
    throw "File vocab kasus tidak ditemukan: $vocabFile"
}

$fusekiRunning = Get-NetTCPConnection -State Listen -LocalPort 3030 -ErrorAction SilentlyContinue
if ($fusekiRunning) {
    throw "Fuseki sedang berjalan di port 3030. Hentikan dulu sebelum menyiapkan case store."
}

if (Test-Path $DataDir) {
    $hasData = @(Get-ChildItem -Path $DataDir -Force -ErrorAction SilentlyContinue).Count -gt 0
    if ($hasData) {
        Write-Host "Case store sudah ada: $DataDir (tidak diubah)."
        exit 0
    }
}

New-Item -ItemType Directory -Force -Path $DataDir | Out-Null

Write-Host "Memuat vocab kasus ke graf urn:kbr:kasus di $DataDir ..."

& java -cp $FusekiJar tdb2.tdbloader --loc $DataDir --graph urn:kbr:kasus $vocabFile

if ($LASTEXITCODE -ne 0) {
    throw "tdb2.tdbloader gagal dengan exit code $LASTEXITCODE"
}

Write-Host "Selesai. Jalankan scripts/start-fuseki.ps1 lalu cek /api/health/cases."
