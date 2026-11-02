"""TBox ontologi "Penyakit Tanaman Pangan Indonesia" (minimal SROIQ(D)).

Profil OWL 2 DL yang didemonstrasikan axioms per huruf:
- S: rdfs:subClassOf; rdfs:subPropertyOf —
  dikendalikanDengan dan pengendalianUmum ⊑ berkaitanPengendalian.
- R: owl:propertyChainAxiom —
  memilikiGejala o terdapatPada ⊑ menyerangBagian.
- O: nominal (owl:oneOf) —
  Serealia ≡ {Padi, Jagung}, Legum ≡ {Kedelai, KacangTanah, KacangHijau}.
- I: 6 pasang owl:inverseOf (12 triple).
- Q: kualifikasi cardinality —
  Penyakit ⊑ (memilikiReferensi min 1 Referensi);
  Buku ⊑ (tahunTerbit exactly 1 xsd:integer).
- D: data property tahunTerbit xsd:integer; literal teks memakai @id
  (rdf:langString) tanpa rdfs:range xsd:string agar tidak disjoint.

Role pada property chain tidak dikenai number restriction (simple role).
"""

from __future__ import annotations

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS, XSD

PTP = "http://kbr.kelompok5.org/penyakit-tanaman-pangan#"
KBR = Namespace(PTP)


def _cls(name: str) -> URIRef:
    return URIRef(PTP + name)


ONTOLOGY_IRI = URIRef("http://kbr.kelompok5.org/penyakit-tanaman-pangan")

CLASS_LABELS: dict[str, str] = {
    "TanamanPangan": "Tanaman Pangan",
    "Penyakit": "Penyakit",
    "PenyakitJamur": "Penyakit Jamur",
    "PenyakitBakteri": "Penyakit Bakteri",
    "PenyakitVirus": "Penyakit Virus",
    "PenyakitLainnya": "Penyakit Lainnya",
    "Gejala": "Gejala",
    "GejalaDaun": "Gejala Daun",
    "GejalaBatang": "Gejala Batang",
    "GejalaAkar": "Gejala Akar",
    "GejalaUmbi": "Gejala Umbi",
    "Patogen": "Patogen",
    "Jamur": "Jamur",
    "Bakteri": "Bakteri",
    "Virus": "Virus",
    "OrganismeLain": "Organisme Lain",
    "BagianTanaman": "Bagian Tanaman",
    "Pengendalian": "Pengendalian",
    "PengendalianKulturTeknis": "Pengendalian Kultur Teknis",
    "PengendalianMekanis": "Pengendalian Mekanis",
    "PengendalianBiologis": "Pengendalian Biologis",
    "PengendalianKimiawi": "Pengendalian Kimiawi",
    "PengendalianTerpadu": "Pengendalian Terpadu",
    "FaktorRisiko": "Faktor Risiko",
    "FaktorLingkungan": "Kondisi Lingkungan",
    "KelembapanTinggi": "Kelembapan Tinggi",
    "Suhu": "Suhu",
    "CurahHujan": "Curah Hujan",
    "MusimHujan": "Musim Hujan",
    "MusimKemarau": "Musim Kemarau",
    "FaktorBudidaya": "Faktor Budidaya",
    "SanitasiLahanBuruk": "Sanitasi Lahan Buruk",
    "DrainaseBuruk": "Drainase Buruk",
    "PenggunaanBenihTerinfeksi": "Penggunaan Benih Terinfeksi",
    "FaktorLahan": "Faktor Lahan",
    "KondisiTanah": "Kondisi Tanah",
    "KondisiDrainase": "Kondisi Drainase",
    "Referensi": "Referensi",
    "Buku": "Buku",
    "JurnalIlmiah": "Jurnal Ilmiah",
    "ArtikelIlmiah": "Artikel Ilmiah",
    "PublikasiInstansi": "Publikasi Instansi",
    "Varietas": "Varietas",
    "FasePertumbuhan": "Fase Pertumbuhan",
    "Serealia": "Serealia",
    "Legum": "Legum",
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
    ("PenyakitJamur", "Penyakit"),
    ("PenyakitBakteri", "Penyakit"),
    ("PenyakitVirus", "Penyakit"),
    ("PenyakitLainnya", "Penyakit"),
    ("GejalaDaun", "Gejala"),
    ("GejalaBatang", "Gejala"),
    ("GejalaAkar", "Gejala"),
    ("GejalaUmbi", "Gejala"),
    ("Jamur", "Patogen"),
    ("Bakteri", "Patogen"),
    ("Virus", "Patogen"),
    ("OrganismeLain", "Patogen"),
    ("PengendalianKulturTeknis", "Pengendalian"),
    ("PengendalianMekanis", "Pengendalian"),
    ("PengendalianBiologis", "Pengendalian"),
    ("PengendalianKimiawi", "Pengendalian"),
    ("PengendalianTerpadu", "Pengendalian"),
    ("FaktorLingkungan", "FaktorRisiko"),
    ("KelembapanTinggi", "FaktorLingkungan"),
    ("Suhu", "FaktorLingkungan"),
    ("CurahHujan", "FaktorLingkungan"),
    ("MusimHujan", "FaktorLingkungan"),
    ("MusimKemarau", "FaktorLingkungan"),
    ("FaktorBudidaya", "FaktorRisiko"),
    ("SanitasiLahanBuruk", "FaktorBudidaya"),
    ("DrainaseBuruk", "FaktorBudidaya"),
    ("PenggunaanBenihTerinfeksi", "FaktorBudidaya"),
    ("FaktorLahan", "FaktorRisiko"),
    ("KondisiTanah", "FaktorLahan"),
    ("KondisiDrainase", "FaktorLahan"),
    ("Buku", "Referensi"),
    ("JurnalIlmiah", "Referensi"),
    ("ArtikelIlmiah", "Referensi"),
    ("PublikasiInstansi", "Referensi"),
    ("Serealia", "TanamanPangan"),
    ("Legum", "TanamanPangan"),
]

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

# Nominal: nama kelas → daftar individual (ABox) yang menjadi anggota oneOf.
NOMINAL_CLASSES: dict[str, list[str]] = {
    "Serealia": ["Padi", "Jagung"],
    "Legum": ["Kedelai", "KacangTanah", "KacangHijau"],
}

DATA_PROPERTIES: dict[str, dict] = {
    "namaIlmiah": {
        "label": "nama ilmiah",
        "comment": "Nama ilmiah tanaman pangan.",
        "domain": "TanamanPangan",
        "range": XSD.string,
    },
    "deskripsiTanaman": {
        "label": "deskripsi tanaman",
        "comment": "Deskripsi tanaman pangan.",
        "domain": "TanamanPangan",
        "range": XSD.string,
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
        "range": XSD.string,
    },
    "deskripsiGejala": {
        "label": "deskripsi gejala",
        "comment": "Penjelasan gejala menurut sumber.",
        "domain": "Gejala",
        "range": XSD.string,
    },
    "tingkatKeparahan": {
        "label": "tingkat keparahan",
        "comment": "Kategori keparahan penyakit bila tersedia di sumber.",
        "domain": "Penyakit",
        "range": XSD.string,
    },
    "judulReferensi": {
        "label": "judul referensi",
        "comment": "Judul sumber referensi.",
        "domain": "Referensi",
        "range": XSD.string,
    },
    "tahunTerbit": {
        "label": "tahun terbit",
        "comment": "Tahun publikasi referensi.",
        "domain": "Referensi",
        "range": XSD.integer,
    },
    "namaPenulis": {
        "label": "nama penulis",
        "comment": "Penulis referensi.",
        "domain": "Referensi",
        "range": XSD.string,
    },
    "urlReferensi": {
        "label": "url referensi",
        "comment": "Tautan sumber referensi.",
        "domain": "Referensi",
        "range": XSD.string,
    },
    "namaPengendalian": {
        "label": "nama pengendalian",
        "comment": "Nama metode pengendalian.",
        "domain": "Pengendalian",
        "range": XSD.string,
    },
    "deskripsiPengendalian": {
        "label": "deskripsi pengendalian",
        "comment": "Penjelasan metode pengendalian menurut sumber.",
        "domain": "Pengendalian",
        "range": XSD.string,
    },
}

EQUIVALENT_CLASSES: list[tuple[str, str]] = [
    ("PenyakitJamur", "Jamur"),
    ("PenyakitBakteri", "Bakteri"),
    ("PenyakitVirus", "Virus"),
]

# Restriction rancangan: (class, prop, target_class, kuantifier).
# Kuantifier: some | only | min1 (kualifikasi: min 1 target).
RESTRICTIONS: list[tuple[str, str, str, str]] = [
    ("Penyakit", "menyerangTanaman", "TanamanPangan", "some"),
    ("Penyakit", "memilikiGejala", "Gejala", "some"),
    ("Penyakit", "disebabkanOleh", "Patogen", "only"),
    ("Penyakit", "memilikiReferensi", "Referensi", "min1"),
]

# Restriksi data: (class, prop, xsd_type, kuantifier exactly1).
DATATYPE_RESTRICTIONS: list[tuple[str, str, str, str]] = [
    ("Buku", "tahunTerbit", "integer", "exactly1"),
]


def _disjoint_pairs(names: list[str]) -> list[tuple[str, str]]:
    return [(names[i], names[j]) for i in range(len(names)) for j in range(i + 1, len(names))]


DISJOINT_PAIRS: list[tuple[str, str]] = (
    _disjoint_pairs(TOP_CLASSES)
    + _disjoint_pairs(["PenyakitJamur", "PenyakitBakteri", "PenyakitVirus", "PenyakitLainnya"])
    + _disjoint_pairs(["Jamur", "Bakteri", "Virus", "OrganismeLain"])
    + _disjoint_pairs(["FaktorLingkungan", "FaktorBudidaya", "FaktorLahan"])
)


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
                "Knowledge base penyakit tanaman pangan Indonesia (padi, kedelai, "
                "jagung, ubi jalar, ubi kayu, kacang tanah, kacang hijau) untuk "
                "penalaran OWL 2 minimal SROIQ(D) di Protégé.",
                lang="id",
            ),
        )
    )

    for name in CLASS_LABELS:
        uri = _cls(name)
        graph.add((uri, RDF.type, OWL.Class))
        graph.add((uri, RDFS.label, Literal(CLASS_LABELS[name], lang="id")))

    for child, parent in SUBCLASSES:
        graph.add((_cls(child), RDFS.subClassOf, _cls(parent)))

    for left, right in DISJOINT_PAIRS:
        graph.add((_cls(left), OWL.disjointWith, _cls(right)))

    # O — nominal owl:oneOf.
    for cls_name, individual_names in NOMINAL_CLASSES.items():
        members = [_cls(n) for n in individual_names]
        graph.add((_cls(cls_name), OWL.equivalentClass, _one_of(graph, members)))

    for penyakit_cls, patogen_cls in EQUIVALENT_CLASSES:
        restr = _restriction(graph, _cls("disebabkanOleh"), _cls(patogen_cls), "some")
        intersection = _intersection(graph, [_cls("Penyakit"), restr])
        graph.add((_cls(penyakit_cls), OWL.equivalentClass, intersection))

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

    for name, spec in OBJECT_PROPERTIES.items():
        uri = _cls(name)
        graph.add((uri, RDF.type, OWL.ObjectProperty))
        graph.add((uri, RDFS.label, Literal(spec["label"], lang="id")))
        graph.add((uri, RDFS.comment, Literal(spec["comment"], lang="id")))
        if spec.get("domain"):
            graph.add((uri, RDFS.domain, _cls(spec["domain"])))
        graph.add((uri, RDFS.range, _cls(spec["range"])))
        if spec.get("inverse"):
            graph.add((uri, OWL.inverseOf, _cls(spec["inverse"])))

    # S — subPropertyOf.
    for sub_prop, super_prop in SUBPROPERTY_OF:
        graph.add((_cls(sub_prop), RDFS.subPropertyOf, _cls(super_prop)))

    # R — property chain.
    for chain, super_prop in PROPERTY_CHAINS:
        chain_node = BNode()
        Collection(graph, chain_node, [_cls(p) for p in chain])
        graph.add((_cls(super_prop), OWL.propertyChainAxiom, chain_node))

    for name, spec in DATA_PROPERTIES.items():
        uri = _cls(name)
        graph.add((uri, RDF.type, OWL.DatatypeProperty))
        graph.add((uri, RDFS.label, Literal(spec["label"], lang="id")))
        graph.add((uri, RDFS.comment, Literal(spec["comment"], lang="id")))
        graph.add((uri, RDFS.domain, _cls(spec["domain"])))
        # rdfs:range sengaja tidak ditulis: nilai teks memakai tag bahasa @id
        # (rdf:langString) yang pada OWL 2 disjoint dengan xsd:string sehingga
        # range xsd:string akan membuat ontologi inkonsisten. Tahun terbit tetap
        # memakai literal xsd:integer sehingga tipe terbaca dari literalnya.
