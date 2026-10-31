# Ontologi OWL 2 — Sistem Pakar Penyakit Tanaman

Folder ini membangun ontologi OWL 2 (Turtle) dari knowledge tables terkurasi di
`03_knowledge_tables/`. TBox didefinisikan manual di `tbox.py`; ABox dibangkitkan
otomatis oleh `build_ontology.py` dari CSV sumber, lalu divalidasi (jumlah
individu/triple, range properti, axiom, ketiadaan literal kosong). Generator
berkode keluar `2` bila validasi gagal.

## Cara menjalankan

```powershell
pip install -r 04_ontology/requirements.txt   # rdflib >=7,<8
python 04_ontology/build_ontology.py          # menulis ontology.ttl
cd 04_ontology
python -m unittest discover -s tests -p "test_*.py"
```

Keluaran build terakhir: **24 652 triple**, **1 932 individu**,
**359 chunk bukti**, **122 bagian dokumen**, 23 test lulus.

## Namespace dan kebijakan IRI

| Namespace | IRI | Dipakai untuk |
|---|---|---|
| `kbr:` | `http://kbr.kelompok5.org/ontology#` | kelas, properti, axioms |
| `kbrd:` | `http://kbr.kelompok5.org/data#` | individu ABox |

Ontologi: `http://kbr.kelompok5.org/ontology`. ID tabel (mis. `PLANT_005`,
`DIS_042`, `PAT_110`, `T5_2_BATANG`) dipakai apa adanya sebagai local name
(karakter non-`[A-Za-z0-9_-]` diganti `_`). Semua literal `rdfs:label`
menggunakan tag bahasa `id` dan diambil verbatim dari kurasi.

Dua penyelesaian tabrakan ID (bukan perubahan data sumber):

- **Patogen DOC003**: `03_knowledge_tables/curated/DOC003/pathogens.csv`
  memakai ulang ID `PAT_106`–`PAT_112` untuk organisme berbeda (mis. DOC002
  `PAT_106` = Ipomovirus, DOC003 `PAT_106` = Rhizoctonia solani). Individu
  DOC003 diskoping: `kbrd:PAT_106_DOC003`, dst. Rujukan
  `DOC003/disease_pathogen.csv` mengikuti aturan yang sama.
- **Baris tabel tanpa nomor**: dua baris `status=unnumbered` di tabel
  T5.2_BATANG punya `row_no` kosong; IRI-nya menjadi
  `kbrd:T5_2_BATANG_R_unnumbered_1` dan `..._2` (berurutan per tabel).

## Pemetaan sumber ke model

| Sumber | Individu | Kelas |
|---|---|---|
| `manual_metadata.json` | DOC002, DOC003, DOC004 | KnowledgeSource |
| `auto/plants.csv` (15) + `DOC003/plants.csv` (2) | PLANT_001–016 … | Plant (17) |
| `curated/diseases.csv` (110) + `DOC003/amorphophallus_spp_diseases.csv` (7) | DIS_001–117 | Disease (117) |
| `curated/pathogens.csv` (105) + `DOC003/pathogens.csv` (7) | PAT_001–112 (+`_DOC003`) | Pathogen (112) + kelas takson (Fungus 57, Bacterium 10, Virus 16, Nematode 7, Oomycete 2, Phytoplasma 1) |
| `curated/symptoms.csv` + `DOC003/symptoms.csv` | SYM_001–609 | Symptom (609) |
| `curated/controls.csv` + `DOC003/controls.csv` | CTR_* | ControlMeasure (532; DiseaseControl 452, ChapterControl 80) |
| `curated/ubi_kayu_tabel_5.csv` | T5.1_DAUN, T5.2_BATANG, T5.3_AKAR + 19 baris | SourceTable (3), SourceTableRow (19) |
| `curated/DOC004/{nutrients,fertilizers,practices,compost}.csv` | NUT/FRT/PRC/CMP_* | 39 individu nutrisi/pupuk (multi-tipe) |
| kolom `chunk_id`/`evidence_chunk_ids` semua tabel | chunk teks sumber | EvidenceChunk (359) |
| judul bab dari `plants.csv` + seksi penyakit | — | SourceSection (122) |

Relasi utama: penyakit ←`causedBy`→ patogen (139), penyakit ←`hasSymptom`→
gejala (609) dengan `observedOn` tanaman, pengendalian ←`appliesTo`→ penyakit
(452) dan `appliesToPlant` (532), `locatedInSection` (110), bukti chunk
`hasEvidence` (1 593) + `hasTaxonEvidence` (9).

## Matriks SHROIQ(D)

| Huruf | Konstruk | Penerapan di ontologi ini |
|---|---|---|
| **S** | Transitive role | `kbr:containsSection` — transitif + asimetris + irrefleksif; hierarki bab → seksi → subseksi |
| **H** | Role hierarchy | `kbr:hasTaxonEvidence rdfs:subPropertyOf kbr:hasEvidence` |
| **R** | Property chain | `appliesTo ∘ occursIn ⊑ appliesToPlant`; `hasSymptom ∘ observedOn ⊑ occursIn` |
| **O** | Nominals | `kbr:CassavaSourceTable ≡ owl:oneOf (T5_1_DAUN T5_2_BATANG T5_3_AKAR)` |
| **I** | Inverses | 6 pasang `owl:inverseOf`: occursIn↔hasDisease, causedBy↔causes, hasSymptom↔symptomOf, appliesTo↔hasControlMeasure, containsSection↔sectionOf, isTableRowOf↔hasTableRow |
| **Q** | Qualified cardinality | FunctionalProperty: `occursIn`, `observedOn`, `isTableRowOf` (satu penyakit → satu tanaman, dst.) |
| **D** | Datatypes | `xsd:integer` (page, chapterNumber, row terkait) dan literal ter-tag `@id` untuk teks |

Selain itu ada 3 axioms `owl:AllDisjointClasses` (mis. tanaman vs patogen vs
penyakit) dan 19 object property + ~35 data property di TBox (`tbox.py`).
Inverse dicetak dua arah langsung di ABox (materialisasi) agar ontologi tetap
bisa ditelusuri tanpa reasoner; axiom `owl:inverseOf` tetap dinyatakan.

## Guardrail konsistensi (fakta kurasi, bukan bug)

- **7 penyakit tanpa patogen**: DIS_005, 022, 039, 088, 090, 098, 109 —
  `disease_pathogen.csv` tidak memuat barisnya; `causedBy` tidak dipaksakan.
- **19 penyakit tanpa gejala**: DIS_028–043 + DIS_110 (DOC002, 17 penyakit
  ubi kayu) dan DIS_112, DIS_116 (DOC003) — tidak ada baris di `symptoms.csv`.
- **PLANT_016 (Porang)** tidak memiliki penyakit di DOC003 (hanya budidaya &
  nutrisi).
- **PLANT_005 (Ubi kayu)** memiliki 17 penyakit (DIS_028–043 + DIS_110).
- Property chain kedua aman terhadap sifat fungsional `occursIn`: kolom
  `plant_id` pada `symptoms.csv` selalu sama dengan `plant_id` penyakitnya
  (divalidasi silang oleh pipeline tahap 2).

## Struktur file

| File | Peran |
|---|---|
| `tbox.py` | TBox: daftar kelas, 33 subClassOf, 3 AllDisjointClasses, object/data property + axiom SHROIQ(D) |
| `build_ontology.py` | Generator ABox + `expected_counts()` + `validate()` (keluaran `ontology.ttl`, exit 2 bila gagal) |
| `ontology.ttl` | Artefak keluaran (Turtle, di-commit bersama generator) |
| `tests/test_ontology.py` | Gate test: snapshot jumlah kelas/triple, axiom SHROIQ(D), guardrail kurasi, build ulang tanpa error |
| `requirements.txt` | `rdflib>=7.0,<8` |
