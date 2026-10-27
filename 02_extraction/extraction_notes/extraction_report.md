# Extraction Report

- Generated at: `2026-10-27T14:44:13Z`
- Schema: `1.0.0`
- Pipeline: `1.0.0`
- Extractor: `PyMuPDF` `1.28.2`

## Ringkasan dokumen

| Dokumen | Halaman | Halaman berteks | Blok | Tabel | Status |
|---|---:|---:|---:|---:|---|
| DOC001 | 874 | 0 | 0 | 0 | no_text_extracted |
| DOC002 | 274 | 273 | 2408 | 5 | completed_with_warnings |

## Detail dokumen

### DOC001 — PenyakitTanamanHortikultura.pdf

- Source: `01_knowledge_sources/pdf_original/PenyakitTanamanHortikultura.pdf`
- SHA-256: `620bd3443f8d25510829b7e56bfac967df55c0f633fbc609d790bc351ee3477e`
- Total halaman PDF: 874
- Status ekstraksi: `no_text_extracted`
- Halaman berteks: 0
- Halaman tanpa teks: 874
- Halaman error: 0
- Blok: 0
- Tabel: 0 (review: 0)
- Judul: None
- Penulis: null
- Tahun: None
- Penerbit: None
- Bahasa: None

Output:
- `blocks`: `02_extraction/extracted_text/DOC001.blocks.jsonl`
- `pages`: `02_extraction/extracted_text/DOC001.pages.jsonl`
- `notes`: `02_extraction/extraction_notes/DOC001.extraction_notes.json`

Catatan:
- `pdf_page_labels_available`
- `no_text_layer_detected`
- `ocr_not_performed`

### DOC002 — PenyakitTanamanPangan.pdf

- Source: `01_knowledge_sources/pdf_original/PenyakitTanamanPangan.pdf`
- SHA-256: `fb503f92c2bbad7b2605bf7e037ec6756613c33b7f82fb04ed7f58e6a050c466`
- Total halaman PDF: 274
- Status ekstraksi: `completed_with_warnings`
- Halaman berteks: 273
- Halaman tanpa teks: 1
- Halaman error: 0
- Blok: 2408
- Tabel: 5 (review: 1)
- Judul: None
- Penulis: null
- Tahun: None
- Penerbit: None
- Bahasa: None

Output:
- `blocks`: `02_extraction/extracted_text/DOC002.blocks.jsonl`
- `pages`: `02_extraction/extracted_text/DOC002.pages.jsonl`
- `notes`: `02_extraction/extraction_notes/DOC002.extraction_notes.json`

Catatan:
- `ocr_not_performed`
- `printed_page_numbers_not_detected`
- `unclassified_headings_present`

## Langkah berikutnya

1. Periksa `extraction_notes` setiap dokumen.
2. Bandingkan sampel halaman dengan PDF asli.
3. Tinjau tabel yang berstatus `needs_manual_review`.
4. Jalankan `validate` dan baca `validation_report.json`.
5. Jangan melanjutkan ke tahap pengetahuan sebelum hasil diperiksa.
