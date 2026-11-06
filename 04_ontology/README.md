# Ontologi OWL 2 — Penyakit Tanaman Pangan Indonesia

Folder ini membangun ontologi OWL 2 berbahasa Indonesia dari knowledge tables
terkurasi di `03_knowledge_tables/`, sesuai rancangan kelas
**TanamanPangan, Penyakit, Gejala, Patogen, BagianTanaman, Pengendalian,
FaktorRisiko, Referensi, Varietas, FasePertumbuhan**. TBox didefinisikan manual
di `tbox.py` dengan profil **minimal SROIQ(D)**; ABox dibangkitkan otomatis oleh
`build_ontology.py` dari CSV sumber (DOC002 + DOC005), lalu divalidasi
(jumlah individu/triple, axioms SROIQ(D), domain/range, ketiadaan literal
kosong, larangan assert eksplisit kelas hasil klasifikasi). Generator berkode
keluar `2` bila validasi gagal.

Cakupan: **7 tanaman pangan** — Padi, Kedelai, Jagung, Ubi Jalar, Ubi Kayu,
Kacang Tanah, Kacang Hijau — dengan **57 penyakit**, **240 gejala**,
**59 patogen**, **261 pengendalian**, **34 varietas**, **3 fase pertumbuhan**,
**5 kondisi lingkungan**.

## Cara menjalankan

```powershell
pip install -r 04_ontology/requirements.txt   # rdflib >=7,<8 dan owlready2 >=0.45
python 04_ontology/build_ontology.py          # menulis ontology.ttl, ontology.owl, extraction_report.json
cd 04_ontology
python -m unittest discover -s tests -p "test_*.py"
```

Keluaran build terakhir: **5 436 triple**, **674 individu**. Test: **34 lulus**,
termasuk uji reasoning HermiT lewat owlready2 (membutuhkan Java di PATH; bila
Java tidak ada, test reasoning dilewati/skip).

Artefak:

- `ontology.ttl` — Turtle, sumber utama di repo.
- `ontology.owl` — RDF/XML, untuk dibuka di Protégé dan untuk test owlready2.
- `extraction_report.json` — bukti ekstraksi varietas/fase/kondisi/kategori.

## Namespace dan kebijakan IRI

| Namespace | IRI | Dipakai untuk |
|---|---|---|
| `ptp:` | `http://kbr.kelompok5.org/penyakit-tanaman-pangan#` | kelas, properti, individu |
| ontologi | `http://kbr.kelompok5.org/penyakit-tanaman-pangan` | header `owl:Ontology` |

Kebijakan local name individu (tanpa mengubah data sumber):

- **Tanaman**: pascal nama verbatim, digabung lintas dokumen per nama →
  `Padi`, `Kedelai`, `Jagung`, `UbiJalar`, `UbiKayu`, `KacangTanah`,
  `KacangHijau` (PLANT_002≡PLANT_018, PLANT_003≡PLANT_019).
- **Penyakit**: pascal(nama penyakit + local tanaman) → `LayuFusariumUbiJalar`;
  bila nama+grup duplikat (mis. "Antraknosa" dua kali pada ubi kayu),
  **semua** anggota grup diberi suffix `pascal(disease_id)` →
  `AntraknosaUbiKayuDIS031`, `AntraknosaUbiKayuDIS110`.
- **Patogen**: pascal(nama ilmiah) disatukan lintas dokumen; tabrakan nama
  ilmiah diberi suffix `pascal(pathogen_id)`. Taxon `unknown` kalah terhadap
  taxon yang diketahui (mis. Peronospora → oomycete dari DOC005).
- **Varietas**: `Varietas` + pascal(nama hasil ekstraksi) → `VarietasTukadUnda`.
- **Fase**: `FaseMatangSusu`, `FaseVegetatif`, `FaseAnakan`, …
- **Kondisi lingkungan**: individu kanonik singleton
  `KondisiKelembapanTinggi`, `KondisiSuhu`, `KondisiCurahHujan`,
  `KondisiMusimHujan`, `KondisiMusimKemarau`.
- **Gejala/Pengendalian**: prefix kelas + pascal(5 kata pertama) + `_` +
  8 karakter pertama md5 teks — teks identik memakai IRI yang sama.

Semua literal teks memakai tag bahasa `@id` (kecuali `tahunTerbit` dan
cardinality `xsd:nonNegativeInteger`). Literal tidak pernah kosong — bila data
tidak ada di sumber, properti tidak ditulis sama sekali.

## Tabel master

### Kelas utama dan subclass

| Kelas utama | Subclass | Individu |
|---|---|---|
| TanamanPangan | Serealia (Padi, Jagung), Legum (Kedelai, KacangTanah, KacangHijau) | 7 |
| Penyakit | PenyakitJamur, PenyakitBakteri, PenyakitVirus, PenyakitLainnya | 57 |
| Gejala | GejalaDaun, GejalaBatang, GejalaAkar, GejalaUmbi | 240 (95/22/11/4) |
| Patogen | Jamur, Bakteri, Virus, OrganismeLain | 59 (29/5/8/2) |
| BagianTanaman | — (Daun, Batang, Akar, Umbi, Buah, Biji) | 6 |
| Pengendalian | PengendalianKulturTeknis, Mekanis, Biologis, Kimiawi, Terpadu | 261 (78/4/59/67/2) |
| FaktorRisiko | FaktorLingkungan (KelembapanTinggi, Suhu, CurahHujan, **MusimHujan**, **MusimKemarau**), FaktorBudidaya (…), FaktorLahan (…) | 5 (kondisi lingkungan) |
| Referensi | Buku, JurnalIlmiah, ArtikelIlmiah, PublikasiInstansi | 2 (Buku DOC002 2021, DOC005 2020) |
| **Varietas** | — | 34 |
| **FasePertumbuhan** | — (FaseAnakan, FaseMatangSusu, FaseVegetatif) | 3 |

Jumlah individu subclass Penyakit* = inferensi reasoner (tidak pernah di-assert
eksplisit, divalidasi test). Subclass Pengendalian* di-assert eksplisit
multi-label dari klasifikasi keyword/`control_category` (subclasses tersebut
**tidak** di-disjoint agar multi-label aman).

### Object property (18)

| Properti | Domain | Range | Invers |
|---|---|---|---|
| menyerangTanaman | Penyakit | TanamanPangan | diserangPenyakit |
| memilikiGejala | Penyakit | Gejala | merupakanGejalaDari |
| disebabkanOleh | Penyakit | Patogen | menyebabkanPenyakit |
| menyerangBagian | Penyakit | BagianTanaman | — (superproperty chain) |
| dikendalikanDengan | Penyakit | Pengendalian | mengendalikanPenyakit |
| pengendalianUmum | TanamanPangan | Pengendalian | — |
| berkaitanPengendalian | *(tanpa domain)* | Pengendalian | — (superproperty S) |
| dipengaruhiOleh | Penyakit | FaktorRisiko | — |
| memilikiReferensi | Penyakit | Referensi | dijelaskanDalam |
| terdapatPada | Gejala | BagianTanaman | — |
| memilikiVarietas | TanamanPangan | Varietas | merupakanVarietasDari |
| tahanTerhadap | Varietas | Penyakit | — |
| menyerangFase | Penyakit | FasePertumbuhan | — |
| + 6 pasang inverse terdaftar di atas (12 axioms `owl:inverseOf`) | | | |

### Data property (12)

| Properti | Domain | Nilai terisi |
|---|---|---|
| namaIlmiah | TanamanPangan | 3 (Kedelai, UbiJalar, UbiKayu) |
| deskripsiTanaman | TanamanPangan | 0 |
| namaIlmiahPatogen | Patogen | 59 |
| deskripsiPenyakit | Penyakit | 0 |
| deskripsiGejala | Gejala | 240 |
| tingkatKeparahan | Penyakit | 0 |
| judulReferensi | Referensi | 2 |
| tahunTerbit | Referensi | 2 (`2020`, `2021` ^^xsd:integer) |
| namaPenulis | Referensi | 2 |
| urlReferensi | Referensi | 0 |
| namaPengendalian | Pengendalian | 0 |
| deskripsiPengendalian | Pengendalian | 261 |

`rdfs:range` sengaja tidak ditulis untuk data property teks: nilai memakai tag
bahasa `@id` (rdf:langString) yang pada OWL 2 **disjoint** dengan `xsd:string`.

## Profil SROIQ(D)

| Huruf | Axiom | Implementasi |
|---|---|---|
| **S** | SubClass Of, SubProperty Of | `Penyakit ⊑ …` (4 restriction); `dikendalikanDengan ⊑ berkaitanPengendalian`, `pengendalianUmum ⊑ berkaitanPengendalian` |
| **R** | Property chain | `memilikiGejala ∘ terdapatPada ⊑ menyerangBagian` |
| **O** | Nominal | `Serealia ≡ {Padi, Jagung}`, `Legum ≡ {Kedelai, KacangTanah, KacangHijau}` (owl:oneOf) |
| **I** | Inverse | 6 pasang = **12** triple `owl:inverseOf` |
| **Q** | Qualified cardinality | `Penyakit ⊑ (memilikiReferensi min 1 Referensi)`; `Buku ⊑ (tahunTerbit exactly 1 xsd:integer)` |
| **D** | Data range | `tahunTerbit` xsd:integer; literal teks @id tanpa range xsd:string |

Role pada property chain tidak dikenai number restriction (simple role).

### Disjoint & equivalent

| Axiom | Jumlah | Isi |
|---|---|---|
| Disjoint Classes | **60** pasang | C(10,2) antar 10 kelas utama, 6 Penyakit*, 6 Patogen*, 3 Faktor*. Gejala* dan Pengendalian* **tidak** di-disjoint. |
| Equivalent Classes | 5 | 3 penalaran penyakit (Jamur/Bakteri/Virus) + 2 nominal Serealia/Legum |
| Sub Class Of + restriction | 4 | some menyerangTanaman, some memilikiGejala, only disebabkanOleh, **min 1** memilikiReferensi |
| Inverse Of | 12 | 6 pasang |
| SubProperty Of | 2 | menuju `berkaitanPengendalian` |
| Property chain | 1 | `memilikiGejala ∘ terdapatPada ⊑ menyerangBagian` |
| Datatype restriction | 1 | `Buku ⊑ tahunTerbit exactly 1 xsd:integer` |

Hasil reasoning HermiT (konsisten, tanpa `owl:Nothing`):

- **PenyakitJamur: 29**, **PenyakitBakteri: 5**, **PenyakitVirus: 5**,
  **PenyakitLainnya: 0** — murni inferensi, tidak pernah di-assert.
- **Serealia: 2** (Padi, Jagung), **Legum: 3** (Kedelai, KacangTanah,
  KacangHijau) — inferensi dari owl:oneOf.

## Ekstraksi deterministik (ABox tambahan)

Semua hasil tercatat di `extraction_report.json`:

- **Varietas** — pola `varietas <NamaProper>` (+ fallback `adalah`); daftar
  "A, B, dan C"; stopword/filler dibuang; akronim patogen (CMMV, PStV) dan
  huruf tunggal ditolak; prefix nama tanaman dipangkas (`Jagung Pioneer 21` →
  `Pioneer 21`). `tahanTerhadap` hanya bila teks punya penanda resistensi
  (tahan/resistan/toleran) **tanpa** penanda rentan/peka.
- **Fase pertumbuhan** — whitelist `fase (matang susu|vegetatif|generatif|
  pembibitan|anakan|matang)`; fase penyakit (kresek, nekrotik, …) ditolak.
- **Kondisi lingkungan** — keyword → 5 individu singleton bertipe eksplisit
  `FaktorRisiko` + `FaktorLingkungan` + subclass; `dipengaruhiOleh` dari
  penyakit pemilik kalimat (baris disease-scope saja).
- **Pengendalian** — DOC005 dari `control_category` via `CATEGORY_MAP`;
  DOC002 multi-label keyword → sub-kelas KulturTeknis/Kimiawi/Biologis/
  Mekanis/Terpadu. 45 baris `scope=chapter` → `pengendalianUmum` per tanaman
  (termasuk 17 penyakit ubi kayu yang tanpa kontrol per-penyakit).
  Superproperty `berkaitanPengendalian` dimaterialisasi di ABox.

## Membuka dan mendemokan di Protégé

1. Buka Protégé 5.6+, **File → Open…**, pilih `ontology.owl` (RDF/XML).
2. Tab **Entities** menampilkan 10 kelas utama berbahasa Indonesia.
3. Tab **Object Properties** — 18 properti + invers (ikon "owl:O").
4. Tab **Data Properties** — 12 properti; `tahunTerbit` ber-range `xsd:integer`.
5. Tab **Reasoner** → pilih **HermiT** → **Synchronize Reasoner**.
6. Classes: `Penyakit Jamur` inferred 29 anggota, `Penyakit Bakteri` 5,
   `Serealia` 2, `Legum` 3.
7. DL Query contoh:    `Penyakit and (disebabkanOleh value Jamur)` → 29 hasil;
   `Varietas and (tahanTerhadap some Penyakit)` memakai properti `tahanTerhadap`.
8. Klik kanan `Serealia` → Equivalent Classes menampilkan `owl:oneOf (Padi Jagung)`.
9. Tutup tanpa menyimpan bila hanya meninjau; file sumber tetap
   `ontology.owl`/`ontology.ttl`.

## Aturan SWRL (opsional)

HermiT **tidak** mengeksekusi aturan SWRL. Untuk mencoba aturan, pasang plugin
**SWRLTab** (Protégé → File → Check for Plugins), lalu jalankan dengan reasoner
SWRL yang mendukung. Contoh:

```
Penyakit(?p) ^ memilikiGejala(?p, ?g) ^ GejalaDaun(?g) -> menyerangBagian(?p, Daun)
```

Property chain TBox sudah menurunkan `menyerangBagian` dari
`memilikiGejala ∘ terdapatPada` — aturan SWRL melengkapi, bukan menggantikan.

## Data yang sengaja kosong (tanpa mengarang)

| Properti/individu | Alasan |
|---|---|
| deskripsiPenyakit, deskripsiTanaman | chunks.jsonl tidak tersedia di repo |
| tingkatKeparahan | tidak ada kolom keparahan di sumber |
| namaPengendalian | sumber tidak punya nama per metode |
| urlReferensi | `manual_metadata.json` tidak punya field URL |
| FaktorBudidaya / FaktorLahan individu | tidak ada pasangan eksplisit di in-scope |
| JurnalIlmiah/ArtikelIlmiah/PublikasiInstansi | hanya DOC002+DOC005 (buku) dalam cakupan |
| namaIlmiah Padi, Jagung, KacangHijau, KacangTanah | scientific_name kosong di sumber |

Penyakit tanpa patogen (3): PenyakitBelangMottleKacangTanah,
NekrosisPadaTitikTunasCassavaBudNecrosisUbiKayu,
PenyakitKerdilRumputDanKerdilHampaPadi — restriksi
`disebabkanOleh only Patogen` tetap terpenuhi secara kosong.

## Struktur generator

- `tbox.py` — semua kelas/properti/axioms SROIQ(D) (sumber kebenaran TBox).
- `build_ontology.py` — baca CSV DOC002+DOC005 → ekstraksi → `Builder` ABox →
  `expected_counts()` → `validate()` → tulis `ontology.ttl` + `ontology.owl`
  + `extraction_report.json`.
- `tests/test_ontology.py` — snapshot jumlah, axioms SROIQ(D), guardrail,
  build gate, dan test reasoning HermiT.
