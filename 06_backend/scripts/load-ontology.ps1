param(
    [string]$OntologyFile = "",
    [string]$DataDir = "",
    [string]$FusekiJar = "E:\apache-jena-fuseki-6.2.0\apache-jena-fuseki-6.2.0\fuseki-server.jar",
    [switch]$Reset
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$backendDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

if ($OntologyFile -eq "") {
    # Runtime memakai closure Pellet lengkap (kategori penyakit, disjointness,
    # hasil SWRL) untuk Fuseki, Java, dan Node.
    $OntologyFile = Join-Path $repoRoot "04_ontology\ontology_md_inferred.ttl"
}

if ($DataDir -eq "") {
    $DataDir = Join-Path $backendDir "fuseki-data"
}

if (-not (Test-Path $FusekiJar)) {
    throw "fuseki-server.jar tidak ditemukan di '$FusekiJar'."
}

if (-not (Test-Path $OntologyFile)) {
    throw "File ontology tidak ditemukan: $OntologyFile"
}

$fusekiRunning = Get-NetTCPConnection -State Listen -LocalPort 3030 -ErrorAction SilentlyContinue
if ($fusekiRunning) {
    throw "Fuseki sedang berjalan di port 3030. Hentikan dulu sebelum memuat ontology."
}

if (Test-Path $DataDir) {
    $hasData = @(Get-ChildItem -Path $DataDir -Force -ErrorAction SilentlyContinue).Count -gt 0
    if ($hasData -and -not $Reset) {
        throw "Folder data sudah berisi data: $DataDir. Gunakan -Reset untuk menghapus dan memuat ulang."
    }
    if ($Reset) {
        Write-Host "Menghapus dataset lama: $DataDir"
        Remove-Item -Path $DataDir -Recurse -Force
    }
}

New-Item -ItemType Directory -Force -Path $DataDir | Out-Null

Write-Host "Memuat $OntologyFile ke $DataDir ..."

& java -cp $FusekiJar tdb2.tdbloader --loc $DataDir $OntologyFile

if ($LASTEXITCODE -ne 0) {
    throw "tdb2.tdbloader gagal dengan exit code $LASTEXITCODE"
}

Write-Host "Selesai. Jalankan scripts/start-fuseki.ps1 lalu cek GET /api/health/fuseki."
