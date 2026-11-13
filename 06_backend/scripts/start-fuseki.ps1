param(
    [int]$Port = 3030,
    [string]$FusekiJar = "E:\apache-jena-fuseki-6.2.0\apache-jena-fuseki-6.2.0\fuseki-server.jar",
    [string]$ConfigFile = "",
    [switch]$Foreground
)

$ErrorActionPreference = "Stop"

$backendDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$configDir = Join-Path $backendDir "fuseki-config"
$logDir = Join-Path $configDir "logs"

if ($ConfigFile -eq "") {
    $ConfigFile = Join-Path $configDir "config.ttl"
}

if (-not (Test-Path $FusekiJar)) {
    throw "fuseki-server.jar tidak ditemukan di '$FusekiJar'. Unduh Apache Jena Fuseki atau berikan -FusekiJar."
}

if (-not (Test-Path $ConfigFile)) {
    throw "Config Fuseki tidak ditemukan: $ConfigFile"
}

$existing = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
if ($existing) {
    throw "Port $Port sudah dipakai (PID $($existing.OwningProcess)). Hentikan proses tersebut dulu."
}

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$arguments = @(
    "-Xmx4G",
    "-cp", $FusekiJar,
    "org.apache.jena.fuseki.main.cmds.FusekiServerCmd",
    "--config", (Split-Path $ConfigFile -Leaf),
    "--shiro", (Join-Path $configDir "shiro.ini"),
    "--port=$Port",
    "--localhost"
)

Write-Host "Menjalankan Fuseki (read-only) pada http://127.0.0.1:$Port ..."

if ($Foreground) {
    Push-Location $configDir
    try {
        & java @arguments
    } finally {
        Pop-Location
    }
    exit $LASTEXITCODE
}

$stdout = Join-Path $logDir "fuseki.out.log"
$stderr = Join-Path $logDir "fuseki.err.log"

$process = Start-Process -FilePath "java" `
    -ArgumentList $arguments `
    -WorkingDirectory $configDir `
    -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr `
    -WindowStyle Hidden `
    -PassThru

$deadline = (Get-Date).AddSeconds(45)
while ((Get-Date) -lt $deadline) {
    if ($process.HasExited) {
        throw "Fuseki berhenti saat startup. Lihat $stderr"
    }
    $listening = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
    if ($listening) {
        Write-Host "Fuseki siap: http://127.0.0.1:$Port/plant-kb (PID $($process.Id))"
        Write-Host "Log: $stdout"
        exit 0
    }
    Start-Sleep -Milliseconds 500
}

throw "Fuseki tidak listen pada port $Port dalam 45 detik. Lihat $stderr"
