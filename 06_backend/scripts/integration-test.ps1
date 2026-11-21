param(
    [string]$BaseUrl = "http://127.0.0.1:3000",
    [string]$ReasoningUrl = "http://127.0.0.1:8082"
)

$ErrorActionPreference = "Stop"

function Assert-Equal($Actual, $Expected, $Label) {
    if ($Actual -ne $Expected) {
        throw "${Label}: expected '$Expected', got '$Actual'"
    }
}

function Assert-True($Condition, $Label) {
    if (-not $Condition) {
        throw $Label
    }
}

Write-Host "M6 integration test"
Write-Host "Node:    $BaseUrl"
Write-Host "Java:    $ReasoningUrl"

# 1. Readiness Node
$ready = Invoke-RestMethod "$BaseUrl/api/health/ready"
Assert-Equal $ready.data.status "UP" "readiness Node"
Assert-Equal $ready.data.dependencies.reasoning.status "UP" "reasoning readiness"
Assert-Equal $ready.data.dependencies.ontology.status "UP" "ontology readiness"

# 2. Java status + request id echo
$status = Invoke-RestMethod "$ReasoningUrl/api/reasoning/status" `
    -Headers @{ "X-Request-Id" = "m6-status" }
Assert-Equal $status.data.loaded $true "Java loaded"
Assert-Equal $status.data.ready $true "Java ready"
Assert-Equal $status.data.consistent $true "Java consistent"
Assert-Equal $status.meta.requestId "m6-status" "Java request id"

# 3. Health ontology: file = Java = Fuseki fingerprint
$health = Invoke-RestMethod "$BaseUrl/api/health/ontology"
Assert-Equal $health.data.status "OK" "ontology health status"
Assert-Equal $health.data.checks.fileMatchesJava $true "checksum file vs Java"
Assert-Equal $health.data.checks.fusekiHasV2Fingerprint $true "fingerprint Fuseki"
Assert-Equal $health.data.java.checksum $health.data.file.sha256 "checksum detail"

# 4. Tujuh kelas fase selalu tersedia, dengan diseaseCount per tanaman
$phases = Invoke-RestMethod "$BaseUrl/api/phases?plantId=Padi"
Assert-Equal $phases.data.count 7 "Padi phase count"
Assert-Equal $phases.data.items[0].id "FasePembibitan" "first Padi phase"
$emptyPhases = Invoke-RestMethod "$BaseUrl/api/phases?plantId=UbiKayu"
Assert-Equal $emptyPhases.data.count 7 "UbiKayu phase count"

# 5. Diagnosis nyata: Blas harus dapat kategori dari Java
$body = @{
    plantId = "Padi"
    symptomIds = @(
        "PengamatanPenyakitBlasPadiBercakDaun",
        "PengamatanPenyakitBlasPadiKhasMalai",
        "PengamatanPenyakitBlasPadiMalaiPatah"
    )
    topN = 5
} | ConvertTo-Json -Depth 5

$diagnosis = Invoke-RestMethod "$BaseUrl/api/diagnosis" `
    -Method Post -ContentType "application/json" -Body $body

Assert-Equal $diagnosis.data.reasoning.status "UP" "reasoning diagnosis"
Assert-Equal $diagnosis.data.reasoning.modelVersion "forward-chaining-cf-v1" "model version"
Assert-Equal $diagnosis.data.candidates[0].diseaseId "PenyakitBlasPadi" "top candidate"
Assert-Equal $diagnosis.data.candidates[0].category "PenyakitJamur" "category from Java"
$riskFactors = @($diagnosis.data.candidates[0].riskFactors)
$musimHujan = @($riskFactors | Where-Object { $_.id -eq "KondisiMusimHujan" })
Assert-True ($riskFactors.Count -ge 1) "riskFactors Blas harus berisi minimal satu faktor"
Assert-True ($musimHujan.Count -ge 1) "riskFactors Blas harus memuat KondisiMusimHujan"
Assert-Equal $musimHujan[0].label "Musim hujan" "label faktor risiko"

# 6. Diagnosis dengan fase pertumbuhan
$phaseBody = @{
    plantId = "Padi"
    phaseId = "FaseAnakan"
    symptomIds = @(
        "PengamatanPenyakitHawarPelepahDaunPadiBercakDaun",
        "PengamatanPenyakitHawarPelepahDaunPadiBusukBatang",
        "PengamatanPenyakitHawarPelepahDaunPadiHDPDilihatSelubung"
    )
    topN = 5
} | ConvertTo-Json -Depth 5

$phaseDiagnosis = Invoke-RestMethod "$BaseUrl/api/diagnosis" `
    -Method Post -ContentType "application/json" -Body $phaseBody

Assert-Equal $phaseDiagnosis.data.input.phaseId "FaseAnakan" "phase input"
$phaseCandidate = $phaseDiagnosis.data.candidates |
    Where-Object { $_.diseaseId -eq "PenyakitHawarPelepahDaunPadi" } |
    Select-Object -First 1
Assert-True ($null -ne $phaseCandidate) "phase candidate missing"
Assert-Equal $phaseCandidate.phaseMatch "match" "phase match"

# 6b. Fase tanpa tautan tetap diterima, bukan 400
$unlinkedPhaseBody = @{
    plantId = "Padi"
    phaseId = "FasePembibitan"
    symptomIds = @(
        "PengamatanPenyakitHawarPelepahDaunPadiBercakDaun",
        "PengamatanPenyakitHawarPelepahDaunPadiBusukBatang",
        "PengamatanPenyakitHawarPelepahDaunPadiHDPDilihatSelubung"
    )
    topN = 5
} | ConvertTo-Json -Depth 5

$unlinkedPhaseDiagnosis = Invoke-RestMethod "$BaseUrl/api/diagnosis" `
    -Method Post -ContentType "application/json" -Body $unlinkedPhaseBody
Assert-Equal $unlinkedPhaseDiagnosis.data.input.phaseId "FasePembibitan" "unlinked phase input"
Assert-True ($unlinkedPhaseDiagnosis.data.candidates.Count -ge 1) "unlinked phase candidates"

# 7. Reload atomik tidak mengubah checksum
$reload = Invoke-RestMethod "$ReasoningUrl/api/ontology/reload" `
    -Method Post -Headers @{ "X-Request-Id" = "m6-reload" }
Assert-Equal $reload.data.ready $true "ready after reload"
Assert-Equal $reload.data.checksum $status.data.checksum "checksum after reload"
Assert-Equal $reload.meta.requestId "m6-reload" "reload request id"

# 6. Validasi input tetap bekerja
$badBody = @{
    plantId = "Padi"
    symptomIds = @("PengamatanPenyakitKaratDaunKedelaiBercakDaun")
} | ConvertTo-Json

$badStatus = $null
$badCode = $null
try {
    Invoke-RestMethod "$BaseUrl/api/diagnosis" `
        -Method Post -ContentType "application/json" -Body $badBody | Out-Null
} catch {
    $badStatus = $_.Exception.Response.StatusCode.value__
    $bad = $_.ErrorDetails.Message | ConvertFrom-Json
    $badCode = $bad.error.code
}

Assert-Equal $badStatus 400 "negative HTTP status"
Assert-Equal $badCode "INVALID_REQUEST" "negative error code"

$badPhaseBody = @{
    plantId = "Padi"
    phaseId = "FasePembibitanTanaman"
    symptomIds = @("PengamatanPenyakitBlasPadiBercakDaun")
} | ConvertTo-Json

$badPhaseStatus = $null
$badPhaseCode = $null
try {
    Invoke-RestMethod "$BaseUrl/api/diagnosis" `
        -Method Post -ContentType "application/json" -Body $badPhaseBody | Out-Null
} catch {
    $badPhaseStatus = $_.Exception.Response.StatusCode.value__
    $badPhase = $_.ErrorDetails.Message | ConvertFrom-Json
    $badPhaseCode = $badPhase.error.code
}

Assert-Equal $badPhaseStatus 400 "negative phase HTTP status"
Assert-Equal $badPhaseCode "INVALID_REQUEST" "negative phase error code"

Write-Host "OK: readiness, checksum, phases, diagnosis, reload, negative"
