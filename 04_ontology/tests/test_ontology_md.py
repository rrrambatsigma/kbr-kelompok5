"""Gate test untuk ontology_md.ttl (enrichment 7 tanaman utama)."""

from __future__ import annotations

import csv
import json
import shutil
import unittest
from pathlib import Path

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS

ONTO_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = ONTO_DIR.parent
PTP = "http://kbr.kelompok5.org/penyakit-tanaman-pangan#"
KBR = lambda name: URIRef(PTP + name)  # noqa: E731

ARTIFACT = ONTO_DIR / "ontology_md.ttl"
OWL_ARTIFACT = ONTO_DIR / "ontology_md.owl"
CANONICAL = ONTO_DIR / "ontology.ttl"
REPORT = ONTO_DIR / "extraction_report_md.json"
TABLE_DIR = PROJECT_ROOT / "03_knowledge_tables"
FACTS = TABLE_DIR / "auto" / "DOC002_md" / "DOC002_enrichment_facts.csv"
ENTITIES = TABLE_DIR / "auto" / "DOC002_md" / "DOC002_enrichment_entities.csv"
DESCRIPTIONS = TABLE_DIR / "auto" / "DOC002_md" / "DOC002_descriptions.csv"

SCOPE_PLANTS = {"Padi", "Kedelai", "Jagung", "UbiJalar", "UbiKayu", "KacangTanah", "KacangHijau"}

COMMENT_GAPS = {
    "KondisiIklimBasah",
    "KondisiKelembapanUdaraRendah",
    "KondisiKelembapanUdaraSedang",
    "KondisiKelembapanUdaraTinggi",
    "KondisiTanahBasa",
    "KondisiTanahBerpasir",
    "KondisiTanahLiat",
    "KondisiTanahNetral",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


class TestOntologyMd(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.graph = Graph()
        cls.graph.parse(ARTIFACT, format="turtle")
        cls.canonical = Graph()
        cls.canonical.parse(CANONICAL, format="turtle")
        cls.report = json.loads(REPORT.read_text(encoding="utf-8"))
        cls.facts = read_csv(FACTS)
        cls.entities = read_csv(ENTITIES)
        cls.descriptions = read_csv(DESCRIPTIONS)

    def objects(self, subject: str, predicate: str) -> set:
        return set(self.graph.objects(KBR(subject), KBR(predicate)))

    def test_artifact_and_report_exist(self) -> None:
        self.assertTrue(ARTIFACT.exists())
        self.assertTrue(REPORT.exists())
        self.assertEqual(self.report["output"], "04_ontology/ontology_md.ttl")
        self.assertTrue(self.report["canonical_untouched"])

    def test_property_definition(self) -> None:
        prop = KBR("memilikiKondisiTumbuh")
        self.assertIn((prop, RDF.type, OWL.ObjectProperty), self.graph)
        self.assertIn((prop, RDFS.domain, KBR("TanamanPangan")), self.graph)
        self.assertIn((prop, RDFS.range, KBR("FaktorLingkungan")), self.graph)
        self.assertTrue(self.graph.value(prop, RDFS.label))

    def test_scope_plants_only(self) -> None:
        plants = set(self.graph.subjects(RDF.type, KBR("TanamanPangan")))
        self.assertEqual({str(plant).split("#")[-1] for plant in plants}, SCOPE_PLANTS)
        self.assertNotIn(KBR("Kentang"), set(self.graph.subjects(RDF.type, KBR("TanamanPangan"))))

    def test_condition_vocabulary(self) -> None:
        conditions = {
            row["entity_local"]
            for row in self.entities
            if row["entity_class"] == "FaktorLingkungan"
        }
        self.assertEqual(len(conditions), 25)
        for local in conditions:
            uri = KBR(local)
            self.assertIn((uri, RDF.type, KBR("FaktorLingkungan")), self.graph)
            self.assertTrue(self.graph.value(uri, RDFS.label), local)

    def test_fact_counts(self) -> None:
        self.assertEqual(len(self.objects("Kedelai", "memilikiKondisiTumbuh")), 3)
        self.assertIn(KBR("KondisiTanahSubur"), self.objects("UbiKayu", "memilikiKondisiTumbuh"))
        self.assertEqual(len(list(self.graph.triples((None, KBR("deskripsiTanaman"), None)))), 7)
        self.assertEqual(len(list(self.graph.triples((None, KBR("deskripsiPenyakit"), None)))), 53)
        self.assertEqual(
            len(list(self.graph.triples((None, KBR("tingkatKeparahan"), None)))),
            self.report["predicate_counts"]["tingkatKeparahan"],
        )
        self.assertGreaterEqual(len(list(self.graph.triples((None, KBR("dipengaruhiOleh"), None)))), 13)

    def test_literals_are_indonesian(self) -> None:
        for predicate in ("deskripsiTanaman", "deskripsiPenyakit", "tingkatKeparahan"):
            for obj in self.graph.objects(None, KBR(predicate)):
                self.assertIsInstance(obj, Literal, predicate)
                self.assertEqual(obj.language, "id", predicate)
                self.assertTrue(str(obj).strip(), predicate)

    def test_condition_objects_are_known(self) -> None:
        known = {
            row["entity_local"]
            for row in self.entities
            if row["entity_class"] == "FaktorLingkungan"
        }
        for obj in self.graph.objects(None, KBR("memilikiKondisiTumbuh")):
            self.assertIn(str(obj).split("#")[-1], known)

    def test_report_matches_graph(self) -> None:
        self.assertEqual(self.report["total_triples"], len(self.graph))
        self.assertEqual(self.report["base_triples"], len(self.canonical))
        self.assertEqual(self.report["added_triples"], len(self.graph) - len(self.canonical))
        self.assertEqual(self.report["facts"], len(self.facts))
        self.assertEqual(self.report["entities"], len(self.entities))
        self.assertEqual(self.report["descriptions"], len(self.descriptions))
        self.assertEqual(
            self.report["named_individuals"],
            sum(1 for _ in self.graph.subjects(RDF.type, OWL.NamedIndividual)),
        )

    def test_entities_are_named_individuals(self) -> None:
        for row in self.entities:
            uri = KBR(row["entity_local"])
            self.assertIn((uri, RDF.type, OWL.NamedIndividual), self.graph, row["entity_local"])

    def test_condition_individuals_are_named(self) -> None:
        conditions = {
            row["entity_local"]
            for row in self.entities
            if row["entity_class"] == "FaktorLingkungan"
        }
        self.assertEqual(len(conditions), 25)
        for local in conditions:
            self.assertIn(
                (KBR(local), RDF.type, OWL.NamedIndividual),
                self.graph,
                local,
            )

    def test_every_description_row_is_in_graph(self) -> None:
        def nl(text: str) -> str:
            return text.replace("\r\n", "\n").replace("\r", "\n")

        comments = {
            (subject, nl(str(literal)), literal.language)
            for subject, literal in self.graph.subject_objects(RDFS.comment)
            if (subject, RDF.type, OWL.Class) in self.graph
            or (subject, RDF.type, OWL.NamedIndividual) in self.graph
        }
        self.assertEqual(len(self.descriptions), self.report["descriptions"])
        for row in self.descriptions:
            key = (
                KBR(row["subject_local"]),
                nl(row["literal_value"]),
                row["literal_lang"] or "id",
            )
            self.assertIn(key, comments, row["subject_local"])

    def test_comment_coverage(self) -> None:
        def commented_set(nodes) -> set[str]:
            return {
                str(node).split("#")[-1]
                for node in nodes
                if (node, RDFS.comment, None) in self.graph
            }

        classes = {
            str(cls).split("#")[-1]
            for cls in self.graph.subjects(RDF.type, OWL.Class)
            if not isinstance(cls, BNode)
        }
        individuals = {
            str(ind).split("#")[-1]
            for ind in self.graph.subjects(RDF.type, OWL.NamedIndividual)
            if not isinstance(ind, BNode)
        }
        commented_classes = commented_set(
            cls
            for cls in self.graph.subjects(RDF.type, OWL.Class)
            if not isinstance(cls, BNode)
        )
        commented_individuals = commented_set(
            ind
            for ind in self.graph.subjects(RDF.type, OWL.NamedIndividual)
            if not isinstance(ind, BNode)
        )

        self.assertEqual(len(individuals), self.report["named_individuals"])
        self.assertEqual(len(commented_classes), self.report["classes_with_comment"])
        self.assertEqual(classes - commented_classes, set())
        self.assertEqual(individuals - commented_individuals, COMMENT_GAPS)

    def test_comments_are_indonesian_literals(self) -> None:
        for obj in self.graph.objects(None, RDFS.comment):
            self.assertIsInstance(obj, Literal)
            self.assertEqual(obj.language, "id")
            self.assertTrue(str(obj).strip())

    def test_canonical_does_not_get_md_property(self) -> None:
        self.assertFalse(list(self.canonical.triples((KBR("memilikiKondisiTumbuh"), None, None))))


@unittest.skipUnless(shutil.which("java"), "Java tidak tersedia untuk HermiT")
class TestOntologyMdReasoning(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            import owlready2  # noqa: F401
        except ImportError as exc:  # pragma: no cover
            raise unittest.SkipTest(f"owlready2 tidak terpasang: {exc}")
        if not OWL_ARTIFACT.exists():
            raise AssertionError(
                f"artefak hilang: {OWL_ARTIFACT} - jalankan python build_ontology_md.py dulu"
            )

        from owlready2 import World, sync_reasoner

        cls.world = World()
        cls.onto = cls.world.get_ontology(PTP.rstrip("#"))
        with OWL_ARTIFACT.open("rb") as handle:
            cls.onto.load(fileobj=handle, format="rdfxml")
        sync_reasoner(cls.onto, debug=0)

    def test_ontology_is_consistent(self) -> None:
        nothing = [
            ind
            for ind in self.onto.individuals()
            if any(getattr(cls, "name", None) == "Nothing" for cls in ind.is_a if cls is not None)
        ]
        self.assertEqual(nothing, [], "tidak boleh ada individu owl:Nothing")

    def test_enriched_conditions_are_typed(self) -> None:
        self.assertIn(self.onto.KondisiSuhuTinggi, self.onto.Suhu.instances())
        self.assertIn(self.onto.KondisiKelembapanTinggi, self.onto.KelembapanUdara.instances())


if __name__ == "__main__":
    unittest.main()
