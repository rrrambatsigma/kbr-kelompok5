"""Gate test untuk ontologi OWL 2 (Tahap 4).

Semua test bersifat read-only terhadap artefak ``ontology.ttl``; satu test
gerbang (gate) membangun ulang ontologi lewat ``build_ontology.build()``.
Jalankan dari ``04_ontology``::

    python -m unittest discover -s tests -p "test_*.py"
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from rdflib import Graph, Literal, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS, XSD

ONTO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ONTO_DIR))

import build_ontology as bo  # noqa: E402
from tbox import KBR, KBRD  # noqa: E402

ARTIFACT = ONTO_DIR / "ontology.ttl"

SNAPSHOT_CLASSES = {
    "KnowledgeSource": 3,
    "Plant": 17,
    "Disease": 117,
    "Pathogen": 112,
    "Symptom": 609,
    "ControlMeasure": 532,
    "DiseaseControl": 452,
    "ChapterControl": 80,
    "SourceTable": 3,
    "CassavaSourceTable": 3,
    "SourceTableRow": 19,
    "EvidenceChunk": 359,
    "SourceSection": 122,
    "Fungus": 57,
    "Bacterium": 10,
    "Virus": 16,
    "Nematode": 7,
    "Phytoplasma": 1,
    "Oomycete": 2,
}

SNAPSHOT_PROPERTIES = {
    "occursIn": 117,
    "causedBy": 139,
    "hasSymptom": 609,
    "observedOn": 609,
    "appliesTo": 452,
    "appliesToPlant": 532,
    "hasEvidence": 1593,
    "hasTaxonEvidence": 9,
    "hasSourceDocument": 1448,
    "locatedInSection": 110,
    "containsSection": 107,
    "isTableRowOf": 19,
    "aboutPlant": 3,
}

INVERSE_PAIRS = [
    ("occursIn", "hasDisease"),
    ("causedBy", "causes"),
    ("hasSymptom", "symptomOf"),
    ("appliesTo", "hasControlMeasure"),
    ("containsSection", "sectionOf"),
    ("isTableRowOf", "hasTableRow"),
]


def label_of(graph: Graph, uri: URIRef) -> str | None:
    for value in graph.objects(uri, RDFS.label):
        return str(value)
    return None


class OntologyArtifactTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not ARTIFACT.exists():
            raise AssertionError(
                f"artefak hilang: {ARTIFACT} — jalankan python build_ontology.py dulu"
            )
        cls.graph = Graph()
        cls.graph.parse(data=ARTIFACT.read_text(encoding="utf-8"), format="turtle")
        cls.diseases = set(cls.graph.subjects(RDF.type, KBR.Disease))
        cls.plants = set(cls.graph.subjects(RDF.type, KBR.Plant))

    def test_artifact_triple_count(self) -> None:
        self.assertEqual(len(self.graph), 24652)

    def test_snapshot_classes(self) -> None:
        for cls_name, count in SNAPSHOT_CLASSES.items():
            with self.subTest(cls=cls_name):
                actual = len(list(self.graph.subjects(RDF.type, KBR[cls_name])))
                self.assertEqual(actual, count)

    def test_snapshot_properties(self) -> None:
        for prop, count in SNAPSHOT_PROPERTIES.items():
            with self.subTest(prop=prop):
                actual = len(list(self.graph.triples((None, KBR[prop], None))))
                self.assertEqual(actual, count)

    def test_named_individuals(self) -> None:
        actual = len(list(self.graph.subjects(RDF.type, OWL.NamedIndividual)))
        self.assertEqual(actual, 1932)

    def test_no_empty_literals(self) -> None:
        for obj in self.graph.objects():
            if isinstance(obj, Literal):
                self.assertNotEqual(str(obj), "", f"literal kosong pada {obj}")

    def test_labels_use_indonesian_language_tag(self) -> None:
        langs = {
            str(literal.language)
            for literal in self.graph.objects(None, RDFS.label)
        }
        self.assertEqual(langs, {"id"})

    def test_guardrail_diseases_without_pathogen(self) -> None:
        with_pathogen = set(self.graph.subjects(KBR.causedBy, None))
        self.assertEqual(len(self.diseases - with_pathogen), 7)

    def test_guardrail_diseases_without_symptom(self) -> None:
        with_symptom = set(self.graph.subjects(KBR.hasSymptom, None))
        self.assertEqual(len(self.diseases - with_symptom), 19)

    def test_plant_016_has_no_disease(self) -> None:
        victims = list(self.graph.subjects(KBR.occursIn, KBRD["PLANT_016"]))
        self.assertEqual(victims, [])

    def test_plant_005_has_17_diseases(self) -> None:
        cassava = list(self.graph.subjects(KBR.occursIn, KBRD["PLANT_005"]))
        self.assertEqual(len(cassava), 17)

    def test_pathogen_id_collision_disambiguated(self) -> None:
        doc2 = KBRD["PAT_106"]
        doc3 = KBRD["PAT_106_DOC003"]
        self.assertIn((doc2, RDF.type, KBR.Pathogen), self.graph)
        self.assertIn((doc3, RDF.type, KBR.Pathogen), self.graph)
        self.assertEqual(label_of(self.graph, doc2), "Ipomovirus")
        self.assertEqual(label_of(self.graph, doc3), "Rhizoctonia solani")

    def test_unnumbered_table_rows_exist(self) -> None:
        first = KBRD["T5_2_BATANG_R_unnumbered_1"]
        second = KBRD["T5_2_BATANG_R_unnumbered_2"]
        for uri in (first, second):
            with self.subTest(row=uri):
                self.assertIn((uri, RDF.type, KBR.SourceTableRow), self.graph)
                table = list(self.graph.objects(uri, KBR.isTableRowOf))
                self.assertEqual(table, [KBRD["T5_2_BATANG"]])

    def test_inverse_materialized_on_sample(self) -> None:
        disease = next(iter(sorted(self.diseases, key=str)))
        plant = next(iter(self.graph.objects(disease, KBR.occursIn)), None)
        self.assertIsNotNone(plant)
        self.assertIn((plant, KBR.hasDisease, disease), self.graph)


class ShroiqAxiomTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.graph = Graph()
        cls.graph.parse(data=ARTIFACT.read_text(encoding="utf-8"), format="turtle")

    def test_s_transitive_asymmetric_irreflexive(self) -> None:
        for prop_type in (OWL.TransitiveProperty, OWL.AsymmetricProperty, OWL.IrreflexiveProperty):
            with self.subTest(prop_type=prop_type):
                self.assertIn((KBR.containsSection, RDF.type, prop_type), self.graph)

    def test_h_role_hierarchy(self) -> None:
        self.assertIn(
            (KBR.hasTaxonEvidence, RDFS.subPropertyOf, KBR.hasEvidence), self.graph
        )

    def test_r_property_chains(self) -> None:
        chains: dict[URIRef, tuple] = {}
        for super_prop, _, node in self.graph.triples((None, OWL.propertyChainAxiom, None)):
            chains[super_prop] = tuple(Collection(self.graph, node))
        self.assertEqual(len(chains), 2)
        self.assertEqual(
            chains[KBR.appliesToPlant], (KBR.appliesTo, KBR.occursIn)
        )
        self.assertEqual(
            chains[KBR.occursIn], (KBR.hasSymptom, KBR.observedOn)
        )

    def test_o_nominals_cassava_tables(self) -> None:
        for equivalent in self.graph.objects(KBR.CassavaSourceTable, OWL.equivalentClass):
            for one_of in self.graph.objects(equivalent, OWL.oneOf):
                members = set(Collection(self.graph, one_of))
                self.assertEqual(
                    members,
                    {
                        KBRD["T5_1_DAUN"],
                        KBRD["T5_2_BATANG"],
                        KBRD["T5_3_AKAR"],
                    },
                )

    def test_i_inverse_of_axioms(self) -> None:
        for prop, inverse in INVERSE_PAIRS:
            with self.subTest(prop=prop):
                self.assertIn((KBR[prop], OWL.inverseOf, KBR[inverse]), self.graph)
                self.assertIn((KBR[inverse], OWL.inverseOf, KBR[prop]), self.graph)

    def test_inverse_materialized_both_directions(self) -> None:
        for prop, inverse in INVERSE_PAIRS:
            with self.subTest(prop=prop):
                for subj, obj in self.graph.subject_objects(KBR[prop]):
                    self.assertIn((obj, KBR[inverse], subj), self.graph)

    def test_q_functional_properties(self) -> None:
        for prop in ("occursIn", "observedOn", "isTableRowOf"):
            with self.subTest(prop=prop):
                self.assertIn((KBR[prop], RDF.type, OWL.FunctionalProperty), self.graph)

    def test_d_datatypes(self) -> None:
        integers = [
            literal
            for literal in self.graph.objects(None, KBR.chapterNumber)
            if isinstance(literal, Literal) and literal.datatype == XSD.integer
        ]
        self.assertTrue(integers)

    def test_disjoint_classes_axioms(self) -> None:
        self.assertEqual(
            len(list(self.graph.subjects(RDF.type, OWL.AllDisjointClasses))), 3
        )


class BuildGateTest(unittest.TestCase):
    def test_fresh_build_has_no_errors(self) -> None:
        graph, _expected, errors, _builder = bo.build()
        self.assertEqual(errors, [])
        self.assertEqual(len(graph), 24652)


if __name__ == "__main__":
    unittest.main()
