# Ontologi OWL 2 — Penyakit Tanaman Pangan Indonesia

Folder ini membangun ontologi OWL 2 berbahasa Indonesia dari knowledge tables
terkurasi di `03_knowledge_tables/`, sesuai rancangan kelas
**TanamanPangan, Penyakit, Gejala, Patogen, BagianTanaman, Pengendalian,
FaktorRisiko, Referensi**. TBox didefinisikan manual di `tbox.py`; ABox
dibangkitkan otomatis oleh `build_ontology.py` dari CSV sumber, lalu divalidasi
(jumlah individu/triple, axioms, domain/range, ketiadaan literal kosong, larangan
assert eksplisit kelas hasil klasifikasi). Generator berkode keluar `2` bila
validasi gagal.

Cakupan prototipe: **3 tanaman** — Kacang Tanah, Ubi Jalar, Ubi Kayu — dengan
**24 penyakit**, **73 gejala**, **28 patogen**, **95 pengendalian**.

## Cara menjalankan

```powershell
pip install -r 04_ontology/requirements.txt   # rdflib >=7,<8 dan owlready2 >=0.45
python 04_ontology/build_ontology.py          # menulis ontology.ttl dan ontology.owl
cd 04_ontology
python -m unittest discover -s tests -p "test_*.py"
```

Keluaran build terakhir: **1 852 triple**, **230 individu** (24 penyakit,
73 gejala, 28 patogen, 95 pengendalian, 3 tanaman, 6 bagian tanaman,
1 referensi). Test: **27 lulus**, termasuk uji reasoning HermiT lewat owlready2
(membutuhkan Java di PATH; bila Java tidak ada, test reasoning dilewati/skip).

Artefak:

- `ontology.ttl` — Turtle, sumber utama di repo.
- `ontology.owl` — RDF/XML, untuk dibuka di Protégé dan untuk test owlready2.

## Namespace dan kebijakan IRI

| Namespace | IRI | Dipakai untuk |
|---|---|---|
| `ptp:` | `http://kbr.kelompok5.org/penyakit-tanaman-pangan#` | kelas, properti, individu |
| ontologi | `http://kbr.kelompok5.org/penyakit-tanaman-pangan` | header `owl:Ontology` |

Kebijakan local name individu (tanpa mengubah data sumber):

- **Tanaman**: pascal case nama verbatim → `KacangTanah`, `UbiJalar`, `UbiKayu`.
- **Penyakit**: pascal(nama penyakit + nama tanaman) → `LayuFusariumUbiJalar`;
  bila nama+grup duplikat (mis. "Antraknosa" muncul dua kali pada ubi kayu),
  **semua** anggota grup diberi suffix `pascal(disease_id)` →
  `AntraknosaUbiKayuDIS031`, `AntraknosaUbiKayuDIS110`.
- **Patogen**: pascal(nama ilmiah); tabrakan nama ilmiah diberi suffix
  `pascal(pathogen_id)`.
- **Gejala/Pengendalian**: prefix kelas + pascal(5 kata pertama) + `_` +
  8 karakter pertama md5 teks — teks identik memakai IRI yang sama.

Semua literal teks memakai tag bahasa `@id` (kecuali `tahunTerbit` yang
`xsd:integer`). Literal tidak pernah kosong — bila data tidak ada di sumber,
properti tidak ditulis sama sekali (lihat "Data yang sengaja kosong").

## Tabel master

### Kelas utama dan subclass

| Kelas utama | Subclass | Individu |
|---|---|---|
| TanamanPangan | — | 3 |
| Penyakit | PenyakitJamur, PenyakitBakteri, PenyakitVirus, PenyakitLainnya | 24 |
| Gejala | GejalaDaun, GejalaBatang, GejalaAkar, GejalaUmbi | 73 (26/10/4/4) |
| Patogen | Jamur, Bakteri, Virus, OrganismeLain | 28 (8/1/3/1) |
| BagianTanaman | — (individual: Daun, Batang, Akar, Umbi, Buah, Biji) | 6 |
| Pengendalian | PengendalianKulturTeknis, Mekanis, Biologis, Kimiawi, Terpadu | 95 |
| FaktorRisiko | FaktorLingkungan (KelembapanTinggi, Suhu, CurahHujan), FaktorBudidaya (SanitasiLahanBuruk, DrainaseBuruk, PenggunaanBenihTerinfeksi), FaktorLahan (KondisiTanah, KondisiDrainase) | 0 |
| Referensi | Buku, JurnalIlmiah, ArtikelIlmiah, PublikasiInstansi | 1 (Buku) |

Jumlah individu subclass = individu kelas induk yang tergolong (mis. 8 penyakit
memiliki patogen jamur, sehingga disimpulkan termasuk PenyakitJamur oleh
reasoner — **tidak pernah di-assert eksplisit**, divalidasi test).

### Object property (13)

| Properti | Domain | Range | Invers |
|---|---|---|---|
| menyerangTanaman | Penyakit | TanamanPangan | diserangPenyakit |
| memilikiGejala | Penyakit | Gejala | merupakanGejalaDari |
| disebabkanOleh | Penyakit | Patogen | menyebabkanPenyakit |
| menyerangBagian | Penyakit | BagianTanaman | — |
| dikendalikanDengan | Penyakit | Pengendalian | mengendalikanPenyakit |
| dipengaruhiOleh | Penyakit | FaktorRisiko | — |
| memilikiReferensi | Penyakit | Referensi | dijelaskanDalam |
| terdapatPada | Gejala | BagianTanaman | — |
| + 4 inverse terdaftar di atas (10 axioms `owl:inverseOf`, semua inverse juga dimaterialisasi di ABox) | | | |

`menjadiReferensiBagi` pada rancangan awal tidak dibuat terpisah; perannya
diambil alih `dijelaskanDalam` (lihat comment di `tbox.py`).

### Data property (12)

| Properti | Domain | Nilai terisi |
|---|---|---|
| namaIlmiah | TanamanPangan | 2 (kacang tanah kosong di sumber) |
| deskripsiTanaman | TanamanPangan | 0 |
| namaIlmiahPatogen | Patogen | 28 |
| deskripsiPenyakit | Penyakit | 0 |
| deskripsiGejala | Gejala | 73 |
| tingkatKeparahan | Penyakit | 0 |
| judulReferensi | Referensi | 1 |
| tahunTerbit | Referensi | 1 (`2021`^^xsd:integer) |
| namaPenulis | Referensi | 1 |
| urlReferensi | Referensi | 0 |
| namaPengendalian | Pengendalian | 0 |
| deskripsiPengendalian | Pengendalian | 95 |

`rdfs:range` sengaja tidak ditulis untuk data property: nilai teks memakai tag
bahasa `@id` (rdf:langString) yang pada OWL 2 **disjoint** dengan `xsd:string`,
sehingga range `xsd:string` akan membuat ontologi inkonsisten.

## Axioms dan penalaran

| Axiom | Jumlah | Isi |
|---|---|---|
| Disjoint Classes | 43 pasang | 28 antar 8 kelas utama, 6 antar kelas Penyakit*, 6 antar Patogen* (Jamur/Bakteri/Virus/OrganismeLain), 3 antar FaktorLingkungan/Budidaya/Lahan. Kelas Gejala* dan Pengendalian* **tidak** di-disjoint (anak bisa tumpang tindih pada kenyataan). |
| Equivalent Classes | 3 | `PenyakitJamur ≡ Penyakit ⊓ (disebabkanOleh some Jamur)` dan pola sama utk Bakteri/Virus |
| Sub Class Of + restriction | 3 | `Penyakit ⊑ menyerangTanaman some TanamanPangan`, `Penyakit ⊑ memilikiGejala some Gejala`, `Penyakit ⊑ disebabkanOleh only Patogen` |
| Inverse Of | 10 | 5 pasang (menyerangTanaman/diserangPenyakit, memilikiGejala/merupakanGejalaDari, disebabkanOleh/menyebabkanPenyakit, dikendalikanDengan/mengendalikanPenyakit, memilikiReferensi/dijelaskanDalam) |

Hasil reasoning HermiT pada ontologi final (konsisten, tanpa individu
`owl:Nothing`):

- **PenyakitJamur: 7** — BercakDaunKacangTanah, KudisUbiJalar,
  BusukHitamBlackRotUbiJalar, LayuFusariumUbiJalar, BusukUmbiUbiKayu,
  BusukPangkalBatangUbiKayu, BusukAkarDanUmbiUbiKayu.
- **PenyakitBakteri: 1** — PenyakitLayuBakteriKacangTanah.
- **PenyakitVirus: 1** — PenyakitBercakKuningUbiJalar.

Individu kelas Penyakit* tidak pernah di-assert; murni inferensi reasoner.

## Membuka dan mendemokan di Protégé

1. Buka Protégé 5.6+, **File → Open…**, pilih `ontology.owl` (RDF/XML).
2. Pastikan tab **Entities** menampilkan 8 kelas utama berbahasa Indonesia
   (Entity Type: Classes).
3. Buka tab **Object Properties** — cek 13 properti + 4 inverse (ikon "owl:O").
4. Buka tab **Data Properties** — cek 12 properti; buka `tahunTerbit` untuk
   melihat range `xsd:integer`.
5. Buka tab **Reasoner**, pilih **HermiT** dari menu Reasoner.
6. Klik **Reasoner → Synchronize Reasoner** (tunggu hingga selesai).
7. Kembali ke tab Classes: kelas yang terinferensi (mis. `Penyakit Bakteri`)
   tersorot; buka klasenya → **Members (inferred)** berisi
   PenyakitLayuBakteriKacangTanah. Utk Penyakit Jamur ada 7 anggota.
8. Buka tab **DL Query**, ketik kelas ekspresi
   `Penyakit and (disebabkanOleh value Jamur)` — klik **Ask** → hasil sama
   dengan 7 anggota PenyakitJamur.
9. Untuk melihat axioms: klik kanan kelas `Penyakit` → **View →
   Description**, sorot restriction `menyerangTanaman some TanamanPangan`
   dsb; klik kanan `Penyakit Jamur` → Equivalent Classes menampilkan
   `Penyakit ⊓ disebabkanOleh some Jamur`.
10. Tutup tanpa menyimpan bila hanya meninjau (inferensi reasoner tidak perlu
    disimpan ke file); file sumber tetap `ontology.owl`/`ontology.ttl`.

## Aturan SWRL (opsional)

HermiT **tidak** mengeksekusi aturan SWRL. Untuk mencoba aturan, pasang plugin
**SWRLTab** (Protégé → File → Check for Plugins), tambahkan rule lewat tab
SWRL, lalu jalankan dengan reasoner SWRL yang mendukung (mis. Drools/Rule
Engine pada SWRLTab). Contoh aturan yang seluruh simbolnya sudah ada di
ontologi — otomatiskan `menyerangBagian` dari gejala daun:

```
Penyakit(?p) ^ memilikiGejala(?p, ?g) ^ GejalaDaun(?g) -> menyerangBagian(?p, Daun)
```

Aturan ini melengkapi (bukan menggantikan) data `menyerangBagian` yang sudah
di-assert dari sumber.

## Data yang sengaja kosong (tanpa mengarang)

| Properti/individu | Alasan |
|---|---|
| deskripsiPenyakit, deskripsiTanaman | `03_knowledge_sources/.../chunks.jsonl` tidak tersedia di repo |
| tingkatKeparahan | tidak ada kolom keparahan di sumber |
| namaPengendalian | sumber tidak punya nama/nategori per metode (kolom kategori kosong) |
| urlReferensi | `manual_metadata.json` tidak punya field URL |
| individu FaktorRisiko; `dipengaruhiOleh` (0 triple) | rancangan mensyaratkan struktur kelasnya saja; tidak ada pasangan penyakit–faktor di sumber |
| PengendalianKulturTeknis … Terpadu (0 individu) | kontrol sumber tidak terkategori |
| Pengendalian penyakit ubi kayu | sumber punya kontrol per-disease hanya untuk kacang tanah (81) dan ubi jalar (14) |
| JurnalIlmiah/ArtikelIlmiah/PublikasiInstansi | hanya DOC002 (buku) yang dalam cakupan; DOC003/DOC004 di luar cakupan |
| namaIlmiah kacang tanah | `plants.csv` kolom scientific_name kosong |

Penyakit tanpa patogen (2): PenyakitBelangMottleKacangTanah,
NekrosisPadaTitikTunasCassavaBudNecrosisUbiKayu — restriksi
`disebabkanOleh only Patogen` tetap terpenuhi secara kosong.

## Struktur generator

- `tbox.py` — semua kelas/properti/axioms (sumber kebenaran tunggal TBox).
- `build_ontology.py` — pembaca CSV → `Builder` ABox → `expected_counts()` →
  `validate()` → tulis `ontology.ttl` + `ontology.owl`.
- `tests/test_ontology.py` — snapshot jumlah, axioms, guardrail, build gate,
  dan test reasoning HermiT.
