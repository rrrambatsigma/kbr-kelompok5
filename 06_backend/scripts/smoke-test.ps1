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
Assert-Equal $fuseki.data.totalTriples 19021 "triple count"

$plants = Invoke-RestMethod "$BaseUrl/api/plants"
Assert-Equal $plants.data.count 7 "plant count"

$diseases = Invoke-RestMethod "$BaseUrl/api/diseases"
Assert-Equal $diseases.data.count 53 "disease count"

$symptoms = Invoke-RestMethod "$BaseUrl/api/symptoms?plantId=Padi"
Assert-Equal $symptoms.data.count 26 "Padi symptom count"

$phases = Invoke-RestMethod "$BaseUrl/api/phases?plantId=Padi"
Assert-Equal $phases.data.count 2 "Padi phase count"

$symptomIds = @(
    $symptoms.data.items |
        Select-Object -First 3 |
        ForEach-Object { $_.id }
)

if ($symptomIds.Count -lt 3) {
    throw "diagnosis: butuh minimal 3 gejala Padi, hanya ditemukan $($symptomIds.Count)"
}

$payload = @{
    plantId = "Padi"
    symptomIds = $symptomIds
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

Write-Host "OK: plants=7, diseases=53, padiSymptoms=$($symptoms.data.count), padiPhases=$($phases.data.count), candidates=$($diagnosis.data.candidates.Count)"
Write-Host "Top candidate: $($first.label) (score=$($first.score), category=$($first.category))"
