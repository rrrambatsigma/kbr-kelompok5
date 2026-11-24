# Audit Knowledge Base — Ontologi Penyakit Tanaman Pangan

Dokumen ini adalah hasil audit langsung terhadap artefak ontologi enrichment,
bukan salinan ringkasan README. Seluruh angka dihitung ulang dari graph dengan
`rdflib` (baca-saja, tanpa menjalankan reasoner).

> **Arsip (snapshot audit 21 November 2026).** Angka di dokumen ini adalah
> kondisi artefak **saat audit**, bukan artefak final. Ontology final
> (24 November 2026) berisi **30.280 triple** di `ontology_md.ttl`,
> **32.506 triple** di `ontology_md_inferred.ttl`, **1.508 individu**,
> **71 kelas TBox PTP**, dan **7 aturan SWRL**. Untuk angka terkini lihat
> `../README.md`; rincian per kelas/per properti di badan dokumen ini belum
> dihitung ulang.

| Item | Nilai (saat audit) |
|---|---|
| Berkas audit | `04_ontology/ontology_md.ttl` |
| Format | Turtle, namespace `ptp:` |
| Triple | 19.021 |
| Individu `owl:NamedIndividual` | 1.366 |
| Kelas TBox PTP | 87 |
| Kelas OWL di graph (termasuk kelas bantu SWRL) | 96 |
| Object property | 31 |
| Data property | 33 |
| Tanggal audit | 21 November 2026 |

Graf `ontology_md.ttl` bersifat berdiri sendiri: seluruh isi `ontology.ttl`
ditambah TBox/ABox enrichment dan 4 aturan SWRL. Artefak kanonik tidak ditulis
ulang oleh build enrichment.

---

## 1. Ringkasan eksekutif

Knowledge Base (KB) mencakup **7 tanaman pangan**, **53 penyakit**, **64 patogen unik**, **25 konsep gejala kanonik**, **71 observasi lingkungan**, dan **48 aksi pengendalian**.

| Dimensi | Cakupan | Status |
|---|---:|---|
| Tanaman | 7 | Lengkap sesuai ruang lingkup |
| Penyakit | 53 | Lengkap, tersebar di 7 tanaman |
| Patogen | 64 unik / 76 tautan | 0 penyakit tanpa patogen |
| Gejala kanonik | 25 konsep | 167 dari 231 pengamatan terpetakan |
| Faktor lingkungan | 71 observasi + 30 kondisi kualitatif | 24 observasi bernilai numerik |
| Pengendalian | 48 aksi kanonik | 38 aksi terpakai, 226 tautan penyakit |
| Varietas | 35 individu | 0 varietas untuk ubi kayu |
| Bukti sumber | 783 node | 2 buku, tanpa URL |

Tiga kesimpulan utama:

1. **Struktur KB siap untuk penalaran.** Semua penyakit punya patogen, gejala, lingkungan, pengendalian, bagian tanaman, dan referensi — syarat restriksi TBox terpenuhi.
2. **Kedalaman data tidak merata.** Pengendalian dan gejala padat (terutama kedelai), sedangkan severity, fase serangan, nama Inggris, dan varietas tahan masih minoritas.
3. **Kualitas data perlu dibersihkan sebelum dipakai sebagai basis evaluasi.** Ditemukan salah eja nama ilmiah, takson placeholder, ambang numerik yang hilang, dan label hasil ekstraksi yang belum dinormalisasi (rincian di §10).

---

## 2. Ruang lingkup dan struktur KB

### Domain utama

KB memakai satu namespace (`ptp:`) dengan 15 domain yang saling disjoint:
`TanamanPangan`, `Penyakit`, `Gejala`, `GejalaKanonik`, `Patogen`, `BagianTanaman`,
`Pengendalian`, `FaktorRisiko`, `Referensi`, `Varietas`, `FasePertumbuhan`,
`Observasi`, `Diagnosis`, `RekomendasiPengendalian`, dan `BuktiSumber`.

### Kelompok tanaman

| Kelompok | Anggota |
|---|---|
| Serealia | Padi, Jagung |
| Legum | Kedelai, Kacang Tanah, Kacang Hijau |
| Umbi-umbian | Ubi Kayu, Ubi Jalar |

### Kategori penyakit (hasil inferensi)

Kelas kategori tidak pernah di-assert eksplisit; semuanya muncul dari
`owl:equivalentClass` terhadap restriksi `disebabkanOleh some <Patogen>`.

| Kelas | Takson patogen | Penyakit (Pellet) |
|---|---|---:|
| `PenyakitJamur` | Jamur | 34 |
| `PenyakitVirus` | Virus | 10 |
| `PenyakitBakteri` | Bakteri | 7 |
| `PenyakitOomycete` | Oomycete | 3 |
| `PenyakitFitoplasma` | Fitoplasma | 1 |
| `PenyakitNematoda` | Nematoda | 0 |

Jumlah per kelas dapat melebihi 53 karena dua penyakit ubi kayu
(`Busuk akar dan umbi`, `Busuk pangkal batang`) disebabkan jamur sekaligus oomycete.
Backend memilih satu kategori per penyakit dengan prioritas
Jamur → Bakteri → Virus → Oomycete → Fitoplasma → Nematoda, sehingga angka
backend menjadi 34/7/10/1/1 dengan 0 penyakit tanpa kategori.

---

## 3. Inventaris tanaman

| Tanaman | Kelompok | Nama ilmiah | Penyakit | Varietas | Kondisi tumbuh | Pengendalian umum |
|---|---|---|---:|---:|---|---:|
| Padi | Serealia | tidak tercatat | 5 | 4 | Curah hujan tinggi | 0 |
| Kedelai | Legum | Glycine max L. Merril | 15 | 12 | Cahaya sedang, Suhu dingin, Suhu sedang | 0 |
| Jagung | Serealia | tidak tercatat | 5 | 3 | Suhu sedang | 0 |
| Ubi jalar | Umbi-umbian | Ipomoea batatas L. (Lam) | 4 | 6 | Tanah gembur | 0 |
| Ubi kayu | Umbi-umbian | Manihot esculenta Crantz | 17 | 0 | Tanah subur | 10 |
| Kacang tanah | Legum | tidak tercatat | 4 | 8 | Suhu hangat | 12 |
| Kacang hijau | Legum | tidak tercatat | 3 | 2 | Suhu hangat | 0 |

Catatan: nama ilmiah hanya terisi untuk Kedelai (`Glycine max L. Merril`),
Ubi Jalar (`Ipomoea batatas L. (Lam)`), dan Ubi Kayu (`Manihot esculenta Crantz`).
Padi, Jagung, Kacang Tanah, dan Kacang Hijau dibiarkan kosong karena sumber tidak
menyebutkannya — bukan karena terlewat.

---

## 4. Matriks penyakit per tanaman

Kolom **Obs** adalah jumlah pengamatan gejala; **Kanonik** adalah konsep gejala
hasil normalisasi. Pengendalian bertanda *fallback* berarti penyakit memakai
`pengendalianUmum` tingkat tanaman, bukan tautan penyakit-spesifik.

### Padi — 5 penyakit

| Penyakit | Obs | Patogen (takson) | Gejala kanonik | Bagian · Fase | Lingkungan | Pengendalian spesifik | Varietas tahan |
|---|---:|---|---|---|---|---|---|
| **Penyakit Blas** | 4 | Magnaporthe grisea (Jamur); Pyricularia grisea (Jamur); Pyricularia oryzae (Jamur) | Bercak daun, Bercak pada tanaman, Malai patah | Daun, Malai · — | Musim hujan | Pemupukan berimbang, Pengairan dan drainase, Pengaturan waktu tanam, Penggunaan Bacillus, Penggunaan Pseudomonas, Penggunaan Trichoderma, Penggunaan agens hayati, Penggunaan bakterisida, Penggunaan benih sehat, Penggunaan fungisida, Pengumpulan dan pemusnahan, Perlakuan benih, Sanitasi lahan | — |
| **Penyakit Hawar Daun Bakteri** | 9 | Xanthomonas oryzae (Bakteri) | Bercak daun, Hawar daun, Klorosis daun, Klorosis pada tanaman, Layu daun, Nekrosis pada tanaman | Daun · — | Suhu 25–34 °C; Kelembapan relatif >70%; Hujan lebat dan angin kencang | Pemupukan berimbang, Pencabutan tanaman, Penerapan pengendalian fisik, Pengairan dan drainase, Pengelolaan gulma, Penggunaan Bacillus, Penggunaan Pseudomonas, Penggunaan agens hayati, Penggunaan bakterisida, Penggunaan benih sehat, Penggunaan varietas tahan, Perlakuan air panas, Perlakuan benih | — |
| **Penyakit Hawar Pelepah Daun** | 5 | Rhizoctonia solani (Jamur) | Bercak daun, Bercak pada tanaman, Busuk batang | Daun · anakan, matang susu | Kelembapan relatif; Suhu | Pengaturan jarak tanam, Penggunaan Pseudomonas, Penggunaan Trichoderma, Penggunaan agens hayati, Penggunaan fungisida, Pengumpulan dan pemusnahan, Sanitasi lahan | — |
| **Penyakit Kerdil Rumput dan Kerdil Hampa** | 4 | Rice grassy stunt virus (Virus); Rice ragged stunt virus (Virus) | Bercak daun, Kerdil tanaman, Klorosis daun | Batang, Daun · — | Kondisi tropis dengan padi sepanjang tahun | Pengelolaan gulma, Pengendalian vektor, Penggunaan Beauveria, Penggunaan Metarhizium, Sanitasi lahan | — |
| **Penyakit Tungro** | 4 | Rice tungro bacillifor virus (Virus); Rice tungro spherical virus (Virus) | Bercak pada tanaman, Kerdil tanaman, Klorosis daun, Pertumbuhan terhambat | Daun, Malai · — | Musim hujan | Pengaturan waktu tanam, Pengelolaan gulma, Pengendalian vektor, Penggunaan Metarhizium, Penggunaan varietas tahan, Pengumpulan dan pemusnahan, Sanitasi lahan | Bondoyudo, Kalimas, Tukad Balian, Tukad Unda |

### Kedelai — 15 penyakit

| Penyakit | Obs | Patogen (takson) | Gejala kanonik | Bagian · Fase | Lingkungan | Pengendalian spesifik | Varietas tahan |
|---|---:|---|---|---|---|---|---|
| **Penyakit Antraknosa** | 7 | Colletotrichum (Jamur); Colletotrichum truncatum (Jamur) | Bercak daun, Bercak pada tanaman, Daun rontok, Kematian tanaman, Nekrosis daun, Nekrosis pada tanaman | Batang, Daun, Polong · vegetatif | Cuaca hangat dan lembap | Penggunaan Pseudomonas, Penggunaan Trichoderma, Penggunaan agens hayati, Penggunaan benih sehat, Penggunaan fungisida, Perlakuan benih, Rotasi tanaman, Sanitasi lahan | — |
| **Penyakit Bakteri Pustul** | 5 | Xanthomonas axonopodis (Bakteri) | Bercak daun, Bercak pada tanaman, Daun rontok, Klorosis pada tanaman | Daun, Polong · — | Suhu 26–30 °C; Kelembapan tinggi dan daun basah | Penggunaan Bacillus, Penggunaan agens hayati, Penggunaan benih sehat, Penggunaan ekstrak tanaman, Sanitasi lahan | — |
| **Penyakit Bercak Biji Ungu** | 8 | Cercospora kikuchii (Jamur) | Bercak daun, Bercak pada tanaman, Hawar daun, Nekrosis daun | Biji · — | Kelembapan tinggi dan suhu hangat | Penggunaan fungisida, Perlakuan benih | — |
| **Penyakit Bercak Daun Mata Katak (Frogeye Leaf Spot)** | 3 | Cercospora sojina (Jamur) | Bercak daun, Bercak pada tanaman | Daun · — | Suhu optimal 25–30 °C; Kelembapan relatif >90% | Penggunaan fungisida, Penggunaan varietas tahan, Perlakuan benih | — |
| **Penyakit Bercak Target** | 4 | Corynespora cassiicola (Jamur) | Bercak daun, Bercak pada tanaman, Klorosis pada tanaman | Batang, Daun, Polong · — | Kelembapan tinggi dan daun basah | Penggunaan benih sehat, Penggunaan fungisida, Penggunaan tanaman bukan inang, Rotasi tanaman, Sanitasi lahan | — |
| **Penyakit Embun Palsu (Downy mildew)** | 9 | Peronospora manshurica (Oomycete) | Bercak daun, Bercak pada tanaman, Klorosis daun, Klorosis pada tanaman, Nekrosis daun, Pertumbuhan abnormal | Daun · — | Kelembapan tinggi; Suhu rendah | Penggunaan benih sehat, Penggunaan fungisida, Penggunaan tanaman bukan inang, Perlakuan benih, Sanitasi lahan | — |
| **Penyakit Embun Tepung (Powdery Mildew)** | 2 | Erysiphae diffusa (Jamur) | Bercak daun, Tepung pada daun | Daun · — | Suhu 18–24 °C; Kelembapan rendah dengan daun basah terbatas | Pemupukan berimbang, Penggunaan agens hayati, Penggunaan tanaman bukan inang, Rotasi tanaman, Sanitasi lahan | — |
| **Penyakit Hawar Bakteri (Bacterial Blight)** | 7 | Pseudomonas syringae (Bakteri) | Bercak daun, Bercak pada tanaman, Daun berlubang, Daun rontok, Klorosis pada tanaman | Daun, Polong · pembibitan | Suhu sejuk dan hujan sering | Penggunaan Bacillus, Penggunaan Pseudomonas, Penggunaan agens hayati, Penggunaan bakterisida, Perlakuan benih, Rotasi tanaman | — |
| **Penyakit Karat Daun** | 8 | Phakopsora meibomiae (Jamur); Phakopsora pachyrhizi (Jamur); Phakopspora pachyrhizi (Jamur) | Bercak daun, Bercak pada tanaman, Daun kering, Daun rontok, Klorosis daun, Klorosis pada tanaman | Daun · — | Curah hujan tinggi; Musim kemarau | Penggunaan Bacillus, Penggunaan agens hayati, Penggunaan fungisida, Penggunaan pestisida nabati, Penggunaan tanaman bukan inang, Penggunaan varietas tahan | Anjasmoro, Dena, Kaba, Sinabung, Tanggamus, Wilis |
| **Penyakit Kerdil Kedelai (Soybean Stunt Virus)** | 4 | Soybean Stunt Virus (Virus) | Kerdil tanaman, Mosaik daun, Pertumbuhan terhambat | Daun · — | Lahan tegalan di bawah tegakan pohon jati | Pengendalian vektor, Penggunaan benih sehat, Penggunaan insektisida, Perlakuan benih, Rotasi tanaman | — |
| **Penyakit Layu Fusarium** | 5 | Fusarium spp (Jamur) | Busuk akar, Kematian tanaman, Layu daun, Nekrosis pada tanaman | Akar · — | Cuaca sejuk dan basah | Pemupukan berimbang, Penggunaan Trichoderma, Penggunaan agens hayati, Penggunaan fungisida, Penggunaan mulsa, Perlakuan benih, Solarisasi tanah | — |
| **Penyakit Mosaik Kedelai (Soybean Mosaic Virus)** | 7 | Soybean Mosaic Virus (Virus) | Belang pada tanaman, Kerdil tanaman, Klorosis daun, Mosaik daun, Pertumbuhan terhambat | Daun · — | Lahan tegalan di bawah tegakan pohon jati | Penggunaan insektisida, Sanitasi lahan | — |
| **Penyakit Rebah Kecambah** | 8 | Rhizoctonia solani (Jamur) | Bercak pada tanaman, Busuk akar, Busuk batang, Busuk pada tanaman, Kematian tanaman, Layu daun | Akar, Batang · — | Musim hujan | Pengairan dan drainase, Penggunaan Bacillus, Penggunaan Trichoderma, Penggunaan agens hayati, Penggunaan fungisida, Perlakuan benih, Rotasi tanaman, Sanitasi lahan | — |
| **Penyakit Rebah Semai** | 5 | Sclerotium rolfsii (Jamur) | Bercak pada tanaman, Busuk batang, Klorosis daun, Layu daun | Akar, Batang, Daun · pembibitan | Tanah jenuh air dan kelembapan tinggi | Penggunaan Bacillus, Penggunaan Beauveria, Penggunaan Trichoderma, Penggunaan agens hayati, Penggunaan varietas tahan, Rotasi tanaman, Solarisasi tanah | Anjasmoro, Dega 1, Dena 1, Dering 1, Devon 1, Grobogan |
| **Penyakit Samar Kacang Tunggak (Cowpea Mild Mottle Virus)** | 6 | Cowpea Mild Mottle Virus (Virus) | Kerdil tanaman, Klorosis daun, Mosaik daun, Pertumbuhan abnormal | Daun · — | Cuaca memengaruhi populasi Bemisia tabaci | Pengaturan jarak tanam, Pengaturan waktu tanam, Penggunaan insektisida, Penggunaan mulsa, Penggunaan tanaman bukan inang, Penggunaan varietas tahan, Rotasi tanaman, Sanitasi lahan | — |

### Jagung — 5 penyakit

| Penyakit | Obs | Patogen (takson) | Gejala kanonik | Bagian · Fase | Lingkungan | Pengendalian spesifik | Varietas tahan |
|---|---:|---|---|---|---|---|---|
| **Penyakit Bulai** | 8 | Peronosclerospora maydis (Jamur); Peronosclerospora sp (Jamur) | Kerdil tanaman, Klorosis daun, Pertumbuhan terhambat, Tepung pada daun | Daun · vegetatif | Kelembapan 90%; Suhu 24 °C | Pemupukan berimbang, Penggunaan Pseudomonas, Penggunaan agens hayati, Penggunaan fungisida, Penggunaan varietas tahan | Asian Honey, Pioneer 21 |
| **Penyakit Busuk Pelepah** | 2 | Rhizoctonia solani (Jamur) | Bercak pada tanaman, Busuk batang | Batang, Buah, Daun · — | Suhu ≥30 °C; Kelembapan tinggi | Penggunaan Bacillus | — |
| **Penyakit Hawar Daun** | 4 | Helminthosporium maydis (Jamur) | Bercak daun, Bercak pada tanaman, Hawar daun, Nekrosis daun | Daun · generatif | Suhu 18–27 °C; Daun basah 6 jam | Pengelolaan gulma, Penggunaan Trichoderma, Penggunaan agens hayati, Penggunaan varietas tahan, Sanitasi lahan | — |
| **Penyakit Karat Daun** | 11 | Puccinia polysora (Jamur) | Klorosis daun | Daun · generatif | Suhu rendah; Suhu 25,2–28,8 °C | Pengaturan jarak tanam, Pengaturan kelembapan, Pengelolaan gulma, Penggunaan varietas tahan, Sanitasi lahan | — |
| **Penyakit Layu Stewart** | 3 | Pantoea stewartii (Bakteri) | Kerdil tanaman, Klorosis daun, Layu daun | Daun · generatif | Musim dingin ringan | Pengelolaan gulma, Penggunaan Bacillus, Penggunaan Pseudomonas, Penggunaan agens hayati, Penggunaan benih sehat, Penggunaan insektisida, Penggunaan varietas tahan, Perlakuan benih, Sanitasi lahan | — |

### Ubi jalar — 4 penyakit

| Penyakit | Obs | Patogen (takson) | Gejala kanonik | Bagian · Fase | Lingkungan | Pengendalian spesifik | Varietas tahan |
|---|---:|---|---|---|---|---|---|
| **Penyakit bercak kuning** | 9 | Sweet Potato Chlorotic Fleck Virus (Virus); Sweet Potato Feathery Mottle Virus (Virus); Sweet Potato Mild Mottle Virus (Virus) | Belang pada tanaman, Bercak daun, Bercak pada tanaman, Klorosis daun, Klorosis pada tanaman, Nekrosis daun, Pucuk mati | Daun, Pucuk · — | Suhu 20–29 °C | Kultur meristem, Pengendalian vektor, Penggunaan varietas tahan, Rotasi tanaman, Sanitasi lahan, Seleksi bahan tanam | — |
| **Penyakit busuk hitam (black rot)** | 6 | Ceratocystis fimbriata (Jamur) | Bercak pada tanaman, Busuk akar, Busuk pada tanaman | Akar, Umbi · — | Suhu lapang 23–27 °C | Penggunaan varietas tahan, Perlakuan kimia tanah, Rotasi tanaman | — |
| **Penyakit kudis** | 7 | Elsinoe batatas (Jamur); Spaceloma batatas (Jamur) | Bercak daun, Bercak pada tanaman, Klorosis pada tanaman | Batang, Daun, Pucuk · — | Musim hujan; Suhu rendah | Pengelolaan terpadu, Penggunaan bakterisida, Penggunaan ekstrak tanaman, Penggunaan fungisida, Penggunaan pestisida nabati, Penggunaan tanaman bukan inang, Penggunaan varietas tahan, Rotasi tanaman, Sanitasi lahan | Abomourow, Bonsasarai, Inanwatan-4, Kuyage-2, Mouwebsi, Wonembai |
| **layu fusarium** | 8 | Fusarium oxysporum (Jamur) | Busuk pada tanaman, Kematian tanaman, Kerdil tanaman, Klorosis daun, Layu daun, Nekrosis pada tanaman | Batang, Daun, Umbi · — | Suhu infeksi optimal 30 °C; Kelembapan tanah 28–75% | Pengaturan suhu penyimpanan, Penggunaan fungisida, Penggunaan varietas tahan, Sanitasi lahan | — |

### Ubi kayu — 17 penyakit

| Penyakit | Obs | Patogen (takson) | Gejala kanonik | Bagian · Fase | Lingkungan | Pengendalian spesifik | Varietas tahan |
|---|---:|---|---|---|---|---|---|
| **Antraknosa** | 1 | Collectothricum gloeosporioides (Jamur) | Pucuk mati | Batang · — | Curah hujan dan kelembapan relatif | *fallback* pengendalian umum | — |
| **Antraknosa** | 1 | Colletotricum spp (Jamur) | Layu daun | Daun · — | Curah hujan dan kelembapan relatif | *fallback* pengendalian umum | — |
| **Bercak daun Coklat** | 1 | Cercospora henningsii (Jamur); Cercosporidium henningsii (Jamur) | Bercak daun | Daun · — | Cuaca hangat dan lembap | *fallback* pengendalian umum | — |
| **Bercak daun baur** | 1 | Cercospora. viscosae (Jamur) | Bercak daun | Daun · — | Iklim lembap dan hangat | *fallback* pengendalian umum | — |
| **Bercak daun putih** | 1 | Phaeoramularia manihotis (Jamur) | Bercak pada tanaman | Daun · — | Iklim lembap dan sejuk; Cuaca sejuk dan hujan | *fallback* pengendalian umum | — |
| **Busuk Umbi** | 2 | Fusarium spp (Jamur) | Busuk pada tanaman, Layu daun | Akar, Umbi · — | Tanah tergenang | *fallback* pengendalian umum | — |
| **Busuk akar** | 4 | Polyporus sulphureus (Jamur) | Busuk akar, Busuk batang, Busuk buah, Klorosis pada tanaman | Akar, Umbi · — | Tanah tergenang | *fallback* pengendalian umum | — |
| **Busuk akar dan umbi** | 2 | Botryodiplodia spp (Jamur); Diplodia spp (Jamur); Phytophthora spp (Oomycete); Sclerotium rolfsii (Jamur) | Busuk akar, Pertumbuhan terhambat | Akar, Umbi · — | Tanah tergenang | *fallback* pengendalian umum | — |
| **Busuk pangkal batang** | 2 | Botryodiplodia spp (Jamur); Diplodia spp (Jamur); Fusarium spp (Jamur); Phytophthora spp (Oomycete); Sclerotium rolfsii (Jamur) | Busuk batang, Layu daun | Batang · — | Kelembapan tinggi; Musim hujan | *fallback* pengendalian umum | — |
| **Cassava Brown Streak Disease (CBSD)** | 2 | Ipomovirus (Virus) | Bercak daun, Klorosis daun | Daun · — | Curah hujan; Suhu | *fallback* pengendalian umum | — |
| **Cassava Mosaic Begomovirus (CMBs)** | 2 | Begomovirus (Virus) | Klorosis daun, Mosaik daun | Daun · — | Suhu, curah hujan, dan angin | *fallback* pengendalian umum | — |
| **Hawar bakteri** | 2 | Xanthomonas campestris pv. Manihotis (Bakteri) | Klorosis pada tanaman, Pucuk mati | Batang · — | Suhu optimal 30 °C; Musim hujan; Kelembapan tinggi | *fallback* pengendalian umum | — |
| **Hawar daun bakteri** | 4 | Xanthomonas Campestrispv. Manihotis (Bakteri) | Bercak daun, Daun rontok, Hawar daun, Layu daun | Daun · — | Suhu 30 °C; Musim hujan; Kelembapan tinggi | *fallback* pengendalian umum | — |
| **Nekrosis pada titik tunas (Cassava bud necrosis)** | 2 | Fungi/Jamur (Jamur) | Bercak pada tanaman, Nekrosis pada tanaman | Batang · — | Iklim lembap; Kelembapan tinggi | *fallback* pengendalian umum | — |
| **Sapu setan (Witches broom)** | 1 | Fitoplasma (Fitoplasma) | Kerdil tanaman | Daun · — | Musim kemarau | *fallback* pengendalian umum | — |
| **Superelongasi** | 1 | Elsinoe brasiliensis (Jamur) | Pertumbuhan abnormal | Batang · — | Musim hujan | *fallback* pengendalian umum | — |
| **Tanaman kerdil (stunt)** | 1 | Begomovirus (Virus) | belum dipetakan | Batang · — | Suhu, curah hujan, dan angin | *fallback* pengendalian umum | — |

Pengendalian umum tingkat tanaman: Karantina tanaman, Panen tepat waktu, Pemupukan berimbang, Pengairan dan drainase, Pengaturan jarak tanam, Penggunaan varietas tahan, Pengumpulan dan pemusnahan, Rotasi tanaman, Sanitasi lahan, Seleksi bahan tanam.

### Kacang tanah — 4 penyakit

| Penyakit | Obs | Patogen (takson) | Gejala kanonik | Bagian · Fase | Lingkungan | Pengendalian spesifik | Varietas tahan |
|---|---:|---|---|---|---|---|---|
| **Penyakit Belang (Mottle)** | 7 | Peanut mottle virus (Virus); Peanut stripe virus (Virus) | Belang pada tanaman, Klorosis daun, Klorosis pada tanaman, Mosaik daun | Daun · — | Musim hujan; Musim kemarau | Kultur meristem, Pemupukan berimbang, Pengaturan waktu tanam, Pengendalian vektor, Penggunaan benih sehat, Penggunaan insektisida, Penggunaan mulsa, Penggunaan varietas tahan, Rotasi tanaman | — |
| **Penyakit Bercak Daun** | 9 | Cercospora arachidicola (Jamur); Cercospora personata (Jamur); Puccinia arachidis (Jamur) | Bercak daun, Bercak pada tanaman, Daun berlubang, Daun kering, Daun rontok, Klorosis daun, Klorosis pada tanaman | Biji, Daun, Polong · generatif | Suhu 18–32 °C; Kelembapan relatif >90% | Penerapan pengendalian kimiawi, Pengelolaan terpadu, Penggunaan Trichoderma, Penggunaan agens hayati, Penggunaan bakterisida, Penggunaan ekstrak tanaman, Penggunaan fungisida, Penggunaan herbisida, Penggunaan insektisida, Penggunaan pestisida nabati, Penggunaan varietas tahan, Rotasi tanaman, Sanitasi lahan | Badak, Bison, Domba, Jerapah, Kelinci, Panther |
| **Penyakit Karat Daun** | 5 | Puccinia arachidis (Jamur) | Bercak daun, Bercak pada tanaman, Klorosis daun, Klorosis pada tanaman, Tepung pada daun | Daun · — | Suhu 20–30 °C; Kelembapan relatif >78% | Pengelolaan gulma, Penggunaan varietas tahan, Rotasi tanaman, Sanitasi lahan | Takar 1, Takar 2 |
| **Penyakit Layu Bakteri** | 2 | Ralstonia solanacearum (Bakteri) | Kematian tanaman, Layu daun | Biji, Polong · — | Suhu 25–37 °C; Tanah basah | Pengelolaan terpadu, Penggunaan Bacillus, Penggunaan Pseudomonas, Penggunaan agens hayati, Penggunaan bakterisida, Penggunaan benih sehat, Penggunaan biopestisida, Penggunaan pestisida nabati, Penggunaan tanaman bukan inang, Penggunaan varietas tahan, Rotasi tanaman | — |

Pengendalian umum tingkat tanaman: Penerapan pengendalian kimiawi, Penggunaan agens hayati, Penggunaan Bacillus, Penggunaan bakterisida, Penggunaan biopestisida, Penggunaan ekstrak tanaman, Penggunaan fungisida, Penggunaan herbisida, Penggunaan insektisida, Penggunaan pestisida nabati, Penggunaan Pseudomonas, Penggunaan Trichoderma.

### Kacang hijau — 3 penyakit

| Penyakit | Obs | Patogen (takson) | Gejala kanonik | Bagian · Fase | Lingkungan | Pengendalian spesifik | Varietas tahan |
|---|---:|---|---|---|---|---|---|
| **Penyakit Bercak Daun** | 2 | Cercospora canescens (Jamur); Cercospora cruenta (Jamur) | Bercak daun | Biji, Daun, Polong · generatif | Suhu 25–30 °C; Kelembapan relatif 98–100% | Pengaturan jarak tanam, Pengaturan kelembapan, Pengelolaan gulma, Penggunaan ekstrak tanaman, Penggunaan pestisida nabati | — |
| **Penyakit Embun Tepung** | 1 | Erysiphe polygoni (Jamur) | Tepung pada daun | Biji · — | Suhu 20–24 °C; Kelembapan tinggi | Penggunaan agens hayati, Penggunaan ekstrak tanaman, Penggunaan fungisida, Penggunaan pestisida nabati, Penggunaan varietas tahan | — |
| **Penyakit Layu** | 3 | Sclerotium rolfsii (Jamur) | Busuk pada tanaman, Layu daun | Akar, Daun · generatif | Suhu 27–35 °C; Tanah jenuh air dan kelembapan tinggi | Penggunaan agens hayati, Penggunaan ekstrak tanaman, Penggunaan pestisida nabati, Penggunaan varietas tahan, Solarisasi tanah | Vima 4, Vima 5 |

---

## 5. Kosakata gejala dan normalisasi

### Konsep gejala kanonik

| Konsep | ID | Jumlah penyakit | Sinonim |
|---|---|---:|---|
| Bercak daun | `BercakDaun` | 23 | bercak daun |
| Bercak pada tanaman | `BercakTanaman` | 22 | bercak pada tanaman |
| Klorosis daun | `KlorosisDaun` | 18 | klorosis daun |
| Klorosis pada tanaman | `KlorosisTanaman` | 13 | klorosis pada tanaman |
| Layu daun | `LayuDaun` | 12 | layu daun |
| Kerdil tanaman | `KerdilTanaman` | 9 | kerdil tanaman |
| Busuk batang | `BusukBatang` | 6 | busuk batang |
| Daun rontok | `DaunRontok` | 6 | daun rontok |
| Busuk akar | `BusukAkar` | 5 | busuk akar |
| Busuk pada tanaman | `BusukTanaman` | 5 | busuk pada tanaman |
| Kematian tanaman | `KematianTanaman` | 5 | kematian tanaman |
| Mosaik daun | `MosaikDaun` | 5 | mosaik daun |
| Nekrosis daun | `NekrosisDaun` | 5 | nekrosis daun |
| Nekrosis pada tanaman | `NekrosisTanaman` | 5 | nekrosis pada tanaman |
| Pertumbuhan terhambat | `PertumbuhanTerhambat` | 5 | pertumbuhan terhambat |
| Hawar daun | `HawarDaun` | 4 | hawar daun |
| Tepung pada daun | `TepungDaun` | 4 | tepung pada daun |
| Belang pada tanaman | `BelangTanaman` | 3 | belang pada tanaman |
| Pertumbuhan abnormal | `PertumbuhanAbnormal` | 3 | pertumbuhan abnormal |
| Pucuk mati | `PucukMati` | 3 | pucuk mati |
| Daun berlubang | `DaunBerlubang` | 2 | daun berlubang |
| Daun kering | `DaunKering` | 2 | daun kering |
| Busuk buah | `BusukBuah` | 1 | busuk buah |
| Malai patah | `MalaiPatah` | 1 | malai patah |
| Malai kosong | `MalaiKosong` | 0 | malai kosong |

Konsep yang belum dipakai penyakit mana pun: **Malai kosong**.

### Normalisasi pengamatan

| Ukuran | Nilai |
|---|---:|
| Pengamatan gejala (individu) | 231 |
| Terpetakan ke konsep kanonik | 167 |
| Belum terpetakan | 64 |
| Kelompok kanonik per penyakit | 167 grup |

Pengamatan yang belum terpetakan tetap disimpan sebagai individu `Gejala*`
dengan kutipan sumber, sehingga dapat ditriase ulang tanpa kehilangan bukti.
Penyakit dengan pengamatan tetapi tanpa satu pun konsep kanonik: **Tanaman kerdil (stunt)**, Ubi Kayu.

---

## 6. Patogen

### Rekap per takson

| Takson | Patogen unik |
|---|---:|
| Jamur | 40 |
| Virus | 14 |
| Bakteri | 7 |
| Oomycete | 2 |
| Fitoplasma | 1 |
| **Total** | **64** |

### Patogen yang dipakai lebih dari satu penyakit

| Patogen | Penyakit |
|---|---|
| Begomovirus | Cassava Mosaic Begomovirus (CMBs); Tanaman kerdil (stunt) |
| Botryodiplodia spp | Busuk akar dan umbi; Busuk pangkal batang |
| Diplodia spp | Busuk akar dan umbi; Busuk pangkal batang |
| Fusarium spp | Busuk Umbi; Busuk pangkal batang; Penyakit Layu Fusarium |
| Phytophthora spp | Busuk akar dan umbi; Busuk pangkal batang |
| Puccinia arachidis | Penyakit Bercak Daun; Penyakit Karat Daun |
| Rhizoctonia solani | Penyakit Busuk Pelepah; Penyakit Hawar Pelepah Daun; Penyakit Rebah Kecambah |
| Sclerotium rolfsii | Busuk akar dan umbi; Busuk pangkal batang; Penyakit Layu; Penyakit Rebah Semai |

### Daftar patogen unik

| Patogen | Takson | Jumlah penyakit |
|---|---|---:|
| Begomovirus | Virus | 2 |
| Botryodiplodia spp | Jamur | 2 |
| Ceratocystis fimbriata | Jamur | 1 |
| Cercospora arachidicola | Jamur | 1 |
| Cercospora canescens | Jamur | 1 |
| Cercospora cruenta | Jamur | 1 |
| Cercospora henningsii | Jamur | 1 |
| Cercospora kikuchii | Jamur | 1 |
| Cercospora personata | Jamur | 1 |
| Cercospora sojina | Jamur | 1 |
| Cercospora. viscosae | Jamur | 1 |
| Cercosporidium henningsii | Jamur | 1 |
| Collectothricum gloeosporioides | Jamur | 1 |
| Colletotrichum | Jamur | 1 |
| Colletotrichum truncatum | Jamur | 1 |
| Colletotricum spp | Jamur | 1 |
| Corynespora cassiicola | Jamur | 1 |
| Cowpea Mild Mottle Virus | Virus | 1 |
| Diplodia spp | Jamur | 2 |
| Elsinoe batatas | Jamur | 1 |
| Elsinoe brasiliensis | Jamur | 1 |
| Erysiphae diffusa | Jamur | 1 |
| Erysiphe polygoni | Jamur | 1 |
| Fitoplasma | Fitoplasma | 1 |
| Fungi/Jamur | Jamur | 1 |
| Fusarium oxysporum | Jamur | 1 |
| Fusarium spp | Jamur | 3 |
| Helminthosporium maydis | Jamur | 1 |
| Ipomovirus | Virus | 1 |
| Magnaporthe grisea | Jamur | 1 |
| Pantoea stewartii | Bakteri | 1 |
| Peanut mottle virus | Virus | 1 |
| Peanut stripe virus | Virus | 1 |
| Peronosclerospora maydis | Jamur | 1 |
| Peronosclerospora sp | Jamur | 1 |
| Peronospora manshurica | Oomycete | 1 |
| Phaeoramularia manihotis | Jamur | 1 |
| Phakopsora meibomiae | Jamur | 1 |
| Phakopsora pachyrhizi | Jamur | 1 |
| Phakopspora pachyrhizi | Jamur | 1 |
| Phytophthora spp | Oomycete | 2 |
| Polyporus sulphureus | Jamur | 1 |
| Pseudomonas syringae | Bakteri | 1 |
| Puccinia arachidis | Jamur | 2 |
| Puccinia polysora | Jamur | 1 |
| Pyricularia grisea | Jamur | 1 |
| Pyricularia oryzae | Jamur | 1 |
| Ralstonia solanacearum | Bakteri | 1 |
| Rhizoctonia solani | Jamur | 3 |
| Rice grassy stunt virus | Virus | 1 |
| Rice ragged stunt virus | Virus | 1 |
| Rice tungro bacillifor virus | Virus | 1 |
| Rice tungro spherical virus | Virus | 1 |
| Sclerotium rolfsii | Jamur | 4 |
| Soybean Mosaic Virus | Virus | 1 |
| Soybean Stunt Virus | Virus | 1 |
| Spaceloma batatas | Jamur | 1 |
| Sweet Potato Chlorotic Fleck Virus | Virus | 1 |
| Sweet Potato Feathery Mottle Virus | Virus | 1 |
| Sweet Potato Mild Mottle Virus | Virus | 1 |
| Xanthomonas Campestrispv. Manihotis | Bakteri | 1 |
| Xanthomonas axonopodis | Bakteri | 1 |
| Xanthomonas campestris pv. Manihotis | Bakteri | 1 |
| Xanthomonas oryzae | Bakteri | 1 |

---

## 7. Faktor lingkungan

### Sebaran observasi

| Kelas faktor | Observasi |
|---|---:|
| Suhu | 21 |
| KelembapanUdara | 17 |
| Iklim | 16 |
| Musim | 7 |
| KelembapanTanah | 7 |
| FaktorRisiko | 2 |
| CurahHujan | 1 |
| **Total observasi** | **71** |

Semua observasi terhubung dua arah: penyakit `dipengaruhiOleh` observasi, dan
observasi `memengaruhiPenyakit` penyakit. 24 observasi bernilai numerik
(suhu/kelembapan/tanah), sisanya berupa pernyataan kualitatif.

### Observasi bernilai numerik

| Penyakit | Faktor | Nilai | Operator |
|---|---|---|---|
| Penyakit Hawar Daun | Daun basah 6 jam | 6 jam | = |
| Penyakit Bulai | Kelembapan 90% | 90 % | > |
| Penyakit Bercak Daun | Kelembapan relatif 98–100% | 98–100 % | rentang |
| Penyakit Hawar Daun Bakteri | Kelembapan relatif >70% | 70 % | > |
| layu fusarium | Kelembapan tanah 28–75% | 28–75 % | rentang |
| Penyakit bercak kuning | Suhu 20–29 °C | 20–29 °C | rentang |
| Penyakit Bulai | Suhu 24 °C | 24 °C | < |
| Penyakit Karat Daun | Suhu 25,2–28,8 °C | 25.2–28.8 °C | rentang |
| Penyakit Bercak Daun | Suhu 25–30 °C | 25–30 °C | rentang |
| Penyakit Hawar Daun Bakteri | Suhu 25–34 °C | 25–34 °C | rentang |
| Penyakit Layu Bakteri | Suhu 25–37 °C | 25–37 °C | rentang |
| Penyakit Layu | Suhu 27–35 °C | 27–35 °C | rentang |
| layu fusarium | Suhu infeksi optimal 30 °C | 30 °C | = |
| Penyakit busuk hitam (black rot) | Suhu lapang 23–27 °C | 23–27 °C | rentang |
| Hawar bakteri | Suhu optimal 30 °C | 30 °C | = |
| Penyakit Bercak Daun Mata Katak (Frogeye Leaf Spot) | Suhu optimal 25–30 °C | 25–30 °C | rentang |
| Hawar daun bakteri | Suhu 30 °C | 30 °C | = |
| Penyakit Bakteri Pustul | Suhu 26–30 °C | 26–30 °C | rentang |
| Penyakit Bercak Daun | Suhu 18–32 °C | 18–32 °C | rentang |
| Penyakit Embun Tepung | Suhu 20–24 °C | 20–24 °C | rentang |
| Penyakit Embun Tepung (Powdery Mildew) | Suhu 18–24 °C | 18–24 °C | rentang |
| Penyakit Hawar Daun | Suhu 18–27 °C | 18–27 °C | rentang |
| Penyakit Karat Daun | Suhu 20–30 °C | 20–30 °C | rentang |
| Penyakit Busuk Pelepah | Suhu ≥30 °C | 30 °C | ≥ |

### Kondisi kualitatif

| Kondisi | ID | Dipakai oleh penyakit | Kondisi tumbuh tanaman |
|---|---|---:|---|
| Cahaya rendah | `KondisiCahayaRendah` | 0 | — |
| Cahaya sedang | `KondisiCahayaSedang` | 0 | Kedelai |
| Cahaya tinggi | `KondisiCahayaTinggi` | 0 | — |
| Curah hujan rendah | `KondisiCurahHujanRendah` | 0 | — |
| Curah hujan sedang | `KondisiCurahHujanSedang` | 0 | — |
| Curah hujan tinggi | `KondisiCurahHujanTinggi` | 1 | Padi |
| Dataran rendah | `KondisiDataranRendah` | 0 | — |
| Dataran tinggi | `KondisiDataranTinggi` | 0 | — |
| Drainase baik | `KondisiDrainaseBaik` | 0 | — |
| Drainase buruk | `KondisiDrainaseBuruk` | 0 | — |
| Iklim basah | `KondisiIklimBasah` | 0 | — |
| Iklim kering | `KondisiIklimKering` | 0 | — |
| Kelembapan tanah rendah | `KondisiKelembapanTanahRendah` | 0 | — |
| Kelembapan tanah sedang | `KondisiKelembapanTanahSedang` | 0 | — |
| Kelembapan tanah tinggi | `KondisiKelembapanTanahTinggi` | 0 | — |
| Kelembapan udara rendah | `KondisiKelembapanUdaraRendah` | 0 | — |
| Kelembapan udara sedang | `KondisiKelembapanUdaraSedang` | 0 | — |
| Kelembapan udara tinggi | `KondisiKelembapanUdaraTinggi` | 0 | — |
| Musim hujan | `KondisiMusimHujan` | 4 | — |
| Musim kemarau | `KondisiMusimKemarau` | 2 | — |
| Suhu dingin | `KondisiSuhuDingin` | 0 | Kedelai |
| Suhu hangat | `KondisiSuhuHangat` | 0 | Kacang hijau, Kacang tanah |
| Suhu sedang | `KondisiSuhuSedang` | 0 | Jagung, Kedelai |
| Tanah asam | `KondisiTanahAsam` | 0 | — |
| Tanah basa | `KondisiTanahBasa` | 0 | — |
| Tanah berpasir | `KondisiTanahBerpasir` | 0 | — |
| Tanah gembur | `KondisiTanahGembur` | 0 | Ubi jalar |
| Tanah liat | `KondisiTanahLiat` | 0 | — |
| Tanah netral | `KondisiTanahNetral` | 0 | — |
| Tanah subur | `KondisiTanahSubur` | 0 | Ubi kayu |

Dari 30 kondisi kualitatif, **9 terpakai** dan 21 masih menjadi kosakata cadangan.

Catatan penting: sebagian besar kondisi lingkungan pada sumber berupa narasi
("cuaca hangat dan lembap", "tanah tergenang"), bukan ambang terukur. Hanya 24 observasi yang dapat dipakai untuk aturan numerik.

---

## 8. Metode pengendalian

### Aksi kanonik per kategori

| Kategori | Aksi | Dipakai penyakit |
|---|---:|---:|
| KulturTeknis | 20 | 15 |
| Biologis | 9 | 8 |
| Kimiawi | 8 | 8 |
| Fisik | 5 | 4 |
| Mekanis | 4 | 2 |
| Terpadu | 2 | 1 |
| **Total** | **48** | **38** |

### Daftar aksi dan frekuensi

| Aksi | Kategori | Penyakit | Tingkat tanaman |
|---|---|---:|---|
| Karantina tanaman | KulturTeknis | 0 | Ubi kayu |
| Kultur meristem | KulturTeknis | 2 | — |
| Panen tepat waktu | KulturTeknis | 0 | Ubi kayu |
| Pemangkasan tanaman | KulturTeknis | 0 | — |
| Pembersihan alat | KulturTeknis | 0 | — |
| Pemupukan berimbang | KulturTeknis | 6 | Ubi kayu |
| Pencabutan tanaman | Mekanis | 1 | — |
| Penerapan kultur teknis | KulturTeknis | 0 | — |
| Penerapan pengendalian biologis | Biologis | 0 | — |
| Penerapan pengendalian fisik | Fisik | 1 | — |
| Penerapan pengendalian kimiawi | Kimiawi | 1 | Kacang tanah |
| Penerapan pengendalian mekanis | Mekanis | 0 | — |
| Pengairan dan drainase | KulturTeknis | 3 | Ubi kayu |
| Pengaturan jarak tanam | KulturTeknis | 4 | Ubi kayu |
| Pengaturan kelembapan | KulturTeknis | 2 | — |
| Pengaturan suhu penyimpanan | Fisik | 1 | — |
| Pengaturan waktu tanam | KulturTeknis | 4 | — |
| Pengelolaan gulma | KulturTeknis | 8 | — |
| Pengelolaan terpadu | Terpadu | 3 | — |
| Pengendalian hama terpadu | Terpadu | 0 | — |
| Pengendalian vektor | Kimiawi | 5 | — |
| Penggunaan Bacillus | Biologis | 10 | Kacang tanah |
| Penggunaan Beauveria | Biologis | 2 | — |
| Penggunaan Metarhizium | Biologis | 2 | — |
| Penggunaan Pseudomonas | Biologis | 8 | Kacang tanah |
| Penggunaan Trichoderma | Biologis | 8 | Kacang tanah |
| Penggunaan agens hayati | Biologis | 18 | Kacang tanah |
| Penggunaan bakterisida | Kimiawi | 6 | Kacang tanah |
| Penggunaan benih sehat | KulturTeknis | 10 | — |
| Penggunaan biopestisida | Biologis | 1 | Kacang tanah |
| Penggunaan ekstrak tanaman | Biologis | 6 | Kacang tanah |
| Penggunaan fungisida | Kimiawi | 15 | Kacang tanah |
| Penggunaan herbisida | Kimiawi | 1 | Kacang tanah |
| Penggunaan insektisida | Kimiawi | 6 | Kacang tanah |
| Penggunaan mulsa | KulturTeknis | 3 | — |
| Penggunaan perangkap | Mekanis | 0 | — |
| Penggunaan pestisida nabati | Kimiawi | 7 | Kacang tanah |
| Penggunaan tanaman bukan inang | KulturTeknis | 7 | — |
| Penggunaan varietas tahan | KulturTeknis | 20 | Ubi kayu |
| Pengumpulan dan pemusnahan | Mekanis | 3 | Ubi kayu |
| Perlakuan air panas | Fisik | 1 | — |
| Perlakuan benih | KulturTeknis | 11 | — |
| Perlakuan kimia tanah | Kimiawi | 1 | — |
| Perlakuan radiasi | Fisik | 0 | — |
| Rotasi tanaman | KulturTeknis | 15 | Ubi kayu |
| Sanitasi lahan | KulturTeknis | 20 | Ubi kayu |
| Seleksi bahan tanam | KulturTeknis | 1 | Ubi kayu |
| Solarisasi tanah | Fisik | 3 | — |

### Distribusi tautan penyakit → pengendalian

| Kategori | Tautan |
|---|---:|
| KulturTeknis | 116 |
| Biologis | 55 |
| Kimiawi | 42 |
| Fisik | 6 |
| Mekanis | 4 |
| Terpadu | 3 |
| **Total** | **226** |

Pengendalian didominasi kultur teknis (116 tautan), diikuti biologis (55) dan kimiawi (42).
Ini konsisten dengan karakter buku sumber yang menekankan PHT, bukan kuratif tunggal.

Aksi yang dideklarasikan tetapi belum dipakai: Karantina tanaman, Panen tepat waktu, Pemangkasan tanaman, Pembersihan alat, Penerapan kultur teknis, Penerapan pengendalian biologis, Penerapan pengendalian mekanis, Pengendalian hama terpadu, Penggunaan perangkap, Perlakuan radiasi.

---

## 9. Kelengkapan dan gap

### Gap per tanaman

| Tanaman | Penyakit | Tanpa severity | Tanpa fase | Tanpa varietas tahan | Kendali fallback |
|---|---:|---:|---:|---:|---:|
| Padi | 5 | 2 | 4 | 4 | 0 |
| Kedelai | 15 | 12 | 12 | 13 | 0 |
| Jagung | 5 | 1 | 1 | 4 | 0 |
| Ubi jalar | 4 | 4 | 4 | 3 | 0 |
| Ubi kayu | 17 | 17 | 17 | 17 | 17 |
| Kacang tanah | 4 | 2 | 3 | 2 | 0 |
| Kacang hijau | 3 | 1 | 1 | 2 | 0 |
| **Total** | **53** | **39** | **42** | **45** | **17** |

### Gap per dimensi

| Dimensi | Terisi | Gap | Sifat |
|---|---:|---:|---|
| Patogen | 53 | 0 | Inti |
| Bukti lingkungan | 53 | 0 | Inti |
| Pengendalian (spesifik atau fallback) | 53 | 0 | Inti |
| Bagian tanaman | 53 | 0 | Inti |
| Gejala terpetakan | 52 | 1 | Inti |
| Pengendalian penyakit-spesifik | 36 | 17 | Mapping |
| Severity | 14 | 39 | Best-effort |
| Fase serangan | 11 | 42 | Best-effort |
| Nama Inggris | 10 | 43 | Best-effort |
| Varietas tahan | 8 | 45 | Best-effort |
| Pengamatan gejala terpetakan | 167 | 64 | Mapping |
| Baris pengendalian belum dipetakan | — | 38 | Mapping |

Gap *inti* berarti melanggar restriksi TBox atau menghilangkan jalur penalaran;
gap *mapping* berarti data ada tetapi belum dinormalisasi; gap *best-effort*
berarti sumber memang tidak selalu menyatakan, sehingga tidak dipaksakan.

---

## 10. Temuan kualitas data

Audit menemukan sejumlah isu yang perlu dicatat sebagai limitasi, atau diperbaiki
pada iterasi berikutnya.

### 10.1 Salah eja dan varian nama ilmiah

| Tertulis di KB | Seharusnya | Penyakit |
|---|---|---|
| `Phakopspora pachyrhizi` | `Phakopsora pachyrhizi` | Karat Daun Kedelai |
| `Collectothricum gloeosporioides` | `Colletotrichum gloeosporioides` | Antraknosa Ubi Kayu (batang) |
| `Colletotricum spp` | `Colletotrichum spp` | Antraknosa Ubi Kayu (daun) |
| `Cercospora. viscosae` | `Cercospora viscosae` | Bercak daun baur |
| `Xanthomonas Campestrispv. Manihotis` | `Xanthomonas campestris pv. manihotis` | Hawar daun bakteri Ubi Kayu |
| `Erysiphae diffusa` | `Erysiphe diffusa` | Embun Tepung Kedelai |

Akibatnya `Phakopsora pachyrhizi` muncul sebagai dua individu patogen berbeda,
padahal merujuk spesies yang sama.

### 10.2 Takson placeholder

- `Fungi/Jamur` — bukan nama takson, dipakai untuk Nekrosis pada titik tunas Ubi Kayu.
- `Peronosclerospora sp`, `Colletotrichum`, `Botryodiplodia spp`, `Diplodia spp`,
  `Fusarium spp`, `Phytophthora spp` — hanya sampai genus, bukan spesies.
- `Begomovirus`, `Ipomovirus`, `Fitoplasma` — tingkat genus/kelompok.

Ini bukan kesalahan ekstraksi: sumber memang hanya menyebut sampai tingkat tersebut.
Namun untuk penalaran berbasis takson, granularitas ini perlu dinyatakan eksplisit.

### 10.3 Ambang numerik yang hilang

`Kelembapan relatif >78% pada Penyakit Karat Daun` (kacang tanah),
`Kelembapan relatif >90% pada Penyakit Bercak Daun` (kacang tanah), dan
`Kelembapan relatif >90% pada ... Frogeye Leaf Spot` memiliki `satuan` `%` dan
operator `>` tetapi **tanpa `nilaiMin`/`nilaiMaks`**. Angka 78 dan 90 hilang dari
properti numerik, sehingga aturan ambang tidak bisa dieksekusi.

Contoh lain: `Suhu pada Cassava Brown Streak Disease` dan
`Kelembapan relatif pada Penyakit Hawar Pelepah Daun` tidak memiliki nilai sama sekali.

### 10.4 Label belum dinormalisasi

Beberapa label individu masih membawa pola hasil ekstraksi:

- `Kelembapan 90Persen pada Penyakit Bulai`
- `Suhu 24Celsius pada Penyakit Bulai`
- `Suhu 25Koma2Sampai28Koma8Celsius pada Penyakit Karat Daun`

Nilai numeriknya benar (`90 %`, `24 °C`, `25,2–28,8 °C`), hanya label manusianya
yang belum dirapikan. Selain itu `Suhu 24Celsius` memakai operator `<` untuk satu
nilai tunggal, yang semantiknya ambigu (kurang dari 24 °C, atau sekitar 24 °C?).

### 10.5 Duplikasi dan tabrakan label

- `OBS_EXT_015` dan `OBS_EXT_016` sama-sama mencatat "Curah hujan dan kelembapan
  relatif pada Antraknosa" sebagai dua observasi berbeda.
- Label penyakit bentrok walau IRI berbeda: `Antraknosa` (2), `Bercak Daun` (2),
  `Karat Daun` (3), `Hawar Daun Bakteri` (2), `layu fusarium` (2).
  Disambiguasi hanya tersedia lewat konteks tanaman pada IRI.

### 10.6 Inkonsistensi bagian tanaman

`Penyakit Embun Tepung` (kacang hijau) hanya tercatat menyerang **Biji**,
`Penyakit Layu Bakteri` (kacang tanah) menyerang **Biji dan Polong**, padahal
gejalanya adalah layu daun. `Penyakit Bercak Biji Ungu` menyerang **Biji** saja
meski gejalanya bercak daun. Nilai ini kemungkinan diambil dari kalimat sumber
yang membahas bagian panen, bukan lokasi gejala.

### 10.7 Sebaran data tidak seimbang

Kedelai memuat 15 penyakit dan 88 pengamatan gejala (38% dari seluruh pengamatan),
sedangkan Ubi Kayu memuat 17 penyakit tetapi hanya 30 pengamatan dan **0 varietas**.
Ubi Kayu juga satu-satunya tanaman yang seluruh pengendaliannya memakai fallback
(`pengendalianUmum`), sehingga pertanyaan "apa pengendalian spesifik penyakit X"
tidak bisa dijawab untuk 17 penyakit tersebut.

### 10.8 Keterbatasan bukti

- Hanya **2 buku** (`DOC002` 2021, `DOC005` 2020) sebagai referensi bibliografis.
- Tidak ada `urlReferensi`; pelacakan hanya lewat `dokumenSumber`, `halamanSumber`,
  `idChunkSumber`, dan kutipan.
- 64 pengamatan gejala dan 38 baris pengendalian belum terpetakan ke kosakata kanonik, meski bukti kutipannya tersimpan.
- Sebagian kutipan berupa fragmen (`fragment_quotes` = 210 pada laporan build),
  bukan kalimat utuh.

---

## 11. Kesiapan untuk penalaran

| Komponen | Status |
|---|---|
| Profil | SROIQ(D) — subclass, inverse, nominal, property chain, cardinality, data range |
| Property chain | `memilikiGejala ∘ terdapatPada ⊑ menyerangBagian` |
| Nominal | `Serealia ≡ {Padi, Jagung}`, `Legum ≡ {Kedelai, KacangTanah, KacangHijau}`, `UmbiUmbian ≡ {UbiKayu, UbiJalar}` |
| Kardinalitas | `Penyakit ⊑ memilikiReferensi min 1`, `Buku ⊑ tahunTerbit exactly 1` |
| Reasoner | Pellet (utama), HermiT (alternatif via `KBR_REASONER=hermit`) |
| Aturan SWRL | 4 aturan di `ontology_md.ttl` |
| Individu `Diagnosis` bawaan | 0 — dibuat saat runtime |

### Aturan SWRL

| Aturan | Fungsi |
|---|---|
| `RuleKandidatGejala` | Diagnosis + tanaman + pengamatan gejala → kandidat penyakit dengan gejala kanonik yang sama |
| `RuleKandidatLingkungan` | Diagnosis + observasi lingkungan ber-`klasifikasiTurunan` → penyakit yang `dipengaruhiOleh` kondisi sekelas |
| `RuleRekomendasiSpesifik` | Penyakit kandidat `dikendalikanDengan` aksi → rekomendasi pengendalian |
| `RuleRekomendasiUmum` | Fallback: penyakit menyerang tanaman → `pengendalianUmum` tanaman |

Karena tidak ada individu `Diagnosis` yang di-assert, seluruh triple hasil aturan
bersifat inferensi dan tidak muncul di berkas Turtle. Ini perlu dijelaskan di
laporan agar pembaca tidak menyimpulkan aturan "tidak berjalan".

### Yang bisa dan tidak bisa dijawab KB

| Pertanyaan | Bisa? | Alasan |
|---|---|---|
| Penyakit apa saja menyerang tanaman X? | Ya | 53 tautan `menyerangTanaman` |
| Patogen penyebab penyakit X? | Ya | 76 tautan, 0 kosong |
| Gejala khas penyakit X? | Ya, dengan catatan | 167 dari 231 pengamatan terpetakan |
| Kondisi lingkungan pemicu X? | Sebagian | 24 observasi numerik, sisanya kualitatif |
| Pengendalian spesifik X? | Sebagian | 36 penyakit; 17 ubi kayu hanya fallback |
| Seberapa parah X? | Tidak | severity hanya 14 dari 53 |
| Varietas tahan X? | Tidak | 8 dari 53; ubi kayu 0 |
| Diagnosis dari gejala bebas? | Sebagian | bergantung kualitas mapping gejala |

---

## 12. Rekomendasi perbaikan

| Prioritas | Tindakan | Dampak |
|---|---|---|
| Tinggi | Normalisasi 64 pengamatan gejala yang belum terpetakan | Menambah cakupan diagnosis |
| Tinggi | Isi `nilaiMin`/`nilaiMaks` untuk 3 observasi ambang yang hilang | Mengaktifkan aturan numerik |
| Tinggi | Perbaiki 6 salah eja nama ilmiah dan gabungkan duplikat `Phakopsora` | Mencegah dua individu untuk satu spesies |
| Sedang | Petakan 38 baris pengendalian yang belum punya aksi kanonik | Memperkaya rekomendasi |
| Sedang | Lengkapi pengendalian spesifik 17 penyakit ubi kayu | Menghapus ketergantungan fallback |
| Sedang | Bersihkan label `Persen`/`Celsius`/`Koma` dan operator ambigu | Kualitas presentasi dan query |
| Rendah | Isi severity, fase, nama Inggris, varietas tahan dari sumber | Nilai tambah, bukan syarat |
| Rendah | Tambah referensi ber-URL di luar 2 buku | Ketertelusuran |

---

## 13. Metode audit dan reproduksi

Audit dilakukan dengan memuat `ontology_md.ttl` ke `rdflib` lalu menghitung:

- jumlah triple, individu, kelas, dan properti per tipe RDF;
- jumlah individu per kelas dan subclass pengendalian (lewat `rdfs:subClassOf`);
- tautan `menyerangTanaman`, `disebabkanOleh`, `memilikiGejala`,
  `memilikiGejalaKanonik`, `dipengaruhiOleh`, `dikendalikanDengan`, dan `pengendalianUmum`;
- nilai data property lingkungan dan tingkat keparahan;
- node bukti per subclass `BuktiSumber`.

Tidak ada berkas yang diubah selama audit. Angka pada dokumen ini adalah snapshot
dari artefak saat audit; bila `build_ontology_md.py` dijalankan ulang, hitung ulang
dengan skrip yang sama. Angka pembanding tersedia di
`03_knowledge_tables/reports/KB_COMPLETENESS.md`, `extraction_report.json`, dan
`extraction_report_md.json`.
