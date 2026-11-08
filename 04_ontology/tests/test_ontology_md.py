"""Gate test untuk ontology_md.ttl (enrichment 7 tanaman utama)."""

from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS

ONTO_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = ONTO_DIR.parent
PTP = "http://kbr.kelompok5.org/penyakit-tanaman-pangan#"
KBR = lambda name: URIRef(PTP + name)  # noqa: E731

ARTIFACT = ONTO_DIR / "ontology_md.ttl"
CANONICAL = ONTO_DIR / "ontology.ttl"
REPORT = ONTO_DIR / "extraction_report_md.json"
ENTITIES = PROJECT_ROOT / "03_knowledge_tables" / "auto" / "DOC002_md" / "DOC002_enrichment_entities.csv"

SCOPE_PLANTS = {"Padi", "Kedelai", "Jagung", "UbiJalar", "UbiKayu", "KacangTanah", "KacangHijau"}


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
        cls.entities = read_csv(ENTITIES)

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
        self.assertEqual(len(list(self.graph.triples((None, KBR("deskripsiPenyakit"), None)))), 57)
        self.assertEqual(len(list(self.graph.triples((None, KBR("tingkatKeparahan"), None)))), 10)
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
        self.assertEqual(self.report["facts"], 98)
        self.assertEqual(self.report["entities"], 93)

    def test_canonical_does_not_get_md_property(self) -> None:
        self.assertFalse(list(self.canonical.triples((KBR("memilikiKondisiTumbuh"), None, None))))


if __name__ == "__main__":
    unittest.main()
