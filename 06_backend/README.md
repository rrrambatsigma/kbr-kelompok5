# Backend KBR Kelompok 5

Backend sistem pakar penyakit tanaman pangan dengan arsitektur:

```text
React
  │
  ├─ GET  /api/plants, /api/diseases, /api/symptoms, /api/phases
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

## Ontology yang dimuat

File `04_ontology/ontology_md.ttl` berisi **24.833 triple**, **1.366 individu**,
**87 kelas**, dan **4 aturan SWRL**. Angka itu sudah termasuk **inferred axiom
Pellet** dari Protégé: kategori penyakit (Jamur 34, Bakteri 7, Virus 10,
Oomycete 3, Fitoplasma 1), tipe individu, `owl:disjointWith`, dan 27 tautan
`menyerangBagian`. Fuseki memuat file yang sama lewat
`scripts/load-ontology.ps1`; Java memuatnya lewat `ONTOLOGY_FILE_PATH`.

SWRL tidak dieksekusi oleh Fuseki maupun Openllet. Aturan SWRL dijalankan
offline dengan Pellet (lihat `04_ontology/tests/test_swrl_reasoning.py`);
backend hanya memakai Openllet untuk konsistensi dan inferensi kategori
penyakit.

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
ONTOLOGY_FILE_PATH=E:/kbr-kelompok5/04_ontology/ontology_md.ttl
FRONTEND_URL=http://localhost:5173
```

`ONTOLOGY_FILE_PATH` di Node opsional; dipakai `/api/health/ontology` untuk
membandingkan SHA-256 file dengan checksum yang dimuat Java. Jika kosong,
statusnya `UNKNOWN` dan readiness tidak diblokir.

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
curl http://127.0.0.1:3000/api/health/ontology
```

`/api/health/ready` mengembalikan `503` jika Fuseki/reasoning tidak siap atau
checksum ontology berbeda (`ONTOLOGY_MISMATCH`). `/api/health/ontology`
menampilkan perbandingan file, Java, dan Fuseki untuk diagnostik; endpoint ini
tetap `200` selama service bisa menjawab. `/api/health` dan `/api/health/live`
hanya mengecek proses Node.

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
| GET | `/api/symptoms` | Daftar konsep gejala kanonik; filter `?plantId=Padi` |
| GET | `/api/phases` | Daftar fase pertumbuhan; filter `?plantId=Padi` |
| GET | `/api/varieties` | Daftar varietas + catatan tahan/rentan; filter `?plantId=Padi` |
| GET | `/api/diseases/:id/reasoning` | Fakta inferred dari Fuseki: kategori + bagian terdampak |

`:id` menerima local name (`Padi`, `PenyakitBlasPadi`) atau IRI penuh.

`GET /api/phases?plantId=Padi` mengembalikan **7 kelas fase** dari ontology
(`FasePembibitan`, `FaseVegetatif`, `FaseAnakan`, `FasePembungaan`,
`FaseGeneratif`, `FasePemasakan`, `FasePanen`) lengkap dengan `diseaseCount`
per tanaman. Kelas yang belum punya tautan penyakit tetap dikembalikan dengan
`diseaseCount: 0`; ini bukan error. ID fase yang dipakai di request adalah ID
kelas, bukan ID individu fase.

`GET /api/symptoms?plantId=Padi` mengembalikan **konsep gejala kanonik**
(`GejalaKanonik`) yang dipakai penyakit tanaman itu, bukan observasi mentah.
Setiap item memuat `observationCount` dan `diseaseCount`; ID yang dikirim UI ke
`POST /api/diagnosis` adalah local name konsep (mis. `BercakDaun`). Untuk Padi
endpoint ini mengembalikan 12 konsep dari 26 observasi. `POST /api/diagnosis`
juga tetap menerima ID observasi (`Pengamatan...`) untuk kompatibilitas dan
pengujian exact-match.

`GET /api/diseases/:id` mengembalikan `controls[].description` dari kutipan
`BuktiPengendalian` milik penyakit tersebut. Deskripsi global
`ptp:deskripsiPengendalian` hanya dipakai sebagai fallback, sehingga
pengendalian tidak menampilkan kalimat dari penyakit atau tanaman lain.

### Diagnosis

`POST /api/diagnosis`

```json
{
  "plantId": "Padi",
  "varietyId": "VarietasBondoyudo",
  "phaseId": "FaseAnakan",
  "symptomIds": [
    "BercakDaun",
    "KlorosisDaun"
  ],
  "topN": 5
}
```

Aturan validasi:

- `plantId` wajib dan harus ada.
- `varietyId` opsional; jika diisi harus varietas milik tanaman yang dipilih.
  Varietas dipakai untuk menandai `varietyMatch` kandidat
  (`resistant`/`susceptible`/`unknown`), belum mengubah skor.
- `phaseId` opsional; jika diisi harus salah satu dari 7 kelas fase. Fase yang
  valid tetapi belum punya tautan penyakit tetap diterima dengan
  `phaseMatch = "unknown"`/`"mismatch"`; ID fase yang tidak dikenal ditolak
  `400`.
- `symptomIds` 1–100 ID, tidak boleh kosong.
- ID gejala harus dikenali untuk tanaman tersebut; menerima ID konsep kanonik
  (`BercakDaun`) maupun ID observasi lama (`Pengamatan...`).
- Duplikat dihapus dan menghasilkan warning `DUPLICATE_SYMPTOM_IDS_IGNORED`.
- `topN` integer 1–10, default 5.

Algoritma reasoning (`forward-chaining-cf-v1`):

```text
spec = 0.5 + 0.5 * log((N+1)/(df+1)) / log(N+1)
w    = min(0.9, bobot_dasar * spec)
CF   = 1 - produk(1 - w)

completeness = matched / jumlah gejala terpilih
coverage     = matched / max(jumlah gejala penyakit, 4)
faktor_fase  = 1.05 jika fase cocok, selain itu 1.0
score        = CF * (0.7 + 0.3*completeness) * (0.5 + 0.5*coverage) * faktor_fase
```

- `bobot_dasar` = 1 untuk exact match, 0.6 untuk match konsep kanonik.
- Fase pertumbuhan bersifat opsional dan hanya menjadi faktor ranking lembut.
  Kandidat tanpa data fase atau dengan fase berbeda tidak dihukum.
- `df` dihitung dari konsep kanonik (`memilikiGejalaKanonik`), bukan ID
  pengamatan, karena pengamatan bersifat spesifik per penyakit.
- Penyebut coverage minimal 4: penyakit dengan 1-2 gejala tercatat tidak
  otomatis mendapat coverage 1.0 (penalti kelengkapan data).
- Satu observasi penyakit tidak dihitung dua kali.
- `confidence`: `TINGGI` jika `score >= 0.7` dan bukti >= 2; `SEDANG` jika
  `score >= 0.4` dan bukti >= 2; selain itu `RENDAH`. Satu bukti selalu
  `RENDAH`.

Kandidat diurutkan berdasarkan `score` desc, jumlah bukti desc, lalu label.
Response berisi `matchedSymptoms`, `unmatchedSelectedSymptoms`, `category`,
`controls`, `riskFactors`, `confidence`, `phaseMatch`, `evidence`,
`explanation`, dan `scoreComponents` (termasuk `phase`). `riskFactors` berasal
dari relasi `dipengaruhiOleh` dan hanya untuk informasi, bukan komponen skor.
`input` memuat `phaseId`, `phaseIri`, dan `phaseLabel` bila fase dikirim.
`matchedSymptoms` berisi gejala yang dipilih user; `evidence.matchedObservationId`
menunjukkan observasi milik penyakit yang menjadi dasar kecocokan (penting untuk
match kanonik). `reasoning.modelVersion` menandai versi model. Node meneruskan
`X-Request-Id` ke Java; Java mengembalikannya di header dan `meta.requestId`.

Jika reasoning API mati/timeout, diagnosis tetap `200` dengan
`reasoning.status = "DEGRADED"`, `category = null`, dan warning
`REASONING_UNAVAILABLE`.

Node membaca kategori dari **triple inferred di Fuseki** dan menandainya
`reasoning.categorySource = "FUSEKI"`; jika query Fuseki gagal, Node memakai
kategori dari Java (`"JAVA"`). Detail derivasi skor dan bobot per bagian:
`../08_documentation/cf-derivation.md`.

Detail metode, rumus, dan validasi M5: `../08_documentation/reasoning.md`.
Skenario demo: `../08_documentation/demo-m5.md`.

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
PenyakitJamur       = 34
PenyakitBakteri     = 7
PenyakitVirus       = 10
PenyakitOomycete    = 1
PenyakitFitoplasma  = 1
PenyakitNematoda    = 0
PenyakitLainnya     = 0
```

Semua 53 penyakit memiliki relasi `disebabkanOleh` ke patogen yang dikenal,
sehingga `unclassifiedDiseaseCount = 0`. Dua penyakit ubi kayu memiliki
patogen jamur sekaligus oomycete; backend memilih satu kategori dengan
prioritas `Jamur → Bakteri → Virus → Oomycete → Fitoplasma → Nematoda`.
Jika ada penyakit tanpa kategori, response tetap mengembalikan
`category: null` dan warning `DISEASE_CATEGORY_UNCLASSIFIED`; tidak ada
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
| 503 | `ONTOLOGY_MISMATCH` | Checksum file Node berbeda dengan yang dimuat Java |
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

# Integration test Node ↔ Java (checksum, request id, reload)
.\06_backend\scripts\integration-test.ps1

# Node: unit test scoring + validasi
cd .\06_backend\node-api
npm run typecheck
npm test

# Inspect dataset diagnosis ternormalisasi (butuh Fuseki hidup)
npm run dataset:inspect -- Padi

# Java: golden inference test + context load
cd .\06_backend\reasoning-api
.\mvnw.cmd test

# Validasi reasoning end-to-end (Fuseki, Java, Node harus hidup)
cd ..\..\05_reasoning_tests
node run.mjs --perf
```

## Troubleshooting

| Gejala | Penyebab umum | Tindakan |
|---|---|---|
| `readiness` DOWN, Fuseki DOWN | Fuseki belum jalan / dataset kosong | Jalankan `start-fuseki.ps1`, cek `/api/health/fuseki` |
| `readiness` DOWN, reasoning DOWN | Java belum selesai load / mati | Cek log Java, `GET /api/reasoning/status` |
| `ONTOLOGY_NOT_LOADED` | File ontology tidak ditemukan | Set `ONTOLOGY_FILE_PATH`, cek log startup |
| `ONTOLOGY_INCONSISTENT` | Ontology kontradiktif | Perbaiki ontology, reload |
| `ONTOLOGY_MISMATCH` | Checksum file Node berbeda dengan Java | Samakan `ONTOLOGY_FILE_PATH`, reload Java |
| `totalTriples` bukan 24833 | Dataset lama/belum dimuat | `load-ontology.ps1 -Reset` |
| Port sudah dipakai | Proses lama masih hidup | Hentikan proses pada port 3000/3030/8082 |

## Catatan keamanan

- Fuseki dijalankan `--localhost` dan **read-only** (tanpa service update).
- `start-fuseki.ps1` memakai `fuseki-config/shiro.ini` lewat opsi `--shiro`.
- Java dan Node bind ke `127.0.0.1` secara default.
- Tidak ada kredensial default di `shiro.ini`.
- Jangan commit `fuseki-data/`, `dist/`, `target/`, `node_modules/`, atau `.env`.
