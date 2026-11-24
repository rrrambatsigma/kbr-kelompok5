# Ontologi OWL 2 — Penyakit Tanaman Pangan Indonesia

Folder ini membangun ontologi OWL 2 berbahasa Indonesia untuk **tujuh tanaman
pangan** dari knowledge tables terkurasi di `03_knowledge_tables/`. TBox
didefinisikan manual di `tbox.py`; ABox dibangkitkan oleh `build_ontology.py`
dari DOC002 + DOC005, lalu divalidasi sebelum artefak ditulis.

Cakupan tanaman: **Padi, Kedelai, Jagung, Ubi Jalar, Ubi Kayu, Kacang Tanah,
Kacang Hijau**. Tanaman di luar cakupan tidak dibuat sebagai individu.

## Artefak dan angka saat ini

| Artefak | Isi |
|---|---|
| `ontology.ttl` | Turtle kanonik, **17.002 triple**, **1.247 individu**, **71 kelas TBox PTP** |
| `ontology.owl` | RDF/XML kanonik untuk Protégé dan owlready2 |
| `extraction_report.json` | Ringkasan build, tautan, dan data quality |
| `ontology_md.ttl` | Kanonik + enrichment + 7 aturan SWRL + 53 diagnosis demo, **30.280 triple** setelah hasil SWRL dimaterialisasi |
| `ontology_md.owl` | RDF/XML hasil enrichment + SWRL |
| `ontology_md_inferred.ttl` | Closure Pellet penuh, **32.506 triple**; satu-satunya artefak yang memuat tipe kategori penyakit dan `owl:disjointWith` hasil inferensi |
| `swrl_rules.ttl` | **7 aturan SWRL** yang digabung ke `ontology_md` |
| `extraction_report_md.json` | Ringkasan build enrichment; `total_triples` mencatat graf asserted saat build (**20.169**) sebelum hasil SWRL diserialisasi |

Ringkasan kanonik:

- **71 kelas TBox PTP**, **32 object property** PTP (+ `prov:wasDerivedFrom`
  eksternal), **29 data property**.
- **7 tanaman**, **53 penyakit**, **78 tautan penyakit-patogen**.
- **227 pengamatan gejala**: **176 grup kanonik**, **27 konsep kanonik terpakai**,
  dan **51 pengamatan belum dipetakan**.
- **226 tautan `dikendalikanDengan`** dan **37 baris belum dipetakan**.
- **35 tautan varietas**, **13 tautan fase pertumbuhan**.
- **68 observasi lingkungan eksternal** dan **115 tautan `klasifikasiTurunan`**.
- **584 deskripsi** dan **942 fakta enrichment**.

Hasil inferensi Pellet: **PenyakitJamur 34**, **PenyakitBakteri 7**,
**PenyakitVirus 10**, **PenyakitOomycete 3**, **PenyakitFitoplasma 1**.
Kelas kategori penyakit tidak pernah di-assert eksplisit; seluruhnya muncul
dari `owl:equivalentClass` dan hanya tertulis di `ontology_md_inferred.ttl`.

## Cara menjalankan

```powershell
pip install -r 04_ontology/requirements.txt
python 02_extraction/build_doc005_chunks.py
python 03_knowledge_tables/src/build_source_gap_audit.py
python 03_knowledge_tables/src/build_external_env_facts.py
python 03_knowledge_tables/src/build_coverage_matrix.py
python 04_ontology/build_ontology.py
python 03_knowledge_tables/src/build_enrichment_facts.py
python 03_knowledge_tables/src/build_descriptions.py
python 04_ontology/build_ontology_md.py
python 03_knowledge_tables/src/build_kb_completeness_report.py
python 03_knowledge_tables/src/build_mapping_triage.py
cd 04_ontology
python -m unittest discover -s tests -p "test_*.py"
```

Test saat ini: **73 lulus** (45 test kanonik + 18 test enrichment + 10 test SWRL),
termasuk reasoning **Pellet** lewat owlready2. Bila Java tidak tersedia, test
reasoning di-skip. Helper `reasoner_utils.py` menyiapkan Jena ARQ 2.10.0 yang
kompatibel dengan Java 21; gunakan `KBR_REASONER=hermit` untuk beralih ke HermiT.

> **Peringatan:** `build_ontology.py` menimpa `ontology.ttl` dan `ontology.owl`.
> Suntingan manual di Protégé akan hilang. Untuk enrichment, bangun ulang
> `ontology_md.ttl`/`ontology_md.owl` saja.

## Namespace dan kebijakan IRI

| Namespace | IRI | Dipakai untuk |
|---|---|---|
| `ptp:` | `http://kbr.kelompok5.org/penyakit-tanaman-pangan#` | kelas, properti, individu |
| ontologi | `http://kbr.kelompok5.org/penyakit-tanaman-pangan` | header `owl:Ontology` |
| `prov:` | `http://www.w3.org/ns/prov#` | `prov:wasDerivedFrom` |

Local name wajib PascalCase/ASCII, tanpa spasi, underscore, hash, UUID, atau ID
mentah. Label manusiawi memakai `rdfs:label`, `skos:prefLabel`, dan
`skos:altLabel` bila relevan.

- **Tanaman**: `Padi`, `Kedelai`, `Jagung`, `UbiJalar`, `UbiKayu`,
  `KacangTanah`, `KacangHijau`. Bila sumber tidak mencantumkan nama ilmiah,
  generator memakai fallback Plants of the World Online (Kew) dan menulis
  `rdfs:seeAlso` ke halaman sumbernya.
- **Penyakit**: `pascal(nama + konteks tanaman/bagian)`; duplikat nama
  disambiguasi dengan konteks, mis. `AntraknosaUbiKayuBatang` dan
  `AntraknosaUbiKayuDaun`. Suffix angka hanya dipakai bila basis nama benar-benar
  sama.
- **Patogen**: `pascal(nama ilmiah)`; tabrakan nama diberi suffix angka.
  Bila satu nama ilmiah punya taxon berbeda antardokumen, taxon yang lebih
  spesifik dipilih (mis. `Peronospora manshurica` → oomycete, bukan jamur).
- **Varietas**: `Varietas` + pascal(nama), mis. `VarietasTukadUnda`.
- **Fase**: individu spesifik, mis. `FaseAnakanTanaman`, `FaseMatangSusu`,
  `FaseVegetatifUmum`; kelasnya `FaseAnakan`, `FasePemasakan`, `FaseVegetatif`.
- **Gejala**: pengamatan adalah individu dari subclass `Gejala*` dengan local
  name `Gejala<Penyakit><Konsep>` (maksimal 60 karakter; sufiks angka bila
  bentrok). Konsep kanonik adalah individu `GejalaKanonik` (28 konsep) dan
  membawa `kodeGejala` stabil untuk pembeda pada SWRL.
- **Pengendalian**: aksi kanonik adalah individu dari subclass `Pengendalian*`
  (48 aksi kanonik).
- **Observasi eksternal**: ID semantik, mis.
  `SuhuPadaHawarDaunBakteriUbiKayu` dan
  `BuktiSuhuPadaHawarDaunBakteriUbiKayu`; `obs_id` di CSV tetap dipakai sebagai
  kunci provenance, bukan sebagai local name ontology.

Semua literal teks memakai tag `@id`; nilai numerik memakai `xsd:decimal` atau
`xsd:integer`. Tidak ada literal kosong: properti tidak ditulis bila data tidak
tersedia di sumber.

## Desain TBox

### Domain dan disjointness

`TOP_DOMAINS` berisi 14 domain utama dan dipasangkan `owl:disjointWith` dua arah:
`TanamanPangan`, `Penyakit`, `Gejala`, `GejalaKanonik`, `Patogen`,
`BagianTanaman`, `Pengendalian`, `FaktorRisiko`, `Referensi`, `Varietas`,
`FasePertumbuhan`, `Observasi`, `Diagnosis`, dan `BuktiSumber`.

`owl:AllDisjointClasses` dipakai untuk kelompok eksklusif:

- `Serealia`, `Legum`, `UmbiUmbian`;
- lima kelas patogen utama (`Jamur`, `Bakteri`, `Virus`, `Oomycete`,
  `Fitoplasma`);
- enam kategori pengendalian;
- `FaktorLingkungan`, `FaktorLahan`;
- enam kategori fase;
- tiga subclass `Referensi` (`Buku`, `JurnalIlmiah`, `PublikasiInstansi`).

Kelas bagian gejala **tidak** di-disjoint karena satu pengamatan dapat
menyebut lebih dari satu bagian tanaman. Kategori penyakit juga **tidak**
di-disjoint karena satu penyakit dapat memiliki lebih dari satu kelompok
patogen.

### Pola kelas dan individu

- Spesifik tanaman adalah individu dari kelas nominal `Serealia`, `Legum`,
  atau `UmbiUmbian` (`owl:oneOf`).
- Penyakit spesifik adalah individu `Penyakit`. Kategori seperti
  `PenyakitJamur` adalah kelas hasil inferensi dari
  `Penyakit ⊓ (disebabkanOleh some Jamur)`.
- Pengamatan gejala adalah individu `Gejala*`. Pengamatan yang berhasil
  dinormalisasi dihubungkan ke satu `GejalaKanonik` lewat
  `memilikiGejalaKanonik`; sisanya tetap sebagai pengamatan belum dipetakan.
- Aksi pengendalian adalah individu dari subclass `Pengendalian*`.
- Setiap pernyataan sumber dapat memiliki node `BuktiSumber` dengan
  `kutipanSumber`, `kutipanNormalisasi`, `dokumenSumber`, `halamanSumber`,
  `idChunkSumber`, dan `prov:wasDerivedFrom` ke `BukuDOC002`/`BukuDOC005`.

### Profil SROIQ(D)

| Huruf | Axiom | Implementasi |
|---|---|---|
| **S** | Transitive role & role hierarchy | `bagianDari` transitive (`Daun → Pucuk → Batang`); `dikendalikanDengan`, `pengendalianUmum`, `merekomendasikanPengendalian` ⊑ `berkaitanPengendalian` |
| **R** | Property chain | `memilikiGejala ∘ terdapatPada ⊑ menyerangBagian` |
| **O** | Nominal | `Serealia ≡ {Padi, Jagung}`, `Legum ≡ {Kedelai, KacangTanah, KacangHijau}`, `UmbiUmbian ≡ {UbiKayu, UbiJalar}` |
| **I** | Inverse | 9 pasang `owl:inverseOf` |
| **Q** | Qualified cardinality | `Penyakit ⊑ (memilikiReferensi min 1 Referensi)`; `Buku ⊑ (tahunTerbit exactly 1 xsd:integer)` |
| **D** | Data range | `xsd:string`, `xsd:integer`, `xsd:decimal`, `xsd:anyURI`, `rdf:PlainLiteral` |

Restriksi kunci:

- `Penyakit ⊑ menyerangTanaman some TanamanPangan`
- `Penyakit ⊑ memilikiGejala some Gejala`
- `Penyakit ⊑ disebabkanOleh only Patogen`
- `Penyakit ⊑ memilikiReferensi min 1 Referensi`
- `BuktiSumber ⊑ prov:wasDerivedFrom some Referensi`
- `Buku ⊑ tahunTerbit exactly 1 xsd:integer`

## Ekstraksi ABox

- **Gejala**: 227 pengamatan dikelompokkan per `(penyakit, konsep kanonik)`
  menjadi 176 grup kanonik dan dihubungkan ke bagian tanaman berdasarkan nama
  penyakit atau konsep kanonik. 51 baris belum cocok dengan kosakata kanonik
  dan dicatat di laporan.
- **Pengendalian**: aksi kanonik dipilih dari 48 tindakan; baris
  disease-scope dan chapter-scope dibedakan. 37 baris belum dipetakan ke aksi
  kanonik dan tetap menyimpan bukti.
- **Patogen**: 78 tautan; 0 kelompok patogen masih `unknown`. Taxon yang lebih
  spesifik menang bila ada konflik antardokumen; nama ilmiah yang setara
  dihubungkan dengan `owl:sameAs`.
- **Lingkungan**: 3 observasi numerik (suhu/kelembapan) dengan `nilaiMin`,
  `nilaiMaks`, atau `nilaiTunggal`, operator, satuan, dan bukti; 7 kondisi
  kualitatif seperti `KondisiMusimHujan`/`KondisiSuhuRendah`; total 68
  observasi eksternal dengan 115 tautan `klasifikasiTurunan`.
- **Varietas/fase**: 35 tautan varietas dan 13 tautan fase. Tautan
  `tahanTerhadap` hanya ditulis bila sumber menyatakan tahan/toleran tanpa
  penanda rentan; varietas unggul juga memperoleh tipe `VarietasUnggul`.
- **Metadata terkurasi**: 17 baris eksplisit di
  `03_knowledge_tables/curated/metadata.csv` mengisi severity, fase, nama
  Inggris, dan relasi varietas rentan; setiap baris membawa kutipan sumber.

Data quality yang sengaja dilaporkan, bukan disembunyikan:

- `fragment_quotes`: **210**
- `unmapped_symptoms`: **51**
- `unmapped_controls`: **37**
- `unknown_pathogens`: **0**
- `diseases_without_explicit_part`: **0**
- Penyakit tanpa patogen: **0**
- Tidak ada data pH; observasi lingkungan numerik masih sparse.

## Enrichment — `ontology_md.ttl`

`ontology_md.ttl` adalah graf berdiri sendiri: seluruh isi `ontology.ttl`
ditambah TBox/ABox enrichment. Kanonik tidak pernah ditulis ulang.

| Item | Nilai |
|---|---|
| Triple `ontology_md.ttl` | **30.280** (laporan build mencatat **20.169 asserted** = base **17.002** + tambahan **3.167**; sisanya hasil SWRL yang dimaterialisasi setelah build) |
| Triple `ontology_md_inferred.ttl` | **32.506** (closure Pellet penuh, termasuk kategori penyakit dan `owl:disjointWith`) |
| Fakta enrichment | **942** (internal 81 + external 861) |
| Entitas yang dirujuk fakta | **313** (internal 93: 7 tanaman, 53 penyakit, 28 kondisi lingkungan, 5 faktor risiko; external 220) |
| Deskripsi `rdfs:comment` | **584** (internal 448 + external 136; `auto_ok` 323, `needs_review` 125, `verified` 136) |
| Individu `owl:NamedIndividual` | **1.508** |
| Diagnosis demo | **53** (satu per penyakit) |
| Kelas dengan deskripsi | **71 dari 71** |
| Individu tanpa deskripsi | **0** |
| TBox tambahan | `memilikiKondisiTumbuh` (domain `TanamanPangan`, range `FaktorRisiko`), `kodeGejala`, serta properti inferensi `kandidatKuat`, `merekomendasikanVarietas`, dan `menandaiRisikoLingkungan` |

Predikat fakta internal: `deskripsiPenyakit` 53, `deskripsiTanaman` 7,
`dipengaruhiOleh` 82, `memilikiKondisiTumbuh` 9, `tingkatKeparahan` 14.
External menambahkan 861 fakta: 856 fakta dari 68 observasi lingkungan +
5 fakta kondisi tumbuh. Termasuk `dipengaruhiOleh` 68,
`memengaruhiPenyakit` 68, `didukungOleh` 68, dan `memilikiKondisiTumbuh` 5.

`swrl_rules.ttl` menambahkan **7 aturan SWRL**: kandidat dari gejala, kandidat
dari faktor lingkungan, rekomendasi pengendalian spesifik, fallback
pengendalian umum tanaman, kandidat kuat dari dua gejala kanonik berbeda,
rekomendasi varietas tahan, dan penanda risiko lingkungan. Builder menandai
setiap node body/head sebagai `swrl:AtomList` agar SWRL terbaca
Protégé/OWLAPI. Pellet dipakai sebagai reasoner utama; hasilnya diserialisasi
ke `ontology_md.ttl` dan closure penuhnya ke `ontology_md_inferred.ttl`.

Deskripsi internal berasal dari
`03_knowledge_tables/auto/DOC002_md/DOC002_descriptions.csv`; deskripsi external
dari `03_knowledge_tables/auto/EXTERNAL_ENV/EXTERNAL_ENV_descriptions.csv`.
Subjek tanpa sumber tidak diisi teks karangan; daftar gap ada di
`03_knowledge_tables/reports/DOC002_description_gaps.md`.

## Membuka dan mendemokan di Protégé

1. Buka Protégé 5.6+, **File → Open…**, pilih `ontology.owl` atau
   `ontology_md.owl`.
2. Tab **Entities** menampilkan 71 kelas PTP; tab **Object Properties**
   menampilkan properti PTP + `prov:wasDerivedFrom`.
3. Tab **Data Properties** menampilkan 29 properti, termasuk nilai lingkungan
   `xsd:decimal`.
4. Tab **Reasoner** → **Pellet** (plugin) atau **HermiT** → **Synchronize Reasoner**.
5. Cek kelas inferensi: `PenyakitJamur` 34, `PenyakitBakteri` 7,
   `PenyakitVirus` 10, `PenyakitOomycete` 3, `PenyakitFitoplasma` 1.
6. Cek nominal: `Serealia` = Padi/Jagung, `Legum` = Kedelai/KacangTanah/
   KacangHijau, `UmbiUmbian` = UbiKayu/UbiJalar.
7. DL Query contoh:
   `Penyakit and (disebabkanOleh some Jamur)` → 34 hasil;
   `Varietas and (tahanTerhadap some Penyakit)` → varietas tahan.

## Demo SWRL

Tujuh aturan di `swrl_rules.ttl` hanya ada di `ontology_md.ttl`/`.owl`, bukan
di artefak kanonik. Semua aturan bekerja pada individu `Diagnosis`. Hasilnya
sudah diserialisasi ke `ontology_md.ttl` dan closure penuhnya ke
`ontology_md_inferred.ttl`, tetapi verifikasi tetap dilakukan dengan
menjalankan ulang Pellet.

| Aturan | Badan aturan | Kepala aturan | Uji cepat |
|---|---|---|---|
| `RuleKandidatGejala` | Diagnosis punya tanaman dan observasi; observasi punya gejala kanonik; penyakit menyerang tanaman dan punya gejala kanonik yang sama | `menghasilkanPenyakit` | `DiagnosisUjiBlas` + `Padi` + `GejalaPenyakitBlasPadiBercakDaun` → `PenyakitBlasPadi` |
| `RuleKandidatLingkungan` | Diagnosis punya observasi lingkungan dengan `klasifikasiTurunan`; penyakit `dipengaruhiOleh` entitas lingkungan dengan klasifikasi yang sama | `menghasilkanPenyakit` | `DiagnosisUjiLingkungan` + `UbiKayu` + observasi `Suhu` → `HawarDaunBakteriUbiKayu` |
| `RuleRekomendasiSpesifik` | Penyakit kandidat punya `dikendalikanDengan` aksi | `merekomendasikanPengendalian` | Diagnosis blas → pengendalian spesifik blas |
| `RuleRekomendasiUmum` | Penyakit kandidat menyerang tanaman; tanaman punya `pengendalianUmum` | `merekomendasikanPengendalian` | `DiagnosisUjiUbiKayu` → `PemupukanBerimbang` |
| `RuleKandidatKuat` | Diagnosis punya dua observasi dengan `kodeGejala` berbeda, dan penyakit kandidat memiliki kedua konsep kanonik tersebut | `kandidatKuat` | `DiagnosisUjiKandidatKuat` + dua gejala blas → `PenyakitBlasPadi` |
| `RuleRekomendasiVarietasTahan` | Diagnosis menghasilkan penyakit; penyakit menyerang tanaman; tanaman punya varietas yang `tahanTerhadap` penyakit itu | `merekomendasikanVarietas` | `DiagnosisUjiVarietas` → `VarietasBondoyudo` |
| `RuleRisikoLingkungan` | Observasi lingkungan diagnosis punya klasifikasi yang sama dengan entitas `dipengaruhiOleh` penyakit | `menandaiRisikoLingkungan` | `DiagnosisUjiLingkungan` → `HawarDaunBakteriUbiKayu` |

Langkah demo di Protégé:

1. Buka `ontology_md.owl`, aktifkan **Pellet**, lalu **Synchronize Reasoner**.
2. Buat individu `DiagnosisUjiBlas` dari kelas `Diagnosis`.
3. Isi `memilikiTanaman` = `Padi` dan `memilikiObservasi` =
   `GejalaPenyakitBlasPadiBercakDaun`.
4. Jalankan reasoner lagi; `menghasilkanPenyakit` harus memuat
   `PenyakitBlasPadi`, lalu `merekomendasikanPengendalian` terisi otomatis.
5. Untuk demo fallback, buat `DiagnosisUjiUbiKayu`, isi `menghasilkanPenyakit`
   = `TanamanKerdilStuntUbiKayu`, jalankan reasoner, dan cek
   `merekomendasikanPengendalian` = `PemupukanBerimbang`.

Verifikasi otomatis yang setara ada di `tests/test_swrl_reasoning.py`:

```powershell
cd 04_ontology
python -m unittest tests.test_swrl_reasoning -v
```

Test membutuhkan Java dan `owlready2`; tanpa Java, seluruh kelas SWRL di-skip.
Jika Pellet tidak tersedia, gunakan `KBR_REASONER=hermit` seperti pada test
kanonik.

## Data yang sengaja kosong

| Properti/individu | Alasan |
|---|---|
| `deskripsiTanaman`, `deskripsiPenyakit` di kanonik | diisi di `ontology_md.ttl` dari enrichment |
| `tingkatKeparahan` di kanonik | diisi di `ontology_md.ttl` bila sumber menyatakan |
| `namaPengendalian` | sumber tidak punya nama per metode |
| `urlReferensi` | hanya diisi untuk sumber registry eksternal yang mencantumkan URL |
| Individu `FaktorLahan` | sumber tidak memberi pasangan eksplisit in-scope |
| `ArtikelIlmiah` | kelas dihapus; registry eksternal memakai `JurnalIlmiah`/`PublikasiInstansi` |
| `namaIlmiah` | lengkap 7/7; empat tanaman memakai fallback Kew dan diberi `rdfs:seeAlso` |

Penyakit tanpa patogen: **0**. Tautan untuk Belang Mottle, Bud Necrosis, dan
Kerdil Rumput/Hampa sudah diisi; takson patogen yang belum diketahui juga
**0**. Pengendalian 17 penyakit UbiKayu memakai fallback
`pengendalianUmum` tingkat tanaman, bukan tautan penyakit-spesifik.

## Struktur generator

- `tbox.py` — seluruh kelas, properti, disjointness, domain/range, restriksi,
  nominal, property chain, dan `build_md_tbox()`.
- `build_ontology.py` — baca CSV DOC002/DOC005 → ekstraksi → `Builder` ABox →
  validasi struktural → tulis `ontology.ttl`, `ontology.owl`,
  `extraction_report.json`.
- `build_ontology_md.py` — baca `ontology.ttl` (hanya baca), tambahkan TBox
  enrichment, entitas, fakta, deskripsi, kondisi tumbuh eksternal, diagnosis
  demo, dan SWRL → tulis `ontology_md.ttl`, `ontology_md.owl`,
  `extraction_report_md.json`. Hasil SWRL dimaterialisasi setelah build;
  closure penuhnya disimpan sebagai `ontology_md_inferred.ttl`.
- `tests/test_ontology.py` — 45 test: snapshot dinamis, IRI hygiene, bukti,
  disjointness, SROIQ(D) termasuk transitive `bagianDari`, nama ilmiah, build
  gate, dan Pellet.
- `tests/test_ontology_md.py` — 18 test enrichment: properti, cakupan tanaman,
  fakta, bahasa literal, konsistensi laporan, deskripsi, kanonik tidak
  tercemari, dan Pellet.
- `tests/test_swrl_reasoning.py` — 10 test SWRL: rule termuat, kandidat gejala,
  kandidat lingkungan, rekomendasi spesifik, fallback umum, kandidat kuat,
  rekomendasi varietas tahan, risiko lingkungan, transitive `bagianDari`, dan
  artefak md-only.

Test tidak mengunci jumlah triple/individu lama. Angka diverifikasi terhadap
`extraction_report.json`/`extraction_report_md.json` dan invarian graf, sehingga
perubahan data yang sah tidak memerlukan pembaruan snapshot manual.
