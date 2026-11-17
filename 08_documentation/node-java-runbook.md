# Runbook Node.js ↔ Java

Panduan operasional untuk menjalankan, memeriksa, dan memperbaiki integrasi
Node–Java. Jalankan dari root repo `E:\kbr-kelompok5`.

## 1. Urutan start

```powershell
# 1. Muat ontology (Fuseki harus berhenti)
.\06_backend\scripts\load-ontology.ps1 -Reset

# 2. Fuseki read-only
.\06_backend\scripts\start-fuseki.ps1

# 3. Java reasoning API (terminal 1)
cd .\06_backend\reasoning-api
.\mvnw.cmd spring-boot:run

# 4. Node API (terminal 2)
cd .\06_backend\node-api
npm run dev
```

Urutan stop: Node → Java → Fuseki.

```powershell
Get-NetTCPConnection -State Listen -LocalPort 3000,8082,3030 |
  ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

## 2. Port dan env

| Service | Port | Env penting |
|---|---:|---|
| Node | 3000 | `REASONING_API_URL`, `REASONING_TIMEOUT_MS`, `ONTOLOGY_FILE_PATH` |
| Java | 8082 | `ONTOLOGY_FILE_PATH`, `ONTOLOGY_FAIL_FAST` |
| Fuseki | 3030 | dataset `plant-kb` |

Node `ONTOLOGY_FILE_PATH` dipakai hanya untuk health check checksum. Java
`ONTOLOGY_FILE_PATH` adalah file yang benar-benar dimuat.

## 3. Cek kesehatan

```powershell
# Node
Invoke-RestMethod http://127.0.0.1:3000/api/health/live
Invoke-RestMethod http://127.0.0.1:3000/api/health/fuseki
Invoke-RestMethod http://127.0.0.1:3000/api/health/ontology
Invoke-RestMethod http://127.0.0.1:3000/api/health/ready

# Java
Invoke-RestMethod http://127.0.0.1:8082/api/reasoning/status
Invoke-RestMethod http://127.0.0.1:8082/api/reasoning/consistency
```

Yang harus terlihat:

- `/api/health/ready` → `UP`.
- `/api/health/ontology` → `status: OK`, `checks.fileMatchesJava: true`.
- Java `loaded`, `ready`, `consistent` = `true`.

Jika `ONTOLOGY_FILE_PATH` Node kosong, status ontology `UNKNOWN`; readiness
tetap `UP` tetapi checksum tidak diverifikasi.

## 4. Cek cepat diagnosis

```powershell
$body = @{
  plantId = "Padi"
  symptomIds = @(
    "PengamatanPenyakitBlasPadiBercakDaun",
    "PengamatanPenyakitBlasPadiKhasMalai",
    "PengamatanPenyakitBlasPadiBerwarnaAbuAbuPutihBagian"
  )
  topN = 5
} | ConvertTo-Json -Depth 5

Invoke-RestMethod http://127.0.0.1:3000/api/diagnosis `
  -Method Post -ContentType "application/json" -Body $body
```

Yang diharapkan: kandidat pertama `PenyakitBlasPadi`, `category =
PenyakitJamur`, `reasoning.status = UP`.

## 5. Test integrasi

```powershell
.\06_backend\scripts\integration-test.ps1
```

Mengecek readiness, checksum, request ID Java, diagnosis, reload, dan validasi
input. Exit code 1 jika ada yang gagal.

Test lain:

```powershell
cd .\06_backend\node-api
npm test

cd ..\reasoning-api
.\mvnw.cmd test

cd ..\..\
.\06_backend\scripts\smoke-test.ps1
```

## 6. Prosedur update ontology

1. Pastikan file final sudah di `04_ontology/ontology_md.ttl`.
2. Hentikan Fuseki.
3. `.\06_backend\scripts\load-ontology.ps1 -Reset`
4. Nyalakan Fuseki.
5. Reload Java:
   ```powershell
   Invoke-RestMethod http://127.0.0.1:8082/api/ontology/reload -Method Post
   ```
6. Cek:
   ```powershell
   Invoke-RestMethod http://127.0.0.1:3000/api/health/ontology
   ```
7. Pastikan `checks.fileMatchesJava = true`.
8. Jalankan `smoke-test.ps1` dan `integration-test.ps1`.
9. Regenerate kasus sanity bila perlu:
   ```powershell
   cd .\05_reasoning_tests
   node generate-sanity.mjs
   node run.mjs --perf
   ```

Jika checksum berbeda, jangan lanjut. Hentikan dan periksa path file di Node
dan Java.

## 7. Troubleshooting

| Gejala | Penyebab umum | Tindakan |
|---|---|---|
| `/ready` DOWN, Fuseki DOWN | Fuseki mati/dataset kosong | Nyalakan Fuseki, cek `/api/health/fuseki` |
| `/ready` DOWN, reasoning DOWN | Java mati/belum selesai load | Cek log Java, `/api/reasoning/status` |
| `/ready` 503 `ONTOLOGY_MISMATCH` | Node dan Java memuat file berbeda | Samakan `ONTOLOGY_FILE_PATH`, reload Java |
| `/api/health/ontology` `UNKNOWN` | `ONTOLOGY_FILE_PATH` Node kosong | Isi env, restart Node |
| `/api/health/ontology` `DOWN` | Java/Fuseki tidak bisa dihubungi | Cek port dan log |
| Diagnosis `DEGRADED` | Java mati/timeout | Cek Java, `REASONING_TIMEOUT_MS` |
| `FUSEKI_UNAVAILABLE` | Fuseki mati/timeout | Nyalakan Fuseki |
| `ONTOLOGY_INCONSISTENT` | Ontology kontradiktif | Perbaiki ontology, reload |
| `totalTriples` bukan 16.391 | Dataset lama | `load-ontology.ps1 -Reset` |
| Port sudah dipakai | Proses lama | Hentikan PID di port 3000/8082/3030 |

## 8. Uji degraded (manual)

```powershell
# Hentikan Java
$conn = Get-NetTCPConnection -State Listen -LocalPort 8082
Stop-Process -Id $conn.OwningProcess -Force
Start-Sleep -Seconds 2
```

Diagnosis harus tetap `200` dengan `reasoning.status = DEGRADED`,
`category = null`, warning `REASONING_UNAVAILABLE`, dan `/ready` menjadi `503`.

Nyalakan Java lagi:

```powershell
cd .\06_backend\reasoning-api
.\mvnw.cmd spring-boot:run
```

## 9. Log

| Service | Lokasi |
|---|---|
| Fuseki | `06_backend/fuseki-config/logs/fuseki.out.log`, `fuseki.err.log` |
| Java | console `mvnw spring-boot:run` |
| Node | console `npm run dev` |

Semua log Node memuat `[requestId]`. Java mengembalikan request id yang sama di
`meta.requestId` dan header `X-Request-Id`.

## 10. Rollback

Jika ontology baru bermasalah:

1. Kembalikan file TTL sebelumnya.
2. `load-ontology.ps1 -Reset`
3. Nyalakan Fuseki.
4. Reload Java.
5. Cek `/api/health/ontology` dan jalankan smoke test.

Jangan mengedit dataset TDB2 langsung. Selalu muat ulang dari file TTL.
