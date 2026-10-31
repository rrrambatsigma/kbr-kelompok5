"""TBox ontologi OWL 2 project kbr-kelompok5.

Membangun seluruh schema: kelas, subkelas, object property, data property,
serta axiom yang membuat ontologi memenuhi ekspresivitas SHROIQ(D):

- S  : kbr:containsSection (owl:TransitiveProperty)
- H  : kbr:hasTaxonEvidence rdfs:subPropertyOf kbr:hasEvidence
- R  : owl:propertyChainAxiom (2 rantai peran)
- O  : kbr:CassavaSourceTable owl:oneOf (3 tabel ubi kayu)
- I  : pasang owl:inverseOf
- Q  : owl:FunctionalProperty -> pembatasan kuantitas berkualifikasi
- D  : data property bertipe xsd:integer / string / literal @id

Semua label dan komentar memakai bahasa Indonesia.
"""

from __future__ import annotations

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

KBR = Namespace("http://kbr.kelompok5.org/ontology#")
KBRD = Namespace("http://kbr.kelompok5.org/data#")
ONTOLOGY_IRI = URIRef("http://kbr.kelompok5.org/ontology")

ONTOLOGY_LABEL = "Ontologi Penyakit dan Pengendalian Tanaman Pangan"
ONTOLOGY_COMMENT = (
    "Ontologi OWL 2 dari knowledge tables Tahap 2 (03_knowledge_tables). "
    "TBox menjelaskan kelas, properti, dan hubungan domain; ABox dibangun dari "
    "tabel curated (tanaman, penyakit, patogen, gejala, pengendalian, tabel ubi "
    "kayu, nutrisi/pupuk) beserta bukti chunk yang dapat ditelusuri ke dokumen sumber."
)

CLASSES: dict[str, tuple[str, str]] = {
    "KnowledgeRecord": (
        "Rekaman Pengetahuan",
        "Setiap entitas hasil ekstraksi dari dokumen sumber; memiliki dokumen "
        "sumber, halaman, dan bukti chunk yang dapat ditelusuri.",
    ),
    "KnowledgeSource": (
        "Sumber Pengetahuan",
        "Dokumen sumber (buku) tempat pengetahuan diambil: DOC002, DOC003, DOC004.",
    ),
    "EvidenceChunk": (
        "Bukti Teks (Chunk)",
        "Potongan teks sumber ber-identified (chunk_id) yang menjadi bukti sebuah "
        "rekaman; dirujuk oleh kbr:hasEvidence.",
    ),
    "SourceSection": (
        "Bagian Dokumen",
        "Struktur bab, seksi, dan subseksi pada dokumen sumber, dibangun dari "
        "kolom chapter_title, section, dan subsection pada tabel penyakit.",
    ),
    "Plant": ("Tanaman", "Tanaman inang yang dibahas pada satu bab dokumen sumber."),
    "Disease": (
        "Penyakit",
        "Penyakit tanaman seperti tercetak pada sumber (verbatim).",
    ),
    "Pathogen": (
        "Patogen",
        "Agen penyebab penyakit; kelompok takson diisi hanya bila sumber menyebutnya.",
    ),
    "Fungus": ("Jamur", "Patogen kelompok jamur/cendawan (taxon_group = jamur)."),
    "Bacterium": ("Bakteri", "Patogen kelompok bakteri (taxon_group = bakteri)."),
    "Virus": ("Virus", "Patogen kelompok virus (taxon_group = virus)."),
    "Nematode": ("Nematoda", "Patogen kelompok nematoda (taxon_group = nematoda)."),
    "Phytoplasma": ("Fitoplasma", "Patogen kelompok fitoplasma (taxon_group = fitoplasma)."),
    "Oomycete": ("Oomycete", "Patogen kelompok oomycete (taxon_group = oomycete)."),
    "Symptom": (
        "Gejala",
        "Satu kalimat gejala verbatim beserta offset karakter pada chunk buktinya.",
    ),
    "ControlMeasure": (
        "Tindakan Pengendalian",
        "Satu kalimat pengendalian verbatim; dapat berskala penyakit atau bab.",
    ),
    "DiseaseControl": (
        "Pengendalian Tingkat Penyakit",
        "Pengendalian yang terikat pada penyakit tertentu (scope = disease).",
    ),
    "ChapterControl": (
        "Pengendalian Tingkat Bab",
        "Pengendalian yang berlaku untuk seluruh bab tanaman, tanpa penyakit "
        "tertentu (scope = chapter).",
    ),
    "SourceTable": ("Tabel pada Sumber", "Tabel yang tercetak pada dokumen sumber."),
    "CassavaSourceTable": (
        "Tabel Penyakit Ubi Kayu",
        "Tiga tabel penyakit ubi kayu T5.1 (daun), T5.2 (batang), T5.3 (akar) "
        "yang jumlahnya tetap pada sumber.",
    ),
    "SourceTableRow": (
        "Baris Tabel pada Sumber",
        "Satu baris tabel sumber; nama penyakit dan patogennya berupa teks "
        "verbatim tanpa foreign key (tidak ditebak keterkaitannya).",
    ),
    "Nutrient": ("Unsur Hara", "Catatan unsur hara (peran, bentuk serapan) dari DOC004."),
    "Macronutrient": ("Makronutrien", "Catatan unsur hara makronutrien."),
    "Micronutrient": ("Mikronutrien", "Catatan unsur hara mikronutrien."),
    "Fertilizer": ("Pupuk", "Catatan jenis pupuk dan sifatnya dari DOC004."),
    "NitrogenFertilizer": ("Pupuk Nitrogen", "Pupuk golongan nitrogen (category = pupuk nitrogen)."),
    "PhosphateFertilizer": ("Pupuk Fosfor", "Pupuk golongan fosfor (category = pupuk fosfor)."),
    "PotassiumFertilizer": ("Pupuk Kalium", "Pupuk golongan kalium (category = pupuk kalium)."),
    "CompoundFertilizer": ("Pupuk Majemuk", "Pupuk majemuk/NPK (category = pupuk majemuk)."),
    "OrganicFertilizer": ("Pupuk Organik", "Pupuk organik dari tabel kompos DOC004."),
    "Compost": ("Kompos", "Catatan kompos (category = kompos)."),
    "Bioactivator": ("Bioaktivator", "Catatan bioaktivator (category = bioaktivator)."),
    "LiquidOrganicFertilizer": (
        "Pupuk Organik Cair",
        "Catatan pupuk organik cair/POC (category = pupuk organik cair).",
    ),
    "FertilizationPractice": ("Praktik Pemupukan", "Catatan praktik pemupukan dari DOC004."),
    "NutrientManagementStrategy": (
        "Strategi Pengelolaan Nutrisi",
        "Strategi pengelolaan nutrisi (category = strategi pengelolaan nutrisi).",
    ),
    "BalancedFertilization": (
        "Pemupukan Berimbang",
        "Langkah dan definisi pemupukan berimbang (category = pemupukan berimbang).",
    ),
    "OrganicFertilizerBenefit": (
        "Manfaat Pupuk Organik",
        "Catatan manfaat pupuk organik (category = manfaat pupuk organik).",
    ),
}

SUBCLASS_AXIOMS: list[tuple[str, str]] = [
    ("Plant", "KnowledgeRecord"),
    ("Disease", "KnowledgeRecord"),
    ("Pathogen", "KnowledgeRecord"),
    ("Symptom", "KnowledgeRecord"),
    ("ControlMeasure", "KnowledgeRecord"),
    ("SourceTable", "KnowledgeRecord"),
    ("SourceTableRow", "KnowledgeRecord"),
    ("Nutrient", "KnowledgeRecord"),
    ("Fertilizer", "KnowledgeRecord"),
    ("FertilizationPractice", "KnowledgeRecord"),
    ("OrganicFertilizerBenefit", "KnowledgeRecord"),
    ("Fungus", "Pathogen"),
    ("Bacterium", "Pathogen"),
    ("Virus", "Pathogen"),
    ("Nematode", "Pathogen"),
    ("Phytoplasma", "Pathogen"),
    ("Oomycete", "Pathogen"),
    ("DiseaseControl", "ControlMeasure"),
    ("ChapterControl", "ControlMeasure"),
    ("CassavaSourceTable", "SourceTable"),
    ("Macronutrient", "Nutrient"),
    ("Micronutrient", "Nutrient"),
    ("NitrogenFertilizer", "Fertilizer"),
    ("PhosphateFertilizer", "Fertilizer"),
    ("PotassiumFertilizer", "Fertilizer"),
    ("CompoundFertilizer", "Fertilizer"),
    ("OrganicFertilizer", "Fertilizer"),
    ("Compost", "OrganicFertilizer"),
    ("Bioactivator", "OrganicFertilizer"),
    ("LiquidOrganicFertilizer", "OrganicFertilizer"),
    ("NutrientManagementStrategy", "FertilizationPractice"),
    ("BalancedFertilization", "FertilizationPractice"),
]

DISJOINT_CLASSES: list[list[str]] = [
    [
        "KnowledgeSource",
        "EvidenceChunk",
        "SourceSection",
        "Plant",
        "Disease",
        "Pathogen",
        "Symptom",
        "ControlMeasure",
        "SourceTable",
        "SourceTableRow",
        "Nutrient",
        "Fertilizer",
        "FertilizationPractice",
        "OrganicFertilizerBenefit",
    ],
    ["Fungus", "Bacterium", "Virus", "Nematode", "Phytoplasma", "Oomycete"],
    ["DiseaseControl", "ChapterControl"],
]

OBJECT_PROPERTIES: dict[str, dict] = {
    "occursIn": {
        "label": "terjadi pada",
        "comment": "Penyakit terjadi pada tanaman inang. Fungsional: satu penyakit "
        "menunjuk tepat satu tanaman (satu baris disease).",
        "domain": "Disease",
        "range": "Plant",
        "inverse": "hasDisease",
        "functional": True,
    },
    "hasDisease": {
        "label": "memiliki penyakit",
        "comment": "Tanaman memiliki penyakit; inverse dari kbr:occursIn.",
        "domain": "Plant",
        "range": "Disease",
        "inverse": "occursIn",
    },
    "causedBy": {
        "label": "disebabkan oleh",
        "comment": "Penyakit disebabkan oleh patogen (relasi banyak-ke-banyak dari "
        "tabel disease_pathogen).",
        "domain": "Disease",
        "range": "Pathogen",
        "inverse": "causes",
    },
    "causes": {
        "label": "menyebabkan",
        "comment": "Patogen menyebabkan penyakit; inverse dari kbr:causedBy.",
        "domain": "Pathogen",
        "range": "Disease",
        "inverse": "causedBy",
    },
    "hasSymptom": {
        "label": "memiliki gejala",
        "comment": "Penyakit memiliki gejala; setiap baris gejala berupa satu kalimat "
        "verbatim.",
        "domain": "Disease",
        "range": "Symptom",
        "inverse": "symptomOf",
    },
    "symptomOf": {
        "label": "gejala dari",
        "comment": "Gejala dari penyakit; inverse dari kbr:hasSymptom.",
        "domain": "Symptom",
        "range": "Disease",
        "inverse": "hasSymptom",
    },
    "observedOn": {
        "label": "diamati pada tanaman",
        "comment": "Gejala diamati pada tanaman tertentu; fungsional (satu baris "
        "gejala menunjuk satu tanaman).",
        "domain": "Symptom",
        "range": "Plant",
        "functional": True,
    },
    "appliesTo": {
        "label": "berlaku untuk penyakit",
        "comment": "Tindakan pengendalian berlaku untuk penyakit tertentu "
        "(scope = disease).",
        "domain": "ControlMeasure",
        "range": "Disease",
        "inverse": "hasControlMeasure",
    },
    "hasControlMeasure": {
        "label": "memiliki tindakan pengendalian",
        "comment": "Penyakit memiliki tindakan pengendalian; inverse dari "
        "kbr:appliesTo.",
        "domain": "Disease",
        "range": "ControlMeasure",
        "inverse": "appliesTo",
    },
    "appliesToPlant": {
        "label": "berlaku untuk tanaman",
        "comment": "Tindakan pengendalian berlaku bagi tanaman (plant_id selalu "
        "terisi, termasuk pengendalian tingkat bab).",
        "domain": "ControlMeasure",
        "range": "Plant",
    },
    "hasEvidence": {
        "label": "memiliki bukti chunk",
        "comment": "Rekaman pengetahuan dirujuk ke chunk teks sumber sebagai bukti "
        "verbatim.",
        "domain": "KnowledgeRecord",
        "range": "EvidenceChunk",
    },
    "hasTaxonEvidence": {
        "label": "memiliki bukti takson",
        "comment": "Bukti kutipan yang menyebut kelompok takson patogen; subproperty "
        "dari kbr:hasEvidence.",
        "domain": "Pathogen",
        "range": "EvidenceChunk",
        "subproperty_of": "hasEvidence",
    },
    "hasSourceDocument": {
        "label": "bersumber dari dokumen",
        "comment": "Rekaman pengetahuan berasal dari dokumen sumber tertentu.",
        "domain": "KnowledgeRecord",
        "range": "KnowledgeSource",
    },
    "locatedInSection": {
        "label": "terletak pada bagian dokumen",
        "comment": "Penyakit terletak pada seksi/subseksi bab tempat namanya "
        "dicetak.",
        "domain": "Disease",
        "range": "SourceSection",
    },
    "containsSection": {
        "label": "memuat bagian",
        "comment": "Relasi hierarki bagian dokumen: bab memuat seksi, seksi memuat "
        "subseksi. Transitif, asimetris, dan irrefleksif.",
        "domain": "SourceSection",
        "range": "SourceSection",
        "inverse": "sectionOf",
        "transitive": True,
        "asymmetric": True,
        "irreflexive": True,
    },
    "sectionOf": {
        "label": "bagian dari",
        "comment": "Kebalikan dari kbr:containsSection.",
        "domain": "SourceSection",
        "range": "SourceSection",
        "inverse": "containsSection",
    },
    "isTableRowOf": {
        "label": "baris dari tabel",
        "comment": "Baris tabel termasuk dalam satu tabel sumber; fungsional.",
        "domain": "SourceTableRow",
        "range": "SourceTable",
        "inverse": "hasTableRow",
        "functional": True,
    },
    "hasTableRow": {
        "label": "memiliki baris tabel",
        "comment": "Tabel sumber memiliki baris; inverse dari kbr:isTableRowOf.",
        "domain": "SourceTable",
        "range": "SourceTableRow",
        "inverse": "isTableRowOf",
    },
    "aboutPlant": {
        "label": "tentang tanaman",
        "comment": "Tabel sumber membahas tanaman tertentu (T5.x -> bab 5 -> ubi "
        "kayu, dari chapter_map.json).",
        "domain": "SourceTable",
        "range": "Plant",
    },
}

PROPERTY_CHAINS: list[tuple[str, list[str]]] = [
    (
        "appliesToPlant",
        ["appliesTo", "occursIn"],
    ),
    (
        "occursIn",
        ["hasSymptom", "observedOn"],
    ),
]

UNION_NUTRITION = ["Nutrient", "Fertilizer", "FertilizationPractice", "OrganicFertilizerBenefit"]

DATA_PROPERTIES: dict[str, dict] = {
    "documentId": {
        "label": "kode dokumen",
        "comment": "Kode dokumen sumber (DOC002, DOC003, DOC004).",
        "domain": ["KnowledgeSource"],
        "range": XSD.string,
    },
    "title": {
        "label": "judul",
        "comment": "Judul dokumen sumber seperti tercetak pada halaman judul/kolofon.",
        "domain": ["KnowledgeSource"],
        "range": XSD.string,
    },
    "author": {
        "label": "penulis",
        "comment": "Nama penulis dokumen sumber (dapat lebih dari satu).",
        "domain": ["KnowledgeSource"],
        "range": XSD.string,
    },
    "publicationYear": {
        "label": "tahun terbit",
        "comment": "Tahun terbit dokumen sumber.",
        "domain": ["KnowledgeSource"],
        "range": XSD.integer,
    },
    "publisher": {
        "label": "penerbit",
        "comment": "Penerbit dokumen sumber.",
        "domain": ["KnowledgeSource"],
        "range": XSD.string,
    },
    "languageCode": {
        "label": "bahasa",
        "comment": "Kode bahasa dokumen sumber.",
        "domain": ["KnowledgeSource"],
        "range": XSD.string,
    },
    "sourceNote": {
        "label": "catatan sumber",
        "comment": "Catatan bibliografis dokumen sumber.",
        "domain": ["KnowledgeSource"],
        "range": XSD.string,
    },
    "plantNameId": {
        "label": "nama tanaman (Indonesia)",
        "comment": "Nama tanaman dalam bahasa Indonesia.",
        "domain": ["Plant"],
        "range": XSD.string,
    },
    "plantNameEn": {
        "label": "nama tanaman (Inggris)",
        "comment": "Nama tanaman dalam bahasa Inggris; hanya bila sumber mencetaknya.",
        "domain": ["Plant"],
        "range": XSD.string,
    },
    "scientificName": {
        "label": "nama ilmiah",
        "comment": "Nama ilmiah verbatim; hanya diisi bila tercetak di sumber.",
        "domain": ["Plant", "Pathogen"],
        "range": XSD.string,
    },
    "scientificNamePage": {
        "label": "halaman nama ilmiah",
        "comment": "Halaman PDF tempat nama ilmiah tanaman tercetak.",
        "domain": ["Plant"],
        "range": XSD.integer,
    },
    "chapterNumber": {
        "label": "nomor bab",
        "comment": "Nomor bab pada dokumen sumber.",
        "domain": ["Plant", "SourceSection"],
        "range": XSD.integer,
    },
    "chapterTitle": {
        "label": "judul bab",
        "comment": "Judul bab verbatim.",
        "domain": ["Plant", "SourceSection"],
        "range": XSD.string,
    },
    "headingLevel": {
        "label": "level heading",
        "comment": "Level heading tempat nama penyakit diambil: section, subsection, "
        "atau table.",
        "domain": ["Disease"],
        "range": XSD.string,
    },
    "section": {
        "label": "seksi",
        "comment": "Teks seksi verbatim tempat penyakit berada.",
        "domain": ["Disease"],
        "range": XSD.string,
    },
    "subsection": {
        "label": "subseksi",
        "comment": "Teks subseksi verbatim tempat penyakit berada (bila ada).",
        "domain": ["Disease"],
        "range": XSD.string,
    },
    "sectionLevel": {
        "label": "tingkat bagian",
        "comment": "Tingkat bagian dokumen: chapter, section, atau subsection.",
        "domain": ["SourceSection"],
        "range": XSD.string,
    },
    "sectionLabel": {
        "label": "nama bagian dokumen",
        "comment": "Teks bagian dokumen persis seperti tercetak.",
        "domain": ["SourceSection"],
        "range": XSD.string,
    },
    "diseaseName": {
        "label": "nama penyakit",
        "comment": "Nama penyakit verbatim; teks bebas pada baris tabel sumber juga "
        "memakai properti ini tanpa dirujuk ke individu penyakit (tidak ditebak).",
        "domain": ["Disease", "SourceTableRow"],
        "range": XSD.string,
    },
    "diseaseNameKey": {
        "label": "kunci nama penyakit",
        "comment": "Slug nama penyakit untuk deteksi duplikat, bukan nama tampilan.",
        "domain": ["Disease"],
        "range": XSD.string,
    },
    "diseaseNameEn": {
        "label": "nama penyakit (Inggris)",
        "comment": "Nama Inggris penyakit verbatim; hanya bila sumber mencetaknya.",
        "domain": ["Disease"],
        "range": XSD.string,
    },
    "hostName": {
        "label": "inang",
        "comment": "Inang seperti tercetak pada sumber (mis. Amorphophallus spp.).",
        "domain": ["Disease"],
        "range": XSD.string,
    },
    "reference": {
        "label": "referensi sumber",
        "comment": "Referensi ilmiah seperti tercetak pada tabel sumber.",
        "domain": ["Disease"],
        "range": XSD.string,
    },
    "sourceType": {
        "label": "jenis sumber baris",
        "comment": "Baris berasal dari tabel atau prosa (table/prose).",
        "domain": ["Disease"],
        "range": XSD.string,
    },
    "verbatimText": {
        "label": "teks verbatim",
        "comment": "Satu atau lebih kalimat utuh dari sumber, tanpa parafrase.",
        "domain": ["KnowledgeRecord"],
        "range": XSD.string,
    },
    "taxonGroupLabel": {
        "label": "kelompok takson",
        "comment": "Kelompok takson seperti tercetak di kolom taxon_group; unknown "
        "bila sumber tidak menyebut.",
        "domain": ["Pathogen"],
        "range": XSD.string,
    },
    "taxonEvidenceQuote": {
        "label": "kutipan bukti takson",
        "comment": "Kutipan verbatim yang menyebut kelompok takson patogen.",
        "domain": ["Pathogen"],
        "range": XSD.string,
    },
    "charStart": {
        "label": "offset karakter mulai",
        "comment": "Offset awal kalimat pada plain_text chunk yang spasinya "
        "dinenormalisasi.",
        "domain": ["Symptom", "ControlMeasure"],
        "range": XSD.integer,
    },
    "charEnd": {
        "label": "offset karakter akhir",
        "comment": "Offset akhir kalimat pada plain_text chunk.",
        "domain": ["Symptom", "ControlMeasure"],
        "range": XSD.integer,
    },
    "controlCategory": {
        "label": "kategori pengendalian",
        "comment": "Kategori pengendalian (mis. fungisida); hanya bila sumber "
        "menyebutnya.",
        "domain": ["ControlMeasure"],
        "range": XSD.string,
    },
    "rowNumber": {
        "label": "nomor baris",
        "comment": "Nomor baris tabel seperti tercetak pada sumber.",
        "domain": ["SourceTableRow"],
        "range": XSD.string,
    },
    "tableTitle": {
        "label": "judul tabel",
        "comment": "Judul tabel seperti tercetak; tidak dinormalkan.",
        "domain": ["SourceTable"],
        "range": XSD.string,
    },
    "pathogenName": {
        "label": "nama patogen (teks tabel)",
        "comment": "Nama patogen pada baris tabel sebagai teks verbatim, termasuk "
        "sitasi dan salah eja sumber.",
        "domain": ["SourceTableRow"],
        "range": XSD.string,
    },
    "symptomText": {
        "label": "teks gejala (tabel)",
        "comment": "Uraian gejala pada baris tabel sebagai teks verbatim.",
        "domain": ["SourceTableRow"],
        "range": XSD.string,
    },
    "rowStatus": {
        "label": "status baris",
        "comment": "Status baris tabel: complete, unnumbered, atau missing_row.",
        "domain": ["SourceTableRow"],
        "range": XSD.string,
    },
    "category": {
        "label": "kategori",
        "comment": "Kelompok kategori seperti tercetak (mis. pupuk nitrogen).",
        "domain": UNION_NUTRITION,
        "range": XSD.string,
    },
    "subject": {
        "label": "subjek",
        "comment": "Nama unsur, pupuk, atau praktik seperti tercetak.",
        "domain": UNION_NUTRITION,
        "range": XSD.string,
    },
    "attribute": {
        "label": "atribut",
        "comment": "Jenis informasi (mis. peran, dosis, manfaat).",
        "domain": UNION_NUTRITION,
        "range": XSD.string,
    },
    "recordValue": {
        "label": "nilai",
        "comment": "Nilai verbatim bila sumber mencetaknya (mis. 100-150 kg ha -1).",
        "domain": UNION_NUTRITION,
        "range": XSD.string,
    },
    "unit": {
        "label": "satuan",
        "comment": "Satuan nilai verbatim bila tercetak.",
        "domain": UNION_NUTRITION,
        "range": XSD.string,
    },
    "pageStart": {
        "label": "halaman mulai",
        "comment": "Nomor halaman PDF awal.",
        "domain": ["KnowledgeRecord"],
        "range": XSD.integer,
    },
    "pageEnd": {
        "label": "halaman akhir",
        "comment": "Nomor halaman PDF akhir.",
        "domain": ["KnowledgeRecord"],
        "range": XSD.integer,
    },
    "sourceBlockId": {
        "label": "id blok sumber",
        "comment": "Id blok sumber (dipisah titik koma bila lebih dari satu).",
        "domain": ["KnowledgeRecord"],
        "range": XSD.string,
    },
    "reviewStatus": {
        "label": "status kurasi",
        "comment": "Status kurasi baris: auto_ok, needs_review, needs_curation, "
        "atau verified.",
        "domain": ["KnowledgeRecord"],
        "range": XSD.string,
    },
    "notes": {
        "label": "catatan",
        "comment": "Catatan kurasi; koreksi salah eja sumber hanya dicatat di sini.",
        "domain": ["KnowledgeRecord"],
        "range": XSD.string,
    },
    "chunkId": {
        "label": "id chunk",
        "comment": "Pengenal chunk teks sumber.",
        "domain": ["EvidenceChunk"],
        "range": XSD.string,
    },
}

ONE_OF_CASSAVA_TABLES = ["T5_1_DAUN", "T5_2_BATANG", "T5_3_AKAR"]


def _add_list(graph: Graph, items: list) -> BNode:
    head = BNode()
    current = head
    for index, item in enumerate(items):
        graph.add((current, RDF.first, item))
        if index == len(items) - 1:
            graph.add((current, RDF.rest, RDF.nil))
        else:
            nxt = BNode()
            graph.add((current, RDF.rest, nxt))
            current = nxt
    return head


def _domain_node(graph: Graph, domain_names: list[str]) -> URIRef | BNode:
    if len(domain_names) == 1:
        return KBR[domain_names[0]]
    node = BNode()
    graph.add((node, RDF.type, OWL.Class))
    graph.add((node, OWL.unionOf, _add_list(graph, [KBR[n] for n in domain_names])))
    return node


def build_tbox(graph: Graph) -> None:
    graph.add((ONTOLOGY_IRI, RDF.type, OWL.Ontology))
    graph.add((ONTOLOGY_IRI, RDFS.label, Literal(ONTOLOGY_LABEL, lang="id")))
    graph.add((ONTOLOGY_IRI, RDFS.comment, Literal(ONTOLOGY_COMMENT, lang="id")))
    graph.add((ONTOLOGY_IRI, OWL.versionInfo, Literal("1.0.0")))

    for name, (label, comment) in CLASSES.items():
        uri = KBR[name]
        graph.add((uri, RDF.type, OWL.Class))
        graph.add((uri, RDFS.label, Literal(label, lang="id")))
        graph.add((uri, RDFS.comment, Literal(comment, lang="id")))

    for sub, sup in SUBCLASS_AXIOMS:
        graph.add((KBR[sub], RDFS.subClassOf, KBR[sup]))

    for members in DISJOINT_CLASSES:
        node = BNode()
        graph.add((node, RDF.type, OWL.AllDisjointClasses))
        graph.add((node, OWL.members, _add_list(graph, [KBR[n] for n in members])))

    for name, spec in OBJECT_PROPERTIES.items():
        uri = KBR[name]
        graph.add((uri, RDF.type, OWL.ObjectProperty))
        graph.add((uri, RDFS.label, Literal(spec["label"], lang="id")))
        graph.add((uri, RDFS.comment, Literal(spec["comment"], lang="id")))
        graph.add((uri, RDFS.domain, _domain_node(graph, spec["domain"])))
        graph.add((uri, RDFS.range, KBR[spec["range"]]))
        if spec.get("inverse"):
            graph.add((uri, OWL.inverseOf, KBR[spec["inverse"]]))
        if spec.get("functional"):
            graph.add((uri, RDF.type, OWL.FunctionalProperty))
        if spec.get("transitive"):
            graph.add((uri, RDF.type, OWL.TransitiveProperty))
        if spec.get("asymmetric"):
            graph.add((uri, RDF.type, OWL.AsymmetricProperty))
        if spec.get("irreflexive"):
            graph.add((uri, RDF.type, OWL.IrreflexiveProperty))
        if spec.get("subproperty_of"):
            graph.add((uri, RDFS.subPropertyOf, KBR[spec["subproperty_of"]]))

    for name, spec in DATA_PROPERTIES.items():
        uri = KBR[name]
        graph.add((uri, RDF.type, OWL.DatatypeProperty))
        graph.add((uri, RDFS.label, Literal(spec["label"], lang="id")))
        graph.add((uri, RDFS.comment, Literal(spec["comment"], lang="id")))
        graph.add((uri, RDFS.domain, _domain_node(graph, spec["domain"])))
        graph.add((uri, RDFS.range, spec["range"]))

    for super_prop, chain in PROPERTY_CHAINS:
        members = [KBR[n] for n in chain]
        graph.add((KBR[super_prop], OWL.propertyChainAxiom, _add_list(graph, members)))

    cassava = BNode()
    graph.add((cassava, RDF.type, OWL.Class))
    graph.add(
        (
            cassava,
            OWL.oneOf,
            _add_list(graph, [KBRD[n] for n in ONE_OF_CASSAVA_TABLES]),
        )
    )
    graph.add((KBR["CassavaSourceTable"], OWL.equivalentClass, cassava))
