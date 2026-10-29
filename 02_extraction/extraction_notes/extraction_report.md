# Extraction Report

- Generated at: `2026-10-28T03:07:24Z`
- Schema: `1.0.0`
- Pipeline: `1.0.0`
- Extractor: `LlamaParse` `2026-09-28`

## Ringkasan dokumen

| Dokumen | Halaman | Halaman berteks | Blok | Tabel | Status |
|---|---:|---:|---:|---:|---|
| DOC002 | 274 | 265 | 1578 | 5 | completed_with_warnings |

## Detail dokumen

### DOC002 — PenyakitTanamanPangan.pdf

- Source: `01_knowledge_sources/pdf_original/PenyakitTanamanPangan.pdf`
- SHA-256: `fb503f92c2bbad7b2605bf7e037ec6756613c33b7f82fb04ed7f58e6a050c466`
- Total halaman PDF: 274
- Status ekstraksi: `completed_with_warnings`
- Halaman berteks: 265
- Halaman tanpa teks: 9
- Halaman error: 0
- Blok: 1578
- Tabel: 5 (review: 0)
- Judul: Penyakit Tanaman dan Pengendaliannya
- Penulis: Evan Purnama Ramdan, Lina Budiarti, Nur Kholida Wulansari, Resti Fajarfika, Riana Murti Handayani, Ratna Dwi Hirma Windriyati, Junairiah, Dwiwiyati Nurul Septariani, Arsi, Muzayyanah Rahmiyah, Wenni Tania Defriyanti, Muh. Adiwena, Akhmad Faisal Malik, Ankardiansyah Pandu Pradana, Muhammad Asril
- Tahun: 2021
- Penerbit: Yayasan Kita Menulis
- Bahasa: id

Output:
- `blocks`: `02_extraction/extracted_text/DOC002.blocks.jsonl`
- `pages`: `02_extraction/extracted_text/DOC002.pages.jsonl`
- `notes`: `02_extraction/extraction_notes/DOC002.extraction_notes.json`

Catatan:
- `extracted_with_llamaparse`
- `parser_tier:cost_effective`
- `parser_version:2026-09-28`
- `parser_run_id:DOC002_cost_effective_full-fb503f92_fbfce257`
- `quality_status:warning`

## Catatan pipeline

- `DOC002 dipromosikan dari LlamaParse setelah gate perbandingan lolos`
- `backup_baseline:02_extraction/extraction_notes/_backups/pre_llamaparse_20261028T030724Z`

## Langkah berikutnya

1. Periksa `extraction_notes` setiap dokumen.
2. Bandingkan sampel halaman dengan PDF asli.
3. Tinjau tabel yang berstatus `needs_manual_review`.
4. Jalankan `validate` dan baca `validation_report.json`.
5. Jangan melanjutkan ke tahap pengetahuan sebelum hasil diperiksa.
