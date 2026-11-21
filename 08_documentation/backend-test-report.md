# Laporan Pengujian dan Evaluasi Backend (M7)

Tanggal: 19 November 2026

Lingkungan:

- Windows, PowerShell
- Node.js 24.21.0, npm 11.19.0
- Java runtime 23.0.1; Maven toolchain Java 21.0.13
- Apache Jena Fuseki 6.2.0
- Ontology gabungan `ontology_md.ttl`
- Checksum `bbf9c78eca83ca04b3185bbba2f1faac29ec062fafa07dbc09adca18307f1175`
- Dataset Fuseki `plant-kb`, 18.981 triple

## Ringkasan

Backend **lolos pengujian teknis** untuk lingkup M5–M6:

- 39 test Node lulus.
- 4 test Java lulus.
- 10 test frontend lulus; build frontend lulus.
- 112 test `03_knowledge_tables` lulus (8 skip), 64 test `04_ontology` lulus.
- Smoke test dan integration test lulus, termasuk fase pertumbuhan.
- 75 kasus evaluasi reasoning + 5 negative berjalan.
- Health check dan checksum konsisten.
- Fallback `DEGRADED` dan `503 FUSEKI_UNAVAILABLE` terbukti.
- Request ID terkorrelasi Node–Java.

Yang **belum** dibuktikan: akurasi klinis independen. Kasus gold masih
di-seed dari ontology.

## 1. Pengujian otomatis

| Pemeriksaan | Hasil | Bukti |
|---|---|---|
| `npm run typecheck` | PASS | tanpa error |
| `npm test` | PASS | 39 test |
| `npm run build` | PASS | `tsc` sukses |
| `mvnw.cmd test` | PASS | 4 test, termasuk golden Openllet |
| `smoke-test.ps1` | PASS | plants=7, diseases=53, Padi symptoms=26, Padi phases=2 |
| `integration-test.ps1` | PASS | readiness, checksum, phases, diagnosis, reload, negative |
| Frontend `npm test` | PASS | 10 test |
| Frontend `npm run build` | PASS | `tsc` + Vite sukses |
| `unittest` `03_knowledge_tables` | PASS | 112 test, 8 skip |
| `unittest` `04_ontology` | PASS | 64 test, termasuk Pellet/SWRL |

Test Node mencakup:

- 8 test client Node–Java: sukses, error envelope, invalid JSON, retry 503,
  timeout tanpa retry, server mati, header request ID, body kategori.
- 19 test engine: exact/kanonik, specificitas, CF, completeness/coverage,
  confidence, determinism, dataset kosong, evidence floor, faktor fase.
- 12 test scoring/parsing/util: termasuk validasi dan trim `phaseId`.

## 2. Kesehatan dan konsistensi

| Pemeriksaan | Hasil |
|---|---|
| `/api/health/live` | `UP` |
| `/api/health/fuseki` | `UP`, 18.981 triple |
| `/api/health/ontology` | `OK` |
| `checks.fileMatchesJava` | `true` |
| `checks.fusekiHasV2Fingerprint` | `true` |
| `/api/health/ready` | `UP` |
| Dependency Fuseki/Reasoning/Ontology | `UP` / `UP` / `UP-OK` |
| Java loaded/ready/consistent | `true` / `true` / `true` |
| Checksum file = Java | `true` |
| Class/individual/object/data property | 87 / 1.368 / 31 / 33 |

Kategori Openllet:

```text
PenyakitJamur      34
PenyakitBakteri     7
PenyakitVirus      10
PenyakitOomycete    1
PenyakitFitoplasma  1
PenyakitNematoda    0
PenyakitLainnya     0
Unclassified        0
```

Jumlah data API:

```text
plants = 7
diseases = 53
Padi symptoms = 26
Padi phases = 2
UbiKayu phases = 0
```

## 3. Kontrak API dan edge case

Semua 18 skenario pemeriksaan manual lulus:

| Kasus | Expected | Hasil |
|---|---|---|
| Diagnosis Blas | 200, Blas top-1, skor 0,7466, `TINGGI` | PASS |
| Evidence Blas | 3 bukti | PASS |
| `explanation` | terisi | PASS |
| `reasoning.modelVersion` | `forward-chaining-cf-v1` | PASS |
| `topN=1` | 1 kandidat, message “Menampilkan 1 dari 4” | PASS |
| ID duplikat | 200 + `DUPLICATE_SYMPTOM_IDS_IGNORED` | PASS |
| Tanaman tak dikenal | 404 `NOT_FOUND` | PASS |
| Gejala tanaman lain | 400 `INVALID_REQUEST` | PASS |
| `symptomIds` kosong | 400 `INVALID_REQUEST` | PASS |
| `topN=0` | 400 `INVALID_REQUEST` | PASS |
| `topN=11` | 400 `INVALID_REQUEST` | PASS |
| Gejala tak dikenal | 400 `INVALID_REQUEST` | PASS |
| JSON invalid | 400 `INVALID_REQUEST` | PASS |
| Endpoint tak dikenal | 404 `NOT_FOUND` | PASS |
| `GET /api/phases?plantId=Padi` | 200, 2 fase | PASS |
| `GET /api/phases?plantId=UbiKayu` | 200, 0 fase | PASS |
| Diagnosis Hawar Pelepah + fase anakan | 200, `phaseMatch=match` | PASS |
| Fase milik tanaman lain | 400 `INVALID_REQUEST` | PASS |

Kasus ambigu kanonik:

```text
top = PenyakitHawarDaunBakteriPadi
score = 0.6385
confidence = SEDANG
evidence = 1 exact + 2 canonical (Bercak daun, Klorosis daun)
harness rank = 1; baseline legacyRank = 3
```

## 4. Evaluasi reasoning

Sumber: `05_reasoning_tests/results.json`, dijalankan 19 Nov 2026.

| Metrik | Baseline 0,7/0,3 | Model baru |
|---|---:|---:|
| Top-1 fokus (gold+ambiguous) | 0,6364 | **0,9091** |
| Top-3 fokus | 0,9091 | **1,0000** |
| MRR fokus | 0,7424 | **0,9545** |
| Top-1 ambiguous | 0,0000 | **0,7500** |
| Top-3 ambiguous | 0,7500 | **1,0000** |
| Top-1 gold | 1,0000 | 1,0000 |
| Top-1 sanity | 1,0000 | 1,0000 |
| Negative tests | — | 5/5 |
| Determinism | — | stabil |

Jumlah kasus:

- 14 gold
- 8 ambiguous
- 53 sanity
- 5 negative
- Total normal: 75

Dua kasus top-1 meleset, tetapi masih top-3:

- `PADI-PURE-HDB-01` → rank 2.
- `KACANGTANAH-PURE-KARAT-01` → rank 2.

Penyebab: penyakit dengan gejala lebih sedikit mendapat coverage lebih tinggi,
atau exact match mengalahkan kanonik. Ini bukan kegagalan sistem, tetapi bahan
kalibrasi berikutnya.

## 5. Performa

Dua pengukuran:

1. Harness `node run.mjs --perf` (20 sampel diagnosis):
   - p50 **35,6 ms**
   - p95 **64,9 ms**

2. Uji beban sequential 50 request diagnosis:
   - error: 0
   - min **19,1 ms**
   - p50 **22,7 ms**
   - p95 **35,8 ms**
   - max **123,4 ms**
   - rata-rata **26,0 ms**

Catatan: pengukuran dilakukan di satu mesin, tanpa konkurensi. Angka ini bukan
kapasitas produksi.

## 6. Ketahanan

### Java mati

| Pemeriksaan | Hasil |
|---|---|
| Diagnosis | HTTP `200`, `DEGRADED` |
| Kategori | `null` |
| Warning | `REASONING_UNAVAILABLE` |
| Kandidat | tetap muncul (4) |
| `/api/health/ontology` | `DOWN` |
| `/api/health/ready` | HTTP `503`, `DEPENDENCY_UNAVAILABLE` |

Setelah Java dinyalakan lagi, readiness kembali `UP`.

### Fuseki mati

| Pemeriksaan | Hasil |
|---|---|
| Diagnosis | HTTP `503`, `FUSEKI_UNAVAILABLE` |
| `/api/health/ready` | HTTP `503`, `DEPENDENCY_UNAVAILABLE` |
| Fuseki dependency | `DOWN` |
| Reasoning dependency | `UP` |
| `/api/health/ontology` | `DOWN`, warning Fuseki |

Setelah Fuseki dinyalakan lagi, readiness kembali `UP`, triple tetap 18.981.

## 7. Observability

Request ID `m7-check-123`:

```text
node.meta.requestId = m7-check-123
java.meta.requestId = m7-check-123
```

Log Node (607 baris) tidak menunjukkan `500` atau `Unhandled error`. Hanya ada
dua warning degradasi yang memang disengaja saat Java dimatikan.

## 8. Temuan

1. **Tidak ada kegagalan kontrak.** Semua endpoint, validasi, envelope, dan
   fallback berjalan sesuai dokumen.
2. **Kanonik bekerja.** Kasus ambigu yang gagal di baseline (top-1 0%) menjadi
   75% top-1 dan 100% top-3.
3. **Dua kasus masih rank 2.** Perlu kalibrasi coverage/prior penyakit.
4. **Gold dan sanity 100% karena di-seed.** Bukan akurasi independen.
5. **Ontology masih sementara.** ID dan jumlah bisa berubah saat TTL final.
6. **Uji performa belum konkuren.** Belum ada load test paralel.
7. **`/api/ontology/reload` belum berautentikasi.** Aman selama bind localhost.
8. **Warning `DISEASE_CATEGORY_UNCLASSIFIED` muncul wajar** saat kandidat berisi
   penyakit tanpa patogen yang dikenal.
9. **Data fase belum lengkap.** Hanya 5 dari 7 tanaman dan 12 tautan
   penyakit–fase; Ubi Jalar/Ubi Kayu belum punya fase. Karena itu fase dibuat
   opsional dan tidak menjadi filter keras.

## 9. Rekomendasi

1. Verifikasi 14 kasus gold ke halaman DOC002 dan ubah `verified` menjadi
   `true`.
2. Tambah 10–20 kasus gold baru, terutama untuk Ubi Kayu yang datanya tipis.
3. Jalankan ulang `generate-sanity.mjs` dan `run.mjs` setelah ontology final.
4. Kalibrasi coverage/prior untuk dua kasus rank 2.
5. Tambah uji konkuren (mis. 10–20 request paralel) bila diperlukan.
6. Pertimbangkan token admin untuk `/api/ontology/reload` jika port dibuka.
7. Lengkapi tautan `menyerangFase` untuk Ubi Jalar, Ubi Kayu, dan penyakit
   yang belum punya fase agar input fase lebih berguna.

## 10. Reproduksi

```powershell
# Service harus hidup: Fuseki :3030, Java :8082, Node :3000

cd .\06_backend\node-api
npm run typecheck
npm test
npm run build

cd ..\reasoning-api
.\mvnw.cmd test

cd ..\..\
.\06_backend\scripts\smoke-test.ps1
.\06_backend\scripts\integration-test.ps1

cd .\05_reasoning_tests
node run.mjs --perf
```
