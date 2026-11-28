"""TBox ontologi "Penyakit Tanaman Pangan Indonesia".

TBox ini sengaja dipisahkan dari ABox (``build_ontology.py``). Semua kelas
kategori, properti objek, properti data, aksioma disjoint, domain/range,
restriksi, dan aksioma rantai properti didefinisikan di sini. Individu konkret
hanya dibangun di ABox.

Profil OWL 2 DL yang didemonstrasikan:
- S: subClassOf dan subPropertyOf.
- R: propertyChainAxiom memilikiGejala o terdapatPada -> menyerangBagian.
- O: nominal owl:oneOf untuk Serealia, Legum, dan UmbiUmbian.
- I: inverseOf berpasangan untuk properti yang punya kebalikan.
- Q: restriksi kardinalitas kualifikasi pada Penyakit dan Buku.
- D: data property bertipe xsd:integer/xsd:decimal/xsd:string/rdf:langString.
"""

from __future__ import annotations

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS, XSD

PTP = "http://kbr.kelompok5.org/penyakit-tanaman-pangan#"
KBR = Namespace(PTP)
PROV = Namespace("http://www.w3.org/ns/prov#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
DCTERMS = Namespace("http://purl.org/dc/terms/")

ONTOLOGY_IRI = URIRef("http://kbr.kelompok5.org/penyakit-tanaman-pangan")


def _cls(name: str) -> URIRef:
    return URIRef(PTP + name)


# name -> (label, parent, comment)
CLASSES: dict[str, tuple[str, str | None, str]] = {
    "TanamanPangan": (
        "Tanaman Pangan",
        None,
        "Tanaman pangan dalam ruang lingkup knowledge base.",
    ),
    "Serealia": (
        "Serealia",
        "TanamanPangan",
        "Kelompok tanaman pangan serealia dalam ruang lingkup.",
    ),
    "Legum": (
        "Legum",
        "TanamanPangan",
        "Kelompok tanaman pangan legum dalam ruang lingkup.",
    ),
    "UmbiUmbian": (
        "Umbi-Umbian",
        "TanamanPangan",
        "Kelompok tanaman pangan umbi-umbian dalam ruang lingkup.",
    ),
    "Penyakit": (
        "Penyakit",
        None,
        "Penyakit tanaman pangan yang dicatat dalam sumber.",
    ),
    "PenyakitJamur": (
        "Penyakit Jamur",
        "Penyakit",
        "Penyakit yang disebabkan oleh patogen kelompok jamur.",
    ),
    "PenyakitBakteri": (
        "Penyakit Bakteri",
        "Penyakit",
        "Penyakit yang disebabkan oleh patogen kelompok bakteri.",
    ),
    "PenyakitVirus": (
        "Penyakit Virus",
        "Penyakit",
        "Penyakit yang disebabkan oleh patogen kelompok virus.",
    ),
    "PenyakitOomycete": (
        "Penyakit Oomycete",
        "Penyakit",
        "Penyakit yang disebabkan oleh patogen kelompok oomycete.",
    ),
    "PenyakitFitoplasma": (
        "Penyakit Fitoplasma",
        "Penyakit",
        "Penyakit yang disebabkan oleh patogen kelompok fitoplasma.",
    ),
    "Gejala": (
        "Gejala",
        None,
        "Pengamatan gejala pada tanaman atau bagian tanaman.",
    ),
    "GejalaDaun": ("Gejala Daun", "Gejala", "Gejala yang diamati pada daun."),
    "GejalaBatang": ("Gejala Batang", "Gejala", "Gejala yang diamati pada batang."),
    "GejalaAkar": ("Gejala Akar", "Gejala", "Gejala yang diamati pada akar."),
    "GejalaUmbi": ("Gejala Umbi", "Gejala", "Gejala yang diamati pada umbi."),
    "GejalaBuah": ("Gejala Buah", "Gejala", "Gejala yang diamati pada buah."),
    "GejalaBiji": ("Gejala Biji", "Gejala", "Gejala yang diamati pada biji."),
    "GejalaMalai": ("Gejala Malai", "Gejala", "Gejala yang diamati pada malai."),
    "GejalaPolong": ("Gejala Polong", "Gejala", "Gejala yang diamati pada polong."),
    "GejalaPucuk": ("Gejala Pucuk", "Gejala", "Gejala yang diamati pada pucuk atau tunas."),
    "GejalaKanonik": (
        "Gejala Kanonik",
        None,
        "Konsep gejala kanonik yang dipakai untuk normalisasi pengamatan.",
    ),
    "Patogen": (
        "Patogen",
        None,
        "Organisme penyebab penyakit tanaman.",
    ),
    "Jamur": ("Jamur", "Patogen", "Patogen kelompok jamur."),
    "Bakteri": ("Bakteri", "Patogen", "Patogen kelompok bakteri."),
    "Virus": ("Virus", "Patogen", "Patogen kelompok virus."),
    "Oomycete": ("Oomycete", "Patogen", "Patogen kelompok oomycete."),
    "Fitoplasma": ("Fitoplasma", "Patogen", "Patogen kelompok fitoplasma."),
    "BagianTanaman": (
        "Bagian Tanaman",
        None,
        "Bagian tanaman yang dapat menjadi lokasi gejala atau serangan.",
    ),
    "Pengendalian": (
        "Pengendalian",
        None,
        "Tindakan pengendalian penyakit tanaman.",
    ),
    "PengendalianKulturTeknis": (
        "Pengendalian Kultur Teknis",
        "Pengendalian",
        "Pengendalian melalui praktik budidaya.",
    ),
    "PengendalianMekanis": (
        "Pengendalian Mekanis",
        "Pengendalian",
        "Pengendalian melalui tindakan fisik-mekanis.",
    ),
    "PengendalianBiologis": (
        "Pengendalian Biologis",
        "Pengendalian",
        "Pengendalian dengan agens hayati atau biopestisida.",
    ),
    "PengendalianKimiawi": (
        "Pengendalian Kimiawi",
        "Pengendalian",
        "Pengendalian dengan bahan kimia atau pestisida.",
    ),
    "PengendalianFisik": (
        "Pengendalian Fisik",
        "Pengendalian",
        "Pengendalian dengan perlakuan fisik seperti panas atau radiasi.",
    ),
    "PengendalianTerpadu": (
        "Pengendalian Terpadu",
        "Pengendalian",
        "Pengendalian terpadu yang menggabungkan beberapa pendekatan.",
    ),
    "FaktorRisiko": (
        "Faktor Risiko",
        None,
        "Faktor lingkungan, budidaya, atau lahan yang memengaruhi penyakit.",
    ),
    "FaktorLingkungan": (
        "Faktor Lingkungan",
        "FaktorRisiko",
        "Faktor lingkungan abiotik atau iklim.",
    ),
    "Suhu": ("Suhu", "FaktorLingkungan", "Faktor suhu lingkungan."),
    "KelembapanUdara": (
        "Kelembapan Udara",
        "FaktorLingkungan",
        "Faktor kelembapan udara.",
    ),
    "KelembapanTanah": (
        "Kelembapan Tanah",
        "FaktorLingkungan",
        "Faktor kelembapan tanah.",
    ),
    "CurahHujan": (
        "Curah Hujan",
        "FaktorLingkungan",
        "Faktor curah hujan.",
    ),
    "Musim": ("Musim", "FaktorLingkungan", "Faktor musim."),
    "IntensitasCahaya": (
        "Intensitas Cahaya",
        "FaktorLingkungan",
        "Faktor intensitas cahaya.",
    ),
    "KetinggianTempat": (
        "Ketinggian Tempat",
        "FaktorLingkungan",
        "Faktor ketinggian tempat.",
    ),
    "Iklim": ("Iklim", "FaktorLingkungan", "Faktor iklim umum."),
    "ObservasiLingkungan": (
        "Observasi Lingkungan",
        "FaktorLingkungan",
        "Individu observasi kuantitatif atau kualitatif faktor lingkungan.",
    ),
    "FaktorLahan": ("Faktor Lahan", "FaktorRisiko", "Faktor kondisi lahan."),
    "KondisiTanah": ("Kondisi Tanah", "FaktorLahan", "Faktor kondisi tanah."),
    "KondisiDrainase": (
        "Kondisi Drainase",
        "FaktorLahan",
        "Faktor kondisi drainase lahan.",
    ),
    "TeksturTanah": ("Tekstur Tanah", "FaktorLahan", "Faktor tekstur tanah."),
    "Referensi": (
        "Referensi",
        None,
        "Sumber bibliografis yang mendukung data.",
    ),
    "Buku": ("Buku", "Referensi", "Referensi berbentuk buku."),
    "JurnalIlmiah": (
        "Jurnal Ilmiah",
        "Referensi",
        "Referensi berbentuk artikel jurnal.",
    ),
    "PublikasiInstansi": (
        "Publikasi Instansi",
        "Referensi",
        "Referensi terbitan instansi.",
    ),
    "Varietas": (
        "Varietas",
        None,
        "Varietas tanaman pangan yang disebut sumber.",
    ),
    "VarietasUnggul": (
        "Varietas Unggul",
        "Varietas",
        "Kategori varietas unggul.",
    ),
    "FasePertumbuhan": (
        "Fase Pertumbuhan",
        None,
        "Fase pertumbuhan tanaman.",
    ),
    "FaseVegetatif": (
        "Fase Vegetatif",
        "FasePertumbuhan",
        "Fase pertumbuhan vegetatif.",
    ),
    "FaseGeneratif": (
        "Fase Generatif",
        "FasePertumbuhan",
        "Fase pertumbuhan generatif.",
    ),
    "FasePembibitan": (
        "Fase Pembibitan",
        "FasePertumbuhan",
        "Fase pembibitan.",
    ),
    "FaseAnakan": (
        "Fase Anakan",
        "FasePertumbuhan",
        "Fase anakan.",
    ),
    "FasePemasakan": (
        "Fase Pemasakan",
        "FasePertumbuhan",
        "Fase pemasakan.",
    ),
    "FasePanen": (
        "Fase Panen",
        "FasePertumbuhan",
        "Fase menjelang atau saat panen.",
    ),
    "Observasi": (
        "Observasi",
        None,
        "Observasi yang menjadi masukan proses diagnosis.",
    ),
    "Diagnosis": (
        "Diagnosis",
        None,
        "Catatan proses diagnosis tanaman.",
    ),
    "BuktiSumber": (
        "Bukti Sumber",
        None,
        "Node bukti yang menyimpan kutipan dan lokasi sumber.",
    ),
    "BuktiPenyakit": (
        "Bukti Penyakit",
        "BuktiSumber",
        "Bukti untuk pernyataan penyakit.",
    ),
    "BuktiGejala": (
        "Bukti Gejala",
        "BuktiSumber",
        "Bukti untuk pengamatan gejala.",
    ),
    "BuktiPengendalian": (
        "Bukti Pengendalian",
        "BuktiSumber",
        "Bukti untuk tindakan pengendalian.",
    ),
    "BuktiPatogen": (
        "Bukti Patogen",
        "BuktiSumber",
        "Bukti untuk hubungan penyakit-patogen.",
    ),
}

TOP_DOMAINS = [
    "TanamanPangan",
    "Penyakit",
    "Gejala",
    "GejalaKanonik",
    "Patogen",
    "BagianTanaman",
    "Pengendalian",
    "FaktorRisiko",
    "Referensi",
    "Varietas",
    "FasePertumbuhan",
    "Observasi",
    "Diagnosis",
    "BuktiSumber",
]

NOMINAL_CLASSES: dict[str, list[str]] = {
    "Serealia": ["Padi", "Jagung"],
    "Legum": ["Kedelai", "KacangTanah", "KacangHijau"],
    "UmbiUmbian": ["UbiKayu", "UbiJalar"],
}

# Kelompok kategori eksklusif; penyakit sengaja TIDAK dibuat disjoint karena
# satu penyakit dapat memiliki lebih dari satu kelompok patogen di sumber.
ALL_DISJOINT_GROUPS: list[list[str]] = [
    ["Serealia", "Legum", "UmbiUmbian"],
    ["Jamur", "Bakteri", "Virus", "Oomycete", "Fitoplasma"],
    [
        "PengendalianKulturTeknis",
        "PengendalianMekanis",
        "PengendalianBiologis",
        "PengendalianKimiawi",
        "PengendalianFisik",
        "PengendalianTerpadu",
    ],
    ["FaktorLingkungan", "FaktorLahan"],
    ["FaseVegetatif", "FaseGeneratif", "FasePembibitan", "FaseAnakan", "FasePemasakan", "FasePanen"],
    ["Buku", "JurnalIlmiah", "PublikasiInstansi"],
]

OBJECT_PROPERTIES: dict[str, dict] = {
    "menyerangTanaman": {
        "label": "menyerang tanaman",
        "comment": "Penyakit menyerang tanaman pangan inang.",
        "domain": "Penyakit",
        "range": "TanamanPangan",
        "inverse": "diserangPenyakit",
    },
    "diserangPenyakit": {
        "label": "diserang penyakit",
        "comment": "Kebalikan dari menyerangTanaman.",
        "domain": "TanamanPangan",
        "range": "Penyakit",
        "inverse": "menyerangTanaman",
    },
    "memilikiGejala": {
        "label": "memiliki gejala",
        "comment": "Penyakit memiliki pengamatan gejala tertentu.",
        "domain": "Penyakit",
        "range": "Gejala",
        "inverse": "merupakanGejalaDari",
    },
    "merupakanGejalaDari": {
        "label": "merupakan gejala dari",
        "comment": "Kebalikan dari memilikiGejala.",
        "domain": "Gejala",
        "range": "Penyakit",
        "inverse": "memilikiGejala",
    },
    "memilikiGejalaKanonik": {
        "label": "memiliki gejala kanonik",
        "comment": "Pengamatan gejala dipetakan ke konsep gejala kanonik.",
        "domain": "Gejala",
        "range": "GejalaKanonik",
        "inverse": "merupakanKanonikDari",
    },
    "merupakanKanonikDari": {
        "label": "merupakan kanonik dari",
        "comment": "Kebalikan dari memilikiGejalaKanonik.",
        "domain": "GejalaKanonik",
        "range": "Gejala",
        "inverse": "memilikiGejalaKanonik",
    },
    "terdapatPada": {
        "label": "terdapat pada",
        "comment": "Gejala diamati pada bagian tanaman tertentu.",
        "domain": "Gejala",
        "range": "BagianTanaman",
    },
    "bagianDari": {
        "label": "bagian dari",
        "comment": "Bagian tanaman merupakan bagian dari bagian tanaman lain.",
        "domain": "BagianTanaman",
        "range": "BagianTanaman",
        "transitive": True,
    },
    "disebabkanOleh": {
        "label": "disebabkan oleh",
        "comment": "Penyakit disebabkan oleh patogen.",
        "domain": "Penyakit",
        "range": "Patogen",
        "inverse": "menyebabkanPenyakit",
    },
    "menyebabkanPenyakit": {
        "label": "menyebabkan penyakit",
        "comment": "Kebalikan dari disebabkanOleh.",
        "domain": "Patogen",
        "range": "Penyakit",
        "inverse": "disebabkanOleh",
    },
    "menyerangBagian": {
        "label": "menyerang bagian",
        "comment": "Bagian tanaman yang terserang penyakit.",
        "domain": "Penyakit",
        "range": "BagianTanaman",
    },
    "menyerangFase": {
        "label": "menyerang fase",
        "comment": "Fase pertumbuhan tanaman yang diserang penyakit.",
        "domain": "Penyakit",
        "range": "FasePertumbuhan",
    },
    "dikendalikanDengan": {
        "label": "dikendalikan dengan",
        "comment": "Tindakan pengendalian yang direkomendasikan untuk penyakit.",
        "domain": "Penyakit",
        "range": "Pengendalian",
        "inverse": "mengendalikanPenyakit",
    },
    "mengendalikanPenyakit": {
        "label": "mengendalikan penyakit",
        "comment": "Kebalikan dari dikendalikanDengan.",
        "domain": "Pengendalian",
        "range": "Penyakit",
        "inverse": "dikendalikanDengan",
    },
    "pengendalianUmum": {
        "label": "pengendalian umum",
        "comment": "Pengendalian umum pada tingkat tanaman.",
        "domain": "TanamanPangan",
        "range": "Pengendalian",
    },
    "diikutiOleh": {
        "label": "diikuti oleh",
        "comment": "Fase pertumbuhan diikuti oleh fase pertumbuhan berikutnya.",
        "domain": "FasePertumbuhan",
        "range": "FasePertumbuhan",
        "inverse": "didahuluiOleh",
    },
    "didahuluiOleh": {
        "label": "didahului oleh",
        "comment": "Kebalikan dari diikutiOleh.",
        "domain": "FasePertumbuhan",
        "range": "FasePertumbuhan",
        "inverse": "diikutiOleh",
    },
    "berkaitanPengendalian": {
        "label": "berkaitan pengendalian",
        "comment": "Superproperti yang menghubungkan entitas dengan tindakan pengendalian.",
        "range": "Pengendalian",
    },
    "dipengaruhiOleh": {
        "label": "dipengaruhi oleh",
        "comment": "Penyakit dipengaruhi oleh faktor risiko atau observasi lingkungan.",
        "domain": "Penyakit",
        "range": "FaktorRisiko",
        "inverse": "memengaruhiPenyakit",
    },
    "memengaruhiPenyakit": {
        "label": "memengaruhi penyakit",
        "comment": "Kebalikan dari dipengaruhiOleh.",
        "domain": "FaktorRisiko",
        "range": "Penyakit",
        "inverse": "dipengaruhiOleh",
    },
    "memilikiReferensi": {
        "label": "memiliki referensi",
        "comment": "Penyakit didukung oleh referensi sumber.",
        "domain": "Penyakit",
        "range": "Referensi",
        "inverse": "dijelaskanDalam",
    },
    "dijelaskanDalam": {
        "label": "dijelaskan dalam",
        "comment": "Kebalikan dari memilikiReferensi.",
        "domain": "Referensi",
        "range": "Penyakit",
        "inverse": "memilikiReferensi",
    },
    "memilikiVarietas": {
        "label": "memiliki varietas",
        "comment": "Tanaman pangan memiliki varietas tertentu.",
        "domain": "TanamanPangan",
        "range": "Varietas",
        "inverse": "merupakanVarietasDari",
    },
    "merupakanVarietasDari": {
        "label": "merupakan varietas dari",
        "comment": "Kebalikan dari memilikiVarietas.",
        "domain": "Varietas",
        "range": "TanamanPangan",
        "inverse": "memilikiVarietas",
    },
    "tahanTerhadap": {
        "label": "tahan terhadap",
        "comment": "Varietas dinyatakan tahan atau toleran terhadap penyakit.",
        "domain": "Varietas",
        "range": "Penyakit",
    },
    "rentanTerhadap": {
        "label": "rentan terhadap",
        "comment": "Varietas dinyatakan rentan atau peka terhadap penyakit.",
        "domain": "Varietas",
        "range": "Penyakit",
    },
    "didukungOleh": {
        "label": "didukung oleh",
        "comment": "Entitas didukung oleh node bukti sumber.",
        "range": "BuktiSumber",
    },
    "memilikiTanaman": {
        "label": "memiliki tanaman",
        "comment": "Diagnosis memiliki tanaman yang diamati.",
        "domain": "Diagnosis",
        "range": "TanamanPangan",
    },
    "memilikiObservasi": {
        "label": "memiliki observasi",
        "comment": "Diagnosis memiliki observasi gejala atau faktor lingkungan.",
        "domain": "Diagnosis",
    },
    "menghasilkanPenyakit": {
        "label": "menghasilkan penyakit",
        "comment": "Diagnosis atau kandidat diagnosis menghasilkan penyakit.",
        "domain": "Diagnosis",
        "range": "Penyakit",
    },
    "merekomendasikanPengendalian": {
        "label": "merekomendasikan pengendalian",
        "comment": "Diagnosis merekomendasikan tindakan pengendalian.",
        "domain": "Diagnosis",
        "range": "Pengendalian",
    },
    "kandidatKuat": {
        "label": "kandidat kuat",
        "comment": "Diagnosis memiliki kandidat penyakit yang didukung minimal dua gejala kanonik berbeda.",
        "domain": "Diagnosis",
        "range": "Penyakit",
    },
    "merekomendasikanVarietas": {
        "label": "merekomendasikan varietas",
        "comment": "Diagnosis merekomendasikan varietas yang tahan terhadap penyakit kandidat.",
        "domain": "Diagnosis",
        "range": "Varietas",
    },
    "menandaiRisikoLingkungan": {
        "label": "menandai risiko lingkungan",
        "comment": "Diagnosis menandai penyakit yang risikonya meningkat oleh kondisi lingkungan.",
        "domain": "Diagnosis",
        "range": "Penyakit",
    },
}

SUBPROPERTY_OF: list[tuple[str, str]] = [
    ("dikendalikanDengan", "berkaitanPengendalian"),
    ("pengendalianUmum", "berkaitanPengendalian"),
    ("merekomendasikanPengendalian", "berkaitanPengendalian"),
]

PROPERTY_CHAINS: list[tuple[list[str], str]] = [
    (["memilikiGejala", "terdapatPada"], "menyerangBagian"),
]

EXTERNAL_OBJECT_PROPERTIES: dict[str, dict] = {
    str(PROV.wasDerivedFrom): {
        "label": "was derived from",
        "comment": "Entitas diturunkan dari sumber atau entitas lain.",
    },
}

EQUIVALENT_CLASSES: list[tuple[str, str]] = [
    ("PenyakitJamur", "Jamur"),
    ("PenyakitBakteri", "Bakteri"),
    ("PenyakitVirus", "Virus"),
    ("PenyakitOomycete", "Oomycete"),
    ("PenyakitFitoplasma", "Fitoplasma"),
]

RESTRICTIONS: list[tuple[str, str, str, str]] = [
    ("Penyakit", "menyerangTanaman", "TanamanPangan", "some"),
    ("Penyakit", "memilikiGejala", "Gejala", "some"),
    ("Penyakit", "disebabkanOleh", "Patogen", "only"),
    ("Penyakit", "memilikiReferensi", "Referensi", "min1"),
    ("BuktiSumber", "prov:wasDerivedFrom", "Referensi", "some"),
]

DATATYPE_RESTRICTIONS: list[tuple[str, str, str, str]] = [
    ("Buku", "tahunTerbit", "integer", "exactly1"),
]

DATA_PROPERTIES: dict[str, dict] = {
    "namaIlmiah": {
        "label": "nama ilmiah",
        "comment": "Nama ilmiah tanaman pangan.",
        "domain": "TanamanPangan",
        "range": XSD.string,
    },
    "deskripsiTanaman": {
        "label": "deskripsi tanaman",
        "comment": "Deskripsi tanaman pangan menurut sumber.",
        "domain": "TanamanPangan",
        "range": RDF.PlainLiteral,
    },
    "namaIlmiahPatogen": {
        "label": "nama ilmiah patogen",
        "comment": "Nama ilmiah patogen penyebab penyakit.",
        "domain": "Patogen",
        "range": XSD.string,
    },
    "deskripsiPenyakit": {
        "label": "deskripsi penyakit",
        "comment": "Penjelasan penyakit menurut sumber.",
        "domain": "Penyakit",
        "range": RDF.PlainLiteral,
    },
    "namaInggrisPenyakit": {
        "label": "nama Inggris penyakit",
        "comment": "Nama Inggris penyakit bila tersedia di sumber.",
        "domain": "Penyakit",
        "range": XSD.string,
    },
    "deskripsiGejala": {
        "label": "deskripsi gejala",
        "comment": "Deskripsi pengamatan gejala menurut sumber.",
        "domain": "Gejala",
        "range": RDF.PlainLiteral,
    },
    "kodeGejala": {
        "label": "kode gejala",
        "comment": "Kode stabil konsep gejala kanonik untuk pembeda pada SWRL.",
        "domain": "GejalaKanonik",
        "range": XSD.string,
    },
    "urutanFase": {
        "label": "urutan fase",
        "comment": "Urutan fase pertumbuhan dalam siklus tanaman.",
        "domain": "FasePertumbuhan",
        "range": XSD.integer,
    },
    "mulaiFase": {
        "label": "mulai fase",
        "comment": "Nilai awal fase pertumbuhan pada satuan sumber.",
        "domain": "FasePertumbuhan",
        "range": XSD.decimal,
    },
    "selesaiFase": {
        "label": "selesai fase",
        "comment": "Nilai akhir fase pertumbuhan pada satuan sumber.",
        "domain": "FasePertumbuhan",
        "range": XSD.decimal,
    },
    "satuanFase": {
        "label": "satuan fase",
        "comment": "Satuan nilai awal dan akhir fase pertumbuhan.",
        "domain": "FasePertumbuhan",
        "range": XSD.string,
    },
    "deskripsiPengendalian": {
        "label": "deskripsi pengendalian",
        "comment": "Deskripsi tindakan pengendalian menurut sumber.",
        "domain": "Pengendalian",
        "range": RDF.PlainLiteral,
    },
    "tingkatKeparahan": {
        "label": "tingkat keparahan",
        "comment": "Kategori keparahan penyakit bila tersedia di sumber.",
        "domain": "Penyakit",
        "range": RDF.PlainLiteral,
    },
    "judulReferensi": {
        "label": "judul referensi",
        "comment": "Judul sumber referensi.",
        "domain": "Referensi",
        "range": RDF.PlainLiteral,
    },
    "tahunTerbit": {
        "label": "tahun terbit",
        "comment": "Tahun publikasi referensi.",
        "domain": "Referensi",
        "range": XSD.integer,
    },
    "namaPenulis": {
        "label": "nama penulis",
        "comment": "Nama penulis referensi.",
        "domain": "Referensi",
        "range": XSD.string,
    },
    "urlReferensi": {
        "label": "url referensi",
        "comment": "Tautan sumber referensi bila tersedia.",
        "domain": "Referensi",
        "range": XSD.anyURI,
    },
    "namaPengendalian": {
        "label": "nama pengendalian",
        "comment": "Nama tindakan pengendalian kanonik.",
        "domain": "Pengendalian",
        "range": RDF.PlainLiteral,
    },
    "nilaiMin": {
        "label": "nilai minimum",
        "comment": "Batas bawah nilai observasi lingkungan.",
        "domain": "ObservasiLingkungan",
        "range": XSD.decimal,
    },
    "nilaiMaks": {
        "label": "nilai maksimum",
        "comment": "Batas atas nilai observasi lingkungan.",
        "domain": "ObservasiLingkungan",
        "range": XSD.decimal,
    },
    "nilaiTunggal": {
        "label": "nilai tunggal",
        "comment": "Nilai tunggal observasi lingkungan.",
        "domain": "ObservasiLingkungan",
        "range": XSD.decimal,
    },
    "operatorNilai": {
        "label": "operator nilai",
        "comment": "Operator pembanding pada observasi lingkungan.",
        "domain": "ObservasiLingkungan",
        "range": XSD.string,
    },
    "satuan": {
        "label": "satuan",
        "comment": "Satuan nilai observasi lingkungan.",
        "domain": "ObservasiLingkungan",
        "range": XSD.string,
    },
    "kondisi": {
        "label": "kondisi",
        "comment": "Kondisi lingkungan kualitatif yang dinyatakan sumber.",
        "domain": "ObservasiLingkungan",
        "range": RDF.PlainLiteral,
    },
    "klasifikasiTurunan": {
        "label": "klasifikasi turunan",
        "comment": "Klasifikasi turunan eksplisit, bukan fakta tambahan.",
        "domain": "ObservasiLingkungan",
        "range": RDF.PlainLiteral,
    },
    "kutipanSumber": {
        "label": "kutipan sumber",
        "comment": "Kutipan verbatim dari sumber.",
        "domain": "BuktiSumber",
        "range": RDF.PlainLiteral,
    },
    "kutipanNormalisasi": {
        "label": "kutipan normalisasi",
        "comment": "Kutipan sumber setelah normalisasi ringan.",
        "domain": "BuktiSumber",
        "range": RDF.PlainLiteral,
    },
    "dokumenSumber": {
        "label": "dokumen sumber",
        "comment": "Kode dokumen sumber.",
        "domain": "BuktiSumber",
        "range": XSD.string,
    },
    "identifierSumber": {
        "label": "identifier sumber",
        "comment": "Identifier baris atau entitas pada sumber.",
        "range": XSD.string,
    },
    "idChunkSumber": {
        "label": "id chunk sumber",
        "comment": "Identifier chunk sumber.",
        "domain": "BuktiSumber",
        "range": XSD.string,
    },
    "idBlokSumber": {
        "label": "id blok sumber",
        "comment": "Identifier blok sumber.",
        "domain": "BuktiSumber",
        "range": XSD.string,
    },
    "halamanSumber": {
        "label": "halaman sumber",
        "comment": "Halaman sumber.",
        "domain": "BuktiSumber",
        "range": XSD.string,
    },
    "catatanKualitas": {
        "label": "catatan kualitas",
        "comment": "Catatan kualitas atau keterbatasan kutipan sumber.",
        "domain": "BuktiSumber",
        "range": RDF.PlainLiteral,
    },
}


MD_OBJECT_PROPERTIES: dict[str, dict] = {
    "memilikiKondisiTumbuh": {
        "label": "memiliki kondisi tumbuh",
        "comment": "Tanaman pangan memiliki kondisi lingkungan tumbuh yang terkontrol.",
        "domain": "TanamanPangan",
        "range": "FaktorRisiko",
    },
    "menggambarkanKondisi": {
        "label": "menggambarkan kondisi",
        "comment": "Observasi lingkungan menggambarkan kondisi lingkungan yang terkontrol.",
        "domain": "ObservasiLingkungan",
        "range": "FaktorRisiko",
    },
    "memilikiFasePertumbuhan": {
        "label": "memiliki fase pertumbuhan",
        "comment": "Tanaman pangan memiliki tahapan fase pertumbuhan.",
        "domain": "TanamanPangan",
        "range": "FasePertumbuhan",
    },
}


def _restriction(graph: Graph, prop: URIRef, target: URIRef, quant: str) -> URIRef:
    node = BNode()
    graph.add((node, RDF.type, OWL.Restriction))
    graph.add((node, OWL.onProperty, prop))
    graph.add((node, OWL.someValuesFrom if quant == "some" else OWL.allValuesFrom, target))
    return node


def _min1_restriction(graph: Graph, prop: URIRef, target: URIRef) -> URIRef:
    node = BNode()
    graph.add((node, RDF.type, OWL.Restriction))
    graph.add((node, OWL.onProperty, prop))
    graph.add((node, OWL.minCardinality, Literal(1, datatype=XSD.nonNegativeInteger)))
    graph.add((node, OWL.onClass, target))
    return node


def _exactly1_datatype_restriction(graph: Graph, prop: URIRef, datatype: URIRef) -> URIRef:
    node = BNode()
    graph.add((node, RDF.type, OWL.Restriction))
    graph.add((node, OWL.onProperty, prop))
    graph.add((node, OWL.cardinality, Literal(1, datatype=XSD.nonNegativeInteger)))
    graph.add((node, OWL.onDatatype, datatype))
    return node


def _one_of(graph: Graph, members: list[URIRef]) -> URIRef:
    node = BNode()
    graph.add((node, RDF.type, OWL.Class))
    coll = BNode()
    Collection(graph, coll, members)
    graph.add((node, OWL.oneOf, coll))
    return node


def _intersection(graph: Graph, parts: list[URIRef]) -> URIRef:
    node = BNode()
    graph.add((node, RDF.type, OWL.Class))
    coll = BNode()
    Collection(graph, coll, parts)
    graph.add((node, OWL.intersectionOf, coll))
    return node


def _all_disjoint(graph: Graph, names: list[str]) -> None:
    node = BNode()
    graph.add((node, RDF.type, OWL.AllDisjointClasses))
    coll = BNode()
    Collection(graph, coll, [_cls(name) for name in names])
    graph.add((node, OWL.members, coll))


def _property_spec(spec: dict) -> dict:
    result = dict(spec)
    prop = result.get("subproperty_of")
    if prop:
        result["domain"] = None
    return result


def _declare_property(graph: Graph, uri: URIRef, kind: URIRef, spec: dict) -> None:
    graph.add((uri, RDF.type, kind))
    graph.add((uri, RDFS.label, Literal(spec["label"], lang="id")))
    graph.add((uri, SKOS.prefLabel, Literal(spec["label"], lang="id")))
    graph.add((uri, RDFS.comment, Literal(spec["comment"], lang="id")))
    if spec.get("domain"):
        graph.add((uri, RDFS.domain, _cls(spec["domain"])))
    if spec.get("range"):
        rng = spec["range"]
        graph.add((uri, RDFS.range, rng if isinstance(rng, URIRef) else _cls(rng)))
    if spec.get("functional"):
        graph.add((uri, RDF.type, OWL.FunctionalProperty))
    if spec.get("transitive"):
        graph.add((uri, RDF.type, OWL.TransitiveProperty))
    if spec.get("inverse"):
        graph.add((uri, OWL.inverseOf, _cls(spec["inverse"])))


def build_md_tbox(graph: Graph) -> None:
    """Tambahkan properti khusus enrichment MD bila belum ada di TBox inti."""
    for name, spec in MD_OBJECT_PROPERTIES.items():
        uri = _cls(name)
        if (uri, RDF.type, OWL.ObjectProperty) in graph:
            continue
        _declare_property(graph, uri, OWL.ObjectProperty, spec)


def build_tbox(graph: Graph) -> None:
    graph.add((ONTOLOGY_IRI, RDF.type, OWL.Ontology))
    graph.add(
        (
            ONTOLOGY_IRI,
            RDFS.label,
            Literal("Ontologi Penyakit Tanaman Pangan Indonesia", lang="id"),
        )
    )
    graph.add(
        (
            ONTOLOGY_IRI,
            RDFS.comment,
            Literal(
                "Knowledge base penyakit tanaman pangan Indonesia untuk tujuh "
                "tanaman: padi, jagung, kedelai, kacang hijau, kacang tanah, "
                "ubi kayu, dan ubi jalar.",
                lang="id",
            ),
        )
    )

    for name, (label, _parent, comment) in CLASSES.items():
        uri = _cls(name)
        graph.add((uri, RDF.type, OWL.Class))
        graph.add((uri, RDFS.label, Literal(label, lang="id")))
        graph.add((uri, SKOS.prefLabel, Literal(label, lang="id")))
        graph.add((uri, RDFS.comment, Literal(comment, lang="id")))

    for name, (_label, parent, _comment) in CLASSES.items():
        if parent:
            graph.add((_cls(name), RDFS.subClassOf, _cls(parent)))

    for i, left in enumerate(TOP_DOMAINS):
        for right in TOP_DOMAINS[i + 1 :]:
            graph.add((_cls(left), OWL.disjointWith, _cls(right)))
            graph.add((_cls(right), OWL.disjointWith, _cls(left)))

    for group in ALL_DISJOINT_GROUPS:
        _all_disjoint(graph, group)

    for cls_name, individual_names in NOMINAL_CLASSES.items():
        members = [_cls(n) for n in individual_names]
        graph.add((_cls(cls_name), OWL.equivalentClass, _one_of(graph, members)))

    for penyakit_cls, patogen_cls in EQUIVALENT_CLASSES:
        restr = _restriction(graph, _cls("disebabkanOleh"), _cls(patogen_cls), "some")
        intersection = _intersection(graph, [_cls("Penyakit"), restr])
        graph.add((_cls(penyakit_cls), OWL.equivalentClass, intersection))

    for sub_cls, prop, target, quant in RESTRICTIONS:
        if prop == "prov:wasDerivedFrom":
            prop_uri = PROV.wasDerivedFrom
        else:
            prop_uri = _cls(prop) if ":" not in prop else URIRef(prop)
        target_uri = _cls(target)
        if quant == "min1":
            restr = _min1_restriction(graph, prop_uri, target_uri)
        else:
            restr = _restriction(graph, prop_uri, target_uri, quant)
        graph.add((_cls(sub_cls), RDFS.subClassOf, restr))

    xsd_types = {"integer": XSD.integer, "string": XSD.string}
    for cls_name, prop, type_name, _quant in DATATYPE_RESTRICTIONS:
        restr = _exactly1_datatype_restriction(graph, _cls(prop), xsd_types[type_name])
        graph.add((_cls(cls_name), RDFS.subClassOf, restr))

    for name, spec in OBJECT_PROPERTIES.items():
        _declare_property(graph, _cls(name), OWL.ObjectProperty, _property_spec(spec))

    for uri_text, spec in EXTERNAL_OBJECT_PROPERTIES.items():
        _declare_property(graph, URIRef(uri_text), OWL.ObjectProperty, spec)

    for sub_prop, super_prop in SUBPROPERTY_OF:
        graph.add((_cls(sub_prop), RDFS.subPropertyOf, _cls(super_prop)))

    for chain, super_prop in PROPERTY_CHAINS:
        chain_node = BNode()
        Collection(graph, chain_node, [_cls(p) for p in chain])
        graph.add((_cls(super_prop), OWL.propertyChainAxiom, chain_node))

    for name, spec in DATA_PROPERTIES.items():
        spec = dict(spec)
        spec["functional"] = bool(spec.get("functional", False))
        _declare_property(graph, _cls(name), OWL.DatatypeProperty, spec)
