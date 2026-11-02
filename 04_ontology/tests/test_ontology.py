"""Gate test untuk ontologi OWL 2 Penyakit Tanaman Pangan Indonesia (Tahap 4).

Sebagian test bersifat read-only terhadap artefak ``ontology.ttl``; satu test
gerbang (gate) membangun ulang ontologi lewat ``build_ontology.build()``; satu
test menjalankan reasoner HermiT lewat owlready2 bila Java tersedia.
Jalankan dari ``04_ontology``::

    python -m unittest discover -s tests -p "test_*.py"
"""

from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path

from rdflib import Graph, Literal, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS, XSD

ONTO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ONTO_DIR))

import build_ontology as bo  # noqa: E402
import tbox  # noqa: E402
from tbox import KBR  # noqa: E402

ARTIFACT = ONTO_DIR / "ontology.ttl"
OWL_ARTIFACT = ONTO_DIR / "ontology.owl"

EXPECTED_TRIPLES = 1852
EXPECTED_INDIVIDUALS = 230

SNAPSHOT_CLASSES = {
    "ArtikelIlmiah": 0,
    "BagianTanaman": 6,
    "Bakteri": 1,
    "Buku": 1,
    "CurahHujan": 0,
    "DrainaseBuruk": 0,
    "FaktorBudidaya": 0,
    "FaktorLahan": 0,
    "FaktorLingkungan": 0,
    "FaktorRisiko": 0,
    "Gejala": 73,
    "GejalaAkar": 4,
    "GejalaBatang": 10,
    "GejalaDaun": 26,
    "GejalaUmbi": 4,
    "Jamur": 8,
    "JurnalIlmiah": 0,
    "KelembapanTinggi": 0,
    "KondisiDrainase": 0,
    "KondisiTanah": 0,
    "OrganismeLain": 1,
    "Patogen": 28,
    "Pengendalian": 95,
    "PengendalianBiologis": 0,
    "PengendalianKimiawi": 0,
    "PengendalianKulturTeknis": 0,
    "PengendalianMekanis": 0,
    "PengendalianTerpadu": 0,
    "PenggunaanBenihTerinfeksi": 0,
    "Penyakit": 24,
    "PenyakitBakteri": 0,
    "PenyakitJamur": 0,
    "PenyakitLainnya": 0,
    "PenyakitVirus": 0,
    "PublikasiInstansi": 0,
    "Referensi": 1,
    "SanitasiLahanBuruk": 0,
    "Suhu": 0,
    "TanamanPangan": 3,
    "Virus": 3,
}

SNAPSHOT_OBJECT_PROPS = {
    "dijelaskanDalam": 24,
    "dikendalikanDengan": 95,
    "dipengaruhiOleh": 0,
    "disebabkanOleh": 34,
    "diserangPenyakit": 24,
    "memilikiGejala": 73,
    "memilikiReferensi": 24,
    "mengendalikanPenyakit": 95,
    "menyebabkanPenyakit": 34,
    "menyerangBagian": 32,
    "menyerangTanaman": 24,
    "merupakanGejalaDari": 73,
    "terdapatPada": 48,
}

SNAPSHOT_DATA_PROPS = {
    "deskripsiGejala": 73,
    "deskripsiPengendalian": 95,
    "deskripsiPenyakit": 0,
    "deskripsiTanaman": 0,
    "judulReferensi": 1,
    "namaIlmiah": 2,
    "namaIlmiahPatogen": 28,
    "namaPengendalian": 0,
    "namaPenulis": 1,
    "tahunTerbit": 1,
    "tingkatKeparahan": 0,
    "urlReferensi": 0,
}


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
                found.append((str(sub).rsplit("#", 1)[-1], str(prop).rsplit("#", 1)[-1], str(target).rsplit("#", 1)[-1], quantifier))
    return found


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
        langs = {
            obj.language
            for obj in self.graph.objects()
            if isinstance(obj, Literal) and obj.datatype != XSD.integer
        }
        self.assertEqual(langs, {"id"})

    def test_tahun_terbit_is_integer(self) -> None:
        values = list(self.graph.objects(None, KBR["tahunTerbit"]))
        self.assertEqual(values, [Literal(2021, datatype=XSD.integer)])

    def test_no_explicit_disease_category_assertion(self) -> None:
        for cls_name in ("PenyakitJamur", "PenyakitBakteri", "PenyakitVirus", "PenyakitLainnya"):
            with self.subTest(cls=cls_name):
                actual = set(self.graph.subjects(RDF.type, KBR[cls_name]))
                self.assertEqual(
                    actual,
                    set(),
                    "kelas hasil klasifikasi wajib hanya muncul lewat inferensi reasoner",
                )

    def test_every_disease_has_plant_symptom_reference(self) -> None:
        for disease in self.diseases:
            with self.subTest(disease=str(disease).rsplit("#", 1)[-1]):
                self.assertTrue(list(self.graph.objects(disease, KBR["menyerangTanaman"])))
                self.assertTrue(list(self.graph.objects(disease, KBR["memilikiGejala"])))
                self.assertTrue(list(self.graph.objects(disease, KBR["memilikiReferensi"])))

    def test_only_two_diseases_without_pathogen(self) -> None:
        with_pathogen = set(self.graph.subjects(KBR["disebabkanOleh"], None))
        without = {str(d).rsplit("#", 1)[-1] for d in self.diseases - with_pathogen}
        self.assertEqual(
            without,
            {"PenyakitBelangMottleKacangTanah", "NekrosisPadaTitikTunasCassavaBudNecrosisUbiKayu"},
        )

    def test_three_scope_plants(self) -> None:
        names = {str(p).rsplit("#", 1)[-1] for p in self.plants}
        self.assertEqual(names, {"KacangTanah", "UbiJalar", "UbiKayu"})
        scientific = {
            str(p).rsplit("#", 1)[-1]: str(next(self.graph.objects(p, KBR["namaIlmiah"])))
            for p in self.plants
            if list(self.graph.objects(p, KBR["namaIlmiah"]))
        }
        self.assertEqual(
            scientific,
            {
                "UbiJalar": "Ipomoea batatas L. (Lam)",
                "UbiKayu": "Manihot esculenta Crantz",
            },
        )

    def test_duplicate_disease_names_disambiguated(self) -> None:
        first = KBR["AntraknosaUbiKayuDIS031"]
        second = KBR["AntraknosaUbiKayuDIS110"]
        self.assertIn((first, RDF.type, KBR["Penyakit"]), self.graph)
        self.assertIn((second, RDF.type, KBR["Penyakit"]), self.graph)
        labels = {str(next(self.graph.objects(u, RDFS.label))) for u in (first, second)}
        self.assertEqual(labels, {"Antraknosa"})

    def test_inverse_materialized_on_sample(self) -> None:
        for prop, inverse in _inverse_pairs():
            with self.subTest(prop=prop):
                for subj, obj in list(self.graph.subject_objects(KBR[prop]))[:3]:
                    self.assertIn((obj, KBR[inverse], subj), self.graph)


class OntologyAxiomTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.graph = Graph()
        cls.graph.parse(data=ARTIFACT.read_text(encoding="utf-8"), format="turtle")

    def test_disjoint_pair_count(self) -> None:
        actual = list(cls_pairs(self.graph))
        self.assertEqual(len(actual), 43)

    def test_top_classes_are_pairwise_disjoint(self) -> None:
        pairs = set(cls_pairs(self.graph))
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
        self.assertEqual(len({frozenset(p) for p in pairs}), 5)
        for prop, inverse in pairs:
            with self.subTest(prop=prop):
                self.assertIn((KBR[prop], OWL.inverseOf, KBR[inverse]), self.graph)
                self.assertIn((KBR[inverse], OWL.inverseOf, KBR[prop]), self.graph)
        self.assertEqual(
            len(list(self.graph.subject_objects(OWL.inverseOf))), 10
        )

    def test_equivalent_classes_structure(self) -> None:
        equivalents = list(self.graph.subjects(OWL.equivalentClass, None))
        self.assertEqual(
            {str(u).rsplit("#", 1)[-1] for u in equivalents},
            {"PenyakitJamur", "PenyakitBakteri", "PenyakitVirus"},
        )
        for penyakit_cls, patogen_cls in tbox.EQUIVALENT_CLASSES:
            with self.subTest(cls=penyakit_cls):
                intersections = list(self.graph.objects(KBR[penyakit_cls], OWL.equivalentClass))
                self.assertEqual(len(intersections), 1)
                members = list(
                    self.graph.objects(intersections[0], OWL.intersectionOf)
                )
                self.assertEqual(len(members), 1)
                chain = list(Collection(self.graph, members[0]))
                self.assertEqual(len(chain), 2)
                self.assertEqual(chain[0], KBR["Penyakit"])
                self.assertEqual(
                    (chain[1], RDF.type, OWL.Restriction) in self.graph,
                    True,
                )
                self.assertIn(
                    (chain[1], OWL.someValuesFrom, KBR[patogen_cls]), self.graph
                )

    def test_restrictions_exactly_as_rancangan(self) -> None:
        found = set(_restriction_nodes(self.graph))
        expected = set(tbox.RESTRICTIONS)
        self.assertEqual(found, expected)

    def test_no_data_property_range_axiom(self) -> None:
        for name in tbox.DATA_PROPERTIES:
            with self.subTest(prop=name):
                self.assertEqual(
                    list(self.graph.objects(KBR[name], RDFS.range)),
                    [],
                    "range xsd:string bentrok dengan literal @id di OWL 2",
                )

    def test_object_property_domain_range(self) -> None:
        for name, spec in tbox.OBJECT_PROPERTIES.items():
            with self.subTest(prop=name):
                self.assertIn((KBR[name], RDFS.domain, KBR[spec["domain"]]), self.graph)
                self.assertIn((KBR[name], RDFS.range, KBR[spec["range"]]), self.graph)

    def test_ontology_header(self) -> None:
        headers = list(self.graph.subjects(RDF.type, OWL.Ontology))
        self.assertEqual(len(headers), 1)
        self.assertEqual(str(headers[0]), str(tbox.ONTOLOGY_IRI))


def cls_pairs(graph: Graph):
    for left, _, right in graph.triples((None, OWL.disjointWith, None)):
        yield str(left).rsplit("#", 1)[-1], str(right).rsplit("#", 1)[-1]


class BuildGateTest(unittest.TestCase):
    def test_fresh_build_has_no_errors(self) -> None:
        graph, _expected, errors, _builder = bo.build()
        self.assertEqual(errors, [])
        self.assertEqual(len(graph), EXPECTED_TRIPLES)


@unittest.skipUnless(shutil.which("java"), "Java tidak tersedia untuk HermiT")
class HermiTReasoningTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            import owlready2  # noqa: F401
        except ImportError as exc:  # pragma: no cover
            raise unittest.SkipTest(f"owlready2 tidak terpasang: {exc}")
        if not OWL_ARTIFACT.exists():
            raise AssertionError(
                f"artefak hilang: {OWL_ARTIFACT} — jalankan python build_ontology.py dulu"
            )
        from owlready2 import World, sync_reasoner

        cls.world = World()
        cls.onto = cls.world.get_ontology(
            "http://kbr.kelompok5.org/penyakit-tanaman-pangan"
        )
        with OWL_ARTIFACT.open("rb") as handle:
            cls.onto.load(fileobj=handle, format="rdfxml")
        sync_reasoner(cls.onto, debug=0)

    def test_ontology_is_consistent(self) -> None:
        nothing = [
            ind
            for ind in self.onto.individuals()
            if any(cls.name == "Nothing" for cls in ind.is_a if cls is not None)
        ]
        self.assertEqual(nothing, [], "tidak boleh ada individu owl:Nothing")

    def test_inferred_disease_categories(self) -> None:
        expected = {
            "PenyakitJamur": 7,
            "PenyakitBakteri": 1,
            "PenyakitVirus": 1,
            "PenyakitLainnya": 0,
        }
        for cls_name, count in expected.items():
            with self.subTest(cls=cls_name):
                cls = getattr(self.onto, cls_name)
                self.assertEqual(len(list(cls.instances())), count)

    def test_inferred_bakteri_example(self) -> None:
        cls = self.onto.PenyakitBakteri
        names = {ind.name for ind in cls.instances()}
        self.assertEqual(names, {"PenyakitLayuBakteriKacangTanah"})


if __name__ == "__main__":
    unittest.main()
