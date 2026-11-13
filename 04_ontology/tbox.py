"""TBox ontologi "Penyakit Tanaman Pangan Indonesia" (OWL 2 SROIQ(D)).

Profil OWL 2 DL yang didemonstrasikan:
- S: rdfs:subClassOf; rdfs:subPropertyOf.
- R: owl:propertyChainAxiom.
- O: nominal owl:oneOf untuk Serealia, Legum, UmbiUmbian.
- I: 6 pasang owl:inverseOf (12 triple).
- Q: kualifikasi cardinality (min 1 Referensi; exactly 1 tahunTerbit).
- D: data property xsd:integer/xsd:decimal; teks memakai rdf:langString (@id).

Annotation memakai rdfs:label, rdfs:comment, skos:prefLabel, skos:altLabel,
skos:definition, dcterms:identifier, dcterms:source, dan prov:wasDerivedFrom.
"""

from __future__ import annotations

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, SKOS, XSD

PTP = "http://kbr.kelompok5.org/penyakit-tanaman-pangan#"
KBR = Namespace(PTP)
PROV = Namespace("http://www.w3.org/ns/prov#")
SWRL = Namespace("http://www.w3.org/2003/11/swrl#")


def _cls(name: str) -> URIRef:
    return URIRef(PTP + name)


ONTOLOGY_IRI = URIRef("http://kbr.kelompok5.org/penyakit-tanaman-pangan")
ONTOLOGY_VERSION = "2.0.0"

# ------------------------------------------------------------------ kelas
CLASS_LABELS: dict[str, str] = {
    "TanamanPangan": "Tanaman Pangan",
    "Serealia": "Serealia",
    "Legum": "Legum / Kacang-kacangan",
    "UmbiUmbian": "Umbi-umbian",
    "Penyakit": "Penyakit",
    "PenyakitJamur": "Penyakit Jamur",
    "PenyakitBakteri": "Penyakit Bakteri",
    "PenyakitVirus": "Penyakit Virus",
    "PenyakitNematoda": "Penyakit Nematoda",
    "PenyakitOomycete": "Penyakit Oomycete",
    "PenyakitFitoplasma": "Penyakit Fitoplasma",
    "PenyakitLainnya": "Penyakit Lainnya",
    "PenyakitRisiko": "Penyakit Risiko",
    "PenyakitRisikoSuhuTinggi": "Penyakit Risiko Suhu Tinggi",
    "PenyakitRisikoKelembapanTinggi": "Penyakit Risiko Kelembapan Tinggi",
    "PenyakitRisikoMusimHujan": "Penyakit Risiko Musim Hujan",
    "Gejala": "Gejala",
    "GejalaDaun": "Gejala Daun",
    "GejalaBatang": "Gejala Batang",
    "GejalaAkar": "Gejala Akar",
    "GejalaUmbi": "Gejala Umbi",
    "GejalaBuah": "Gejala Buah",
    "GejalaBiji": "Gejala Biji",
    "GejalaBunga": "Gejala Bunga",
    "GejalaMalai": "Gejala Malai",
    "GejalaPelepah": "Gejala Pelepah",
    "GejalaPolong": "Gejala Polong",
    "GejalaPucuk": "Gejala Pucuk",
    "GejalaTongkol": "Gejala Tongkol",
    "GejalaLeherMalai": "Gejala Leher Malai",
    "Patogen": "Patogen",
    "Jamur": "Jamur",
    "Bakteri": "Bakteri",
    "Virus": "Virus",
    "OrganismeLain": "Organisme Lain",
    "Nematoda": "Nematoda",
    "Oomycete": "Oomycete",
    "Fitoplasma": "Fitoplasma",
    "BagianTanaman": "Bagian Tanaman",
    "Pengendalian": "Pengendalian",
    "PengendalianKulturTeknis": "Pengendalian Kultur Teknis",
    "PengendalianMekanis": "Pengendalian Mekanis",
    "PengendalianBiologis": "Pengendalian Biologis",
    "PengendalianKimiawi": "Pengendalian Kimiawi",
    "PengendalianFisik": "Pengendalian Fisik",
    "PengendalianTerpadu": "Pengendalian Terpadu",
    "FaktorRisiko": "Faktor Risiko",
    "FaktorLingkungan": "Faktor Lingkungan",
    "Suhu": "Suhu",
    "Kelembapan": "Kelembapan",
    "KelembapanUdara": "Kelembapan Udara",
    "KelembapanTanah": "Kelembapan Tanah",
    "CurahHujan": "Curah Hujan",
    "Musim": "Musim",
    "MusimHujan": "Musim Hujan",
    "MusimKemarau": "Musim Kemarau",
    "Cahaya": "Cahaya",
    "Angin": "Angin",
    "DerajatKeasamanTanah": "Derajat Keasaman Tanah (pH)",
    "FaktorBudidaya": "Faktor Budidaya",
    "SanitasiLahanBuruk": "Sanitasi Lahan Buruk",
    "DrainaseBuruk": "Drainase Buruk",
    "PenggunaanBenihTerinfeksi": "Penggunaan Benih Terinfeksi",
    "JarakTanamRapat": "Jarak Tanam Rapat",
    "PemupukanTidakSeimbang": "Pemupukan Tidak Seimbang",
    "RotasiTanamanTidakDilakukan": "Rotasi Tanaman Tidak Dilakukan",
    "PengolahanTanahBuruk": "Pengolahan Tanah Buruk",
    "FaktorLahan": "Faktor Lahan",
    "KondisiTanah": "Kondisi Tanah",
    "KondisiDrainase": "Kondisi Drainase",
    "KondisiUnsurHara": "Kondisi Unsur Hara",
    "Referensi": "Referensi",
    "Buku": "Buku",
    "JurnalIlmiah": "Jurnal Ilmiah",
    "ArtikelIlmiah": "Artikel Ilmiah",
    "PublikasiInstansi": "Publikasi Instansi",
    "Varietas": "Varietas",
    "VarietasUnggul": "Varietas Unggul",
    "VarietasLokal": "Varietas Lokal",
    "FasePertumbuhan": "Fase Pertumbuhan",
}

CLASS_COMMENTS: dict[str, str] = {
    "TanamanPangan": "Tanaman pangan yang menjadi inang penyakit dalam cakupan ontologi.",
    "Serealia": "Kelompok tanaman pangan biji-bijian (padi dan jagung).",
    "Legum": "Kelompok tanaman kacang-kacangan (kedelai, kacang tanah, kacang hijau).",
    "UmbiUmbian": "Kelompok tanaman pangan umbi-umbian (ubi jalar dan ubi kayu).",
    "Penyakit": "Penyakit tanaman pangan yang dideskripsikan pada sumber.",
    "PenyakitJamur": "Penyakit yang disebabkan oleh jamur (inferensi reasoner).",
    "PenyakitBakteri": "Penyakit yang disebabkan oleh bakteri (inferensi reasoner).",
    "PenyakitVirus": "Penyakit yang disebabkan oleh virus (inferensi reasoner).",
    "PenyakitNematoda": "Penyakit yang disebabkan oleh nematoda (inferensi reasoner).",
    "PenyakitOomycete": "Penyakit yang disebabkan oleh oomycete (inferensi reasoner).",
    "PenyakitFitoplasma": "Penyakit yang disebabkan oleh fitoplasma (inferensi reasoner).",
    "PenyakitLainnya": "Penyakit dengan patogen yang belum terklasifikasi.",
    "PenyakitRisiko": "Kelas turunan penyakit yang memiliki faktor risiko lingkungan (inferensi SWRL).",
    "PenyakitRisikoSuhuTinggi": "Penyakit yang dipengaruhi faktor lingkungan bersuhu tinggi (inferensi SWRL).",
    "PenyakitRisikoKelembapanTinggi": "Penyakit yang dipengaruhi faktor kelembapan tinggi (inferensi SWRL).",
    "PenyakitRisikoMusimHujan": "Penyakit yang dipengaruhi musim hujan (inferensi SWRL).",
    "Gejala": "Gejala serangan penyakit pada tanaman.",
    "Patogen": "Organisme penyebab penyakit.",
    "OrganismeLain": "Patogen selain jamur, bakteri, dan virus.",
    "BagianTanaman": "Bagian tanaman tempat gejala atau penyakit muncul.",
    "Pengendalian": "Metode pengendalian penyakit.",
    "FaktorRisiko": "Faktor lingkungan, budidaya, atau lahan yang memengaruhi penyakit.",
    "FaktorLingkungan": "Kondisi iklim dan lingkungan tumbuh.",
    "FaktorBudidaya": "Praktik budidaya yang meningkatkan risiko penyakit.",
    "FaktorLahan": "Kondisi lahan dan tanah yang meningkatkan risiko penyakit.",
    "Referensi": "Sumber pustaka yang mendukung pengetahuan.",
    "Varietas": "Varietas tanaman pangan.",
    "FasePertumbuhan": "Fase pertumbuhan tanaman yang rentan terserang penyakit.",
}

TOP_CLASSES = [
    "TanamanPangan",
    "Penyakit",
    "Gejala",
    "Patogen",
    "BagianTanaman",
    "Pengendalian",
    "FaktorRisiko",
    "Referensi",
    "Varietas",
    "FasePertumbuhan",
]

SUBCLASSES: list[tuple[str, str]] = [
    ("Serealia", "TanamanPangan"),
    ("Legum", "TanamanPangan"),
    ("UmbiUmbian", "TanamanPangan"),
    ("PenyakitJamur", "Penyakit"),
    ("PenyakitBakteri", "Penyakit"),
    ("PenyakitVirus", "Penyakit"),
    ("PenyakitNematoda", "Penyakit"),
    ("PenyakitOomycete", "Penyakit"),
    ("PenyakitFitoplasma", "Penyakit"),
    ("PenyakitLainnya", "Penyakit"),
    ("PenyakitRisiko", "Penyakit"),
    ("PenyakitRisikoSuhuTinggi", "PenyakitRisiko"),
    ("PenyakitRisikoKelembapanTinggi", "PenyakitRisiko"),
    ("PenyakitRisikoMusimHujan", "PenyakitRisiko"),
    ("GejalaDaun", "Gejala"),
    ("GejalaBatang", "Gejala"),
    ("GejalaAkar", "Gejala"),
    ("GejalaUmbi", "Gejala"),
    ("GejalaBuah", "Gejala"),
    ("GejalaBiji", "Gejala"),
    ("GejalaBunga", "Gejala"),
    ("GejalaMalai", "Gejala"),
    ("GejalaPelepah", "Gejala"),
    ("GejalaPolong", "Gejala"),
    ("GejalaPucuk", "Gejala"),
    ("GejalaTongkol", "Gejala"),
    ("GejalaLeherMalai", "Gejala"),
    ("Jamur", "Patogen"),
    ("Bakteri", "Patogen"),
    ("Virus", "Patogen"),
    ("OrganismeLain", "Patogen"),
    ("Nematoda", "OrganismeLain"),
    ("Oomycete", "OrganismeLain"),
    ("Fitoplasma", "OrganismeLain"),
    ("PengendalianKulturTeknis", "Pengendalian"),
    ("PengendalianMekanis", "Pengendalian"),
    ("PengendalianBiologis", "Pengendalian"),
    ("PengendalianKimiawi", "Pengendalian"),
    ("PengendalianFisik", "Pengendalian"),
    ("PengendalianTerpadu", "Pengendalian"),
    ("FaktorLingkungan", "FaktorRisiko"),
    ("Suhu", "FaktorLingkungan"),
    ("Kelembapan", "FaktorLingkungan"),
    ("KelembapanUdara", "Kelembapan"),
    ("KelembapanTanah", "Kelembapan"),
    ("CurahHujan", "FaktorLingkungan"),
    ("Musim", "FaktorLingkungan"),
    ("MusimHujan", "Musim"),
    ("MusimKemarau", "Musim"),
    ("Cahaya", "FaktorLingkungan"),
    ("Angin", "FaktorLingkungan"),
    ("DerajatKeasamanTanah", "FaktorLingkungan"),
    ("FaktorBudidaya", "FaktorRisiko"),
    ("SanitasiLahanBuruk", "FaktorBudidaya"),
    ("DrainaseBuruk", "FaktorBudidaya"),
    ("PenggunaanBenihTerinfeksi", "FaktorBudidaya"),
    ("JarakTanamRapat", "FaktorBudidaya"),
    ("PemupukanTidakSeimbang", "FaktorBudidaya"),
    ("RotasiTanamanTidakDilakukan", "FaktorBudidaya"),
    ("PengolahanTanahBuruk", "FaktorBudidaya"),
    ("FaktorLahan", "FaktorRisiko"),
    ("KondisiTanah", "FaktorLahan"),
    ("KondisiDrainase", "FaktorLahan"),
    ("KondisiUnsurHara", "FaktorLahan"),
    ("Buku", "Referensi"),
    ("JurnalIlmiah", "Referensi"),
    ("ArtikelIlmiah", "Referensi"),
    ("PublikasiInstansi", "Referensi"),
    ("VarietasUnggul", "Varietas"),
    ("VarietasLokal", "Varietas"),
]

# ---------------------------------------------------------------- properti
OBJECT_PROPERTIES: dict[str, dict] = {
    "menyerangTanaman": {
        "label": "menyerang tanaman",
        "comment": "Penyakit menyerang tanaman pangan tertentu (tanaman inang).",
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
        "comment": "Penyakit menimbulkan gejala tertentu pada tanaman.",
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
    "disebabkanOleh": {
        "label": "disebabkan oleh",
        "comment": "Penyakit disebabkan oleh patogen tertentu.",
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
        "comment": "Bagian tanaman (daun, batang, akar, umbi) yang terserang penyakit.",
        "domain": "Penyakit",
        "range": "BagianTanaman",
    },
    "dikendalikanDengan": {
        "label": "dikendalikan dengan",
        "comment": "Metode pengendalian yang direkomendasikan untuk penyakit.",
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
        "comment": "Pengendalian umum per tanaman yang berlaku lintas penyakit.",
        "domain": "TanamanPangan",
        "range": "Pengendalian",
    },
    "berkaitanPengendalian": {
        "label": "berkaitan pengendalian",
        "comment": (
            "Superproperty pengendalian tanpa domain: menghubungkan penyakit "
            "atau tanaman dengan metode pengendalian."
        ),
        "range": "Pengendalian",
    },
    "dipengaruhiOleh": {
        "label": "dipengaruhi oleh",
        "comment": "Faktor risiko lingkungan/budidaya yang memengaruhi kemunculan penyakit.",
        "domain": "Penyakit",
        "range": "FaktorRisiko",
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
        "comment": "Referensi menjelaskan penyakit; kebalikan dari memilikiReferensi.",
        "domain": "Referensi",
        "range": "Penyakit",
        "inverse": "memilikiReferensi",
    },
    "terdapatPada": {
        "label": "terdapat pada",
        "comment": "Lokasi gejala pada bagian tanaman tertentu.",
        "domain": "Gejala",
        "range": "BagianTanaman",
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
        "comment": "Varietas tahan/resisten terhadap penyakit tertentu.",
        "domain": "Varietas",
        "range": "Penyakit",
    },
    "rentanTerhadap": {
        "label": "rentan terhadap",
        "comment": "Varietas rentan/peka terhadap penyakit tertentu.",
        "domain": "Varietas",
        "range": "Penyakit",
    },
    "menyerangFase": {
        "label": "menyerang fase",
        "comment": "Fase pertumbuhan tanaman yang diserang penyakit.",
        "domain": "Penyakit",
        "range": "FasePertumbuhan",
    },
}

SUBPROPERTY_OF: list[tuple[str, str]] = [
    ("dikendalikanDengan", "berkaitanPengendalian"),
    ("pengendalianUmum", "berkaitanPengendalian"),
]

PROPERTY_CHAINS: list[tuple[list[str], str]] = [
    (["memilikiGejala", "terdapatPada"], "menyerangBagian"),
]

# owl:propertyDisjointWith yang punya dasar sumber: varietas tidak mungkin
# sekaligus tahan dan rentan terhadap penyakit yang sama.
PROPERTY_DISJOINT: list[tuple[str, str]] = [
    ("tahanTerhadap", "rentanTerhadap"),
]

# ---------------------------------------------------------------- nominal
NOMINAL_CLASSES: dict[str, list[str]] = {
    "Serealia": ["Padi", "Jagung"],
    "Legum": ["Kedelai", "KacangTanah", "KacangHijau"],
    "UmbiUmbian": ["UbiJalar", "UbiKayu"],
}

EQUIVALENT_CLASSES: list[tuple[str, str]] = [
    ("PenyakitJamur", "Jamur"),
    ("PenyakitBakteri", "Bakteri"),
    ("PenyakitVirus", "Virus"),
    ("PenyakitNematoda", "Nematoda"),
    ("PenyakitOomycete", "Oomycete"),
    ("PenyakitFitoplasma", "Fitoplasma"),
]

# Disjoint union: seluruh anggota OrganismeLain tercakup tiga subkelas ini.
DISJOINT_UNIONS: dict[str, list[str]] = {
    "OrganismeLain": ["Nematoda", "Oomycete", "Fitoplasma"],
}

# ---------------------------------------------------------------- data
DATA_PROPERTIES: dict[str, dict] = {
    "namaIlmiah": {
        "label": "nama ilmiah",
        "comment": "Nama ilmiah tanaman pangan.",
        "domain": "TanamanPangan",
        "functional": True,
    },
    "deskripsiTanaman": {
        "label": "deskripsi tanaman",
        "comment": "Deskripsi tanaman pangan.",
        "domain": "TanamanPangan",
        "functional": True,
    },
    "namaIlmiahPatogen": {
        "label": "nama ilmiah patogen",
        "comment": "Nama ilmiah patogen penyebab penyakit.",
        "domain": "Patogen",
        "functional": True,
    },
    "catatanTakson": {
        "label": "catatan takson",
        "comment": "Catatan taksonomi atau salah eja dari sumber.",
        "domain": "Patogen",
        "functional": True,
    },
    "deskripsiPenyakit": {
        "label": "deskripsi penyakit",
        "comment": "Penjelasan penyakit menurut sumber.",
        "domain": "Penyakit",
        "functional": True,
    },
    "namaInggrisPenyakit": {
        "label": "nama inggris penyakit",
        "comment": "Nama Inggris penyakit bila tercetak di sumber.",
        "domain": "Penyakit",
        "functional": True,
    },
    "tingkatKeparahan": {
        "label": "tingkat keparahan",
        "comment": "Kategori keparahan penyakit bila tersedia di sumber.",
        "domain": "Penyakit",
        "functional": True,
    },
    "deskripsiGejala": {
        "label": "deskripsi gejala",
        "comment": "Penjelasan gejala menurut sumber.",
        "domain": "Gejala",
        "functional": True,
    },
    "judulReferensi": {
        "label": "judul referensi",
        "comment": "Judul sumber referensi.",
        "domain": "Referensi",
        "functional": True,
    },
    "tahunTerbit": {
        "label": "tahun terbit",
        "comment": "Tahun publikasi referensi.",
        "domain": "Referensi",
        "functional": True,
        "range": XSD.integer,
    },
    "namaPenulis": {
        "label": "nama penulis",
        "comment": "Penulis referensi.",
        "domain": "Referensi",
        "functional": True,
    },
    "urlReferensi": {
        "label": "url referensi",
        "comment": "Tautan sumber referensi.",
        "domain": "Referensi",
        "functional": True,
    },
    "namaPengendalian": {
        "label": "nama pengendalian",
        "comment": "Nama metode pengendalian.",
        "domain": "Pengendalian",
        "functional": True,
    },
    "deskripsiPengendalian": {
        "label": "deskripsi pengendalian",
        "comment": "Penjelasan metode pengendalian menurut sumber.",
        "domain": "Pengendalian",
        "functional": True,
    },
    "nilaiMin": {
        "label": "nilai minimum",
        "comment": "Batas bawah nilai faktor lingkungan.",
        "domain": "FaktorLingkungan",
        "functional": True,
        "range": XSD.decimal,
    },
    "nilaiMaks": {
        "label": "nilai maksimum",
        "comment": "Batas atas nilai faktor lingkungan.",
        "domain": "FaktorLingkungan",
        "functional": True,
        "range": XSD.decimal,
    },
    "nilaiTunggal": {
        "label": "nilai tunggal",
        "comment": "Nilai tunggal faktor lingkungan.",
        "domain": "FaktorLingkungan",
        "functional": True,
        "range": XSD.decimal,
    },
    "satuan": {
        "label": "satuan",
        "comment": "Satuan nilai faktor lingkungan.",
        "domain": "FaktorLingkungan",
        "functional": True,
    },
    "tingkat": {
        "label": "tingkat",
        "comment": "Tingkat kualitatif faktor lingkungan (rendah/sedang/tinggi).",
        "domain": "FaktorLingkungan",
        "functional": True,
    },
    "kondisi": {
        "label": "kondisi",
        "comment": "Kondisi faktor lingkungan (optimal/minimum/maksimum/mendukung).",
        "domain": "FaktorLingkungan",
        "functional": True,
    },
    "kutipanSumber": {
        "label": "kutipan sumber",
        "comment": "Kutipan verbatim dari sumber sebagai bukti.",
        "domain": None,
    },
    "halamanSumber": {
        "label": "halaman sumber",
        "comment": "Halaman PDF sumber.",
        "domain": None,
        "range": XSD.integer,
    },
    "idBlokSumber": {
        "label": "id blok sumber",
        "comment": "ID blok/chunk sumber (mis. DOC002_P028_B005).",
        "domain": None,
    },
}

DATA_PROPERTY_DISJOINT: list[tuple[str, str]] = [
    ("nilaiTunggal", "nilaiMin"),
    ("nilaiTunggal", "nilaiMaks"),
]

# ---------------------------------------------------------------- restriksi
RESTRICTIONS: list[tuple[str, str, str, str]] = [
    ("Penyakit", "menyerangTanaman", "TanamanPangan", "some"),
    ("Penyakit", "memilikiGejala", "Gejala", "some"),
    ("Penyakit", "disebabkanOleh", "Patogen", "only"),
    ("Penyakit", "memilikiReferensi", "Referensi", "min1"),
]

DATATYPE_RESTRICTIONS: list[tuple[str, str, str, str]] = [
    ("Buku", "tahunTerbit", "integer", "exactly1"),
]


def _disjoint_pairs(names: list[str]) -> list[tuple[str, str]]:
    return [(names[i], names[j]) for i in range(len(names)) for j in range(i + 1, len(names))]


DISJOINT_PAIRS: list[tuple[str, str]] = (
    _disjoint_pairs(TOP_CLASSES)
    + _disjoint_pairs(
        [
            "PenyakitJamur",
            "PenyakitBakteri",
            "PenyakitVirus",
            "PenyakitNematoda",
            "PenyakitOomycete",
            "PenyakitFitoplasma",
            "PenyakitLainnya",
        ]
    )
    + _disjoint_pairs(["Jamur", "Bakteri", "Virus", "OrganismeLain"])
    + _disjoint_pairs(["Nematoda", "Oomycete", "Fitoplasma"])
    + _disjoint_pairs(["Serealia", "Legum", "UmbiUmbian"])
    + _disjoint_pairs(["FaktorLingkungan", "FaktorBudidaya", "FaktorLahan"])
    + _disjoint_pairs(["Buku", "JurnalIlmiah", "ArtikelIlmiah", "PublikasiInstansi"])
    + _disjoint_pairs(["VarietasUnggul", "VarietasLokal"])
)

# ---------------------------------------------------------------- helper RDF


def _restriction(graph: Graph, prop: URIRef, target: URIRef, quant: str) -> URIRef:
    node = BNode()
    graph.add((node, RDF.type, OWL.Restriction))
    graph.add((node, OWL.onProperty, prop))
    if quant == "some":
        graph.add((node, OWL.someValuesFrom, target))
    else:
        graph.add((node, OWL.allValuesFrom, target))
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


def _collection_class(graph: Graph, predicate: URIRef, members: list[URIRef]) -> URIRef:
    node = BNode()
    graph.add((node, RDF.type, OWL.Class))
    coll = BNode()
    Collection(graph, coll, members)
    graph.add((node, predicate, coll))
    return node


def _intersection(graph: Graph, parts: list[URIRef]) -> URIRef:
    return _collection_class(graph, OWL.intersectionOf, parts)


def _one_of(graph: Graph, members: list[URIRef]) -> URIRef:
    return _collection_class(graph, OWL.oneOf, members)


def _ann(graph: Graph, subject: URIRef, prop: URIRef, text: str) -> None:
    if text:
        graph.add((subject, prop, Literal(text, lang="id")))


SWRL_RULES: list[dict[str, str]] = [
    {
        "head": "PenyakitRisikoSuhuTinggi",
        "factor": "Suhu",
        "level": "tinggi",
    },
    {
        "head": "PenyakitRisikoKelembapanTinggi",
        "factor": "KelembapanUdara",
        "level": "tinggi",
    },
    {
        "head": "PenyakitRisikoMusimHujan",
        "factor": "MusimHujan",
        "level": "",
    },
]


def _swrl_variable(graph: Graph) -> BNode:
    node = BNode()
    graph.add((node, RDF.type, SWRL.Variable))
    return node


def _swrl_class_atom(graph: Graph, cls: URIRef, var: BNode) -> BNode:
    atom = BNode()
    graph.add((atom, RDF.type, SWRL.ClassAtom))
    graph.add((atom, SWRL.classPredicate, cls))
    graph.add((atom, SWRL.argument1, var))
    return atom


def _swrl_property_atom(
    graph: Graph, prop: URIRef, first: BNode, second: BNode
) -> BNode:
    atom = BNode()
    graph.add((atom, RDF.type, SWRL.IndividualPropertyAtom))
    graph.add((atom, SWRL.propertyPredicate, prop))
    graph.add((atom, SWRL.argument1, first))
    graph.add((atom, SWRL.argument2, second))
    return atom


def _swrl_data_atom(
    graph: Graph, prop: URIRef, first: BNode, value: str
) -> BNode:
    atom = BNode()
    graph.add((atom, RDF.type, SWRL.DatavaluedPropertyAtom))
    graph.add((atom, SWRL.propertyPredicate, prop))
    graph.add((atom, SWRL.argument1, first))
    graph.add((atom, SWRL.argument2, Literal(value, lang="id")))
    return atom


def _add_swrl_rules(graph: Graph) -> None:
    for spec in SWRL_RULES:
        disease = _swrl_variable(graph)
        factor = _swrl_variable(graph)
        body = [
            _swrl_class_atom(graph, KBR["Penyakit"], disease),
            _swrl_property_atom(graph, KBR["dipengaruhiOleh"], disease, factor),
            _swrl_class_atom(graph, KBR[spec["factor"]], factor),
        ]
        if spec["level"]:
            body.append(_swrl_data_atom(graph, KBR["tingkat"], factor, spec["level"]))
        head = [_swrl_class_atom(graph, KBR[spec["head"]], disease)]
        body_node = BNode()
        head_node = BNode()
        Collection(graph, body_node, body)
        Collection(graph, head_node, head)
        rule = BNode()
        graph.add((rule, RDF.type, SWRL.Imp))
        graph.add((rule, SWRL.body, body_node))
        graph.add((rule, SWRL.head, head_node))


def build_tbox(graph: Graph) -> None:
    graph.bind("ptp", KBR)
    graph.bind("skos", SKOS)
    graph.bind("dcterms", DCTERMS)
    graph.bind("prov", PROV)
    graph.bind("swrl", SWRL)

    graph.add((ONTOLOGY_IRI, RDF.type, OWL.Ontology))
    _ann(graph, ONTOLOGY_IRI, RDFS.label, "Ontologi Penyakit Tanaman Pangan Indonesia")
    _ann(
        graph,
        ONTOLOGY_IRI,
        DCTERMS.title,
        "Ontologi Penyakit Tanaman Pangan Indonesia",
    )
    _ann(
        graph,
        ONTOLOGY_IRI,
        DCTERMS.description,
        "Knowledge base penyakit tanaman pangan Indonesia untuk tujuh tanaman: "
        "padi, kedelai, jagung, ubi jalar, ubi kayu, kacang tanah, dan kacang hijau.",
    )
    graph.add((ONTOLOGY_IRI, OWL.versionInfo, Literal(ONTOLOGY_VERSION)))
    _ann(graph, ONTOLOGY_IRI, DCTERMS.creator, "Kelompok 5 KBR")
    _ann(graph, ONTOLOGY_IRI, DCTERMS.source, "DOC002")
    _ann(graph, ONTOLOGY_IRI, DCTERMS.source, "DOC005")

    for name, label in CLASS_LABELS.items():
        uri = _cls(name)
        graph.add((uri, RDF.type, OWL.Class))
        _ann(graph, uri, RDFS.label, label)
        _ann(graph, uri, SKOS.prefLabel, label)
        _ann(
            graph,
            uri,
            RDFS.comment,
            CLASS_COMMENTS.get(name, f"Kelas {label} pada ontologi penyakit tanaman pangan."),
        )
        graph.add((uri, RDFS.isDefinedBy, ONTOLOGY_IRI))

    for child, parent in SUBCLASSES:
        graph.add((_cls(child), RDFS.subClassOf, _cls(parent)))

    for left, right in DISJOINT_PAIRS:
        graph.add((_cls(left), OWL.disjointWith, _cls(right)))

    # O - nominal owl:oneOf.
    for cls_name, individual_names in NOMINAL_CLASSES.items():
        members = [_cls(n) for n in individual_names]
        graph.add((_cls(cls_name), OWL.equivalentClass, _one_of(graph, members)))

    # Equivalent class penyakit berdasarkan patogen.
    for penyakit_cls, patogen_cls in EQUIVALENT_CLASSES:
        restr = _restriction(graph, _cls("disebabkanOleh"), _cls(patogen_cls), "some")
        intersection = _intersection(graph, [_cls("Penyakit"), restr])
        graph.add((_cls(penyakit_cls), OWL.equivalentClass, intersection))

    # Disjoint union OrganismeLain.
    for cls_name, members in DISJOINT_UNIONS.items():
        node = _collection_class(graph, OWL.disjointUnionOf, [_cls(m) for m in members])
        graph.add((_cls(cls_name), OWL.equivalentClass, node))

    for sub_cls, prop, target, quant in RESTRICTIONS:
        if quant == "min1":
            restr = _min1_restriction(graph, _cls(prop), _cls(target))
        else:
            restr = _restriction(graph, _cls(prop), _cls(target), quant)
        graph.add((_cls(sub_cls), RDFS.subClassOf, restr))

    xsd_types = {"integer": XSD.integer, "string": XSD.string}
    for cls_name, prop, type_name, _quant in DATATYPE_RESTRICTIONS:
        restr = _exactly1_datatype_restriction(graph, _cls(prop), xsd_types[type_name])
        graph.add((_cls(cls_name), RDFS.subClassOf, restr))

    _add_swrl_rules(graph)

    for name, spec in OBJECT_PROPERTIES.items():
        uri = _cls(name)
        graph.add((uri, RDF.type, OWL.ObjectProperty))
        _ann(graph, uri, RDFS.label, spec["label"])
        _ann(graph, uri, SKOS.prefLabel, spec["label"])
        _ann(graph, uri, RDFS.comment, spec["comment"])
        _ann(graph, uri, SKOS.definition, spec["comment"])
        graph.add((uri, RDFS.isDefinedBy, ONTOLOGY_IRI))
        if spec.get("domain"):
            graph.add((uri, RDFS.domain, _cls(spec["domain"])))
        graph.add((uri, RDFS.range, _cls(spec["range"])))
        if spec.get("inverse"):
            graph.add((uri, OWL.inverseOf, _cls(spec["inverse"])))

    # S - subPropertyOf.
    for sub_prop, super_prop in SUBPROPERTY_OF:
        graph.add((_cls(sub_prop), RDFS.subPropertyOf, _cls(super_prop)))

    # Disjoint object properties.
    for left, right in PROPERTY_DISJOINT:
        graph.add((_cls(left), OWL.propertyDisjointWith, _cls(right)))

    # R - property chain.
    for chain, super_prop in PROPERTY_CHAINS:
        chain_node = BNode()
        Collection(graph, chain_node, [_cls(p) for p in chain])
        graph.add((_cls(super_prop), OWL.propertyChainAxiom, chain_node))

    for name, spec in DATA_PROPERTIES.items():
        uri = _cls(name)
        graph.add((uri, RDF.type, OWL.DatatypeProperty))
        _ann(graph, uri, RDFS.label, spec["label"])
        _ann(graph, uri, SKOS.prefLabel, spec["label"])
        _ann(graph, uri, RDFS.comment, spec["comment"])
        _ann(graph, uri, SKOS.definition, spec["comment"])
        graph.add((uri, RDFS.isDefinedBy, ONTOLOGY_IRI))
        if spec.get("domain"):
            graph.add((uri, RDFS.domain, _cls(spec["domain"])))
        if spec.get("range") is not None:
            graph.add((uri, RDFS.range, spec["range"]))
        if spec.get("functional"):
            graph.add((uri, RDF.type, OWL.FunctionalProperty))

    for left, right in DATA_PROPERTY_DISJOINT:
        graph.add((_cls(left), OWL.propertyDisjointWith, _cls(right)))

    # Annotation property declarations (termasuk standar yang dipakai).
    for uri, label in (
        (SKOS.prefLabel, "preferred label"),
        (SKOS.altLabel, "alternative label"),
        (SKOS.definition, "definition"),
        (DCTERMS.identifier, "identifier"),
        (DCTERMS.source, "source"),
        (DCTERMS.title, "title"),
        (DCTERMS.description, "description"),
        (DCTERMS.creator, "creator"),
        (PROV.wasDerivedFrom, "was derived from"),
    ):
        graph.add((uri, RDF.type, OWL.AnnotationProperty))
        _ann(graph, uri, RDFS.label, label)
