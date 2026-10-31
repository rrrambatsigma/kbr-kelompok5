# Extraction Report

- Generated at: `2026-10-31T03:48:36Z`
- Schema: `1.0.0`
- Pipeline: `1.0.0`
- Extractor: `LlamaParse` `latest`

## Ringkasan dokumen

| Dokumen | Halaman | Halaman berteks | Blok | Tabel | Status |
|---|---:|---:|---:|---:|---|
| DOC002 | 274 | 265 | 1578 | 5 | completed_with_warnings |
| DOC003 | 56 | 54 | 279 | 10 | completed_with_warnings |
| DOC004 | 65 | 65 | 364 | 13 | completed_with_warnings |
| DOC005 | 84 | 80 | 510 | 17 | completed_with_warnings |

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

### DOC003 — porang.pdf

- Source: `01_knowledge_sources/pdf_original/porang.pdf`
- SHA-256: `71122ed5fdd8ba41ca091d7752ffe77e5c3355686112e968008df7933c8a4239`
- Total halaman PDF: 56
- Status ekstraksi: `completed_with_warnings`
- Halaman berteks: 54
- Halaman tanpa teks: 2
- Halaman error: 0
- Blok: 279
- Tabel: 10 (review: 7)
- Judul: Tanaman Porang: Pengenalan, Budidaya, dan Pemanfaatannya
- Penulis: Nasir Saleh, St. A. Rahayuningsih, Budhi Santoso Radjit, Erliana Ginting, Didik Harnowo, I Made Jana Mejaya
- Tahun: 2015
- Penerbit: Pusat Penelitian dan Pengembangan Tanaman Pangan
- Bahasa: id

Output:
- `blocks`: `02_extraction/extracted_text/DOC003.blocks.jsonl`
- `pages`: `02_extraction/extracted_text/DOC003.pages.jsonl`
- `notes`: `02_extraction/extraction_notes/DOC003.extraction_notes.json`

Catatan:
- `extracted_with_llamaparse`
- `parser_tier:cost_effective`
- `parser_version:2026-09-28`
- `parser_run_id:DOC003_cost_effective_full-71122ed5_c9e9cb8e`
- `quality_status:warning`
- `blocks_context_missing:1`
- `tables_with_concerns:7`

### DOC004 — TPTPkhususjamilah.pdf

- Source: `01_knowledge_sources/pdf_original/TPTPkhususjamilah.pdf`
- SHA-256: `e120ee97185633d8a11372b5d5d76db2f6d084f3942a23926f2ead8628688873`
- Total halaman PDF: 65
- Status ekstraksi: `completed_with_warnings`
- Halaman berteks: 65
- Halaman tanpa teks: 0
- Halaman error: 0
- Blok: 364
- Tabel: 13 (review: 13)
- Judul: Teknologi Produksi Tanaman Pangan
- Penulis: Andi Adriani Wahditiya, Ari Kurniawan, Jeanne Ivonne Nendissa, Aulia Meyuliana, Muharama Yora, Jamilah, Dewi Jayagma Ilham, Iid Mufaidah, Ali Zainal Abidin Alaydrus, Filya Hidayati, Alex Copernikus Andaria
- Tahun: 2024
- Penerbit: Yayasan Tri Edukasi Ilmiah
- Bahasa: id

Output:
- `blocks`: `02_extraction/extracted_text/DOC004.blocks.jsonl`
- `pages`: `02_extraction/extracted_text/DOC004.pages.jsonl`
- `notes`: `02_extraction/extraction_notes/DOC004.extraction_notes.json`

Catatan:
- `extracted_with_llamaparse`
- `parser_tier:cost_effective`
- `parser_version:2026-09-28`
- `parser_run_id:DOC004_cost_effective_full-e120ee97_cd3fd5fc`
- `quality_status:warning`
- `blocks_context_missing:22`
- `tables_with_concerns:13`

### DOC005 — PenyakitTanamanKedelaiKacangTanahKacangHijau.pdf

- Source: `01_knowledge_sources/pdf_sources/PenyakitTanamanKedelaiKacangTanahKacangHijau.pdf`
- SHA-256: `d2aec48f63af965b58cc756170814b5e3f6c078c303f4a24b4e051b460f1f1bf`
- Total halaman PDF: 84
- Status ekstraksi: `completed_with_warnings`
- Halaman berteks: 80
- Halaman tanpa teks: 4
- Halaman error: 0
- Blok: 510
- Tabel: 17 (review: 10)
- Judul: Penyakit Utama Pada Tanaman: Kedelai, Kacang Tanah Dan Kacang Hijau
- Penulis: Sumartini, Emerensiana Uge, Yuliantoro Baliadi
- Tahun: 2020
- Penerbit: Balai Penelitian Tanaman Aneka Kacang dan Umbi
- Bahasa: id

Output:
- `blocks`: `02_extraction/extracted_text/DOC005.blocks.jsonl`
- `pages`: `02_extraction/extracted_text/DOC005.pages.jsonl`
- `notes`: `02_extraction/extraction_notes/DOC005.extraction_notes.json`

Catatan:
- `extracted_with_llamaparse`
- `parser_tier:agentic`
- `parser_version:latest`
- `parser_run_id:DOC005_agentic_full-d2aec48f_733d33b7`
- `quality_status:warning`
- `blocks_context_missing:42`
- `tables_with_concerns:12`

## Catatan pipeline

- `DOC002 dipromosikan dari LlamaParse setelah gate perbandingan lolos`
- `backup_baseline:02_extraction/extraction_notes/_backups/pre_llamaparse_20261028T030724Z`
- `DOC003 dipromosikan dari LlamaParse setelah gate verifikasi internal lolos`
- `backup_baseline:DOC003:02_extraction/extraction_notes/_backups/pre_llamaparse_20261030T131126Z`
- `DOC004 dipromosikan dari LlamaParse setelah gate verifikasi internal lolos`
- `backup_baseline:DOC004:02_extraction/extraction_notes/_backups/pre_llamaparse_20261030T131556Z`
- `DOC005 dipromosikan dari LlamaParse setelah gate verifikasi internal lolos`
- `backup_baseline:DOC005:02_extraction/extraction_notes/_backups/pre_llamaparse_20261031T034836Z`

## Langkah berikutnya

1. Periksa `extraction_notes` setiap dokumen.
2. Bandingkan sampel halaman dengan PDF asli.
3. Tinjau tabel yang berstatus `needs_manual_review`.
4. Jalankan `validate` dan baca `validation_report.json`.
5. Jangan melanjutkan ke tahap pengetahuan sebelum hasil diperiksa.
