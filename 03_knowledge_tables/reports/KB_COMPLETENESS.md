# Audit Kelengkapan KB

Sumber: `04_ontology/ontology_md.ttl`

## Ringkasan

| Dimensi | Gap |
|---|---:|
| Penyakit | 53 |
| Tanaman | 7 |
| Tanpa bukti lingkungan | 0 |
| Tanpa patogen | 0 |
| Patogen tanpa takson | 0 unik |
| Tanpa pengendalian spesifik | 17 |
| Memakai fallback pengendalian tanaman | 17 |
| Tanpa pengendalian sama sekali | 0 |
| Tanpa bagian tanaman | 0 |
| Tanpa severity | 39 |
| Tanpa fase | 42 |
| Tanpa varietas tahan | 45 |
| Tanpa deskripsi penyakit | 0 |
| Tanpa nama Inggris | 43 |
| Tanaman tanpa kondisi tumbuh | 0 |
| Gejala belum dipetakan | 58 |
| Pengendalian belum dipetakan | 37 |

## Klasifikasi gap

| Jenis gap | Jumlah | Sifat | Sumber | Tindakan |
|---|---:|---|---|---|
| Tanpa bukti lingkungan | 0 | Inti | DOC002/DOC005 | Isi dari kutipan sumber |
| Tanpa patogen | 0 | Inti | DOC002/DOC005 | Lengkapi tautan patogen |
| Patogen tanpa takson | 0 | Inti | DOC002/DOC005 | Lengkapi takson |
| Tanpa pengendalian sama sekali | 0 | Inti | DOC002/DOC005 | Isi aksi pengendalian |
| Tanpa bagian tanaman | 0 | Inti | DOC002/DOC005 | Isi bagian tanaman |
| Tanaman tanpa kondisi tumbuh | 0 | Inti | DOC002/DOC005/EXTERNAL_ENV | Isi kondisi tumbuh |
| Gejala belum dipetakan | 58 | Mapping | DOC002/DOC005 | Triage lalu petakan/exception |
| Pengendalian belum dipetakan | 37 | Mapping | DOC002/DOC005 | Triage lalu petakan/exception |
| Tanpa severity | 39 | Best-effort | DOC002/DOC005 | Isi bila sumber eksplisit |
| Tanpa fase | 42 | Best-effort | DOC002/DOC005 | Isi bila sumber eksplisit |
| Tanpa varietas tahan | 45 | Best-effort | DOC002/DOC005 | Isi bila sumber eksplisit |
| Tanpa nama Inggris | 43 | Best-effort | DOC002/DOC005/eksternal | Isi bila sumber eksplisit |

## Status per tanaman

| Tanaman | Penyakit | Kondisi tumbuh | Pengendalian umum |
|---|---:|---:|---:|
| Padi | 5 | 1 | 0 |
| Kedelai | 15 | 3 | 0 |
| Jagung | 5 | 1 | 0 |
| UbiJalar | 4 | 1 | 0 |
| UbiKayu | 17 | 1 | 10 |
| KacangTanah | 4 | 1 | 12 |
| KacangHijau | 3 | 1 | 0 |

## Matriks per penyakit

| Tanaman | Penyakit | Lingkungan | Patogen | Kendali | Bagian | Severity | Fase | Gejala | Varietas | Deskripsi |
|---|---|---:|---|---|---:|---|---|---:|---:|---|
| UbiKayu | Antraknosa | 1 | ok | fallback | 1 | - | - | 1 | 0 | ya |
| UbiKayu | Antraknosa | 1 | ok | fallback | 1 | - | - | 1 | 0 | ya |
| UbiKayu | Bercak daun baur | 1 | ok | fallback | 1 | - | - | 1 | 0 | ya |
| UbiKayu | Bercak daun Coklat | 1 | ok | fallback | 1 | - | - | 1 | 0 | ya |
| UbiKayu | Bercak daun putih | 2 | ok | fallback | 1 | - | - | 1 | 0 | ya |
| UbiKayu | Busuk akar dan umbi | 1 | ok | fallback | 2 | - | - | 2 | 0 | ya |
| UbiKayu | Busuk akar | 1 | ok | fallback | 2 | - | - | 4 | 0 | ya |
| UbiKayu | Busuk pangkal batang | 2 | ok | fallback | 1 | - | - | 2 | 0 | ya |
| UbiKayu | Busuk Umbi | 1 | ok | fallback | 2 | - | - | 2 | 0 | ya |
| UbiKayu | Cassava Brown Streak Disease (CBSD) | 2 | ok | fallback | 1 | - | - | 2 | 0 | ya |
| UbiKayu | Cassava Mosaic Begomovirus (CMBs) | 1 | ok | fallback | 1 | - | - | 2 | 0 | ya |
| UbiKayu | Hawar bakteri | 3 | ok | fallback | 1 | - | - | 2 | 0 | ya |
| UbiKayu | Hawar daun bakteri | 3 | ok | fallback | 1 | - | - | 4 | 0 | ya |
| UbiJalar | layu fusarium | 2 | ok | specific | 3 | - | - | 8 | 0 | ya |
| UbiKayu | Nekrosis pada titik tunas (Cassava bud necrosis) | 2 | ok | fallback | 1 | - | - | 2 | 0 | ya |
| Kedelai | Penyakit Antraknosa | 1 | ok | specific | 3 | - | ya | 8 | 0 | ya |
| Kedelai | Penyakit Bakteri Pustul | 2 | ok | specific | 2 | - | - | 5 | 0 | ya |
| KacangTanah | Penyakit Belang (Mottle) | 2 | ok | specific | 1 | - | - | 6 | 0 | ya |
| Kedelai | Penyakit Bercak Biji Ungu | 1 | ok | specific | 1 | - | - | 8 | 0 | ya |
| KacangHijau | Penyakit Bercak Daun | 2 | ok | specific | 3 | ya | ya | 2 | 0 | ya |
| KacangTanah | Penyakit Bercak Daun | 2 | ok | specific | 3 | ya | ya | 9 | 6 | ya |
| Kedelai | Penyakit Bercak Daun Mata Katak (Frogeye Leaf Spot) | 2 | ok | specific | 1 | - | - | 3 | 0 | ya |
| UbiJalar | Penyakit bercak kuning | 1 | ok | specific | 2 | - | - | 9 | 0 | ya |
| Kedelai | Penyakit Bercak Target | 1 | ok | specific | 3 | - | - | 4 | 0 | ya |
| Padi | Penyakit Blas | 1 | ok | specific | 2 | ya | - | 4 | 0 | ya |
| Jagung | Penyakit Bulai | 2 | ok | specific | 1 | ya | ya | 8 | 2 | ya |
| UbiJalar | Penyakit busuk hitam (black rot) | 1 | ok | specific | 2 | - | - | 6 | 0 | ya |
| Jagung | Penyakit Busuk Pelepah | 2 | ok | specific | 3 | - | - | 2 | 0 | ya |
| Kedelai | Penyakit Embun Palsu (Downy mildew) | 2 | ok | specific | 1 | ya | - | 9 | 0 | ya |
| KacangHijau | Penyakit Embun Tepung | 2 | ok | specific | 1 | ya | - | 1 | 0 | ya |
| Kedelai | Penyakit Embun Tepung (Powdery Mildew) | 2 | ok | specific | 1 | - | - | 2 | 0 | ya |
| Kedelai | Penyakit Hawar Bakteri (Bacterial Blight) | 1 | ok | specific | 2 | ya | ya | 7 | 0 | ya |
| Padi | Penyakit Hawar Daun Bakteri | 3 | ok | specific | 1 | ya | - | 9 | 0 | ya |
| Jagung | Penyakit Hawar Daun | 2 | ok | specific | 1 | ya | ya | 4 | 0 | ya |
| Padi | Penyakit Hawar Pelepah Daun | 2 | ok | specific | 1 | ya | ya | 5 | 0 | ya |
| Jagung | Penyakit Karat Daun | 2 | ok | specific | 1 | ya | ya | 10 | 0 | ya |
| KacangTanah | Penyakit Karat Daun | 2 | ok | specific | 1 | ya | - | 5 | 2 | ya |
| Kedelai | Penyakit Karat Daun | 2 | ok | specific | 1 | ya | - | 8 | 6 | ya |
| Kedelai | Penyakit Kerdil Kedelai (Soybean Stunt Virus) | 1 | ok | specific | 1 | - | - | 4 | 0 | ya |
| Padi | Penyakit Kerdil Rumput dan Kerdil Hampa | 1 | ok | specific | 2 | - | - | 4 | 0 | ya |
| UbiJalar | Penyakit kudis | 2 | ok | specific | 3 | - | - | 7 | 6 | ya |
| KacangTanah | Penyakit Layu Bakteri | 2 | ok | specific | 2 | - | - | 2 | 0 | ya |
| Kedelai | Penyakit Layu Fusarium | 1 | ok | specific | 1 | - | - | 5 | 0 | ya |
| KacangHijau | Penyakit Layu | 2 | ok | specific | 2 | - | ya | 3 | 2 | ya |
| Jagung | Penyakit Layu Stewart | 1 | ok | specific | 1 | ya | ya | 4 | 0 | ya |
| Kedelai | Penyakit Mosaik Kedelai (Soybean Mosaic Virus) | 1 | ok | specific | 1 | - | - | 7 | 0 | ya |
| Kedelai | Penyakit Rebah Kecambah | 1 | ok | specific | 2 | - | - | 7 | 0 | ya |
| Kedelai | Penyakit Rebah Semai | 1 | ok | specific | 3 | - | ya | 5 | 6 | ya |
| Kedelai | Penyakit Samar Kacang Tunggak (Cowpea Mild Mottle Virus) | 1 | ok | specific | 1 | - | - | 5 | 0 | ya |
| Padi | Penyakit Tungro | 1 | ok | specific | 2 | - | - | 4 | 4 | ya |
| UbiKayu | Sapu setan (Witches broom) | 1 | ok | fallback | 1 | - | - | 1 | 0 | ya |
| UbiKayu | Superelongasi | 1 | ok | fallback | 1 | - | - | 1 | 0 | ya |
| UbiKayu | Tanaman kerdil (stunt) | 1 | ok | fallback | 1 | - | - | 1 | 0 | ya |

## Patogen tanpa takson

Tidak ada.

## Penyakit berbagi patogen

- Begomovirus: CassavaMosaicBegomovirusCMBsUbiKayu, TanamanKerdilStuntUbiKayu
- FusariumSpp: BusukUmbiUbiKayu, PenyakitLayuFusariumKedelai
- RhizoctoniaSolani: PenyakitBusukPelepahJagung, PenyakitHawarPelepahDaunPadi, PenyakitRebahKecambahKedelai
- SclerotiumRolfsii: PenyakitLayuKacangHijau, PenyakitRebahSemaiKedelai

## Label duplikat

- `antraknosa`: AntraknosaUbiKayuBatang, AntraknosaUbiKayuDaun, PenyakitAntraknosaKedelai
- `bercak daun`: PenyakitBercakDaunKacangHijau, PenyakitBercakDaunKacangTanah
- `hawar daun bakteri`: HawarDaunBakteriUbiKayu, PenyakitHawarDaunBakteriPadi
- `karat daun`: PenyakitKaratDaunJagung, PenyakitKaratDaunKacangTanah, PenyakitKaratDaunKedelai
- `layu fusarium`: LayuFusariumUbiJalar, PenyakitLayuFusariumKedelai

## Catatan audit

- `TanamanKerdilStuntUbiKayu` berbagi patogen Begomovirus dengan `CassavaMosaicBegomovirusCMBsUbiKayu`; perlu keputusan merge/alias sebelum dipaksa punya bukti lingkungan.
- `PenyakitRebahSemaiKedelai` (Sclerotium rolfsii) dan `PenyakitRebahKecambahKedelai` (Rhizoctonia solani) adalah dua penyakit berbeda; jangan digabung.
- Pengendalian UbiKayu tersedia sebagai `pengendalianUmum` level tanaman; fallback ini dihitung sebagai jalur rekomendasi yang sah.
- Spike SWRL/Pellet berhasil: Pellet 2.3.1 lewat owlready2 dapat menginfer object property dari SWRL dengan `infer_property_values=True`.
- Empat aturan SWRL sudah digabung ke ontology_md: kandidat gejala, kandidat lingkungan, rekomendasi spesifik, dan fallback pengendalian umum.
- Kondisi tumbuh 7/7 tanaman diisi dari sumber eksternal; 5 fakta baru ditambahkan ke ontology_md.
- Severity, fase, varietas, dan nama Inggris tetap best-effort; nilainya tidak dipaksakan bila sumber tidak menyatakan.
- `00_sumber_data/02_PenyakitTanamanPangan.md` hanya preview/truncated; teks lengkap DOC002 yang dipakai audit ada di `02_extraction/llamaparse/baseline/DOC002.blocks.jsonl`.
- Audit sumber per gap ada di `03_knowledge_tables/reports/SOURCE_GAP_AUDIT.md`; triage mapping ada di `03_knowledge_tables/reports/MAPPING_TRIAGE.md`.
