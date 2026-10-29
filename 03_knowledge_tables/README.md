# Tahap 2 — Knowledge Tables DOC002

Tabel pengetahuan untuk **PenyakitTanamanPangan.pdf** (DOC002), 15 bab tanaman pangan.
Semua isi diturunkan dari keluaran Tahap 1 (`02_extraction/extracted_text/`) tanpa
model bahasa di dalam pipeline dan tanpa pengetahuan dari luar buku.

## Aturan yang tidak boleh dilanggar

1. **Verbatim.** Setiap teks yang masuk tabel harus substring dari `plain_text`
   chunk yang dirujuk, setelah spasi dinormalisasi. Tidak ada parafrase.
2. **Tanpa tebakan.** Field yang tidak tercetak di sumber dibiarkan kosong.
   Nama ilmiah hanya diisi bila benar-benar muncul di dalam badan bab; Daftar
   Pustaka tidak dihitung.
3. **Halaman = halaman PDF**, bukan halaman cetak buku.
4. **Tidak membetulkan sumber.** Nama yang terpotong (mis. "Penyakit Antraknos")
   disimpan apa adanya dan diberi catatan.
5. **Sumber read-only.** Builder hanya membaca; tidak menulis balik ke Tahap 1.

## Lapisan data

```
auto/     keluaran builder, apa adanya, belum diperiksa manusia
review/   catatan masalah + log keputusan kurasi
curated/  hasil final yang sudah diperiksa manusia (otoritas akhir)
```

Alur: `auto` → `review` → `curated`. Baris `auto` tidak pernah ditimpa kurasi;
`curated/` adalah salinan yang diedit dengan jejak alasan di `review/curation_log.csv`.

## Struktur

| Path | Isi |
|---|---|
| `config/chapter_map.json` | 15 bab → tanaman, level heading penyakit, nama ilmiah terverifikasi, grup tabel Bab 5 |
| `build_knowledge_tables.py` | builder deterministik + gate verbatim |
| `schema/knowledge_tables.schema.json` | skema 7 tabel + invarian |
| `auto/plants.csv` | 15 tanaman |
| `auto/diseases.csv` | inventaris penyakit dari heading/tabel |
| `auto/ubi_kayu_table_rows.csv` | baris tabel 5.1–5.3 termasuk penanda celah |
| `reports/build_report.json` / `.md` | ringkasan build |
| `tests/test_knowledge_tables.py` | gate G1, G2, G3, G5 |

## Menjalankan

```powershell
# dari root repo
python 03_knowledge_tables/build_knowledge_tables.py

# dari folder ini
python -m unittest discover -s tests -p "test_*.py"
```

Builder keluar dengan kode `2` bila ada pelanggaran verbatim, `0` bila bersih.

## Cara membaca kolom penting

**`diseases.csv`**

- `disease_name_verbatim` — nama seperti tercetak pada heading/tabel. Kosong bila
  heading bab berisi nama patogen (Bab 4 & 15) dan nama penyakit belum dikurasi.
- `disease_name_key` — slug untuk deteksi duplikat, bukan nama tampilan.
- `evidence_chunk_ids` — dipisah `;`, satu atau lebih chunk tempat nama itu muncul.
- `source_block_ids` — dipakai untuk penyakit yang berasal dari tabel (Bab 5).
- `review_status` — `auto_ok` (heading panjang & jelas), `needs_review` (nama pendek
  atau dari tabel), `needs_curation` (heading berisi patogen, nama penyakit harus
  dibaca dari prosa).

**`ubi_kayu_table_rows.csv`**

- `status=complete` — baris bernomor lengkap.
- `status=unnumbered` — baris tanpa nomor di sumber (sel terpotong antar halaman).
- `status=missing_row` — nomor baris tidak tercetak; tidak diisi, hanya penanda.

## Kondisi saat ini

- 15 tanaman, 109 penyakit, 19 baris tabel ubi kayu.
- Status review: 85 `auto_ok`, 7 `needs_curation`, 17 `needs_review`.
- Celah tabel: nomor 3 dan 7 pada T5.1 (daun).
- Pelanggaran verbatim: 0.

## Batas tahap ini

Belum ada patogen, gejala, pengendalian, RAG, embedding, basis vektor, backend,
frontend, atau ontologi. Tahap berikutnya menambah tabel tersebut di atas skema
yang sudah dibekukan.
