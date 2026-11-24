# KBR — Sistem Pakar Penyakit Tanaman Pangan

Knowledge base dan prototipe expert system untuk diagnosis awal penyakit pada
**tujuh tanaman pangan tropis**: padi, kedelai, jagung, ubi jalar, ubi kayu,
kacang tanah, dan kacang hijau.

Sumber utama adalah dua buku penyakit tanaman. Pipeline mengekstrak tabel
pengetahuan, membangun ontologi OWL 2, menambahkan aturan SWRL, lalu menyediakan
backend diagnosis: Node/Express untuk retrieval + scoring, Java/Spring Boot
(OWL API + Openllet) untuk inferensi kategori, dan Apache Jena Fuseki untuk
menyimpan RDF dan melayani SPARQL read-only.

## Status

| Bagian | Status |
|---|---|
| Knowledge tables + audit sumber | Selesai |
| Ontologi OWL 2 kanonik | Selesai |
| Enrichment + deskripsi + kondisi tumbuh | Selesai |
| Reasoning Pellet + 4 aturan SWRL | Selesai |
| Backend Node + Java reasoning + Fuseki | Selesai |
| Endpoint diagnosis + ranking + evaluasi | Selesai |
| Frontend TaniCare (React/Vite) | MVP |

## Struktur repository

| Path | Isi |
|---|---|
| `00_sumber_data/` | Buku sumber dan pratinjau teks |
| `01_knowledge_sources/` | Registry sumber internal/eksternal |
| `02_extraction/` | Ekstraksi teks, chunk DOC005, dan test ekstraksi |
| `03_knowledge_tables/` | Tabel gejala, pengendalian, patogen, varietas, metadata, audit, dan deskripsi |
| `04_ontology/` | Generator TBox/ABox, ontology kanonik, enrichment, SWRL, dan test |
| `05_reasoning_tests/` | Harness evaluasi diagnosis (75 kasus + baseline) |
| `06_backend/` | Node/Express API + Java reasoning API (OWL API + Openllet) + Fuseki |
| `07_frontend/` | Frontend React + Vite + TypeScript (TaniCare) |
| `08_documentation/` | Kontrak, runbook, laporan test, dan dokumentasi reasoning |

## Angka kunci

- Ontologi kanonik: **16.732 triple**, **1.204 individu**, **87 kelas**,
  **29 object property**, **53 penyakit**, **7 tanaman**, **78 tautan penyakit-patogen**.
- `ontology_md.ttl`: **24.833 triple**, **1.366 individu**, **4 aturan SWRL**,
  termasuk inferred axiom Pellet (kategori penyakit, tipe, `disjointWith`,
  `menyerangBagian`).
- **240 baris gejala** menjadi **171 pengamatan kanonik**; **58** belum dipetakan.
- **226 tautan `dikendalikanDengan`**; **37** baris pengendalian belum dipetakan.
- **40 varietas**, **12 tautan fase**, **17 baris metadata terkurasi**.
- **68 observasi lingkungan eksternal** dan **92 tautan kondisi**.
- **942 fakta enrichment** dan **561 deskripsi `rdfs:comment`**.
- Audit terbaru: **severity 39**, **fase 42**, **varietas tahan 45**, dan
  **nama Inggris 43** masih kosong. Angka ini best-effort, bukan target yang
  dipaksakan.

## Menjalankan pipeline

Dari root repository:

```powershell
pip install -r 04_ontology/requirements.txt

# bahan teks dan tabel pengetahuan
python 02_extraction/build_doc005_chunks.py
python 03_knowledge_tables/src/build_source_gap_audit.py
python 03_knowledge_tables/src/build_external_env_facts.py
python 03_knowledge_tables/src/build_coverage_matrix.py

# ontologi kanonik
python 04_ontology/build_ontology.py

# enrichment dan artefak pendukung
python 03_knowledge_tables/src/build_enrichment_facts.py
python 03_knowledge_tables/src/build_descriptions.py
python 04_ontology/build_ontology_md.py

# audit akhir
python 03_knowledge_tables/src/build_kb_completeness_report.py
python 03_knowledge_tables/src/build_mapping_triage.py
```

Urutan ini penting: `build_ontology_md.py` membaca `ontology.ttl` dan CSV
enrichment; jangan mengedit `ontology_md.owl` secara manual.

Untuk membangun ulang tabel dari sumber mentah, lihat urutan lengkap di
`03_knowledge_tables/README.md`.

## Verifikasi

```powershell
cd 03_knowledge_tables
python -m unittest discover -s tests -p "test_*.py"

cd ../04_ontology
python -m unittest discover -s tests -p "test_*.py"
```

Status terakhir:

- `03_knowledge_tables`: **115 test OK**, 8 skipped.
- `04_ontology`: **68 test OK**, termasuk test Pellet/SWRL.

Test SWRL membutuhkan Java dan `owlready2`. Jika Java tidak tersedia, test
reasoning di-skip.

## Menjalankan backend

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
cd ..\node-api
npm install
npm run dev
```

Endpoint utama:

- Node `:3000` — `GET /api/plants`, `/api/diseases`, `/api/symptoms`,
  `/api/phases`, `POST /api/diagnosis`, dan `/api/health/*`.
- Java `:8082` — `GET /api/reasoning/status`,
  `POST /api/reasoning/disease-categories`, `POST /api/ontology/reload`.
- Fuseki `:3030` — dataset `plant-kb` (SPARQL read-only).

Detail konfigurasi, kontrak, dan troubleshooting ada di `06_backend/README.md`.

## Status backend (M5–M7)

- **M5 - Reasoning diagnosis:** engine exact/kanonik + certainty factor,
  `confidence`/`evidence`/`explanation`, input varietas + fase pertumbuhan
  opsional, harness validasi. Lihat `08_documentation/reasoning.md` dan
  `08_documentation/cf-derivation.md`.
- **M6 — Integrasi Node ↔ Java:** kontrak, client HTTP + retry/timeout, health
  checksum/fingerprint, request id, dan integration test.
  Lihat `08_documentation/node-java-contract.md` dan
  `08_documentation/node-java-runbook.md`.
- **M7 - Pengujian dan evaluasi:** 40 test Node, 11 test frontend, 4 test Java,
  115 test `03_knowledge_tables` (8 skip), 68 test `04_ontology`,
  smoke/integration test (termasuk fase pertumbuhan), 75 kasus evaluasi, dan
  uji ketahanan.
  Lihat `08_documentation/backend-test-report.md`.

## Batasan

- Backend tidak mengeksekusi SWRL; aturan dijalankan offline dengan Pellet.
  Java hanya memakai Openllet untuk konsistensi dan inferensi kategori.
- Ranking dan scoring diagnosis dijalankan di Node
  (`forward-chaining-cf-v1`); Java tidak menghitung skor.
- Metadata severity/fase/varietas/nama Inggris hanya diisi bila sumber
  menyatakan secara eksplisit.
- Pengendalian 17 penyakit ubi kayu memakai fallback `pengendalianUmum`
  tingkat tanaman.
- `00_sumber_data/02_PenyakitTanamanPangan.md` adalah pratinjau; teks lengkap
  DOC002 yang dipakai audit ada di `02_extraction/llamaparse/baseline/`.

## Dokumentasi lanjutan

- `02_extraction/README.md` — ekstraksi dan chunking.
- `03_knowledge_tables/README.md` — aturan verbatim, tabel, audit, dan deskripsi.
- `04_ontology/README.md` — desain OWL, angka build, demo Protégé, dan SWRL.
- `06_backend/README.md` — API, konfigurasi, dan kontrak integrasi.
- `03_knowledge_tables/reports/KB_COMPLETENESS.md` — dashboard gap KB.
- `03_knowledge_tables/reports/SOURCE_GAP_AUDIT.md` — audit sumber per gap.
- `03_knowledge_tables/reports/MAPPING_TRIAGE.md` — triage pemetaan gagal.
