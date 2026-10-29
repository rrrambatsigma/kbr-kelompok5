# Tahap 1 — PDF Extraction & Document Parsing

Pipeline lokal untuk mengubah PDF sumber proyek KBR menjadi data teks terstruktur
yang mempertahankan identitas dokumen, nomor halaman PDF, konteks bab/subbab,
dan catatan masalah ekstraksi.

Status: `DOC002` (`PenyakitTanamanPangan.pdf`) sudah diekstrak dengan LlamaParse
(lihat bagian 15) dan menggantikan output PyMuPDF setelah gate perbandingan
lolos. `DOC001` (hortikultura) berada di luar lingkup proyek dan sudah dihapus
dari registry, sehingga pipeline hanya memproses satu dokumen. Perintah di bawah
tetap dijalankan manual oleh pengguna; pipeline tidak berjalan otomatis.

---

## 1. Batas ruang lingkup

Termasuk:

- penemuan PDF sumber;
- ekstraksi teks per halaman;
- pemeliharaan nomor halaman PDF 1-based;
- parsing heading, paragraf, list item, dan tabel secara konservatif;
- pembersihan teks terbatas;
- metadata tingkat dokumen;
- catatan masalah dan validasi kualitas;
- penyimpanan JSON/JSONL.

Tidak termasuk:

- OCR otomatis;
- RAG, embedding, vector database, semantic search, BM25;
- LLM atau API eksternal;
- ontology OWL, reasoner, backend, frontend;
- ekstraksi fakta penyakit menjadi relasi ontology;
- diagnosis atau rekomendasi pengobatan.

---

## 2. Dependensi

- Python 3.9 atau lebih baru.
- PyMuPDF (`PyMuPDF>=1.23,<2`).

Tidak ada dependensi jaringan. Pipeline dapat berjalan offline setelah PyMuPDF
terpasang.

PyMuPDF diimpor secara lazy. Modul parser dan validator dapat diuji tanpa
PyMuPDF, tetapi ekstraksi PDF memerlukannya.

---

## 3. Struktur input dan output

### Input

```text
01_knowledge_sources/pdf_original/
└── PenyakitTanamanPangan.pdf           -> DOC002

01_knowledge_sources/source_metadata/
└── manual_metadata.json                -> opsional, diisi manual
```

Registry dokumen ada di `02_extraction/pdf_pipeline/config.py` dan saat ini hanya
memuat `DOC002`. PDF yang tidak terdaftar akan dilaporkan dan dilewati.

`manual_metadata.json` hanya boleh diisi dari halaman judul, kolofon, atau
sumber bibliografis yang benar-benar tersedia. Jangan menebak.

### Output

```text
01_knowledge_sources/source_metadata/
└── manifest.json

02_extraction/extracted_text/
├── DOC002.blocks.jsonl
├── DOC002.chunks.jsonl
└── DOC002.pages.jsonl

02_extraction/extraction_notes/
├── DOC002.extraction_notes.json
├── extraction_report.md
└── validation_report.json
```

Peran file:

| File | Peran |
|---|---|
| `manifest.json` | Sumber utama metadata tingkat dokumen. |
| `*.blocks.jsonl` | Format utama data terstruktur; satu baris satu blok. |
| `*.pages.jsonl` | Audit teks mentah per halaman dan status halaman. |
| `*.extraction_notes.json` | Masalah, halaman bermasalah, tabel, struktur. |
| `extraction_report.md` | Ringkasan manusiawi. |
| `validation_report.json` | Hasil `validate`; dibuat ulang setiap validasi. |

---

## 4. Skema metadata

### 4.1 Metadata dokumen (`manifest.json`)

Field utama:

| Field | Tipe | Keterangan |
|---|---|---|
| `document_id` | string | `DOC002`. |
| `document_name` | string | Nama file PDF. |
| `source_path` | string | Path relatif terhadap root proyek. |
| `source_sha256` | string | Hash sebelum ekstraksi. |
| `source_sha256_after` | string | Hash setelah ekstraksi. |
| `file_size_bytes` | integer | Ukuran file. |
| `title` | string/null | Hanya manual atau metadata PDF. |
| `authors` | array | Hanya manual atau metadata PDF. |
| `publication_year` | integer/null | Hanya manual; tidak dari CreationDate. |
| `publisher` | string/null | Hanya manual. |
| `language` | string/null | Hanya manual. |
| `total_pdf_pages` | integer/null | Jumlah halaman PDF. |
| `document_type` | string | `pdf`. |
| `extraction_status` | string | Lihat status di bawah. |
| `notes` | array | Catatan dokumen. |
| `pdf_metadata` | object | Metadata mentah PyMuPDF. |
| `metadata_source` | object | Asal tiap field metadata. |
| `statistics` | object | Statistik ekstraksi. |
| `output_files` | object | Path output relatif. |

Status dokumen:

- `completed`
- `completed_with_warnings`
- `no_text_extracted`
- `partial`
- `failed`

### 4.2 Blok konten (`*.blocks.jsonl`)

```json
{
  "schema_version": "1.0.0",
  "block_id": "DOC002_P001_B001",
  "document_id": "DOC002",
  "page_number": 1,
  "printed_page_number": null,
  "chapter": null,
  "section": null,
  "subsection": null,
  "content_type": "paragraph",
  "sequence_number": 1,
  "text": "Teks hasil ekstraksi.",
  "extraction_status": "extracted",
  "parsing_notes": [],
  "bbox": [72.0, 90.0, 523.0, 120.0],
  "cleaning_actions": [],
  "raw_text": null,
  "table": null
}
```

- `block_id`: `{document_id}_P{page:03d}_B{page_block:03d}`.
- `sequence_number`: global per dokumen, mulai 1.
- `page_number`: nomor halaman PDF, 1-based.
- `printed_page_number`: string atau `null`.
- `content_type`: `chapter_heading`, `section_heading`, `subsection_heading`,
  `heading_unclassified`, `paragraph`, `list_item`, `table`.
- `extraction_status`: `extracted` atau `needs_manual_review`.
- `bbox`: koordinat PyMuPDF dalam points; origin kiri-atas.
- `raw_text`: hanya diisi jika dehyphenation atau penghapusan karakter kontrol
  benar-benar dilakukan pada blok tersebut.
- `table`: payload tabel atau `null`.

Payload tabel:

```json
{
  "detection_method": "pymupdf_find_tables",
  "row_count": 5,
  "column_count": 4,
  "cells": [["...", "..."]],
  "bbox": [0.0, 0.0, 0.0, 0.0],
  "review_required": true,
  "review_reasons": ["empty_cells_high"]
}
```

`text` pada blok tabel adalah pratinjau manusiawi. Data utama tabel adalah
`table.cells`.

### 4.3 Halaman (`*.pages.jsonl`)

```json
{
  "schema_version": "1.0.0",
  "document_id": "DOC002",
  "page_number": 1,
  "page_width": 595.28,
  "page_height": 841.89,
  "page_rotation": 0,
  "raw_text": "...",
  "text_char_count": 1234,
  "block_count": 4,
  "image_count": 0,
  "image_coverage_ratio": 0.0,
  "printed_page_number": null,
  "printed_page_number_source": null,
  "extraction_status": "text_extracted",
  "flags": [],
  "notes": []
}
```

Status halaman:

- `text_extracted`
- `no_text_extracted`
- `extraction_error`

Flag halaman:

- `likely_scanned_image_only`
- `ocr_candidate`
- `possible_multi_column_layout`
- `repeated_header_candidate`
- `repeated_footer_candidate`

---

## 5. Perbedaan nomor halaman PDF dan nomor halaman tercetak

- `page_number` selalu nomor halaman PDF, 1-based. Halaman pertama PDF = 1.
- `printed_page_number` adalah nomor yang tercetak di dokumen, misalnya `xii`
  atau `12`.
- Deteksi nomor tercetak memakai urutan prioritas:
  1. PDF page labels (`get_page_labels`) jika tersedia;
  2. urutan teks header/footer yang konsisten minimal 3 halaman;
  3. `null` jika tidak yakin.
- Nomor tercetak tidak pernah menggantikan `page_number`.

---

## 6. PDF hasil scan

Jika halaman tidak menghasilkan teks:

- `extraction_status` halaman menjadi `no_text_extracted`;
- jika ada gambar, halaman diberi flag `ocr_candidate`;
- jika gambar menutupi sebagian besar halaman, diberi flag
  `likely_scanned_image_only`;
- dokumen yang seluruh halamannya tanpa teks mendapat status
  `no_text_extracted`;
- tidak ada teks tebakan dan tidak ada OCR otomatis.

OCR tidak termasuk implementasi ini. Jika diperlukan, OCR harus disiapkan
sebagai langkah terpisah dengan dependensi dan validasi sendiri.

---

## 7. Tabel dan dokumen multi-kolom

### Tabel

- Deteksi memakai `page.find_tables()` jika tersedia.
- Sel disimpan di `table.cells`.
- Blok teks hanya dibuang jika hampir seluruhnya berada di dalam tabel yang
  memiliki minimal 2 baris dan 2 kolom. Ini untuk mengurangi duplikasi tanpa
  menghilangkan teks ketika tabel gagal diekstrak.
- Tabel ditandai `needs_manual_review` jika:
  - kurang dari 2 baris/kolom;
  - jumlah kolom tidak konsisten;
  - rasio sel kosong tinggi;
  - ada sel sangat panjang;
  - tabel menyentuh batas halaman (kemungkinan lintas halaman).
- Jika deteksi tabel gagal, teks asli tetap disimpan dan masalah dicatat.

### Multi-kolom

- Ekstraksi memakai urutan native PyMuPDF.
- Pipeline hanya menandai `possible_multi_column_layout`.
- Tidak ada reordering otomatis karena dapat mengacaukan urutan baca.
- Halaman yang ditandai harus diperiksa manual.

---

## 8. Aturan pembersihan

Dilakukan:

- normalisasi line ending ke `\n`;
- Unicode NFC;
- penghapusan karakter kontrol tidak valid;
- perapian spasi horizontal;
- penggabungan baris dalam paragraf;
- opsional `--dehyphenate` untuk kata terpotong hyphen di akhir baris.

Tidak dilakukan:

- koreksi ejaan;
- normalisasi nama ilmiah/patogen;
- penghapusan angka, satuan, simbol, tanda baca, referensi silang;
- penghapusan header/footer otomatis;
- peringkasan atau penulisan ulang;
- OCR;
- penggunaan LLM.

Dehyphenation nonaktif secara default karena tanpa kamus tidak dapat dipastikan
apakah hyphen merupakan soft hyphen atau bagian istilah majemuk.

---

## 9. Kebijakan rerun dan backup

- Default: pipeline menolak menimpa output yang sudah ada.
- `--overwrite`: output lama disalin ke
  `02_extraction/extraction_notes/_backups/<timestamp>/`, lalu output baru
  ditulis.
- `--dry-run`: ekstraksi dan parsing dijalankan di memori, tetapi tidak ada file
  yang ditulis.
- `--doc DOC002`: memproses satu dokumen; manifest lama digabung agar entri
  dokumen lain tidak hilang.
- Output ditulis secara atomik per file (`.tmp` lalu `os.replace`).
- PDF dibuka read-only. Hash sebelum dan sesudah ekstraksi dicatat.
- `validation_report.json` lama tidak dihapus otomatis saat ekstraksi ulang.
  Jalankan `validate` lagi setelah setiap ekstraksi agar laporan sesuai output
  terbaru.

---

## 10. Cara menjalankan di PowerShell

Jalankan dari root proyek `E:\kbr-kelompok5`.

### 10.1 Virtual environment (opsional)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Jika aktivasi diblokir:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Jika tidak memakai virtual environment, lewati langkah ini.

### 10.2 Instalasi dependensi

```powershell
python -m pip install --upgrade pip
python -m pip install -r 02_extraction\requirements.txt
```

Cek instalasi:

```powershell
python -c "import pymupdf; print(pymupdf.__version__)"
```

Jika `pymupdf` tidak dapat diimpor, coba:

```powershell
python -c "import fitz; print(fitz.VersionBind)"
```

### 10.3 Uji kering

```powershell
python 02_extraction\run_extraction.py extract --dry-run
```

Tidak menulis output. Berguna untuk memeriksa penemuan PDF dan estimasi hasil.

### 10.4 Ekstraksi

```powershell
python 02_extraction\run_extraction.py extract
```

Satu dokumen saja:

```powershell
python 02_extraction\run_extraction.py extract --doc DOC002
```

Rerun dengan backup:

```powershell
python 02_extraction\run_extraction.py extract --overwrite
```

Opsi lain:

```powershell
# Tanpa deteksi tabel
python 02_extraction\run_extraction.py extract --no-tables

# Tanpa deteksi nomor halaman tercetak
python 02_extraction\run_extraction.py extract --no-printed-page-detection

# Dehyphenation opt-in
python 02_extraction\run_extraction.py extract --dehyphenate
```

### 10.5 Validasi

```powershell
python 02_extraction\run_extraction.py validate
```

Warning dianggap gagal:

```powershell
python 02_extraction\run_extraction.py validate --strict
```

### 10.6 Unit test

```powershell
python -m unittest discover -s 02_extraction\tests -t 02_extraction -v
```

Test parser dan validator tidak memerlukan PyMuPDF karena modul ekstraksi
mengimpor PyMuPDF secara lazy.

---

## 11. Cara memeriksa hasil

```powershell
Get-Content 01_knowledge_sources\source_metadata\manifest.json -Encoding UTF8
Get-Content 02_extraction\extracted_text\DOC002.blocks.jsonl -TotalCount 3 -Encoding UTF8
Get-Content 02_extraction\extraction_notes\DOC002.extraction_notes.json -Encoding UTF8
Get-Content 02_extraction\extraction_notes\extraction_report.md -Encoding UTF8
Get-Content 02_extraction\extraction_notes\validation_report.json -Encoding UTF8
```

Menghitung baris blok:

```powershell
(Get-Content 02_extraction\extracted_text\DOC002.blocks.jsonl | Measure-Object -Line).Lines
```

Melihat isi manifest sebagai object:

```powershell
Get-Content 01_knowledge_sources\source_metadata\manifest.json -Encoding UTF8 |
    ConvertFrom-Json |
    ConvertTo-Json -Depth 6
```

---

## 12. Checklist pemeriksaan manual

1. Cocokkan `total_pdf_pages` di manifest dengan jumlah halaman di PDF reader.
2. Periksa `DOC002.extraction_notes.json`:
   - apakah ada halaman yang gagal diekstrak;
   - apakah ada catatan rekonsiliasi yang perlu ditinjau.
3. Bandingkan halaman sampel 1, 5, 20, 50, 100, dan terakhir antara
   `blocks.jsonl` dan PDF asli.
4. Periksa heading bab/subbab dan konteksnya.
5. Periksa blok tabel, terutama `review_required: true`.
6. Periksa `printed_page_number` terhadap nomor halaman tercetak.
7. Periksa halaman dengan `possible_multi_column_layout`.
8. Periksa halaman dengan `repeated_header_candidate` atau
   `repeated_footer_candidate`.
9. Pastikan `source_sha256` di manifest sama dengan hash PDF asli:
   ```powershell
   Get-FileHash 01_knowledge_sources\pdf_original\PenyakitTanamanPangan.pdf -Algorithm SHA256
   ```
10. Baca `validation_report.json` dan tindak lanjuti error/warning.
11. Jangan lanjut ke tahap 2 sebelum hasil ekstraksi diperiksa.

---

## 13. Keterbatasan yang diketahui

- Lingkup proyek hanya `DOC002`; PDF hortikultura tidak dipakai sehingga
  keterbatasan khusus dokumen hasil scan tidak lagi relevan.
- Deteksi heading bergantung pada font, bold, dan pola penomoran. Heading yang
  tidak memenuhi kriteria akan menjadi paragraf atau `heading_unclassified`.
- Deteksi tabel best-effort dan bisa memperlambat pemrosesan pada PDF yang
  banyak berisi tabel; gunakan `--no-tables` bila waktu pemrosesan menjadi
  masalah, lalu tinjau tabel secara terpisah.
- Nomor halaman tercetak tidak selalu tersedia.
- Tabel diekstraksi best-effort dan dapat memerlukan pemeriksaan manual.
- Urutan baca dokumen multi-kolom tidak diubah otomatis.
- Header/footer berulang hanya dideteksi, tidak dihapus otomatis.
- Dehyphenation nonaktif secara default.
- Metadata bibliografis hanya diisi jika tersedia di PDF atau diisi manual.
- PDF terenkripsi yang memerlukan password tidak didukung dan akan dilaporkan
  sebagai kegagalan.
- Pipeline native (PyMuPDF) tidak menggunakan OCR, LLM, atau API eksternal.
  Jalur LlamaParse bersifat opsional dan terpisah; lihat bagian 15.

---

## 14. Catatan pengembangan

- Jangan mengubah PDF asli.
- Jangan mengisi `manual_metadata.json` dengan tebakan.
- Jangan menambahkan RAG, embedding, ontology, reasoning, backend, atau frontend
  pada tahap ini.
- Jika menemukan masalah parsing, perbaiki parser dan jalankan ulang dengan
  `--overwrite`, lalu bandingkan hasilnya dengan output lama di folder backup.

---

## 15. Pipeline LlamaParse untuk DOC002

Jalur ini khusus `DOC002` (`PenyakitTanamanPangan.pdf`), satu-satunya dokumen
dalam lingkup proyek, dan tidak menyentuh `03_knowledge_tables` atau folder
setelahnya.

### 15.1 Pemisahan namespace

- Output mentah, normalisasi, dan laporan berada di `02_extraction/llamaparse/`.
- Output canonical `02_extraction/extracted_text/DOC002.*` hanya ditimpa
  setelah full run 274 halaman lolos gate perbandingan dengan baseline PyMuPDF.
- Sebelum penimpaan, baseline dibackup ke
  `02_extraction/extraction_notes/_backups/pre_llamaparse_<stamp>/`.

### 15.2 Konfigurasi API key

`.env` di root proyek boleh memakai `LLAMA_CLOUD_API_KEY` atau alias lama
`LLAMA_KEY`. Nilai key tidak pernah dicetak; `env-check` hanya melaporkan
apakah key terdeteksi.

### 15.3 Perintah

```powershell
# cek key tanpa memanggil API
python 02_extraction\run_llamaparse.py env-check

# daftar versi parser per tier (tanpa kredit)
python 02_extraction\run_llamaparse.py versions

# uji 1 halaman (murah) sebelum pilot
python 02_extraction\run_llamaparse.py smoke --page 25 --tier cost_effective

# pilot 20 halaman pada beberapa tier
python 02_extraction\run_llamaparse.py pilot --tiers fast,cost_effective,agentic

# full run + normalisasi + chunking + quality + perbandingan
python 02_extraction\run_llamaparse.py full --tier cost_effective --version 2026-09-28

# full run tanpa menimpa output canonical (review dulu)
python 02_extraction\run_llamaparse.py full --tier cost_effective --version 2026-09-28 --no-promote

# promosikan run yang sudah lolos gate (tanpa memanggil API lagi)
python 02_extraction\run_llamaparse.py promote --run <run_id>
```

Perintah lain: `build`, `quality`, `compare`, `images`, dan `runs` (dengan
`--run <run_id>` opsional; default run selesai terakhir). `quality` dan
`compare` menolak berjalan bila `normalized/DOC002.*.jsonl` berasal dari run
lain; jalankan `build --run <run_id>` lebih dulu.

`images --run <run_id>` mengambil ulang gambar yang gagal diunduh saat parsing
(presigned URL kedaluwarsa) lewat `parsing.get` tanpa membuat job baru sehingga
tidak memakai kredit. `--dry-run` hanya menampilkan daftar nama yang belum ada.

### 15.4 Artefak

| Path | Isi |
|---|---|
| `llamaparse/raw/DOC002/<run_id>/response.json` | respons API lengkap (audit) |
| `.../pages/page_XXXX.md` | markdown mentah per halaman |
| `.../pages/page_XXXX.items.json` | heading, teks, tabel, gambar, bbox |
| `.../pages/page_XXXX.meta.json` | confidence, header/footer, nomor cetak |
| `.../tables/*.csv` | tabel hasil parser |
| `.../images/` | gambar embedded + `index.json` |
| `.../run_manifest.json` | file_id, job_id, opsi, kredit, status |
| `llamaparse/normalized/DOC002.*.jsonl` | pages, blocks, chunks |
| `llamaparse/baseline/DOC002.*.jsonl` | snapshot beku baseline PyMuPDF + `baseline_manifest.json` (hash & asal) |
| `llamaparse/reports/DOC002.*.json` | quality, manual review, comparison, cost, validation |
| `llamaparse/reports/DOC002.reconciliations.json` | ringkasan rekonsiliasi verbatim per run |
| `llamaparse/reports/DOC002.reconciliations.jsonl` | audit setiap token/blok yang dipulihkan |
| `llamaparse/reports/DOC002.pilot.json` | ringkasan perbandingan tier |

### 15.5 Pembersihan dan struktur

- Markdown emphasis (`*...*`, `**...**`, backtick) dibuang dari teks blok;
  isi kata tidak diubah dan dibandingkan lewat `substance_tokens`.
- Sintaks markdown/HTML dibuang tanpa menyentuh isi: tautan disimpan sebagai
  labelnya, tag seperti `<u>` dihapus. Hanya tag bernama yang dikenali, jadi
  polaritas angka (`<30 °C`) tidak berubah. Teks asli tetap tersimpan di
  `raw_text` blok.
- Running header/footer dibuang hanya bila berada di tepi halaman dan memuat
  nomor halaman; bila parser menggabungkan header ke paragraf (tier `fast`),
  header dipisahkan dan dipakai untuk memulihkan konteks bab.
- Caption `Gambar N.N` yang salah diklasifikasi sebagai heading diubah menjadi
  `figure_caption`; caption `Tabel N.N` menjadi paragraf bertipe chunk `table`.
- Level heading ditentukan ulang dari pola nomor (`1.2` section, `1.2.1`
  subsection) karena level dari parser tidak konsisten.
- Nomor halaman cetak diambil dari metadata parser; bila kosong, diturunkan dari
  header/footer yang memuat angka halaman (`source: header|footer`).
- Tabel yang oleh model layout justru dinyatakan bukan tabel
  (`no table/form`, mis. diagram alur halaman 41) tidak diklaim sebagai tabel:
  `content_type` menjadi `paragraph`, teksnya diratakan, diberi catatan
  `spurious_table_reclassified`, dan masuk review manual. Data tabel asli tetap
  tersimpan di field `table` blok.
- Halaman dengan tabel yang bertumpuk dengan blok teks diberi flag
  `layout_conflict_table_text` dan masuk antrean review manual.

### 15.6 Rekonsiliasi verbatim

DOC002 adalah PDF born-digital, sehingga text layer PyMuPDF menjadi otoritas
kata. LlamaParse tetap dipakai untuk struktur (urutan baca, tabel, caption,
nomor halaman cetak), tetapi kata yang ditulis ulang atau dihilangkan parser
dikembalikan dari baseline. Setiap perubahan dapat dilacak di
`reports/DOC002.reconciliations.jsonl`.

Baseline dibekukan di `llamaparse/baseline/` (dibuat sekali dari backup
`pre_llamaparse_*`, lengkap dengan hash di `baseline_manifest.json`). Tanpa
snapshot ini, build berikutnya akan membandingkan keluaran parser dengan
dirinya sendiri karena `extracted_text/` sudah berisi hasil promosi.

- Substitusi 1:1 hanya dipulihkan bila blok masih sejajar dengan baseline
  (>= 50% token) dan bentuk katanya wajar: huruf awal sama atau kemiripan
  >= 0,75. Pasangan seperti `jember` → `image` dari blok yang salah posisi
  tidak diterapkan.
- Kandidat pembanding diambil dari blok terdekat, jendela tiga blok, dan
  seluruh halaman; kandidat dengan pasangan valid terbanyak dipilih agar blok
  parser yang menggabungkan beberapa blok baseline tetap tertangani.
- Halaman yang kehilangan hampir seluruh teks (< 25% karakter baseline)
  dibangun ulang dari blok baseline dan ditandai `text_source:
  pymupdf_text_layer`.
- Blok di ujung halaman yang hilang seluruhnya dipulihkan bila blok sebelumnya
  sudah terwakili, sehingga entri daftar pustaka yang terpotong tidak hilang.
- Placeholder `Image` (alt-text gambar bawaan parser) dibuang karena bukan isi
  dokumen.
- Sel tabel juga direkonsiliasi, tetapi dengan syarat lebih ketat: sel harus
  sejajar dengan sel baseline (>= 50% token) dan kata pengganti harus berbeda
  tepat satu huruf dengan huruf awal sama. Perubahan diterapkan serentak ke
  `cells`, `rows`, `md`, `csv`, dan teks blok agar tidak ada dua versi isi
  tabel; struktur baris/kolom tidak diubah.
- Metadata DOC002 diisi dari halaman hak cipta PDF (halaman 6), bukan tebakan:
  judul, 15 penulis, tahun 2021, penerbit, dan bahasa `id`; ISBN dicatat di
  `notes`.
- Saat promosi, record diselaraskan dengan skema canonical: teks final menjadi
  `raw_text` (teks parser asli disimpan di `parser_raw_text`), `sequence_number`
  unik global, `printed_page_number` berupa string, bbox yang tidak tersedia
  diisi `[0, 0, 0, 0]` dan diberi catatan `bbox_unavailable`, serta payload
  tabel mendapat `cells`, `row_count`, `column_count`, dan `review_required`.
- `figure_caption` dan flag `layout_conflict_table_text` didaftarkan sebagai
  tipe/flag resmi agar lolos validator lintas-pipeline.

### 15.7 Gate promosi

Promosi ke `extracted_text/` hanya terjadi bila seluruh gate pada
`reports/DOC002.comparison.json` lolos:

- 274 halaman lengkap.
- `content_recall` rata-rata <= 1%. Metrik ini mengukur **kehilangan isi**
  tanpa terpengaruh urutan blok: urutan baca yang lebih baik (mis. tabel
  dipindah ke tempat semestinya) bukan kehilangan informasi. Token yang hanya
  muncul di keluaran LlamaParse (mis. label diagram) juga tidak dihitung.
  CER simetris dan noise-adjusted tetap dilaporkan sebagai pembanding.
- `content_loss_max_page` <= 10%: tidak ada satu halaman pun yang kehilangan
  lebih dari 10% isinya. Batas per halaman ini mencegah rata-rata yang bagus
  menutupi satu halaman yang rusak.
- Dua jenis halaman dikecualikan dari rata-rata dan dicatat di laporan:
  baseline < 100 karakter (mis. sampul belakang) dan halaman non-isi
  (`excluded_non_content_pages`, mis. sampul ResearchGate halaman 1).
- 15 bab terdeteksi. Hitungan memakai bab yang punya blok isi, sehingga daftar
  bab di sampul belakang tidak menambah hitungan.
- Nomor halaman cetak terdeteksi (dari metadata parser atau diturunkan dari
  header/footer).
- Tabel minimal sebanyak baseline pada rentang halaman yang diproses.
- Semua blok non-heading di halaman body punya konteks bab.

Skor `confidence` parser hanya dipakai untuk triase review, bukan bukti
akurasi. Halaman dengan kehilangan isi >= 2% atau tambahan isi >= 20 token
otomatis masuk `reports/DOC002.manual_review.jsonl`.

### 15.8 Versi parser

Versi LlamaParse berbeda per tier. Pilot DOC002 memakai `latest` yang saat itu
berarti `cost_effective` versi `2026-09-28` (dikonfirmasi dengan perintah
`versions`); full run memakai versi yang sama agar hasil pilot tetap berlaku.
Versi `2026-07-24` hanya tersedia untuk tier `agentic`, bukan `cost_effective`.

```powershell
python 02_extraction\run_llamaparse.py versions
python 02_extraction\run_llamaparse.py full --tier cost_effective --version 2026-09-28
```

Nilai `--version` divalidasi sebagai `latest` atau `YYYY-MM-DD`; tanggal yang
tidak tersedia untuk tier tersebut akan ditolak API saat parse.

### 15.9 Biaya

Tarif acuan $1,25 per 1.000 kredit. Perkiraan DOC002: `fast` 274 kredit,
`cost_effective` 822 kredit, `agentic` 2.740 kredit. Pilot 20 halaman pada tiga
tier memakai sekitar 280 kredit. Run yang sudah selesai tidak diulang karena
`run_id` diturunkan dari hash PDF + opsi + rentang halaman.
