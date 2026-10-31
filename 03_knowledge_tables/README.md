# Tahap 2 — Knowledge Tables

Tabel pengetahuan Tahap 2. Dokumen utama adalah **PenyakitTanamanPangan.pdf**
(DOC002, 15 bab tanaman pangan); dokumen tambahan **porang.pdf** (DOC003) dan
**TPTPkhususjamilah.pdf** (DOC004) memakai builder terpisah. Semua isi
diturunkan dari keluaran Tahap 1 (`02_extraction/extracted_text/`) tanpa model
bahasa di dalam pipeline dan tanpa pengetahuan dari luar buku.

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
| `build_knowledge_tables.py` | builder deterministik + gate verbatim (tanaman, penyakit, tabel 5) |
| `curate.py` | menerapkan keputusan manual penyakit + verifikasi kutipan |
| `build_extended_tables.py` | builder patogen, relasi penyakit-patogen, gejala, pengendalian |
| `curate_pathogens.py` | menerapkan keputusan manual patogen + verifikasi kutipan |
| `curate_sentences.py` | memverifikasi offset lalu menyalin gejala/pengendalian ke `curated/` |
| `build_reports.py` | laporan cakupan + gate validasi G1–G7 |
| `schema/knowledge_tables.schema.json` | skema 7 tabel + invarian |
| `auto/plants.csv` | 15 tanaman |
| `auto/diseases.csv` | inventaris penyakit dari heading/tabel |
| `auto/pathogens.csv` | kandidat patogen (belum dikurasi) |
| `auto/disease_pathogen.csv` | relasi penyakit-patogen sebelum kurasi |
| `auto/symptoms.csv` | kalimat gejala + offset |
| `auto/controls.csv` | kalimat pengendalian + offset |
| `auto/ubi_kayu_table_rows.csv` | baris tabel 5.1–5.3 termasuk penanda celah |
| `review/curation_decisions.json` | keputusan manusia penyakit: kutipan + alasan |
| `review/pathogen_decisions.json` | keputusan manusia patogen: tolak, takson, catatan |
| `review/curation_log.csv` / `pathogen_log.csv` | log per field yang berubah |
| `review/ambiguous_sentences.csv` | kalimat yang memuat isyarat gejala dan kendali sekaligus |
| `review/unresolved.csv` | gabungan butir yang belum tuntas |
| `curated/diseases.csv` | otoritas akhir inventaris penyakit |
| `curated/pathogens.csv` | otoritas akhir patogen |
| `curated/disease_pathogen.csv` | otoritas akhir relasi penyakit-patogen |
| `curated/symptoms.csv` | otoritas akhir gejala |
| `curated/controls.csv` | otoritas akhir pengendalian |
| `curated/ubi_kayu_tabel_5.csv` | otoritas akhir tabel ubi kayu |
| `reports/build_report.json` / `.md` | ringkasan build penyakit |
| `reports/coverage.md` / `.json` | cakupan per tanaman |
| `reports/validation.json` | gate G1–G7 |
| `tests/test_knowledge_tables.py` | 33 gate test |
| `config/DOC003_tables.json` / `DOC004_tables.json` | spesifikasi baris kurasi dokumen tambahan |
| `build_document_tables.py` | builder + validator verbatim DOC003/DOC004 |
| `schema/knowledge_tables_DOC003.schema.json` | skema 6 tabel DOC003 |
| `schema/production_tables.schema.json` | skema 4 tabel produksi DOC004 |
| `curated/DOC003/*.csv` | otoritas akhir tabel porang/suweg |
| `curated/DOC004/*.csv` | otoritas akhir tabel nutrisi dan pupuk |
| `reports/DOC003.tables.validation.json` / `DOC004.tables.validation.json` | hasil gate verbatim dokumen tambahan |
| `tests/test_document_tables.py` | 17 gate test DOC003/DOC004 |

## Menjalankan

```powershell
# dari root repo — urutan lengkap
python 03_knowledge_tables/build_knowledge_tables.py
python 03_knowledge_tables/curate.py
python 03_knowledge_tables/build_extended_tables.py
python 03_knowledge_tables/curate_pathogens.py
python 03_knowledge_tables/curate_sentences.py
python 03_knowledge_tables/build_reports.py

# dokumen tambahan DOC003/DOC004 (dari root repo atau folder ini)
python 03_knowledge_tables/build_document_tables.py

# dari folder ini
python -m unittest discover -s tests -p "test_*.py"
```

Builder keluar dengan kode `2` bila ada pelanggaran verbatim, `0` bila bersih.
`curate.py`/`curate_pathogens.py` keluar dengan kode `2` bila ada kutipan yang
tidak ditemukan atau nama baru yang tidak verbatim, dan kode `1` bila masih ada
baris yang menggantung. `build_reports.py` keluar `2` bila salah satu gate G1–G7
gagal.

## Blok B/C — patogen, gejala, pengendalian

- **Patogen** hanya diambil dari bagian penyebab/patogen atau kalimat dengan
  penanda sebab-akibat tegas (`disebabkan oleh`, `patogen penyebab`,
  `menginfeksi`, `menyebabkan penyakit`, `patogen yang menyebabkan`).
  Kalimat pengendalian, agens hayati, dan vektor serangga ditolak; kandidat yang
  ditolak tetap tercatat di `review/pathogen_candidates.csv`.
- **Takson** hanya diisi bila sumber menyebutnya (`jamur`, `cendawan`, `bakteri`,
  `virus`, `nematoda`, `fitoplasma`, `Oomycete`). Tanpa sebutan → `unknown`.
  Perubahan takson manual wajib punya kutipan di `taxon_evidence_quote`.
- **Nama patogen** disimpan verbatim, termasuk salah eja yang tercetak
  (`Phakopspora pachyrhizi`, `Fussarium oxysporum`, `Collectothricum
  gloeosporioides`); koreksi hanya di kolom `note`.
- **Gejala dan pengendalian** disimpan sebagai satu kalimat utuh dengan offset
  `char_start`/`char_end` pada `plain_text` chunk yang spasinya dinormalisasi.
  Tidak ada pemotongan frasa atau parafrase.
- **Pengendalian tingkat bab** (mis. Bab 5.3) disimpan dengan `scope=chapter`,
  `plant_id` terisi, dan `disease_id` kosong.
- Kalimat yang memuat isyarat gejala sekaligus pengendalian tidak dipaksakan ke
  salah satu tabel; barisnya masuk `review/ambiguous_sentences.csv`.

## Gate validasi (G1–G7)

| Gate | Isi |
|---|---|
| G1 | 15 tanaman, 15 bab, setiap tanaman punya penyakit |
| G2 | tidak ada duplikat penyakit per tanaman/tabel; nama tidak kosong |
| G3 | id patogen unik, semua relasi valid, tidak ada patogen yatim |
| G4 | nama patogen verbatim di chunk/blok/heading bukti |
| G5 | offset gejala dan pengendalian cocok persis |
| G6 | foreign key penyakit/tanaman valid; aturan `scope` pengendalian |
| G7 | takson dalam enum; kutipan bukti takson verbatim |

## Cara mengoreksi hasil kurasi

1. Tambah atau ubah entri di `review/curation_decisions.json` untuk penyakit
   atau `review/pathogen_decisions.json` untuk patogen. Wajib ada
   `evidence_ref` (id chunk `DOC002_C…` atau blok `DOC002_P…`) dan
   `evidence_quote` yang tercetak persis di sumber (khusus `verifications`,
   bukti diambil dari `verbatim_text` dan chunk/tabel patogen itu sendiri).
2. Jalankan `python 03_knowledge_tables/curate.py` lalu
   `python 03_knowledge_tables/curate_pathogens.py`.
3. Periksa `review/curation_log.csv` dan `review/pathogen_log.csv`; satu baris =
   satu field yang berubah.
4. Jalankan test. Jangan mengedit `curated/*.csv` langsung — perubahan akan
   hilang pada eksekusi berikutnya.

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

**`pathogens.csv`**

- `scientific_name` / `verbatim_text` — nama seperti tercetak; salah eja sumber
  tidak dibetulkan.
- `taxon_group` — hanya diisi bila sumber menyebut kelompoknya; jika tidak,
  `unknown` dan masuk `review/unresolved.csv`.
- `taxon_evidence_chunk_id` / `taxon_evidence_quote` — bukti kutipan untuk
  takson hasil koreksi manual.
- `note` — catatan salah eja, sinonim, atau nama tingkat genus.
- `review_status` — `auto_ok` (pola deterministik yakin), `verified` (dibaca
  manusia), `needs_review` (belum diperiksa; saat ini tidak ada).

**`ubi_kayu_table_rows.csv`**

- `status=complete` — baris bernomor lengkap.
- `status=unnumbered` — baris tanpa nomor di sumber (sel terpotong antar halaman).
- `status=missing_row` — nomor baris tidak tercetak; tidak diisi, hanya penanda.

## Kondisi saat ini

- 15 tanaman, 110 penyakit, 105 patogen, 132 relasi penyakit-patogen.
- 601 baris gejala, 528 baris pengendalian (448 tingkat penyakit, 80 tingkat bab).
- Status penyakit setelah kurasi: 84 `auto_ok`, 26 `verified`; tidak ada baris
  yang masih menggantung.
- Status patogen: 63 `auto_ok`, 42 `verified`, tidak ada `needs_review`.
- 8 kandidat patogen ditolak, 7 takson dikoreksi, 25 catatan salah eja/sinonim,
  17 nama diverifikasi manual; 19 patogen tetap `unknown` karena sumber tidak
  menyebut kelompoknya.
- Celah tabel: nomor 3 dan 7 pada T5.1 (daun), tidak diisi.
- Pelanggaran verbatim: 0; gate G1–G7 lulus.

Keputusan kurasi yang perlu diketahui pembaca:

- Bab 4 dan 15: heading berisi nama patogen, nama penyakit diambil dari prosa
  (`layu fusarium`, `Penyakit kudis`, `Penyakit bercak kuning`,
  `Penyakit busuk hitam (black rot)`, `Busuk pangkal batang`, `busuk pucuk`,
  `bercak daun`).
- `Hawar daun bakteri` (daun) dan `Hawar bakteri` (batang) tetap dua baris;
  patogen sama, bagian tanaman berbeda.
- `Antraknosa` muncul di tabel 5.1 (daun) dan 5.2 (batang) dengan penulisan
  patogen berbeda; penyakit dipisah mengikuti tabel. Baris 5.2 ditambahkan
  lewat `additions` karena builder awal menduplikasi nama.
- `Penyakit Antraknos` (Bab 11) terpotong di sumber dan dibiarkan apa adanya.
- Nama ilmiah hanya diisi untuk 8 tanaman yang mencetaknya di badan bab.
- Gejala ubi kayu tidak diduplikasi ke `symptoms.csv`; sumbernya tabel 5.1–5.3
  di `curated/ubi_kayu_tabel_5.csv`, dan laporan cakupan menghitungnya dari sana.

## Dokumen tambahan — DOC003 dan DOC004

Kedua dokumen memakai jalur terpisah dari DOC002. Baris tidak diturunkan dari
heading otomatis, melainkan ditulis di `config/DOC003_tables.json` dan
`config/DOC004_tables.json`, lalu diverifikasi ulang oleh
`build_document_tables.py` terhadap blok dan chunk Tahap 1, termasuk verifikasi
kutipan, foreign key, dan offset karakter, lalu menulis CSV.

**DOC003 — porang.pdf.** 56 halaman PDF, 9 bab. Bab 6 (Hama Penyakit dan
Pengendaliannya) secara eksplisit merangkum penyakit **suweg**
(`Amorphophallus spp.`), bukan penyakit porang. Karena itu:

- `plants` berisi `PLANT_016` Porang dan `PLANT_017` Suweg;
- penyakit suweg masuk tabel `amorphophallus_spp_diseases`, tidak digabung ke
  `diseases` DOC002;
- 7 penyakit, 7 patogen, 7 relasi, 8 gejala, 4 pengendalian;
- salah eja sumber dipertahankan (`Pythium helicoides` vs `Phytium helicoides`,
  `Sclerotium rolfsii` vs `Slerotium rolfsii`) dan hanya dijelaskan di `note`.

**DOC004 — TPTPkhususjamilah.pdf.** PDF yang tersedia hanya cuplikan Bab 7
(Pengelolaan Nutrisi Tanaman), 65 halaman PDF; badan bab 12–55, referensi dan
sampul belakang di luar rentang. Empat tabel produksi:

| Tabel | Baris | Isi |
|---|---|---|
| `nutrients` | 4 | peran dan bentuk serapan unsur hara |
| `fertilizers` | 8 | jenis pupuk dan dosis yang tercetak |
| `practices` | 17 | strategi dan langkah pemupukan berimbang |
| `compost` | 10 | kompos, bioaktivator, POC, dan manfaatnya |

Dosis hanya diisi bila angka benar-benar tercetak (urea, ammonium sulfat,
superfosfat, KCl); pupuk tanpa angka dosis dibiarkan kosong. PDF DOC004 memuat
derau parser/OCR, sehingga hanya kalimat bersih dan tidak ambigu yang dikutip.

Perintah dan gate:

```powershell
python 03_knowledge_tables/build_document_tables.py --doc DOC003 --doc DOC004
```

Builder keluar `2` bila ada kutipan yang tidak ada di blok/chunk, nilai/unit
tidak ada di kutipan, ID duplikat/tidak sesuai pola, foreign key menggantung,
atau offset karakter gagal. Laporan per dokumen ditulis ke
`reports/DOC003.tables.validation.json` dan
`reports/DOC004.tables.validation.json`.

## Batas tahap ini

Tidak ada model bahasa di dalam pipeline, RAG, embedding, basis vektor, backend,
frontend, atau ontologi. Seluruh nilai berasal dari chunk/blok DOC002 dan dapat
ditelusuri lewat `chunk_id`/`source_block_ids` serta offset karakter.
