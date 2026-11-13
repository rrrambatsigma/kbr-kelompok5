# Ontologi OWL 2 — Penyakit Tanaman Pangan Indonesia

Folder ini membangun ontologi OWL 2 berbahasa Indonesia dari knowledge tables
terkurasi di `03_knowledge_tables/`, sesuai rancangan kelas
**TanamanPangan, Penyakit, Gejala, Patogen, BagianTanaman, Pengendalian,
FaktorRisiko, Referensi, Varietas, FasePertumbuhan**. TBox didefinisikan manual
di `tbox.py` dengan profil **SROIQ(D)**; ABox dibangkitkan otomatis oleh
`build_ontology.py` dari CSV dan teks sumber (DOC002 + DOC005), lalu divalidasi
(konsistensi tipe, domain/range, inverse, disjoint, restriksi, penamaan IRI,
ketiadaan literal kosong, larangan assert eksplisit kelas hasil klasifikasi).
Generator berkode keluar `2` bila validasi gagal.

Cakupan: **7 tanaman pangan** — Padi, Kedelai, Jagung, Ubi Jalar, Ubi Kayu,
Kacang Tanah, Kacang Hijau — dengan **54 penyakit**, **238 gejala**,
**59 patogen**, **261 pengendalian**, **34 varietas**, **3 fase pertumbuhan**,
dan **55 individu faktor lingkungan**. Artefak terakhir berisi **12.110 triple**
dan **726 individu**.

## Cara menjalankan

```powershell
pip install -r 04_ontology/requirements.txt   # rdflib >=7,<8 dan owlready2 >=0.45
python -X utf8 -B 04_ontology/build_ontology.py
cd 04_ontology
python -X utf8 -B -m unittest discover -s tests -p "test_*.py" -v
```

Keluaran build terakhir: **12.110 triple**, **726 individu**, dengan **54/54**
penyakit berdeskripsi, **51/54** berpatogen, **54/54** bergejala, **54/54**
berpengendalian, dan **25/54** memiliki faktor lingkungan. Test: **48 lulus**
(sekitar 7 detik), termasuk reasoning **Pellet** lewat owlready2 dan uji aturan
SWRL. Bila Java tidak tersedia, test reasoning dilewati (`skip`).

Artefak:

- `ontology.ttl` — Turtle, sumber utama di repo.
- `ontology.owl` — RDF/XML, untuk dibuka di Protégé dan untuk test owlready2.
- `extraction_report.json` — laporan cakupan, provenance, varietas, fase,
  faktor lingkungan, dan kategori pengendalian.

Catatan: `rdflib` 7.6.0 pada lingkungan ini gagal mem-parse RDF/XML
(`PluginException: No plugin registered for (rdfxml, ...)`). Test memakai
`ontology.ttl`; validasi `.owl` dilakukan lewat owlready2/Pellet.

## Namespace dan kebijakan IRI

| Namespace | IRI | Dipakai untuk |
|---|---|---|
| `ptp:` | `http://kbr.kelompok5.org/penyakit-tanaman-pangan#` | kelas, properti, individu |
| ontologi | `http://kbr.kelompok5.org/penyakit-tanaman-pangan` | header `owl:Ontology` |

Local name individu memakai **PascalCase deskriptif**; tidak ada hash md5,
tidak ada `DIS####`/`SYM_####`, dan tidak ada tahun di awal nama. Kode sumber
tetap disimpan di `dcterms:identifier`. Tabrakan local name tidak lagi
diselesaikan dengan suffix `Var2`/`Var3`; generator memilih nama alternatif yang
semantik atau gagal secara eksplisit.

- **Tanaman**: `Padi`, `Kedelai`, `Jagung`, `UbiJalar`, `UbiKayu`,
  `KacangTanah`, `KacangHijau` (PLANT_002≡PLANT_018, PLANT_003≡PLANT_019).
- **Penyakit**: `pascal(nama penyakit + nama tanaman)` →
  `KaratKedelai`, `LayuFusariumUbiJalar`, `HawarDaunBakteriPadi`.
  Tiga duplikat digabung: `AntraknosaKedelai`, `BercakDaunKacangTanah`, dan
  `KaratKedelai`; `AntraknosaUbiKayuDaun` dan `AntraknosaUbiKayuBatang` tetap
  terpisah karena bagian tanaman berbeda.
- **Patogen**: `pascal(nama ilmiah)` → `FusariumOxysporum`,
  `CercosporaKikuchii`.
- **Varietas**: `Varietas` + pascal(nama hasil ekstraksi) → `VarietasTukadUnda`.
- **Fase**: `FaseAnakan`, `FaseMatangSusu`, `FaseVegetatif`.
- **Faktor lingkungan**: nama terstruktur dari kondisi dan nilai, memakai
  `Desimal` untuk pecahan dan tanpa unit di local name →
  `SuhuHangat20Sampai24`, `KelembapanUdaraTercatat80Sampai88`,
  `KelembapanTanahTercatat60Sampai80`,
  `DerajatKeasamanTanahRendah3Desimal6`, `CurahHujanTinggi`.
- **Gejala/Pengendalian**: prefix deskriptif + kata kunci/slug; teks identik
  memakai IRI yang sama.
- **Referensi**: `BukuPenyakitTanamanDanPengendaliannya` dan
  `BukuPenyakitUtamaPadaTanamanKedelaiKacangTanahDanKacangHijau`.

Literal teks memakai tag bahasa `@id`. Literal terstruktur memakai tipe:
`tahunTerbit`/`halamanSumber` = `xsd:integer`; `nilaiMin`/`nilaiMaks`/
`nilaiTunggal` = `xsd:decimal`. `dcterms:identifier`, `dcterms:source`,
`idBlokSumber`, dan `prov:wasDerivedFrom` berupa literal biasa. Literal tidak
pernah kosong — bila data tidak ada di sumber, properti tidak ditulis.

## Tabel master

### Kelas utama dan subclass

| Kelas utama | Subclass | Individu |
|---|---|---|
| TanamanPangan | Serealia (Padi, Jagung), Legum (Kedelai, KacangTanah, KacangHijau), UmbiUmbian (UbiJalar, UbiKayu) | 7 |
| Penyakit | PenyakitJamur, PenyakitBakteri, PenyakitVirus, PenyakitNematoda, PenyakitOomycete, PenyakitFitoplasma, PenyakitLainnya | 54 |
| PenyakitRisiko | PenyakitRisikoSuhuTinggi, PenyakitRisikoKelembapanTinggi, PenyakitRisikoMusimHujan | 0 asserted; 16 inferred |
| Gejala | GejalaDaun, GejalaBatang, GejalaAkar, GejalaUmbi, GejalaBuah, GejalaBiji, GejalaBunga, GejalaMalai, GejalaPelepah, GejalaPolong, GejalaPucuk, GejalaTongkol, GejalaLeherMalai | 238 |
| Patogen | Jamur, Bakteri, Virus, OrganismeLain (Nematoda, Oomycete, Fitoplasma) | 59 (29/5/8/1/1/0) |
| BagianTanaman | — (Daun, Batang, Akar, Umbi, Buah, Biji, Bunga, Malai, Pelepah, Polong, Pucuk, Tongkol, LeherMalai) | 13 |
| Pengendalian | KulturTeknis, Mekanis, Biologis, Kimiawi, Fisik, Terpadu | 261 (82/5/59/67/9/2) |
| FaktorRisiko | FaktorLingkungan (Suhu, KelembapanUdara, KelembapanTanah, CurahHujan, MusimHujan, MusimKemarau, Cahaya, Angin, DerajatKeasamanTanah), FaktorBudidaya, FaktorLahan | 55 |
| Referensi | Buku, JurnalIlmiah, ArtikelIlmiah, PublikasiInstansi | 2 (Buku DOC002 2021, DOC005 2020) |
| Varietas | VarietasUnggul, VarietasLokal | 34 (2 unggul eksplisit) |
| FasePertumbuhan | — | 3 |

Jumlah individu subclass Penyakit* = inferensi reasoner (tidak pernah di-assert
eksplisit, divalidasi test). Subclass Pengendalian* di-assert eksplisit
multi-label dari klasifikasi keyword/`control_category` (subclass tersebut
**tidak** di-disjoint agar multi-label aman). Kelas `PenyakitRisiko*` juga
hanya diisi lewat SWRL/Pellet dan divalidasi agar tidak pernah di-assert.

### Object property (20)

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
| tahanTerhadap | Varietas | Penyakit | — (disjoint dengan rentan) |
| rentanTerhadap | Varietas | Penyakit | — |
| menyerangFase | Penyakit | FasePertumbuhan | — |

### Data property (23)

| Properti | Domain | Nilai terisi |
|---|---|---|
| namaIlmiah | TanamanPangan | 7 |
| deskripsiTanaman | TanamanPangan | 7 |
| namaIlmiahPatogen | Patogen | 59 |
| catatanTakson | Patogen | 20 |
| deskripsiPenyakit | Penyakit | 54 |
| namaInggrisPenyakit | Penyakit | 9 |
| tingkatKeparahan | Penyakit | 0 |
| deskripsiGejala | Gejala | 238 |
| judulReferensi | Referensi | 2 |
| tahunTerbit | Referensi | 2 (`2020`, `2021` ^^xsd:integer) |
| namaPenulis | Referensi | 2 |
| urlReferensi | Referensi | 0 |
| namaPengendalian | Pengendalian | 129 |
| deskripsiPengendalian | Pengendalian | 261 |
| nilaiMin / nilaiMaks | FaktorLingkungan | 22 / 22 (^^xsd:decimal) |
| nilaiTunggal | FaktorLingkungan | 25 (^^xsd:decimal) |
| satuan / tingkat / kondisi | FaktorLingkungan | 47 / 50 / 55 |
| kutipanSumber | *(tanpa domain)* | 713 |
| halamanSumber | *(tanpa domain)* | 708 (^^xsd:integer) |
| idBlokSumber | *(tanpa domain)* | 670 |

`rdfs:range` sengaja tidak ditulis untuk data property teks: nilai memakai tag
bahasa `@id` (rdf:langString) yang pada OWL 2 **disjoint** dengan `xsd:string`.

## Profil SROIQ(D)

| Huruf | Axiom | Implementasi |
|---|---|---|
| **S** | SubClass Of, SubProperty Of | `Penyakit ⊑ …` (4 restriction); `dikendalikanDengan ⊑ berkaitanPengendalian`, `pengendalianUmum ⊑ berkaitanPengendalian` |
| **R** | Property chain | `memilikiGejala ∘ terdapatPada ⊑ menyerangBagian` |
| **O** | Nominal | `Serealia ≡ {Padi, Jagung}`, `Legum ≡ {Kedelai, KacangTanah, KacangHijau}`, `UmbiUmbian ≡ {UbiJalar, UbiKayu}` (owl:oneOf) |
| **I** | Inverse | 6 pasang = **12** triple `owl:inverseOf` |
| **Q** | Qualified cardinality | `Penyakit ⊑ (memilikiReferensi min 1 Referensi)`; `Buku ⊑ (tahunTerbit exactly 1 xsd:integer)` |
| **D** | Data range | `tahunTerbit`/`halamanSumber` xsd:integer; `nilaiMin/Maks/Tunggal` xsd:decimal; literal teks @id tanpa range xsd:string |

Role pada property chain tidak dikenai number restriction (simple role). Data
property yang bernilai tunggal (mis. `deskripsiPenyakit`, `nilaiMin`) ditandai
`owl:FunctionalProperty`.

### Disjoint, equivalent, dan restriksi

| Axiom | Jumlah | Isi |
|---|---|---|
| Disjoint Classes | **88** pasang | 45 antarkelas utama; 21 antarkelas Penyakit*; 9 Patogen (6 antarkelas Jamur/Bakteri/Virus/OrganismeLain + 3 antarkelas Nematoda/Oomycete/Fitoplasma); 3 tanaman; 3 Faktor*; 6 Referensi*; 1 Varietas*. Gejala* dan Pengendalian* **tidak** di-disjoint. |
| Equivalent Classes | 10 | 6 penalaran penyakit (Jamur/Bakteri/Virus/Nematoda/Oomycete/Fitoplasma) + 3 nominal tanaman + 1 disjoint union `OrganismeLain` |
| Disjoint Union | 1 | `OrganismeLain ≡ Nematoda ⊔ Oomycete ⊔ Fitoplasma` |
| Sub Class Of + restriction | 4 | some menyerangTanaman, some memilikiGejala, only disebabkanOleh, **min 1** memilikiReferensi |
| Inverse Of | 12 | 6 pasang |
| SubProperty Of | 2 | menuju `berkaitanPengendalian` |
| Property chain | 1 | `memilikiGejala ∘ terdapatPada ⊑ menyerangBagian` |
| Property disjoint | 1 | `tahanTerhadap` disjoint `rentanTerhadap` |
| Data property disjoint | 2 | `nilaiTunggal` disjoint `nilaiMin` dan `nilaiMaks` |
| Datatype restriction | 1 | `Buku ⊑ tahunTerbit exactly 1 xsd:integer` |

Hasil reasoning **Pellet** (konsisten, tanpa `owl:Nothing`):

- **PenyakitJamur: 26**, **PenyakitBakteri: 5**, **PenyakitVirus: 5**,
  **PenyakitOomycete: 2**, **PenyakitFitoplasma: 1**, **PenyakitNematoda: 0**,
  **PenyakitLainnya: 0** — murni inferensi, tidak pernah di-assert.
- **Serealia: 2** (Padi, Jagung), **Legum: 3** (Kedelai, KacangTanah,
  KacangHijau), **UmbiUmbian: 2** (UbiJalar, UbiKayu) — inferensi dari
  `owl:oneOf`.
- **PenyakitRisiko: 16**, **PenyakitRisikoSuhuTinggi: 3**,
  **PenyakitRisikoKelembapanTinggi: 10**, **PenyakitRisikoMusimHujan: 6** —
  inferensi dari 3 aturan SWRL.

## Aturan SWRL

Tiga aturan di `tbox.py` memakai variabel `?p` (penyakit) dan `?f` (faktor):

```
Penyakit(?p) ^ dipengaruhiOleh(?p, ?f) ^ Suhu(?f) ^ tingkat(?f, "tinggi"@id)
  -> PenyakitRisikoSuhuTinggi(?p)

Penyakit(?p) ^ dipengaruhiOleh(?p, ?f) ^ KelembapanUdara(?f) ^ tingkat(?f, "tinggi"@id)
  -> PenyakitRisikoKelembapanTinggi(?p)

Penyakit(?p) ^ dipengaruhiOleh(?p, ?f) ^ MusimHujan(?f)
  -> PenyakitRisikoMusimHujan(?p)
```

Literal pada `tingkat` wajib memakai `lang="id"` agar cocok dengan ABox.
Property chain TBox sudah menurunkan `menyerangBagian` dari
`memilikiGejala ∘ terdapatPada`; aturan SWRL melengkapi, bukan menggantikan.

## Cakupan ABox

| Aspek | Terisi | Persen |
|---|---|---|
| Deskripsi penyakit (verbatim) | 54 / 54 | 100 % |
| Patogen penyebab | 51 / 54 | 94,4 % |
| Gejala | 54 / 54 | 100 % |
| Pengendalian (per penyakit atau umum per tanaman) | 54 / 54 | 100 % |
| Faktor lingkungan | 25 / 54 | 46,3 % |

Rincian kekurangan dicatat di `extraction_report.json` pada kunci
`coverage.tanpaDeskripsi`, `tanpaPatogen`, `tanpaPengendalian`, dan
`tanpaFaktorLingkungan`.

## Ekstraksi deterministik (ABox tambahan)

Semua hasil tercatat di `extraction_report.json`:

- **Deskripsi penyakit** — DOC002 dari blok paragraf pada rentang halaman
  penyakit (prioritas subbagian "Penyebab"); DOC005 dari bagian markdown
  "Penyebab Penyakit". Kutipan 1–2 kalimat verbatim + halaman/id blok.
  Teks tabel Ubi Kayu memakai fallback `symptom_text` minimal 20 karakter.
- **Varietas** — pola `varietas <NamaProper>` (+ fallback `adalah`); daftar
  "A, B, dan C"; stopword/filler dibuang; akronim patogen dan huruf tunggal
  ditolak; prefix nama tanaman dipangkas. `tahanTerhadap` hanya bila teks
  punya penanda resistensi (tahan/resistan/toleran) **tanpa** penanda
  rentan/peka.
- **Fase pertumbuhan** — whitelist `fase (matang susu|vegetatif|generatif|
  pembibitan|anakan|matang|pembungaan|pengisian polong|panen)`.
- **Faktor lingkungan** — suhu, kelembapan udara/tanah, pH, curah hujan,
  musim, cahaya, dan angin diekstrak dari teks "Faktor Lingkungan"/"Penyebab"/
  "Siklus". Nilai numerik disimpan sebagai `nilaiMin`/`nilaiMaks`/
  `nilaiTunggal` + `satuan` + `tingkat` + `kondisi`; OCR `260C`/`27,50C`
  dinormalisasi menjadi 26/27,5 °C. Baris tabel dan teks pengendalian
  dikecualikan dari ekstraksi faktor agar tidak menangkap suhu perlakuan.
  `KelembapanRelatif` dipetakan ke `KelembapanUdara`; pH tanah dipetakan ke
  `DerajatKeasamanTanah`; humidity yang menyebut "tanah" dipetakan ke
  `KelembapanTanah`.
- **Pengendalian** — DOC005 dari `control_category`; DOC002 multi-label
  keyword → KulturTeknis/Kimiawi/Biologis/Mekanis/Fisik/Terpadu. 37 penyakit
  memiliki kontrol per-penyakit (`dikendalikanDengan`, 257 tautan); 17
  penyakit UbiKayu tanpa kontrol per-penyakit memakai kontrol umum tanaman.
  45 baris `scope=chapter` dalam cakupan → `pengendalianUmum`.
  Superproperty `berkaitanPengendalian` dimaterialisasi di ABox.
- **Provenance** — setiap penyakit, gejala, pengendalian, varietas, faktor
  lingkungan, dan referensi menyimpan `kutipanSumber`; halaman dan id blok
  disimpan bila tersedia. `BagianTanaman` adalah kosakata struktural 13 istilah
  dan sengaja tidak diberi kutipan palsu.

## Membuka dan mendemokan di Protégé

1. Buka Protégé 5.6+, **File → Open…**, pilih `ontology.owl` (RDF/XML).
2. Tab **Entities** menampilkan 10 kelas utama berbahasa Indonesia.
3. Tab **Object Properties** — 20 properti + invers (ikon "owl:O").
4. Tab **Data Properties** — 23 properti; `tahunTerbit`/`halamanSumber`
   ber-range `xsd:integer`, nilai lingkungan `xsd:decimal`.
5. Pasang plugin **Pellet** bila belum tersedia, lalu **Reasoner → Pellet →
   Synchronize Reasoner**.
6. Classes: `Penyakit Jamur` inferred 26 anggota, `Penyakit Bakteri` 5,
   `Penyakit Virus` 5, `Serealia` 2, `Legum` 3, `UmbiUmbian` 2.
7. DL Query contoh: `Penyakit and (disebabkanOleh some Jamur)` → 26 hasil;
   `Varietas and (tahanTerhadap some Penyakit)` → 32 tautan.
8. Klik kanan `Serealia` → Equivalent Classes menampilkan
   `owl:oneOf (Padi Jagung)`.
9. Tutup tanpa menyimpan bila hanya meninjau; file sumber tetap
   `ontology.owl`/`ontology.ttl`.

## Catatan Pellet di lingkungan ini

`owlready2.sync_reasoner_pellet()` memakai loader **Jena** bawaan. Pada
lingkungan ini Pellet/Jena gagal dengan `UnsupportedClassVersionError`
(class file 69/Java 25, sedangkan runtime Java 21). Test memakai workaround yang
sama dengan CLI: ganti loader `Jena` menjadi `OWLAPI`.

```powershell
$cp = (Get-ChildItem "$env:APPDATA\Python\Python*\site-packages\owlready2\pellet\*.jar" |
       ForEach-Object { $_.FullName }) -join ';'
java -Xmx2000M -cp $cp pellet.Pellet realize `
  --loader OWLAPI --input-format N-Triples --ignore-imports ontology.nt
```

Workaround ini sudah diverifikasi: Pellet konsisten dan menginfer kelas
kategori penyakit, kelas nominal, serta ketiga kelas risiko SWRL.

## Data yang sengaja kosong (tanpa mengarang)

| Properti/individu | Alasan |
|---|---|
| tingkatKeparahan | tidak ada kolom keparahan di sumber |
| urlReferensi | `manual_metadata.json` tidak punya field URL |
| FaktorBudidaya / FaktorLahan individu | tidak ada pasangan eksplisit yang dapat dikutip di in-scope |
| JurnalIlmiah/ArtikelIlmiah/PublikasiInstansi | hanya DOC002+DOC005 (buku) dalam cakupan |
| VarietasLokal | teks sumber tidak menyebut varietas sebagai "lokal" secara eksplisit |
| rentanTerhadap | tidak ada pernyataan varietas rentan/peka yang berdiri sendiri |
| PenyakitLainnya | patogen bertakson `unknown` tetap diketik `Patogen`; OWA mencegah klasifikasi negatif otomatis |
| Nematoda (penyakit) | tidak ada penyakit bertakson Nematoda pada sumber in-scope |

Penyakit tanpa patogen (3): `BelangMottleKacangTanah`,
`KerdilRumputDanKerdilHampaPadi`,
`NekrosisPadaTitikTunasCassavaBudNecrosisUbiKayu` — restriksi
`disebabkanOleh only Patogen` tetap terpenuhi secara kosong.

## Struktur generator

- `tbox.py` — semua kelas/properti/axioms SROIQ(D), 3 aturan SWRL, dan kelas
  risiko (sumber kebenaran TBox).
- `build_ontology.py` — baca CSV DOC002+DOC005 dan
  `curated/plant_descriptions.csv` → ekstraksi → merge penyakit → `Builder`
  ABox → `counts()` → `validate()` → tulis `ontology.ttl` + `ontology.owl` +
  `extraction_report.json`.
- `tests/test_ontology.py` — snapshot jumlah, axioms SROIQ(D), guardrail
  penamaan/annotasi/provenance/cakupan, build gate, dan test reasoning Pellet
  beserta aturan SWRL.
