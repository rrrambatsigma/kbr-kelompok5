# Reasoning Tests — Milestone 5

Folder ini berisi verifikasi integrasi dan kasus uji reasoning diagnosis.
Ontology yang dipakai adalah **ontology gabungan** dari branch
`feat/ontology-baru` (`04_ontology/ontology_md.ttl`, 24.833 triple).

> **Diperbarui 24 November 2026:** artefak `ontology_md.ttl` sekarang memuat
> **inferred axiom Pellet** dari Protégé (kategori penyakit, tipe individu,
> `owl:disjointWith`, `menyerangBagian`). Triple naik dari 19.021 ke **24.833**.
> Status di bawah diverifikasi ulang dengan dataset Fuseki baru
> (`load-ontology.ps1 -Reset`), termasuk `smoke-test.ps1`,
> `integration-test.ps1`, dan `node run.mjs`.

## Status verifikasi integrasi (24 Nov 2026)

| Komponen | Versi / Nilai | Status |
|---|---|---|
| Ontology | `ontology_md.ttl`, 24.833 triple (termasuk inferred) | v3 + Pellet |
| SHA-256 ontology | `2085d0a7f36841e6d2b5ce04a2d79b48028f02e1d8a504037be8b8866bf5cbc4` | cocok dengan Java |
| Fuseki | `plant-kb`, read-only, port 3030 | UP |
| Java reasoning API | Openllet, port 8082 | UP, konsisten |
| Node API | port 3000 | UP |
| Smoke test | plants=7, diseases=53, Padi symptom concepts=12, Padi varieties=4 | OK |

Pemeriksaan yang lolos:

- [x] `totalTriples = 24.833`
- [x] Fingerprint v2: `deskripsiPenyakit = 53`, `memilikiKondisiTumbuh = 9`
- [x] Java memuat `ontology_md.ttl` dan checksum-nya sama dengan file
- [x] Ontology konsisten (Openllet)
- [x] Kategori: Jamur 34, Bakteri 7, Virus 10, Oomycete 1, Fitoplasma 1,
      Nematoda 0, Lainnya 0; 0 penyakit belum berkategori
- [x] `/api/health/ready` = UP
- [x] `npm run typecheck`, `npm test` (40 test) hijau
- [x] `mvnw test` (4 test, termasuk golden Openllet) hijau
- [x] `smoke-test.ps1` OK

## Ringkasan data ontology sementara

| Item | Jumlah |
|---|---:|
| Pengamatan gejala yang dipakai penyakit | 229 |
| Pengamatan dengan `memilikiGejalaKanonik` | 171 |
| Konsep kanonik yang terpakai | 24 |
| Penyakit dengan gejala | 53 |
| Tautan `dipengaruhiOleh` | 82 |
| Tautan `dikendalikanDengan` | 226 |
| Tautan `disebabkanOleh` | 76 |
| `deskripsiPenyakit` | 53 |
| `tingkatKeparahan` | 14 |

Sebaran per tanaman:

| Tanaman | Penyakit | Pengamatan gejala |
|---|---:|---:|
| Jagung | 5 | 28 |
| Kacang hijau | 3 | 6 |
| Kacang tanah | 4 | 23 |
| Kedelai | 15 | 88 |
| Padi | 5 | 26 |
| Ubi jalar | 4 | 30 |
| Ubi kayu | 17 | 30 |

## Layer data ternormalisasi (Langkah 2)

`getDiagnosisDataset(plantId)` sekarang mengembalikan satu objek
`DiagnosisDataset`:

```ts
interface DiagnosisDataset {
  plant: PlantSummary;
  diseases: DiagnosisDisease[];
  stats: DiagnosisDatasetStats;
}
```

Setiap penyakit membawa:

- `symptoms[]` dengan `canonical: { id, iri, label } | null`
- `riskFactors[]` dari `dipengaruhiOleh`
- `description` dari `deskripsiPenyakit`
- `severity` dari `tingkatKeparahan`

Statistik dataset per tanaman (22 Nov 2026):

| Tanaman | Penyakit | Pengamatan | Punya kanonik | Konsep kanonik |
|---|---:|---:|---:|---:|
| Padi | 5 | 26 | 20 | 12 |
| Kedelai | 15 | 87 | 65 | 21 |
| Jagung | 5 | 28 | 16 | 11 |
| Ubi jalar | 4 | 30 | 19 | 13 |
| Ubi kayu | 17 | 30 | 29 | 17 |
| Kacang tanah | 4 | 22 | 18 | 12 |
| Kacang hijau | 3 | 6 | 4 | 4 |

Periksa dataset tanpa mengubah kode:

```powershell
cd .\06_backend\node-api
npm run dataset:inspect -- Padi
```

Kontrak engine ada di `src/lib/reasoning/types.ts`:

- `ReasoningCandidate` - kandidat + skor + keyakinan + evidence
- `ReasoningEvidence` - union `exact` / `canonical` / `condition`
- `ScoreComponents` - `evidence`, `completeness`, `coverage`
- `ReasoningOptions` - `topN`, `canonicalWeight`, `evidenceFloor`
- `ReasoningResult` - `candidates`, `totalMatched`, `warnings`, `modelVersion`

Kosakata ontology dipusatkan di `src/config/ontology.ts`:

- **Wajib**: `TanamanPangan`, `Penyakit`, `Gejala`; `menyerangTanaman`,
  `memilikiGejala`.
- **Opsional**: `GejalaKanonik`, `Pengendalian`, `FaktorRisiko`;
  `memilikiGejalaKanonik`, `dikendalikanDengan`, `disebabkanOleh`,
  `dipengaruhiOleh`, `deskripsiPenyakit`, `tingkatKeparahan`.

Refactor layer data tidak mengubah skor: ketiga kasus baseline menghasilkan
skor yang sama persis seperti sebelum perubahan.

## Baseline diagnosis sebelum M5

File: `baseline/before.json`. Diambil dari API yang berjalan dengan skor lama
(`0,7 × matchRatio + 0,3 × coverage`).

| Kasus | Input | Hasil lama |
|---|---|---|
| `PADI-BLAS-01` | 3 gejala khas Blas | Blas skor 0,85 (3/6) |
| `PADI-BLAS-02` | BercakDaun milik HDB + 2 gejala khas Blas | Blas 0,5667 (2/6); HDB 0,2667 (1/9) |
| `PADI-BERCAK-01` | 1 gejala generik BercakDaun (milik HDB) | hanya HDB 0,7333 (1/9) |

### Gap yang terlihat

1. **Pencocokan masih berdasarkan ID pengamatan, bukan konsep kanonik.**
   Pada `PADI-BLAS-02`, gejala `BercakDaun` milik HDB tidak dihitung sebagai
   bukti untuk Blas, padahal keduanya terhubung ke konsep `BercakDaun`.
2. **Satu gejala generik hanya memunculkan satu penyakit.** Pada
   `PADI-BERCAK-01`, Blas/Hawar Pelepah/Kerdil juga memiliki `BercakDaun`,
   tetapi tidak muncul karena ID-nya berbeda.
3. **Tidak ada `confidence`, `evidence`, atau `explanation`** di response.
4. **Skor belum mempertimbangkan specificitas gejala.** Gejala umum dan gejala
   khas diberi bobot sama.

## Cara menjalankan ulang

```powershell
# 1. Fuseki (hentikan dulu bila sedang jalan)
.\06_backend\scripts\load-ontology.ps1 -Reset
.\06_backend\scripts\start-fuseki.ps1

# 2. Java
cd .\06_backend\reasoning-api
.\mvnw.cmd spring-boot:run

# 3. Node
cd .\06_backend\node-api
npm run dev

# 4. Verifikasi
.\06_backend\scripts\smoke-test.ps1
```

Service yang berjalan setelah verifikasi: Fuseki (3030), Java (8082), Node (3000).

Menghentikan service:

```powershell
Get-NetTCPConnection -State Listen -LocalPort 3030,8082,3000 |
  ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

## Engine reasoning (Langkah 3)

Engine ada di `06_backend/node-api/src/lib/reasoning/`:

- `specificity.ts` - bobot gejala khas vs umum.
- `rules.ts` - index observasi/kanonik dan `df`.
- `certainty.ts` - CF, skor, klasifikasi keyakinan.
- `engine.ts` - `reason(dataset, selectedIds)`.
- `explain.ts` - narasi alasan.

Rumus:

```text
spec = 0.5 + 0.5 * log((N+1)/(df+1)) / log(N+1)
w    = min(0.9, bobot_dasar * spec)
CF   = 1 - produk(1 - w)
score = CF * (0.7 + 0.3*completeness) * (0.5 + 0.5*coverage)
```

`coverage = matched / max(total gejala penyakit, 4)`. Penyebut minimum 4
mencegah penyakit dengan 1-2 gejala tercatat mendapat coverage 1.0.

Specificitas memakai `df` konsep kanonik (bukan ID pengamatan), karena
pengamatan di ontology ini spesifik per penyakit.

Perbandingan sebelum/sesudah:

| Kasus | Sebelum | Sesudah |
|---|---|---|
| `PADI-BLAS-01` | Blas 0,85; 1 kandidat | Blas 0,7466 `TINGGI`; 4 kandidat |
| `PADI-BLAS-02` | Blas 0,5667; HDB 0,2667 | Blas 0,745 `TINGGI`; HDB 0,2448 `RENDAH` |
| `PADI-BERCAK-01` | hanya HDB 0,7333 | HDB 0,306 `RENDAH`; Blas/Kerdil/Hawar Pelepah muncul |

Temuan:

- `PADI-BLAS-02`: BercakDaun milik HDB sekarang menjadi bukti **kanonik**
  untuk Blas (2 exact + 1 kanonik), sesuai tujuan M5.
- `PADI-BERCAK-01`: empat penyakit Padi yang punya `BercakDaun` muncul;
  HDB tetap top karena exact match.
- Satu bukti selalu `RENDAH`; `TINGGI` butuh minimal 2 bukti.
- Saat Java dimatikan, diagnosis tetap `200` dengan `DEGRADED`,
  `category = null`, dan warning `REASONING_UNAVAILABLE`.

Baseline sesudah engine: `baseline/after.json`.

Test: **40 test** lulus (termasuk test reasoning dan client Node-Java).

## Validasi (Langkah 4)

Harness ada di folder ini:

```text
cases/manual.json     14 kasus gold
cases/ambiguous.json   8 kasus lintas-penyakit (uji pencocokan kanonik)
cases/sanity.json     53 kasus generated (regression)
cases/negative.json    5 kasus validasi/error
generate-sanity.mjs   generator sanity
run.mjs               runner + metrik + baseline
results.json          output mesin
results.md            laporan manusia
```

Menjalankan (Fuseki, Java, dan Node harus hidup):

```powershell
cd .\05_reasoning_tests
node run.mjs --perf
```

Regenerate sanity setelah ontology berubah:

```powershell
node generate-sanity.mjs
```

Generator memilih observasi yang punya `memilikiGejalaKanonik` lebih dulu,
lalu melengkapi dengan observasi lain. Label dan jumlah gejala mengikuti
ontology yang sedang dimuat Node API, jadi jalankan setelah reload Fuseki.

Opsi lain:

```powershell
node run.mjs --no-thresholds
node run.mjs --base-url http://127.0.0.1:3000
node run.mjs --out hasil-lain
```

Hasil 24 Nov 2026 (ontology `2085d0a7...`):

| Metrik | Baseline 0,7/0,3 | Model baru |
|---|---:|---:|
| Top-1 fokus (gold + ambiguous) | 0,636 | **0,909** |
| Top-3 fokus | 0,909 | **1,000** |
| MRR fokus | 0,742 | **0,955** |
| Top-1 ambiguous | 0,000 | **0,750** |
| Top-3 ambiguous | 0,750 | **1,000** |
| Top-1 gold | 1,000 | 1,000 |
| Top-1 sanity | 1,000 | 1,000 |
| Negative tests | - | 5/5 lulus |

Dua kasus ambiguous masih rank 2 (masih top-3):
`PADI-PURE-HDB-01` dan `KACANGTANAH-PURE-KARAT-01`. Detailnya ada di
`results.md`.

Catatan penting:

- Kasus `gold` masih di-seed dari ontology (`source: ontology-temporary`,
  `verified: false`). Verifikasi halaman DOC002 sebelum mengklaim akurasi
  independen.
- Kasus `sanity` dibuat dari gejala penyakit itu sendiri; hanya regression.
- Kasus `ambiguous` sengaja mencampur gejala generik milik penyakit lain;
  inilah yang membedakan model lama (0% top-1) dari model baru (75% top-1).
- Baseline dihitung ulang pada kasus yang sama, bukan dari `before.json`.
- UI mengirim ID **konsep kanonik**; kasus `gold`/`ambiguous`/`sanity` tetap
  memakai ID observasi untuk menguji exact-match. Evaluasi dengan pemetaan
  observasi → kanonik (input seperti UI) menghasilkan top-1 fokus **0,909**,
  top-3 **1,000**, dan MRR **0,955** pada ontology `2085d0a7...`.

## Dokumentasi M5

- Metode, arsitektur, rumus, dan validasi: `../08_documentation/reasoning.md`
- Skenario demo + perintah: `../08_documentation/demo-m5.md`

## Integrasi M6

- Kontrak Node ↔ Java: `../08_documentation/node-java-contract.md`
- Runbook operasional: `../08_documentation/node-java-runbook.md`
- Test integrasi: `../06_backend/scripts/integration-test.ps1`

## Selanjutnya

- [x] Layer data: `memilikiGejalaKanonik`, `dipengaruhiOleh`,
      `deskripsiPenyakit`, `tingkatKeparahan` di `knowledge.service.ts`.
- [x] Engine reasoning: rule + certainty factor + specificitas.
- [x] Penjelasan: `evidence`, `explanation`, `confidence`.
- [x] Validasi: kasus gold/ambiguous/sanity/negative + metrik + baseline.
- [x] Dokumentasi dan demo M5 (Langkah 5).
- [x] Integrasi Node–Java M6: kontrak, health checksum, request id, integration test.

Catatan: karena ontology masih sementara, kasus uji ditandai
`"ontology": "temporary-v2"` agar mudah diperbarui saat ontology final masuk.
