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
| `ontology.ttl` | Turtle kanonik, **15.801 triple**, **1.159 individu** |
| `ontology.owl` | RDF/XML kanonik untuk Protégé dan owlready2 |
| `extraction_report.json` | Ringkasan build, tautan, dan data quality |
| `ontology_md.ttl` | Kanonik + enrichment, **16.391 triple** |
| `ontology_md.owl` | RDF/XML hasil enrichment |
| `extraction_report_md.json` | Ringkasan build enrichment |

Ringkasan kanonik:

- **89 kelas**, **28 object property** PTP (+ `prov:wasDerivedFrom` eksternal),
  **33 data property**.
- **7 tanaman**, **53 penyakit**, **73 tautan penyakit-patogen**.
- **240 baris gejala** menjadi **222 pengamatan gejala**: **91 grup kanonik**
  dan **131 pengamatan belum dipetakan**.
- **257 baris pengendalian disease-scope + 45 baris chapter-scope**;
  **192 tautan `dikendalikanDengan`**.
- **38 item varietas**, **3 tautan fase pertumbuhan**.
- **7 observasi lingkungan numerik** dan **8 kondisi kualitatif**.
- **698 node bukti** dan **1.139 tautan `didukungOleh`**.

Hasil inferensi HermiT: **PenyakitJamur 26**, **PenyakitBakteri 5**,
**PenyakitVirus 5**, **PenyakitOomycete 1**, **PenyakitFitoplasma 1**,
**PenyakitNematoda 0**. Kelas kategori penyakit tidak pernah di-assert
eksplisit; seluruhnya muncul dari `owl:equivalentClass`.

## Cara menjalankan

```powershell
pip install -r 04_ontology/requirements.txt
python 04_ontology/build_ontology.py
python 03_knowledge_tables/src/build_enrichment_facts.py
python 03_knowledge_tables/src/build_descriptions.py
python 04_ontology/build_ontology_md.py
cd 04_ontology
python -m unittest discover -s tests -p "test_*.py"
```

Test saat ini: **55 lulus** (39 test kanonik + 16 test enrichment), termasuk
reasoning **HermiT** lewat owlready2. Bila Java tidak tersedia, test reasoning
di-skip.

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
  `KacangTanah`, `KacangHijau`.
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
- **Gejala**: pengamatan adalah individu dari subclass `Gejala*`; konsep
  kanonik adalah individu `GejalaKanonik` (12 konsep).
- **Pengendalian**: aksi kanonik adalah individu dari subclass `Pengendalian*`
  (44 aksi kanonik).

Semua literal teks memakai tag `@id`; nilai numerik memakai `xsd:decimal` atau
`xsd:integer`. Tidak ada literal kosong: properti tidak ditulis bila data tidak
tersedia di sumber.

## Desain TBox

### Domain dan disjointness

`TOP_DOMAINS` berisi 15 domain utama dan dipasangkan `owl:disjointWith` dua arah:
`TanamanPangan`, `Penyakit`, `Gejala`, `GejalaKanonik`, `Patogen`,
`BagianTanaman`, `Pengendalian`, `FaktorRisiko`, `Referensi`, `Varietas`,
`FasePertumbuhan`, `Observasi`, `Diagnosis`, `RekomendasiPengendalian`, dan
`BuktiSumber`.

`owl:AllDisjointClasses` dipakai untuk kelompok eksklusif:

- `Serealia`, `Legum`, `UmbiUmbian`;
- tujuh kelas patogen utama;
- enam kategori pengendalian;
- `FaktorLingkungan`, `FaktorBudidaya`, `FaktorLahan`;
- tujuh kategori fase;
- `VarietasUnggul`, `VarietasLokal`;
- empat subclass `Referensi`.

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
| **S** | SubClassOf, SubPropertyOf | Taksonomi kelas; `dikendalikanDengan`, `pengendalianUmum`, `merekomendasikanPengendalian` ⊑ `berkaitanPengendalian` |
| **R** | Property chain | `memilikiGejala ∘ terdapatPada ⊑ menyerangBagian` |
| **O** | Nominal | `Serealia ≡ {Padi, Jagung}`, `Legum ≡ {Kedelai, KacangTanah, KacangHijau}`, `UmbiUmbian ≡ {UbiKayu, UbiJalar}` |
| **I** | Inverse | 8 pasang `owl:inverseOf` |
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

- **Gejala**: 240 baris diproses; pengamatan dikelompokkan per
  `(penyakit, konsep kanonik)` dan dihubungkan ke bagian tanaman. 131 baris
  belum cocok dengan kosakata kanonik dan dicatat di laporan.
- **Pengendalian**: aksi kanonik dipilih dari 44 tindakan; baris
  disease-scope dan chapter-scope dibedakan. 108 baris belum dipetakan ke aksi
  kanonik dan tetap menyimpan bukti.
- **Patogen**: 73 tautan; 15 kelompok patogen masih `unknown`. Taxon yang lebih
  spesifik menang bila ada konflik antardokumen.
- **Lingkungan**: 7 observasi numerik (suhu/kelembapan) dengan `nilaiMin`,
  `nilaiMaks`, atau `nilaiTunggal`, operator, satuan, dan bukti; 8 kondisi
  kualitatif seperti `KondisiMusimHujan`/`KondisiSuhuRendah`.
- **Varietas/fase**: 38 item varietas dan 3 tautan fase. Tautan `tahanTerhadap`
  hanya ditulis bila sumber menyatakan tahan/toleran tanpa penanda rentan.

Data quality yang sengaja dilaporkan, bukan disembunyikan:

- `fragment_quotes`: **209**
- `unmapped_symptoms`: **131**
- `unmapped_controls`: **108**
- `unknown_pathogens`: **15**
- `diseases_without_explicit_part`: **35**
- Penyakit tanpa patogen: **3**
- Tidak ada data pH; observasi lingkungan numerik masih sparse.

## Enrichment — `ontology_md.ttl`

`ontology_md.ttl` adalah graf berdiri sendiri: seluruh isi `ontology.ttl`
ditambah TBox/ABox enrichment. Kanonik tidak pernah ditulis ulang.

| Item | Nilai |
|---|---|
| Triple total | **16.391** = base **15.801** + tambahan **590** |
| Fakta enrichment | **84** |
| Entitas yang dirujuk fakta | **91** (7 tanaman, 53 penyakit, 25 kondisi lingkungan, 6 faktor risiko) |
| Deskripsi `rdfs:comment` | **420** (`auto_ok` 299, `needs_review` 121) |
| Individu `owl:NamedIndividual` | **1.182** |
| Kelas dengan deskripsi | **89 dari 89** |
| Individu tanpa deskripsi | **8 kondisi lingkungan dan 9 pengamatan gejala** |
| TBox tambahan | `memilikiKondisiTumbuh` (domain `TanamanPangan`, range `FaktorLingkungan`) |

Predikat fakta enrichment: `deskripsiPenyakit` 53, `deskripsiTanaman` 7,
`dipengaruhiOleh` 11, `memilikiKondisiTumbuh` 4, `tingkatKeparahan` 9.

Deskripsi berasal dari
`03_knowledge_tables/auto/DOC002_md/DOC002_descriptions.csv`. Subjek tanpa
sumber tidak diisi teks karangan; daftar gap ada di
`03_knowledge_tables/reports/DOC002_description_gaps.md`.

## Membuka dan mendemokan di Protégé

1. Buka Protégé 5.6+, **File → Open…**, pilih `ontology.owl` atau
   `ontology_md.owl`.
2. Tab **Entities** menampilkan 89 kelas; tab **Object Properties** menampilkan
   properti PTP + `prov:wasDerivedFrom`.
3. Tab **Data Properties** menampilkan 33 properti, termasuk nilai lingkungan
   `xsd:decimal`.
4. Tab **Reasoner** → **HermiT** → **Synchronize Reasoner**.
5. Cek kelas inferensi: `PenyakitJamur` 29, `PenyakitBakteri` 5,
   `PenyakitVirus` 5, `PenyakitOomycete` 2, `PenyakitFitoplasma` 1.
6. Cek nominal: `Serealia` = Padi/Jagung, `Legum` = Kedelai/KacangTanah/
   KacangHijau, `UmbiUmbian` = UbiKayu/UbiJalar.
7. DL Query contoh:
   `Penyakit and (disebabkanOleh some Jamur)` → 29 hasil;
   `Varietas and (tahanTerhadap some Penyakit)` → varietas tahan.

## Data yang sengaja kosong

| Properti/individu | Alasan |
|---|---|
| `deskripsiTanaman`, `deskripsiPenyakit` di kanonik | diisi di `ontology_md.ttl` dari enrichment |
| `tingkatKeparahan` di kanonik | diisi di `ontology_md.ttl` bila sumber menyatakan |
| `namaPengendalian` | sumber tidak punya nama per metode |
| `urlReferensi` | metadata tidak punya URL |
| Individu `FaktorBudidaya`/`FaktorLahan` | tidak ada pasangan eksplisit in-scope |
| `JurnalIlmiah`/`ArtikelIlmiah`/`PublikasiInstansi` | hanya dua buku dalam cakupan |
| `namaIlmiah` Padi/Jagung/KacangHijau/KacangTanah | scientific name kosong di sumber |

Penyakit tanpa patogen (3): `PenyakitBelangMottleKacangTanah`,
`NekrosisPadaTitikTunasCassavaBudNecrosisUbiKayu`,
`PenyakitKerdilRumputDanKerdilHampaPadi`. Restriksi
`disebabkanOleh only Patogen` tetap terpenuhi secara kosong.

## Struktur generator

- `tbox.py` — seluruh kelas, properti, disjointness, domain/range, restriksi,
  nominal, property chain, dan `build_md_tbox()`.
- `build_ontology.py` — baca CSV DOC002/DOC005 → ekstraksi → `Builder` ABox →
  validasi struktural → tulis `ontology.ttl`, `ontology.owl`,
  `extraction_report.json`.
- `build_ontology_md.py` — baca `ontology.ttl` (hanya baca), tambahkan TBox
  enrichment, entitas, fakta, dan deskripsi → tulis `ontology_md.ttl`,
  `ontology_md.owl`, `extraction_report_md.json`.
- `tests/test_ontology.py` — 39 test: snapshot dinamis, IRI hygiene, bukti,
  disjointness, SROIQ(D), build gate, dan HermiT.
- `tests/test_ontology_md.py` — 16 test enrichment: properti, cakupan tanaman,
  fakta, bahasa literal, konsistensi laporan, deskripsi, kanonik tidak
  tercemari, dan HermiT.

Test tidak mengunci jumlah triple/individu lama. Angka diverifikasi terhadap
`extraction_report.json`/`extraction_report_md.json` dan invarian graf, sehingga
perubahan data yang sah tidak memerlukan pembaruan snapshot manual.
