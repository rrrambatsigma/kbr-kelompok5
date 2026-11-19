# Demo Milestone 5 — Reasoning Diagnosis

Panduan demo backend M5. Tiga skenario: kasus jelas, kasus ambigu, dan
validasi/ketahanan. Jalankan perintah dari root repo (`E:\kbr-kelompok5`).

## Checklist sebelum demo

- [ ] Fuseki hidup di `:3030`, Java di `:8082`, Node di `:3000`.
- [ ] `Invoke-RestMethod http://127.0.0.1:3000/api/health/ready` → `UP`.
- [ ] `Invoke-RestMethod http://127.0.0.1:3000/api/health/ontology` → `status: OK`.
- [ ] `.\06_backend\scripts\smoke-test.ps1` → OK.
- [ ] `cd .\05_reasoning_tests; node run.mjs --perf` sudah dijalankan.
- [ ] `05_reasoning_tests/results.md` terbuka di tab lain.
- [ ] Siapkan screenshot/json cadangan kalau service bermasalah.

Perintah cek cepat:

```powershell
Invoke-RestMethod http://127.0.0.1:3000/api/health/fuseki
Invoke-RestMethod http://127.0.0.1:8082/api/reasoning/status
Invoke-RestMethod http://127.0.0.1:3000/api/health/ready
```

## Skenario 1 — kasus jelas (Blas)

Tujuan: menunjukkan exact match, skor, keyakinan, dan alasan.

```powershell
$body = @{
  plantId = "Padi"
  symptomIds = @(
    "PengamatanPenyakitBlasPadiBercakDaun",
    "PengamatanPenyakitBlasPadiKhasMalai",
    "PengamatanPenyakitBlasPadiMalaiPatah"
  )
  topN = 5
} | ConvertTo-Json -Depth 5

$r = Invoke-RestMethod http://127.0.0.1:3000/api/diagnosis `
  -Method Post -ContentType "application/json" -Body $body

$r.data.candidates |
  Select-Object diseaseId, score, confidence, explanation |
  Format-Table -Wrap
```

Yang diharapkan:

- Peringkat 1: `PenyakitBlasPadi`, skor **0,7466**, `TINGGI`.
- Kandidat lain muncul dengan skor rendah dan `RENDAH`.
- `explanation`: “3 gejala cocok persis. Kandidat ini menjelaskan seluruh gejala
  yang dipilih.”

Tunjukkan komponen skor:

```powershell
$r.data.candidates[0].scoreComponents | Format-List
$r.data.candidates[0].evidence |
  Select-Object type, ruleId, weight, cfAfter |
  Format-Table -Wrap
```

Poin yang diucapkan: tiga gejala persis menghasilkan CF tinggi, tetapi coverage
3/6 dan penalti kelengkapan menjaga skor tetap 0,7466, bukan 1,0.

## Skenario 2 — kasus ambigu (kanonik)

Tujuan: menunjukkan nilai utama M5. Gejala generik milik penyakit lain tetap
dikenali sebagai bukti untuk target melalui konsep kanonik.

```powershell
$body = @{
  plantId = "Padi"
  symptomIds = @(
    "PengamatanPenyakitHawarDaunBakteriPadiIstilahKresekSendiriDiambilBahasa",
    "PengamatanPenyakitHawarPelepahDaunPadiBercakDaun",
    "PengamatanPenyakitKerdilRumputDanKerdilHampaPadiKlorosisDaun"
  )
  topN = 5
} | ConvertTo-Json -Depth 5

$r = Invoke-RestMethod http://127.0.0.1:3000/api/diagnosis `
  -Method Post -ContentType "application/json" -Body $body

$r.data.candidates |
  Select-Object diseaseId, score, confidence, explanation |
  Format-Table -Wrap
```

Yang diharapkan:

- Peringkat 1: `PenyakitHawarDaunBakteriPadi`, skor **0,6385**, `SEDANG`.
- Peringkat 2: `PenyakitKerdilRumputDanKerdilHampaPadi`, skor **0,5002**.
- Peringkat 3: `PenyakitHawarPelepahDaunPadi`, skor **0,2518**.

Tunjukkan bukti kanonik:

```powershell
$r.data.candidates[0].evidence |
  Select-Object type, symptomId, matchedObservationId, canonicalSymptomLabel, weight |
  Format-Table -Wrap
```

Bandingkan dengan baseline:

```powershell
$results = Get-Content .\05_reasoning_tests\results.json -Raw | ConvertFrom-Json
$results.cases |
  Where-Object { $_.id -eq "PADI-AMBIG-HDB-01" } |
  Select-Object id, rank, legacyRank, expectedScore, expectedConfidence
```

Yang diharapkan: `rank = 1`, `legacyRank = 3`. Artinya model lama menempatkan HDB
di peringkat 3; model baru menempatkannya di peringkat 1 karena dua gejala
generik cocok secara kanonik.

Poin yang diucapkan: exact match hanya mengenal ID pengamatan; padahal
`BercakDaun` milik Hawar Pelepah dan `KlorosisDaun` milik Kerdil adalah konsep
yang juga dimiliki HDB. Di sinilah reasoning berbasis ontology bekerja.

## Skenario 3 — validasi input

Tujuan: menunjukkan validasi tetap ketat.

```powershell
$body = @{
  plantId = "Padi"
  symptomIds = @("PengamatanPenyakitKaratDaunKedelaiBercakDaun")
} | ConvertTo-Json

try {
  Invoke-RestMethod http://127.0.0.1:3000/api/diagnosis `
    -Method Post -ContentType "application/json" -Body $body
} catch {
  $resp = $_.ErrorDetails.Message | ConvertFrom-Json
  "HTTP=$($_.Exception.Response.StatusCode.value__) code=$($resp.error.code)"
}
```

Yang diharapkan: `HTTP=400 code=INVALID_REQUEST`, karena gejala Kedelai dipakai
untuk tanaman Padi.

## Skenario 3b — ketahanan (opsional)

Hanya lakukan kalau ingin menunjukkan fallback. Ini akan mematikan Java
sementara.

```powershell
$conn = Get-NetTCPConnection -State Listen -LocalPort 8082
Stop-Process -Id $conn.OwningProcess -Force
Start-Sleep -Seconds 2
```

Lalu jalankan diagnosis seperti Skenario 1. Yang diharapkan:

- HTTP tetap `200`.
- `reasoning.status = DEGRADED`.
- `category = null`.
- Warning `REASONING_UNAVAILABLE`.
- Kandidat tetap muncul.

Nyalakan Java lagi:

```powershell
cd .\06_backend\reasoning-api
.\mvnw.cmd spring-boot:run
```

## Urutan demo yang disarankan

1. Sebutkan tujuan M5 dan arsitektur singkat (30 detik).
2. Skenario 1 — tunjukkan response dan evidence (1 menit).
3. Skenario 2 — tunjukkan `legacyRank = 3` vs `rank = 1` (2 menit).
4. Buka `results.md` — tunjukkan tabel baseline vs baru (1 menit).
5. Skenario 3 — validasi input (30 detik).
6. Keterbatasan: ontology sementara, gold di-seed, 131 gejala belum kanonik
   (1 menit).
7. Rencana M6: kontrak, health/version, integration test, runbook (30 detik).

## Kalau demo gagal

- Node mati → jalankan `npm run dev` di `06_backend/node-api`.
- Java mati → jalankan `mvnw.cmd spring-boot:run`.
- Fuseki mati → `start-fuseki.ps1`.
- Dataset salah → `load-ontology.ps1 -Reset`, lalu ulangi start.
- Tetap gagal → gunakan `05_reasoning_tests/results.md` dan `results.json`
  sebagai bukti, lalu jelaskan skenario secara manual.

## Slide minimum (kalau diminta)

1. Masalah dan tujuan M5.
2. Ontologi dan data (angka utama).
3. Arsitektur Node–Fuseki–Java.
4. Aturan + CF + specificitas.
5. Hasil validasi (tabel before/after).
6. Demo, keterbatasan, dan rencana M6.
