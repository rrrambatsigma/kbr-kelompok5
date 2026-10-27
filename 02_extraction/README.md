# Tahap 1 — PDF Extraction & Document Parsing

Pipeline lokal untuk mengubah PDF sumber proyek KBR menjadi data teks terstruktur
yang mempertahankan identitas dokumen, nomor halaman PDF, konteks bab/subbab,
dan catatan masalah ekstraksi.

Pipeline ini **belum dijalankan** saat dokumentasi ini dibuat. Semua perintah di
bawah harus dijalankan sendiri oleh pengguna.

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
├── PenyakitTanamanHortikultura.pdf     -> DOC001
└── PenyakitTanamanPangan.pdf           -> DOC002

01_knowledge_sources/source_metadata/
└── manual_metadata.json                -> opsional, diisi manual
```

Registry dokumen ada di `02_extraction/pdf_pipeline/config.py`. PDF yang tidak
terdaftar akan dilaporkan dan dilewati.

`manual_metadata.json` hanya boleh diisi dari halaman judul, kolofon, atau
sumber bibliografis yang benar-benar tersedia. Jangan menebak.

### Output

```text
01_knowledge_sources/source_metadata/
└── manifest.json

02_extraction/extracted_text/
├── DOC001.blocks.jsonl
├── DOC001.pages.jsonl
├── DOC002.blocks.jsonl
└── DOC002.pages.jsonl

02_extraction/extraction_notes/
├── DOC001.extraction_notes.json
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
| `document_id` | string | `DOC001` atau `DOC002`. |
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
- `--doc DOC001` atau `--doc DOC002`: memproses satu dokumen; manifest lama
  digabung agar entri dokumen lain tidak hilang.
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
Get-Content 02_extraction\extraction_notes\DOC001.extraction_notes.json -Encoding UTF8
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
2. Periksa `DOC001.extraction_notes.json`:
   - apakah semua halaman `no_text_extracted`;
   - apakah ada `likely_scanned_image_only`;
   - putuskan apakah OCR diperlukan.
3. Untuk `DOC002`, bandingkan halaman sampel 1, 5, 20, 50, 100, dan terakhir
   antara `blocks.jsonl` dan PDF asli.
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

- `DOC001` kemungkinan besar berupa PDF hasil scan. Tanpa OCR, hasil teksnya
  mungkin kosong. Ini akan dikonfirmasi saat pipeline dijalankan.
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
- Pipeline tidak menggunakan OCR, LLM, atau API eksternal.

---

## 14. Catatan pengembangan

- Jangan mengubah PDF asli.
- Jangan mengisi `manual_metadata.json` dengan tebakan.
- Jangan menambahkan RAG, embedding, ontology, reasoning, backend, atau frontend
  pada tahap ini.
- Jika menemukan masalah parsing, perbaiki parser dan jalankan ulang dengan
  `--overwrite`, lalu bandingkan hasilnya dengan output lama di folder backup.
