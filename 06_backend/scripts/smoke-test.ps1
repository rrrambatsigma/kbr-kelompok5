param(
    [string]$BaseUrl = "http://127.0.0.1:3000"
)

$ErrorActionPreference = "Stop"

function Assert-Equal($Actual, $Expected, $Label) {
    if ($Actual -ne $Expected) {
        throw "${Label}: expected $Expected, got $Actual"
    }
}

Write-Host "Smoke test $BaseUrl"

$live = Invoke-RestMethod "$BaseUrl/api/health/live"
Assert-Equal $live.data.status "UP" "liveness"

$ready = Invoke-RestMethod "$BaseUrl/api/health/ready"
Assert-Equal $ready.data.status "UP" "readiness"
Assert-Equal $ready.data.dependencies.fuseki.status "UP" "fuseki readiness"
Assert-Equal $ready.data.dependencies.reasoning.status "UP" "reasoning readiness"

$fuseki = Invoke-RestMethod "$BaseUrl/api/health/fuseki"
Assert-Equal $fuseki.data.totalTriples 5436 "triple count"

$plants = Invoke-RestMethod "$BaseUrl/api/plants"
Assert-Equal $plants.data.count 7 "plant count"

$diseases = Invoke-RestMethod "$BaseUrl/api/diseases"
Assert-Equal $diseases.data.count 57 "disease count"

$symptoms = Invoke-RestMethod "$BaseUrl/api/symptoms"
Assert-Equal $symptoms.data.count 240 "symptom count"

$payload = @{
    plantId = "Padi"
    symptomIds = @(
        "GejalaAdapunBentukBercakSendiriDapat_626f021f",
        "GejalaAdapunBentukWarnaDanUkuran_f8023518",
        "GejalaAkibatnyaLeherMalaiTidakAkan_fe97cd7f"
    )
    topN = 5
} | ConvertTo-Json -Depth 5

$diagnosis = Invoke-RestMethod "$BaseUrl/api/diagnosis" `
    -Method Post `
    -ContentType "application/json" `
    -Body $payload

if ($diagnosis.data.candidates.Count -lt 1) {
    throw "diagnosis: tidak ada kandidat"
}

$first = $diagnosis.data.candidates[0]
if ($first.score -le 0) {
    throw "diagnosis: skor kandidat pertama tidak valid"
}

if ($diagnosis.data.reasoning.status -ne "UP") {
    throw "diagnosis: reasoning tidak UP"
}

Write-Host "OK: plants=7, diseases=57, symptoms=240, candidates=$($diagnosis.data.candidates.Count)"
Write-Host "Top candidate: $($first.label) (score=$($first.score), category=$($first.category))"
