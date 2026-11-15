# Backend KBR Kelompok 5

Backend sistem pakar penyakit tanaman pangan dengan arsitektur:

```text
React
  │
  ├─ GET  /api/plants, /api/diseases, /api/symptoms
  │        └─ Node/Express → Fuseki/TDB2 (SPARQL read-only)
  │
  └─ POST /api/diagnosis
           ├─ Node: validasi + retrieval + scoring
           ├─ Node → Java: POST /api/reasoning/disease-categories
           │        └─ Java: OWL API + Openllet (inferensi kategori)
           └─ Node: gabungkan kandidat + evidence
```

Pembagian tanggung jawab:

| Komponen | Tanggung jawab |
|---|---|
| Fuseki/TDB2 | Menyimpan RDF dan melayani SPARQL **read-only** |
| Node/Express | Validasi, retrieval, scoring, orkestrasi, response JSON |
| Java/Spring Boot | Memuat ontology, cek konsistensi, inferensi kategori penyakit |
| React | UI dan pemanggilan API Node |

Diagnosis **tidak** dilakukan dengan menambahkan individual gejala ke ontology
setiap request. Node menghitung kandidat dari data Fuseki; Java hanya
menyediakan kategori penyakit hasil inferensi Openllet.

## Prasyarat

- Java 21+ (dipakai Java 23 juga OK)
- Node.js 20+
- Apache Jena Fuseki 6.x (`fuseki-server.jar`)
- File `04_ontology/ontology_md.ttl`

Script `scripts/start-fuseki.ps1` dan `scripts/load-ontology.ps1` memakai
default `E:\apache-jena-fuseki-6.2.0\apache-jena-fuseki-6.2.0\fuseki-server.jar`.
Jika lokasi berbeda, berikan parameter `-FusekiJar "<path>"`.

## Konfigurasi

### Node API (`node-api/.env`)

Salin dari `.env.example`:

```ini
PORT=3000
HOST=127.0.0.1
FUSEKI_BASE_URL=http://localhost:3030
FUSEKI_DATASET=plant-kb
FUSEKI_TIMEOUT_MS=5000
REASONING_API_URL=http://localhost:8082
REASONING_TIMEOUT_MS=15000
FRONTEND_URL=http://localhost:5173
```

### Java reasoning API

Override lewat environment variable bila perlu:

| Variable | Default | Arti |
|---|---|---|
| `SERVER_PORT` | `8082` | Port Java |
| `SERVER_ADDRESS` | `127.0.0.1` | Bind address |
| `ONTOLOGY_FILE_PATH` | `E:/kbr-kelompok5/04_ontology/ontology_md.ttl` | Lokasi ontology |
| `ONTOLOGY_REASONING_TIMEOUT_MS` | `120000` | Timeout precompute/klasifikasi |
| `ONTOLOGY_FAIL_FAST` | `false` | `true` = startup gagal jika ontology invalid |

Ontology dimuat otomatis saat startup. `POST /api/ontology/reload` tersedia
untuk admin/diagnostik.

## Menjalankan

Urutan yang benar:

```powershell
# 1. Muat ontology ke TDB2 (Fuseki harus berhenti)
.\06_backend\scripts\load-ontology.ps1 -Reset

# 2. Jalankan Fuseki read-only
.\06_backend\scripts\start-fuseki.ps1

# 3. Jalankan Java reasoning API
cd .\06_backend\reasoning-api
.\mvnw.cmd spring-boot:run

# 4. Jalankan Node API (terminal lain)
cd .\06_backend\node-api
npm install
npm run dev
```

Produksi Node:

```powershell
npm start   # menjalankan clean + build + node dist/server.js
```

Cek kesehatan:

```powershell
curl http://127.0.0.1:3000/api/health/live
curl http://127.0.0.1:3000/api/health/ready
curl http://127.0.0.1:3000/api/health/fuseki
```

`/api/health/ready` mengembalikan `503` jika Fuseki atau reasoning API tidak
siap. `/api/health` dan `/api/health/live` hanya mengecek proses Node.

## Endpoint

Semua response sukses memakai envelope:

```json
{
  "success": true,
  "data": {},
  "meta": { "requestId": "...", "timestamp": "..." }
}
```

Error:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "INVALID_REQUEST",
    "message": "...",
    "details": [{ "field": "symptomIds", "message": "..." }]
  },
  "meta": { "requestId": "...", "timestamp": "..." }
}
```

### Retrieval

| Method | Path | Keterangan |
|---|---|---|
| GET | `/api/plants` | Daftar tanaman + jumlah penyakit |
| GET | `/api/plants/:id` | Detail tanaman + daftar penyakit |
| GET | `/api/diseases` | Daftar penyakit; filter `?plantId=Padi` |
| GET | `/api/diseases/:id` | Detail penyakit, gejala, pengendalian, patogen |
| GET | `/api/symptoms` | Daftar gejala; filter `?plantId=Padi` |

`:id` menerima local name (`Padi`, `PenyakitBlasPadi`) atau IRI penuh.

### Diagnosis

`POST /api/diagnosis`

```json
{
  "plantId": "Padi",
  "symptomIds": [
    "GejalaAdapunBentukBercakSendiriDapat_626f021f",
    "GejalaAkibatnyaLeherMalaiTidakAkan_fe97cd7f"
  ],
  "topN": 5
}
```

Aturan validasi:

- `plantId` wajib dan harus ada.
- `symptomIds` 1–100 ID, tidak boleh kosong.
- ID gejala harus dikenali untuk tanaman tersebut.
- Duplikat dihapus dan menghasilkan warning `DUPLICATE_SYMPTOM_IDS_IGNORED`.
- `topN` integer 1–10, default 5.

Algoritma skor:

```text
matched      = jumlah gejala terpilih yang dimiliki penyakit
matchRatio   = matched / jumlah gejala terpilih
coverage     = matched / jumlah seluruh gejala penyakit
score        = 0.7 * matchRatio + 0.3 * coverage
```

Kandidat diurutkan berdasarkan `score` desc, `matchedCount` desc, lalu label.
Response berisi `matchedSymptoms`, `unmatchedSelectedSymptoms`, `category`,
dan `controls`.

Jika reasoning API mati/timeout, diagnosis tetap `200` dengan
`reasoning.status = "DEGRADED"`, `category = null`, dan warning
`REASONING_UNAVAILABLE`.

### Reasoning (Java)

| Method | Path | Keterangan |
|---|---|---|
| GET | `/api/reasoning/status` | loaded, ready, consistent, version, checksum, counts |
| GET | `/api/reasoning/consistency` | Status konsistensi |
| POST | `/api/reasoning/disease-categories` | Body `{ "diseaseIris": [] }`; kosong = semua |
| POST | `/api/ontology/reload` | Reload atomik (admin) |
| POST | `/api/ontology/load` | Alias reload (kompatibilitas) |

Kategori yang diinferensi Openllet:

```text
PenyakitJamur       = 26
PenyakitBakteri     = 5
PenyakitVirus       = 5
PenyakitOomycete    = 1
PenyakitFitoplasma  = 1
PenyakitNematoda    = 0
PenyakitLainnya     = 0
```

Ada 15 penyakit yang tidak masuk kategori mana pun karena tidak memiliki
relasi `disebabkanOleh` ke kelompok patogen yang dikenal (`Jamur`, `Bakteri`,
`Virus`, `Oomycete`, `Fitoplasma`, `Nematoda`). Penyakit tersebut dikembalikan
dengan `category: null` dan warning `DISEASE_CATEGORY_UNCLASSIFIED`; tidak ada
kategori yang dikarang.

## Kode error

| HTTP | Code | Arti |
|---:|---|---|
| 400 | `INVALID_REQUEST` | Body/ID tidak valid |
| 404 | `NOT_FOUND` | Tanaman/penyakit/endpoint tidak ada |
| 422 | `ONTOLOGY_INCONSISTENT` | Ontology tidak konsisten |
| 500 | `FUSEKI_QUERY_ERROR` | Query internal ditolak Fuseki |
| 500 | `INTERNAL_ERROR` | Error tak terduga |
| 502 | `FUSEKI_INVALID_RESPONSE` / `REASONING_INVALID_RESPONSE` | Response upstream tidak valid |
| 503 | `FUSEKI_UNAVAILABLE` | Fuseki mati/timeout |
| 503 | `REASONING_UNAVAILABLE` | Reasoning API mati/timeout |
| 503 | `ONTOLOGY_NOT_LOADED` | Ontology belum dimuat |
| 504 | `REASONING_TIMEOUT` | Reasoning melebihi batas waktu |

## Konsistensi ontology

Java menghitung SHA-256 file ontology saat load. Nilainya tersedia di
`/api/reasoning/status` dan `/api/health/ready`. Prosedur update:

1. Validasi `04_ontology/ontology_md.ttl`.
2. Hentikan Fuseki, jalankan `load-ontology.ps1 -Reset`.
3. Jalankan Fuseki read-only.
4. Reload Java (`POST /api/ontology/reload`) atau restart.
5. Bandingkan checksum/versi di `/api/health/ready`.

Jika checksum Fuseki dan Java berbeda, jangan anggap sistem siap.

## Tes

```powershell
# Smoke test end-to-end (semua service harus hidup)
.\06_backend\scripts\smoke-test.ps1

# Node: unit test scoring + validasi
cd .\06_backend\node-api
npm run typecheck
npm test

# Java: golden inference test + context load
cd .\06_backend\reasoning-api
.\mvnw.cmd test
```

## Troubleshooting

| Gejala | Penyebab umum | Tindakan |
|---|---|---|
| `readiness` DOWN, Fuseki DOWN | Fuseki belum jalan / dataset kosong | Jalankan `start-fuseki.ps1`, cek `/api/health/fuseki` |
| `readiness` DOWN, reasoning DOWN | Java belum selesai load / mati | Cek log Java, `GET /api/reasoning/status` |
| `ONTOLOGY_NOT_LOADED` | File ontology tidak ditemukan | Set `ONTOLOGY_FILE_PATH`, cek log startup |
| `ONTOLOGY_INCONSISTENT` | Ontology kontradiktif | Perbaiki ontology, reload |
| `totalTriples` bukan 16391 | Dataset lama/belum dimuat | `load-ontology.ps1 -Reset` |
| Port sudah dipakai | Proses lama masih hidup | Hentikan proses pada port 3000/3030/8082 |

## Catatan keamanan

- Fuseki dijalankan `--localhost` dan **read-only** (tanpa service update).
- `start-fuseki.ps1` memakai `fuseki-config/shiro.ini` lewat opsi `--shiro`.
- Java dan Node bind ke `127.0.0.1` secara default.
- Tidak ada kredensial default di `shiro.ini`.
- Jangan commit `fuseki-data/`, `dist/`, `target/`, `node_modules/`, atau `.env`.
