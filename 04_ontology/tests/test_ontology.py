"""Gate test untuk ontologi OWL 2 Penyakit Tanaman Pangan Indonesia (Tahap 4).

Sebagian test bersifat read-only terhadap artefak ``ontology.ttl``; satu test
gerbang (gate) membangun ulang ontologi lewat ``build_ontology.build()``; satu
test menjalankan reasoner Pellet lewat owlready2 bila Java tersedia.
Jalankan dari ``04_ontology``::

    python -m unittest discover -s tests -p "test_*.py"
"""

from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path
from unittest import mock

from rdflib import Graph, Literal, URIRef
from rdflib.collection import Collection
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, XSD

ONTO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ONTO_DIR))

import build_ontology as bo  # noqa: E402
import tbox  # noqa: E402
from tbox import KBR, PROV, SWRL  # noqa: E402

ARTIFACT = ONTO_DIR / "ontology.ttl"
OWL_ARTIFACT = ONTO_DIR / "ontology.owl"

EXPECTED_TRIPLES = 12110
EXPECTED_INDIVIDUALS = 726

SNAPSHOT_CLASSES = {
    "Angin": 1,
    "ArtikelIlmiah": 0,
    "BagianTanaman": 13,
    "Bakteri": 5,
    "Buku": 2,
    "Cahaya": 2,
    "CurahHujan": 1,
    "DerajatKeasamanTanah": 2,
    "DrainaseBuruk": 0,
    "FaktorBudidaya": 0,
    "FaktorLahan": 0,
    "FaktorLingkungan": 55,
    "FaktorRisiko": 55,
    "FasePertumbuhan": 3,
    "Fitoplasma": 1,
    "Gejala": 238,
    "GejalaAkar": 11,
    "GejalaBatang": 21,
    "GejalaBiji": 8,
    "GejalaBuah": 3,
    "GejalaBunga": 0,
    "GejalaDaun": 94,
    "GejalaLeherMalai": 4,
    "GejalaMalai": 4,
    "GejalaPelepah": 3,
    "GejalaPolong": 11,
    "GejalaPucuk": 3,
    "GejalaTongkol": 1,
    "GejalaUmbi": 4,
    "Jamur": 29,
    "JarakTanamRapat": 0,
    "JurnalIlmiah": 0,
    "Kelembapan": 0,
    "KelembapanTanah": 2,
    "KelembapanUdara": 9,
    "KondisiDrainase": 0,
    "KondisiTanah": 0,
    "KondisiUnsurHara": 0,
    "Legum": 3,
    "Musim": 0,
    "MusimHujan": 1,
    "MusimKemarau": 1,
    "Nematoda": 0,
    "Oomycete": 1,
    "OrganismeLain": 0,
    "Patogen": 59,
    "PemupukanTidakSeimbang": 0,
    "Pengendalian": 261,
    "PengendalianBiologis": 59,
    "PengendalianFisik": 9,
    "PengendalianKimiawi": 67,
    "PengendalianKulturTeknis": 82,
    "PengendalianMekanis": 5,
    "PengendalianTerpadu": 2,
    "PenggunaanBenihTerinfeksi": 0,
    "PengolahanTanahBuruk": 0,
    "Penyakit": 54,
    "PenyakitBakteri": 0,
    "PenyakitFitoplasma": 0,
    "PenyakitJamur": 0,
    "PenyakitLainnya": 0,
    "PenyakitNematoda": 0,
    "PenyakitOomycete": 0,
    "PenyakitRisiko": 0,
    "PenyakitRisikoKelembapanTinggi": 0,
    "PenyakitRisikoMusimHujan": 0,
    "PenyakitRisikoSuhuTinggi": 0,
    "PenyakitVirus": 0,
    "PublikasiInstansi": 0,
    "Referensi": 2,
    "RotasiTanamanTidakDilakukan": 0,
    "SanitasiLahanBuruk": 0,
    "Serealia": 2,
    "Suhu": 36,
    "TanamanPangan": 7,
    "UmbiUmbian": 2,
    "Varietas": 34,
    "VarietasLokal": 0,
    "VarietasUnggul": 2,
    "Virus": 8,
}

SNAPSHOT_OBJECT_PROPS = {
    "berkaitanPengendalian": 302,
    "dijelaskanDalam": 57,
    "dikendalikanDengan": 257,
    "dipengaruhiOleh": 89,
    "disebabkanOleh": 72,
    "diserangPenyakit": 54,
    "memilikiGejala": 238,
    "memilikiReferensi": 57,
    "memilikiVarietas": 34,
    "mengendalikanPenyakit": 257,
    "menyebabkanPenyakit": 72,
    "menyerangBagian": 89,
    "menyerangFase": 3,
    "menyerangTanaman": 54,
    "merupakanGejalaDari": 238,
    "merupakanVarietasDari": 34,
    "pengendalianUmum": 45,
    "rentanTerhadap": 0,
    "tahanTerhadap": 32,
    "terdapatPada": 167,
}

SNAPSHOT_DATA_PROPS = {
    "catatanTakson": 20,
    "deskripsiGejala": 238,
    "deskripsiPengendalian": 261,
    "deskripsiPenyakit": 54,
    "deskripsiTanaman": 7,
    "halamanSumber": 708,
    "idBlokSumber": 670,
    "judulReferensi": 2,
    "kondisi": 55,
    "kutipanSumber": 713,
    "namaIlmiah": 7,
    "namaIlmiahPatogen": 59,
    "namaInggrisPenyakit": 9,
    "namaPengendalian": 129,
    "namaPenulis": 2,
    "nilaiMaks": 22,
    "nilaiMin": 22,
    "nilaiTunggal": 25,
    "satuan": 47,
    "tahunTerbit": 2,
    "tingkat": 50,
    "tingkatKeparahan": 0,
    "urlReferensi": 0,
}

LANG_TAGGED_PROPS = (
    "deskripsiPenyakit", "deskripsiGejala", "deskripsiTanaman",
    "deskripsiPengendalian", "namaIlmiah", "namaIlmiahPatogen",
    "namaInggrisPenyakit", "namaPengendalian", "kutipanSumber", "satuan",
    "tingkat", "kondisi", "judulReferensi", "namaPenulis", "catatanTakson",
)


def _local(uri: URIRef) -> str:
    return str(uri).rsplit("#", 1)[-1]


def _inverse_pairs() -> list[tuple[str, str]]:
    return [
        (name, spec["inverse"])
        for name, spec in tbox.OBJECT_PROPERTIES.items()
        if spec.get("inverse")
    ]


def _restriction_nodes(graph: Graph) -> list[tuple[str, str, str, str]]:
    found: list[tuple[str, str, str, str]] = []
    for sub, _, restr in graph.triples((None, RDFS.subClassOf, None)):
        if (restr, RDF.type, OWL.Restriction) not in graph:
            continue
        prop = next(graph.objects(restr, OWL.onProperty), None)
        if prop is None:
            continue
        for quantifier, pred in (("some", OWL.someValuesFrom), ("only", OWL.allValuesFrom)):
            target = next(graph.objects(restr, pred), None)
            if target is not None:
                found.append((_local(sub), _local(prop), _local(target), quantifier))
        if (restr, OWL.minCardinality, None) in graph:
            target = next(graph.objects(restr, OWL.onClass), None)
            if target is not None:
                found.append((_local(sub), _local(prop), _local(target), "min1"))
    return found


def cls_pairs(graph: Graph):
    for left, _, right in graph.triples((None, OWL.disjointWith, None)):
        yield _local(left), _local(right)


class OntologyArtifactTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not ARTIFACT.exists():
            raise AssertionError(
                f"artefak hilang: {ARTIFACT} — jalankan python build_ontology.py dulu"
            )
        cls.graph = Graph()
        cls.graph.parse(data=ARTIFACT.read_text(encoding="utf-8"), format="turtle")
        cls.diseases = set(cls.graph.subjects(RDF.type, KBR["Penyakit"]))
        cls.plants = set(cls.graph.subjects(RDF.type, KBR["TanamanPangan"]))

    def test_artifact_triple_count(self) -> None:
        self.assertEqual(len(self.graph), EXPECTED_TRIPLES)

    def test_named_individuals(self) -> None:
        actual = len(list(self.graph.subjects(RDF.type, OWL.NamedIndividual)))
        self.assertEqual(actual, EXPECTED_INDIVIDUALS)

    def test_snapshot_classes(self) -> None:
        for cls_name, count in SNAPSHOT_CLASSES.items():
            with self.subTest(cls=cls_name):
                actual = len(list(self.graph.subjects(RDF.type, KBR[cls_name])))
                self.assertEqual(actual, count)

    def test_snapshot_object_properties(self) -> None:
        for prop, count in SNAPSHOT_OBJECT_PROPS.items():
            with self.subTest(prop=prop):
                actual = len(list(self.graph.triples((None, KBR[prop], None))))
                self.assertEqual(actual, count)

    def test_snapshot_data_properties(self) -> None:
        for prop, count in SNAPSHOT_DATA_PROPS.items():
            with self.subTest(prop=prop):
                actual = len(list(self.graph.triples((None, KBR[prop], None))))
                self.assertEqual(actual, count)

    def test_no_empty_literals(self) -> None:
        for obj in self.graph.objects():
            if isinstance(obj, Literal):
                self.assertNotEqual(str(obj), "", f"literal kosong pada {obj}")

    def test_text_literals_use_indonesian_language_tag(self) -> None:
        for prop in LANG_TAGGED_PROPS:
            for obj in self.graph.objects(None, KBR[prop]):
                with self.subTest(prop=prop, value=str(obj)[:40]):
                    self.assertEqual(obj.language, "id")

    def test_typed_literals(self) -> None:
        for prop in ("tahunTerbit", "halamanSumber"):
            for obj in self.graph.objects(None, KBR[prop]):
                with self.subTest(prop=prop, value=str(obj)):
                    self.assertEqual(obj.datatype, XSD.integer)
        for prop in ("nilaiMin", "nilaiMaks", "nilaiTunggal"):
            for obj in self.graph.objects(None, KBR[prop]):
                with self.subTest(prop=prop, value=str(obj)):
                    self.assertEqual(obj.datatype, XSD.decimal)

    def test_tahun_terbit_is_integer(self) -> None:
        values = sorted(int(v) for v in self.graph.objects(None, KBR["tahunTerbit"]))
        self.assertEqual(values, [2020, 2021])

    def test_no_explicit_disease_category_assertion(self) -> None:
        for cls_name in (
            "PenyakitJamur", "PenyakitBakteri", "PenyakitVirus",
            "PenyakitNematoda", "PenyakitOomycete", "PenyakitFitoplasma",
            "PenyakitLainnya", "PenyakitRisiko", "PenyakitRisikoSuhuTinggi",
            "PenyakitRisikoKelembapanTinggi", "PenyakitRisikoMusimHujan",
        ):
            with self.subTest(cls=cls_name):
                actual = set(self.graph.subjects(RDF.type, KBR[cls_name]))
                self.assertEqual(
                    actual,
                    set(),
                    "kelas hasil klasifikasi wajib hanya muncul lewat inferensi reasoner",
                )

    def test_every_disease_has_plant_symptom_reference(self) -> None:
        for disease in self.diseases:
            with self.subTest(disease=_local(disease)):
                self.assertTrue(list(self.graph.objects(disease, KBR["menyerangTanaman"])))
                self.assertTrue(list(self.graph.objects(disease, KBR["memilikiGejala"])))
                self.assertTrue(list(self.graph.objects(disease, KBR["memilikiReferensi"])))

    def test_every_disease_has_identifier_and_description(self) -> None:
        for disease in self.diseases:
            with self.subTest(disease=_local(disease)):
                self.assertTrue(list(self.graph.objects(disease, DCTERMS.identifier)))
                self.assertTrue(list(self.graph.objects(disease, KBR["deskripsiPenyakit"])))

    def test_three_diseases_without_pathogen(self) -> None:
        with_pathogen = set(self.graph.subjects(KBR["disebabkanOleh"], None))
        without = {_local(d) for d in self.diseases - with_pathogen}
        self.assertEqual(
            without,
            {
                "BelangMottleKacangTanah",
                "KerdilRumputDanKerdilHampaPadi",
                "NekrosisPadaTitikTunasCassavaBudNecrosisUbiKayu",
            },
        )

    def test_seven_scope_plants(self) -> None:
        names = {_local(p) for p in self.plants}
        self.assertEqual(
            names,
            {"Padi", "Kedelai", "Jagung", "UbiJalar", "UbiKayu", "KacangTanah", "KacangHijau"},
        )
        scientific = {
            _local(p): str(next(self.graph.objects(p, KBR["namaIlmiah"])))
            for p in self.plants
            if list(self.graph.objects(p, KBR["namaIlmiah"]))
        }
        self.assertEqual(
            scientific,
            {
                "Padi": "Oryza sativa L.",
                "Kedelai": "Glycine max L. Merril",
                "Jagung": "Zea mays L.",
                "UbiJalar": "Ipomoea batatas L. (Lam)",
                "UbiKayu": "Manihot esculenta Crantz",
                "KacangTanah": "Arachis hypogaea L.",
                "KacangHijau": "Vigna radiata (L.) R. Wilczek",
            },
        )

    def test_plant_subclass_exactly_one(self) -> None:
        for plant in self.plants:
            hits = [
                cls for cls in ("Serealia", "Legum", "UmbiUmbian")
                if (plant, RDF.type, KBR[cls]) in self.graph
            ]
            with self.subTest(plant=_local(plant)):
                self.assertEqual(len(hits), 1)
        self.assertEqual(
            {_local(p) for p in self.graph.subjects(RDF.type, KBR["Serealia"])},
            {"Padi", "Jagung"},
        )
        self.assertEqual(
            {_local(p) for p in self.graph.subjects(RDF.type, KBR["Legum"])},
            {"Kedelai", "KacangTanah", "KacangHijau"},
        )
        self.assertEqual(
            {_local(p) for p in self.graph.subjects(RDF.type, KBR["UmbiUmbian"])},
            {"UbiJalar", "UbiKayu"},
        )

    def test_duplicate_disease_names_disambiguated(self) -> None:
        first = KBR["AntraknosaUbiKayuDaun"]
        second = KBR["AntraknosaUbiKayuBatang"]
        self.assertIn((first, RDF.type, KBR["Penyakit"]), self.graph)
        self.assertIn((second, RDF.type, KBR["Penyakit"]), self.graph)
        labels = {str(next(self.graph.objects(u, RDFS.label))) for u in (first, second)}
        self.assertEqual(labels, {"Antraknosa"})

    def test_inverse_materialized_on_sample(self) -> None:
        for prop, inverse in _inverse_pairs():
            with self.subTest(prop=prop):
                for subj, obj in list(self.graph.subject_objects(KBR[prop]))[:3]:
                    self.assertIn((obj, KBR[inverse], subj), self.graph)

    def test_varieties_and_phases_present(self) -> None:
        self.assertEqual(len(list(self.graph.subjects(RDF.type, KBR["Varietas"]))), 34)
        self.assertEqual(len(list(self.graph.subjects(RDF.type, KBR["FasePertumbuhan"]))), 3)
        self.assertTrue(list(self.graph.subjects(KBR["menyerangFase"], None)))
        self.assertTrue(list(self.graph.subjects(KBR["memilikiVarietas"], None)))
        self.assertTrue(list(self.graph.subjects(KBR["tahanTerhadap"], None)))

    def test_environment_individuals_typed_and_valued(self) -> None:
        envs = list(self.graph.subjects(RDF.type, KBR["FaktorLingkungan"]))
        self.assertGreaterEqual(len(envs), 40)
        numeric = 0
        ranged = 0
        for env in envs:
            with self.subTest(env=_local(env)):
                self.assertIn((env, RDF.type, KBR["FaktorRisiko"]), self.graph)
                values = [
                    obj for prop in ("nilaiMin", "nilaiMaks", "nilaiTunggal", "tingkat", "kondisi")
                    for obj in self.graph.objects(env, KBR[prop])
                ]
                self.assertTrue(values, "faktor lingkungan tanpa nilai/tingkat/kondisi")
                if list(self.graph.objects(env, KBR["nilaiTunggal"])):
                    numeric += 1
                if list(self.graph.objects(env, KBR["nilaiMin"])) and list(
                    self.graph.objects(env, KBR["nilaiMaks"])
                ):
                    ranged += 1
        self.assertGreater(numeric, 0)
        self.assertGreater(ranged, 0)

    def test_environment_has_temperature_and_humidity(self) -> None:
        self.assertTrue(list(self.graph.subjects(RDF.type, KBR["Suhu"])))
        self.assertTrue(list(self.graph.subjects(RDF.type, KBR["KelembapanUdara"])))
        for temp in self.graph.subjects(RDF.type, KBR["Suhu"]):
            for value in self.graph.objects(temp, KBR["nilaiTunggal"]):
                self.assertLessEqual(float(value), 45)
            for value in self.graph.objects(temp, KBR["nilaiMaks"]):
                self.assertLessEqual(float(value), 45)

    def test_pengendalian_subclass_classification(self) -> None:
        for cls_name in (
            "PengendalianKulturTeknis",
            "PengendalianKimiawi",
            "PengendalianBiologis",
            "PengendalianMekanis",
            "PengendalianFisik",
            "PengendalianTerpadu",
        ):
            with self.subTest(cls=cls_name):
                self.assertGreater(
                    len(list(self.graph.subjects(RDF.type, KBR[cls_name]))), 0
                )

    def test_naming_policy_and_provenance(self) -> None:
        bad_local = __import__("re").compile(
            r"(_[0-9a-f]{8}$)|(DIS\d+)|(DIS_)|(^20\d\d)|([A-Z]{4,})"
        )
        for subject in self.graph.subjects(RDF.type, OWL.NamedIndividual):
            local = _local(subject)
            with self.subTest(local=local):
                self.assertRegex(local, r"^[A-Z][A-Za-z0-9]*$")
                self.assertIsNone(bad_local.search(local))
        quotes = list(self.graph.subject_objects(KBR["kutipanSumber"]))
        self.assertGreaterEqual(len(quotes), 670)
        for disease in self.diseases:
            with self.subTest(disease=_local(disease)):
                self.assertGreaterEqual(
                    len(str(next(self.graph.objects(disease, KBR["deskripsiPenyakit"])))),
                    20,
                )

    def test_annotations_present(self) -> None:
        for subject in self.graph.subjects(RDF.type, OWL.NamedIndividual):
            with self.subTest(subject=_local(subject)):
                self.assertTrue(list(self.graph.objects(subject, RDFS.label)))
        for name in tbox.CLASS_LABELS:
            with self.subTest(cls=name):
                self.assertTrue(list(self.graph.objects(KBR[name], RDFS.label)))
                self.assertTrue(list(self.graph.objects(KBR[name], RDFS.comment)))
        for name in (*tbox.OBJECT_PROPERTIES, *tbox.DATA_PROPERTIES):
            with self.subTest(prop=name):
                self.assertTrue(list(self.graph.objects(KBR[name], RDFS.label)))
                self.assertTrue(list(self.graph.objects(KBR[name], RDFS.comment)))


class OntologyAxiomTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.graph = Graph()
        cls.graph.parse(data=ARTIFACT.read_text(encoding="utf-8"), format="turtle")

    def test_disjoint_pair_count(self) -> None:
        actual = list(cls_pairs(self.graph))
        self.assertEqual(len(actual), len(tbox.DISJOINT_PAIRS))
        self.assertEqual(len(actual), 88)

    def test_top_classes_are_pairwise_disjoint(self) -> None:
        for i, left in enumerate(tbox.TOP_CLASSES):
            for right in tbox.TOP_CLASSES[i + 1:]:
                with self.subTest(pair=(left, right)):
                    self.assertIn((KBR[left], OWL.disjointWith, KBR[right]), self.graph)
                    self.assertNotIn((KBR[right], OWL.disjointWith, KBR[left]), self.graph)

    def test_subclass_taxonomy(self) -> None:
        for child, parent in tbox.SUBCLASSES:
            with self.subTest(child=child):
                self.assertIn((KBR[child], RDFS.subClassOf, KBR[parent]), self.graph)

    def test_inverse_of_axioms(self) -> None:
        pairs = _inverse_pairs()
        self.assertEqual(len({frozenset(p) for p in pairs}), 6)
        for prop, inverse in pairs:
            with self.subTest(prop=prop):
                self.assertIn((KBR[prop], OWL.inverseOf, KBR[inverse]), self.graph)
                self.assertIn((KBR[inverse], OWL.inverseOf, KBR[prop]), self.graph)
        self.assertEqual(len(list(self.graph.subject_objects(OWL.inverseOf))), 12)

    def test_equivalent_classes_structure(self) -> None:
        equivalents = list(self.graph.subjects(OWL.equivalentClass, None))
        self.assertEqual(
            {_local(u) for u in equivalents},
            {
                "PenyakitJamur", "PenyakitBakteri", "PenyakitVirus",
                "PenyakitNematoda", "PenyakitOomycete", "PenyakitFitoplasma",
                "Serealia", "Legum", "UmbiUmbian", "OrganismeLain",
            },
        )
        for penyakit_cls, patogen_cls in tbox.EQUIVALENT_CLASSES:
            with self.subTest(cls=penyakit_cls):
                intersections = list(self.graph.objects(KBR[penyakit_cls], OWL.equivalentClass))
                self.assertEqual(len(intersections), 1)
                members = list(self.graph.objects(intersections[0], OWL.intersectionOf))
                self.assertEqual(len(members), 1)
                chain = list(Collection(self.graph, members[0]))
                self.assertEqual(len(chain), 2)
                self.assertEqual(chain[0], KBR["Penyakit"])
                self.assertIn((chain[1], RDF.type, OWL.Restriction), self.graph)
                self.assertIn((chain[1], OWL.someValuesFrom, KBR[patogen_cls]), self.graph)

    def test_swrl_rules_present(self) -> None:
        rules = list(self.graph.subjects(RDF.type, SWRL.Imp))
        self.assertEqual(len(rules), len(tbox.SWRL_RULES))
        for rule in rules:
            self.assertTrue(list(self.graph.objects(rule, SWRL.body)))
            self.assertTrue(list(self.graph.objects(rule, SWRL.head)))
        data_atoms = list(self.graph.subjects(RDF.type, SWRL.DatavaluedPropertyAtom))
        self.assertEqual(len(data_atoms), 2)
        for atom in data_atoms:
            value = next(self.graph.objects(atom, SWRL.argument2))
            with self.subTest(atom=atom):
                self.assertEqual(value.language, "id")

    def test_nominal_one_of(self) -> None:
        for cls_name, members in tbox.NOMINAL_CLASSES.items():
            with self.subTest(cls=cls_name):
                eq = list(self.graph.objects(KBR[cls_name], OWL.equivalentClass))
                self.assertEqual(len(eq), 1)
                colls = list(self.graph.objects(eq[0], OWL.oneOf))
                self.assertEqual(len(colls), 1)
                chain = list(Collection(self.graph, colls[0]))
                self.assertEqual(chain, [KBR[m] for m in members])

    def test_disjoint_union_organisme_lain(self) -> None:
        eq = list(self.graph.objects(KBR["OrganismeLain"], OWL.equivalentClass))
        self.assertEqual(len(eq), 1)
        colls = list(self.graph.objects(eq[0], OWL.disjointUnionOf))
        self.assertEqual(len(colls), 1)
        chain = list(Collection(self.graph, colls[0]))
        self.assertEqual(chain, [KBR[m] for m in tbox.DISJOINT_UNIONS["OrganismeLain"]])

    def test_restrictions_exactly_as_rancangan(self) -> None:
        found = set(_restriction_nodes(self.graph))
        expected = set(tbox.RESTRICTIONS)
        self.assertEqual(found, expected)

    def test_datatype_restriction_buku(self) -> None:
        found = False
        for node in self.graph.objects(KBR["Buku"], RDFS.subClassOf):
            if (node, OWL.onProperty, KBR["tahunTerbit"]) not in self.graph:
                continue
            for lit in self.graph.objects(node, OWL.cardinality):
                if (node, OWL.onDatatype, XSD.integer) in self.graph and int(lit) == 1:
                    found = True
        self.assertTrue(found)

    def test_object_property_domain_range(self) -> None:
        for name, spec in tbox.OBJECT_PROPERTIES.items():
            with self.subTest(prop=name):
                if spec.get("domain"):
                    self.assertIn((KBR[name], RDFS.domain, KBR[spec["domain"]]), self.graph)
                else:
                    self.assertEqual(list(self.graph.objects(KBR[name], RDFS.domain)), [])
                self.assertIn((KBR[name], RDFS.range, KBR[spec["range"]]), self.graph)

    def test_data_property_domain_and_ranges(self) -> None:
        for name, spec in tbox.DATA_PROPERTIES.items():
            with self.subTest(prop=name):
                if spec.get("domain"):
                    self.assertIn((KBR[name], RDFS.domain, KBR[spec["domain"]]), self.graph)
                else:
                    self.assertEqual(list(self.graph.objects(KBR[name], RDFS.domain)), [])
                if spec.get("range") is not None:
                    self.assertIn((KBR[name], RDFS.range, spec["range"]), self.graph)
                else:
                    self.assertEqual(list(self.graph.objects(KBR[name], RDFS.range)), [])

    def test_annotation_properties_declared(self) -> None:
        for prop, label in (
            ("prefLabel", "preferred label"),
            ("altLabel", "alternative label"),
            ("definition", "definition"),
        ):
            with self.subTest(prop=prop):
                uri = getattr(__import__("rdflib.namespace", fromlist=["SKOS"]).SKOS, prop)
                self.assertIn((uri, RDF.type, OWL.AnnotationProperty), self.graph)
                self.assertTrue(list(self.graph.objects(uri, RDFS.label)))
        for uri in (DCTERMS.identifier, DCTERMS.source, PROV.wasDerivedFrom):
            with self.subTest(prop=str(uri)):
                self.assertIn((uri, RDF.type, OWL.AnnotationProperty), self.graph)

    def test_functional_data_properties(self) -> None:
        self.assertTrue(
            list(self.graph.subjects(RDF.type, OWL.FunctionalProperty)),
            "harus ada FunctionalDataProperty",
        )
        for name, spec in tbox.DATA_PROPERTIES.items():
            if not spec.get("functional"):
                continue
            for subj in set(self.graph.subjects(KBR[name], None)):
                values = list(self.graph.objects(subj, KBR[name]))
                with self.subTest(prop=name, subject=_local(subj)):
                    self.assertLessEqual(len(values), 1)

    def test_sroiq_d_features_present(self) -> None:
        self.assertTrue(list(self.graph.objects(None, OWL.propertyChainAxiom)), "R: property chain")
        for sub_prop, super_prop in tbox.SUBPROPERTY_OF:
            with self.subTest(sub=sub_prop):
                self.assertIn(
                    (KBR[sub_prop], RDFS.subPropertyOf, KBR[super_prop]), self.graph, "S: subPropertyOf"
                )
        for cls_name in tbox.NOMINAL_CLASSES:
            with self.subTest(nominal=cls_name):
                self.assertTrue(
                    list(self.graph.objects(KBR[cls_name], OWL.equivalentClass)), "O: oneOf"
                )
        self.assertEqual(len(list(self.graph.subject_objects(OWL.inverseOf))), 12, "I: inverseOf")
        min1 = False
        for node in self.graph.objects(KBR["Penyakit"], RDFS.subClassOf):
            if (node, OWL.onProperty, KBR["memilikiReferensi"]) in self.graph:
                for lit in self.graph.objects(node, OWL.minCardinality):
                    if (node, OWL.onClass, KBR["Referensi"]) in self.graph and int(lit) == 1:
                        min1 = True
        self.assertTrue(min1, "Q: min 1 Referensi")
        ex1 = False
        for node in self.graph.objects(KBR["Buku"], RDFS.subClassOf):
            if (node, OWL.onProperty, KBR["tahunTerbit"]) in self.graph:
                for lit in self.graph.objects(node, OWL.cardinality):
                    if (node, OWL.onDatatype, XSD.integer) in self.graph and int(lit) == 1:
                        ex1 = True
        self.assertTrue(ex1, "Q/D: exactly 1 xsd:integer tahunTerbit")

    def test_property_chain_members(self) -> None:
        chains = list(self.graph.objects(None, OWL.propertyChainAxiom))
        self.assertEqual(len(chains), 1)
        chain = list(Collection(self.graph, chains[0]))
        self.assertEqual(chain, [KBR["memilikiGejala"], KBR["terdapatPada"]])
        self.assertIn((KBR["menyerangBagian"], OWL.propertyChainAxiom, chains[0]), self.graph)

    def test_property_disjointness(self) -> None:
        for left, right in tbox.PROPERTY_DISJOINT:
            with self.subTest(pair=(left, right)):
                self.assertIn((KBR[left], OWL.propertyDisjointWith, KBR[right]), self.graph)
        for left, right in tbox.DATA_PROPERTY_DISJOINT:
            with self.subTest(pair=(left, right)):
                self.assertIn((KBR[left], OWL.propertyDisjointWith, KBR[right]), self.graph)

    def test_no_punning(self) -> None:
        class_iris = set(self.graph.subjects(RDF.type, OWL.Class))
        individual_iris = set(self.graph.subjects(RDF.type, OWL.NamedIndividual))
        self.assertEqual(class_iris & individual_iris, set())

    def test_ontology_header(self) -> None:
        headers = list(self.graph.subjects(RDF.type, OWL.Ontology))
        self.assertEqual(len(headers), 1)
        self.assertEqual(str(headers[0]), str(tbox.ONTOLOGY_IRI))


class BuildGateTest(unittest.TestCase):
    def test_fresh_build_has_no_errors(self) -> None:
        graph, _expected, errors, _builder, report = bo.build()
        self.assertEqual(errors, [])
        self.assertEqual(len(graph), EXPECTED_TRIPLES)
        self.assertEqual(report["coverage"]["berDeskripsi"], 54)
        self.assertEqual(report["coverage"]["berPengendalian"], 54)
        self.assertEqual(report["coverage"]["berPatogen"], 51)
        self.assertEqual(len(report["coverage"]["tanpaPatogen"]), 3)
        self.assertEqual(report["coverage"]["tanpaDeskripsi"], [])
        self.assertEqual(report["coverage"]["tanpaPengendalian"], [])


@unittest.skipUnless(shutil.which("java"), "Java tidak tersedia untuk Pellet")
class PelletReasoningTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            import owlready2  # noqa: F401
            import owlready2.reasoning as reasoning
        except ImportError as exc:  # pragma: no cover
            raise unittest.SkipTest(f"owlready2 tidak terpasang: {exc}")
        if not OWL_ARTIFACT.exists():
            raise AssertionError(
                f"artefak hilang: {OWL_ARTIFACT} — jalankan python build_ontology.py dulu"
            )
        from owlready2 import JAVA_EXE, World, sync_reasoner_pellet

        cls.world = World()
        cls.onto = cls.world.get_ontology(
            "http://kbr.kelompok5.org/penyakit-tanaman-pangan"
        )
        with OWL_ARTIFACT.open("rb") as handle:
            cls.onto.load(fileobj=handle, format="rdfxml")

        original_run = reasoning.subprocess.run

        def run_with_owlapi(command, *args, **kwargs):
            if isinstance(command, list) and command and command[0] == JAVA_EXE:
                command = [
                    "OWLAPI" if part == "Jena" else part for part in command
                ]
            return original_run(command, *args, **kwargs)

        with mock.patch.object(reasoning.subprocess, "run", side_effect=run_with_owlapi):
            sync_reasoner_pellet(cls.onto, debug=0)

    def test_ontology_is_consistent(self) -> None:
        nothing = [
            ind
            for ind in self.onto.individuals()
            if any(getattr(cls, "name", None) == "Nothing" for cls in ind.is_a)
        ]
        self.assertEqual(nothing, [], "tidak boleh ada individu owl:Nothing")

    def test_inferred_disease_categories(self) -> None:
        expected = {
            "PenyakitJamur": 26,
            "PenyakitBakteri": 5,
            "PenyakitVirus": 5,
            "PenyakitNematoda": 0,
            "PenyakitOomycete": 2,
            "PenyakitFitoplasma": 1,
            "PenyakitLainnya": 0,
        }
        for cls_name, count in expected.items():
            with self.subTest(cls=cls_name):
                cls = getattr(self.onto, cls_name)
                self.assertEqual(len(list(cls.instances())), count)

    def test_inferred_risk_classes(self) -> None:
        expected = {
            "PenyakitRisiko": 16,
            "PenyakitRisikoSuhuTinggi": 3,
            "PenyakitRisikoKelembapanTinggi": 10,
            "PenyakitRisikoMusimHujan": 6,
        }
        for cls_name, count in expected.items():
            with self.subTest(cls=cls_name):
                cls = getattr(self.onto, cls_name)
                self.assertEqual(len(list(cls.instances())), count)

    def test_inferred_nominal_classes(self) -> None:
        self.assertEqual(
            {ind.name for ind in self.onto.Serealia.instances()}, {"Padi", "Jagung"}
        )
        self.assertEqual(
            {ind.name for ind in self.onto.Legum.instances()},
            {"Kedelai", "KacangTanah", "KacangHijau"},
        )
        self.assertEqual(
            {ind.name for ind in self.onto.UmbiUmbian.instances()},
            {"UbiJalar", "UbiKayu"},
        )

    def test_inferred_bakteri_examples(self) -> None:
        names = {ind.name for ind in self.onto.PenyakitBakteri.instances()}
        self.assertIn("HawarDaunBakteriPadi", names)
        self.assertIn("LayuBakteriKacangTanah", names)


if __name__ == "__main__":
    unittest.main()
