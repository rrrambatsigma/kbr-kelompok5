"""Gate test untuk ontologi OWL 2 Penyakit Tanaman Pangan Indonesia.

Sebagian test bersifat read-only terhadap artefak ``ontology.ttl``; satu test
gerbang membangun ulang ontologi lewat ``build_ontology.build()``; satu test
menjalankan reasoner HermiT lewat owlready2 bila Java tersedia.
Jalankan dari ``04_ontology``::

    python -m unittest discover -s tests -p "test_*.py"
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import unittest
from collections import defaultdict
from pathlib import Path

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS, XSD

ONTO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ONTO_DIR))

import build_ontology as bo  # noqa: E402
import tbox  # noqa: E402
from tbox import KBR, PROV  # noqa: E402

ARTIFACT = ONTO_DIR / "ontology.ttl"
OWL_ARTIFACT = ONTO_DIR / "ontology.owl"
REPORT = ONTO_DIR / "extraction_report.json"

SCOPE_PLANTS = {"Padi", "Kedelai", "Jagung", "UbiJalar", "UbiKayu", "KacangTanah", "KacangHijau"}
FORBIDDEN_PLANTS = {"Kentang", "Kubis", "Cabai", "Tomat", "KacangPanjang", "Apel", "Lada", "Kopi", "KelapaSawit"}
LOCAL_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")
RAW_ID_RE = re.compile(r"^(?:DIS|PAT|GEJ|PEN|VAR|FASE)\d")
TAXON_CATEGORY = {
    "jamur": "PenyakitJamur",
    "bakteri": "PenyakitBakteri",
    "virus": "PenyakitVirus",
    "nematoda": "PenyakitNematoda",
    "oomycete": "PenyakitOomycete",
    "fitoplasma": "PenyakitFitoplasma",
}


def local(node: URIRef) -> str:
    return str(node).rsplit("#", 1)[-1]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def inverse_pairs() -> list[tuple[str, str]]:
    return [
        (name, spec["inverse"])
        for name, spec in tbox.OBJECT_PROPERTIES.items()
        if spec.get("inverse")
    ]


def is_descendant(cls_name: str, ancestor: str) -> bool:
    seen: set[str] = set()
    current: str | None = cls_name
    while current and current not in seen:
        if current == ancestor:
            return True
        seen.add(current)
        current = tbox.CLASSES.get(current, (None, None, None))[1]
    return False


def restriction_nodes(graph: Graph) -> set[tuple[str, str, str, str]]:
    found: set[tuple[str, str, str, str]] = set()
    for sub, _, restr in graph.triples((None, RDFS.subClassOf, None)):
        if (restr, RDF.type, OWL.Restriction) not in graph:
            continue
        prop = next(graph.objects(restr, OWL.onProperty), None)
        if prop is None:
            continue
        prop_name = "prov:wasDerivedFrom" if str(prop) == str(PROV.wasDerivedFrom) else local(prop)
        for quantifier, pred in (("some", OWL.someValuesFrom), ("only", OWL.allValuesFrom)):
            target = next(graph.objects(restr, pred), None)
            if target is not None:
                found.add((local(sub), prop_name, local(target), quantifier))
        if (restr, OWL.minCardinality, None) in graph or (restr, OWL.minQualifiedCardinality, None) in graph:
            target = next(graph.objects(restr, OWL.onClass), None)
            if target is not None:
                found.add((local(sub), prop_name, local(target), "min1"))
    return found


def disjoint_groups(graph: Graph) -> set[frozenset[str]]:
    groups: set[frozenset[str]] = set()
    for node in graph.subjects(RDF.type, OWL.AllDisjointClasses):
        members = graph.value(node, OWL.members)
        if members is not None:
            groups.add(frozenset(local(member) for member in Collection(graph, members)))
    return groups


class OntologyArtifactTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not ARTIFACT.exists():
            raise AssertionError(
                f"artefak hilang: {ARTIFACT} — jalankan python build_ontology.py dulu"
            )
        cls.graph = Graph()
        cls.graph.parse(ARTIFACT, format="turtle")
        cls.report = read_json(REPORT)
        cls.summary = cls.report["summary"]
        cls.named = set(cls.graph.subjects(RDF.type, OWL.NamedIndividual))
        cls.diseases = set(cls.graph.subjects(RDF.type, KBR["Penyakit"]))
        cls.plants = set()
        for cls_name in tbox.NOMINAL_CLASSES:
            cls.plants |= set(cls.graph.subjects(RDF.type, KBR[cls_name]))

    def test_artifact_matches_report(self) -> None:
        self.assertEqual(len(self.graph), self.summary["triples"])
        self.assertEqual(len(self.named), self.summary["named_individuals"])
        self.assertEqual(len(self.diseases), self.summary["diseases"])
        self.assertEqual(len(self.plants), self.summary["plants"])
        classes = {
            cls
            for cls in self.graph.subjects(RDF.type, OWL.Class)
            if isinstance(cls, URIRef) and str(cls).startswith(tbox.PTP)
        }
        object_props = {
            prop
            for prop in self.graph.subjects(RDF.type, OWL.ObjectProperty)
            if isinstance(prop, URIRef) and str(prop).startswith(tbox.PTP)
        }
        data_props = {
            prop
            for prop in self.graph.subjects(RDF.type, OWL.DatatypeProperty)
            if isinstance(prop, URIRef) and str(prop).startswith(tbox.PTP)
        }
        self.assertEqual(len(classes), self.summary["classes"])
        self.assertEqual(len(object_props), self.summary["object_properties"])
        self.assertEqual(len(data_props), self.summary["data_properties"])

    def test_scope_plants(self) -> None:
        self.assertEqual({local(plant) for plant in self.plants}, SCOPE_PLANTS)
        self.assertFalse({local(plant) for plant in self.plants} & FORBIDDEN_PLANTS)
        for cls_name, members in tbox.NOMINAL_CLASSES.items():
            with self.subTest(cls=cls_name):
                for member in members:
                    self.assertIn((KBR[member], RDF.type, KBR[cls_name]), self.graph)

    def test_local_name_hygiene(self) -> None:
        nodes = set(self.graph.subjects(RDF.type, OWL.Class))
        nodes |= set(self.graph.subjects(RDF.type, OWL.ObjectProperty))
        nodes |= set(self.graph.subjects(RDF.type, OWL.DatatypeProperty))
        nodes |= self.named
        for node in nodes:
            if not isinstance(node, URIRef) or not str(node).startswith(tbox.PTP):
                continue
            name = local(node)
            with self.subTest(local=name):
                self.assertNotIn("#", name)
                self.assertNotIn("_", name)
                self.assertNotIn(" ", name)
                self.assertRegex(name, LOCAL_NAME_RE)
                self.assertIsNone(RAW_ID_RE.match(name))

    def test_no_class_individual_collision(self) -> None:
        classes = {
            local(cls)
            for cls in self.graph.subjects(RDF.type, OWL.Class)
            if isinstance(cls, URIRef) and str(cls).startswith(tbox.PTP)
        }
        self.assertFalse(classes & {local(ind) for ind in self.named})

    def test_labels_and_comments_present(self) -> None:
        nodes = set(self.graph.subjects(RDF.type, OWL.Class))
        nodes |= set(self.graph.subjects(RDF.type, OWL.ObjectProperty))
        nodes |= set(self.graph.subjects(RDF.type, OWL.DatatypeProperty))
        nodes |= self.named
        for node in nodes:
            if not isinstance(node, URIRef) or not str(node).startswith(tbox.PTP):
                continue
            with self.subTest(local=local(node)):
                self.assertTrue(list(self.graph.objects(node, RDFS.label)))
                self.assertTrue(list(self.graph.objects(node, RDFS.comment)))

    def test_no_empty_literals(self) -> None:
        for obj in self.graph.objects():
            if isinstance(obj, Literal):
                self.assertNotEqual(str(obj), "", f"literal kosong pada {obj}")

    def test_literals_are_indonesian_or_typed(self) -> None:
        for obj in self.graph.objects():
            if isinstance(obj, Literal) and obj.language:
                self.assertEqual(obj.language, "id", f"literal @{obj.language}: {obj}")

    def test_tahun_terbit_is_integer(self) -> None:
        values = list(self.graph.objects(None, KBR["tahunTerbit"]))
        self.assertTrue(values)
        for value in values:
            self.assertIsInstance(value, Literal)
            self.assertEqual(value.datatype, XSD.integer)
            self.assertGreaterEqual(int(value), 1900)

    def test_every_disease_has_core_links(self) -> None:
        for disease in self.diseases:
            with self.subTest(disease=local(disease)):
                self.assertTrue(list(self.graph.objects(disease, KBR["menyerangTanaman"])))
                self.assertTrue(list(self.graph.objects(disease, KBR["memilikiGejala"])))
                self.assertTrue(list(self.graph.objects(disease, KBR["memilikiReferensi"])))
                self.assertTrue(list(self.graph.objects(disease, KBR["didukungOleh"])))

    def test_disease_without_pathogen_matches_report(self) -> None:
        with_pathogen = set(self.graph.subjects(KBR["disebabkanOleh"], None))
        without = {local(disease) for disease in self.diseases - with_pathogen}
        self.assertEqual(without, set(self.report["data_quality"]["diseases_without_pathogen"]))

    def test_disease_categories_are_inferred_not_asserted(self) -> None:
        for cls_name in {cls for cls, _ in tbox.EQUIVALENT_CLASSES} | {"PenyakitPenyebabTidakDiketahui"}:
            with self.subTest(cls=cls_name):
                self.assertEqual(set(self.graph.subjects(RDF.type, KBR[cls_name])), set())

    def test_evidence_integrity(self) -> None:
        evidence = set(self.graph.objects(None, KBR["didukungOleh"]))
        self.assertTrue(evidence)
        for node in evidence:
            with self.subTest(evidence=local(node)):
                types = {local(cls) for cls in self.graph.objects(node, RDF.type) if isinstance(cls, URIRef)}
                self.assertTrue(any(is_descendant(cls, "BuktiSumber") for cls in types))
                self.assertTrue(list(self.graph.objects(node, KBR["kutipanSumber"])))
                self.assertTrue(list(self.graph.objects(node, KBR["kutipanNormalisasi"])))
                self.assertTrue(list(self.graph.objects(node, KBR["dokumenSumber"])))
                self.assertTrue(list(self.graph.objects(node, PROV.wasDerivedFrom)))

    def test_references_are_books(self) -> None:
        references = set(self.graph.objects(None, PROV.wasDerivedFrom))
        self.assertTrue(references)
        for reference in references:
            with self.subTest(reference=local(reference)):
                self.assertIn((reference, RDF.type, KBR["Buku"]), self.graph)
                self.assertTrue(list(self.graph.objects(reference, KBR["judulReferensi"])))
                self.assertTrue(list(self.graph.objects(reference, KBR["tahunTerbit"])))

    def test_inverse_properties_materialized(self) -> None:
        for prop, inverse in inverse_pairs():
            with self.subTest(prop=prop):
                for subj, obj in self.graph.subject_objects(KBR[prop]):
                    self.assertIn((obj, KBR[inverse], subj), self.graph)

    def test_canonical_symptoms(self) -> None:
        canonicals = {
            local(ind)
            for ind in self.graph.subjects(RDF.type, KBR["GejalaKanonik"])
        }
        self.assertEqual(canonicals, set(bo.CANONICAL_SYMPTOMS))
        mapped = set(self.graph.subjects(KBR["memilikiGejalaKanonik"], None))
        self.assertEqual(len(mapped), self.report["canonical_symptoms"]["canonical_groups"])
        for observation in mapped:
            with self.subTest(observation=local(observation)):
                types = {local(cls) for cls in self.graph.objects(observation, RDF.type) if isinstance(cls, URIRef)}
                self.assertTrue(any(is_descendant(cls, "Gejala") for cls in types))
                self.assertEqual(len(list(self.graph.objects(observation, KBR["memilikiGejalaKanonik"]))), 1)
                self.assertTrue(list(self.graph.objects(observation, KBR["terdapatPada"])))

    def test_unmapped_symptoms_match_report(self) -> None:
        symptom_observations = set(self.graph.objects(None, KBR["memilikiGejala"]))
        mapped = set(self.graph.subjects(KBR["memilikiGejalaKanonik"], None))
        self.assertEqual(len(symptom_observations - mapped), self.report["data_quality"]["unmapped_symptoms"])
        self.assertEqual(len(symptom_observations), self.report["canonical_symptoms"]["total"])

    def test_control_actions_and_categories(self) -> None:
        for action, spec in bo.CONTROL_ACTIONS.items():
            with self.subTest(action=action):
                uri = KBR[action]
                self.assertIn((uri, RDF.type, OWL.NamedIndividual), self.graph)
                self.assertIn((uri, RDF.type, KBR[spec["category"]]), self.graph)
                self.assertTrue(list(self.graph.objects(uri, RDFS.label)))
        for disease, action in self.graph.subject_objects(KBR["dikendalikanDengan"]):
            self.assertTrue(list(self.graph.objects(disease, RDF.type, KBR["Penyakit"])))
            types = {local(cls) for cls in self.graph.objects(action, RDF.type) if isinstance(cls, URIRef)}
            self.assertTrue(any(is_descendant(cls, "Pengendalian") for cls in types))

    def test_environment_observations(self) -> None:
        numeric = self.report["environment"]["numeric"]
        numeric_nodes = set(self.graph.subjects(RDF.type, KBR["ObservasiLingkungan"]))
        self.assertEqual(len(numeric_nodes), len(numeric))
        for node in numeric_nodes:
            with self.subTest(node=local(node)):
                types = {local(cls) for cls in self.graph.objects(node, RDF.type) if isinstance(cls, URIRef)}
                self.assertTrue(any(is_descendant(cls, "FaktorLingkungan") for cls in types))
                self.assertTrue(any(is_descendant(cls, "FaktorRisiko") for cls in types))
                self.assertTrue(
                    list(self.graph.objects(node, KBR["nilaiTunggal"]))
                    or list(self.graph.objects(node, KBR["nilaiMin"]))
                    or list(self.graph.objects(node, KBR["nilaiMaks"]))
                )
                units = {str(unit) for unit in self.graph.objects(node, KBR["satuan"])}
                self.assertTrue(units & {"°C", "%"})
        for row in self.report["environment"]["qualitative"]:
            with self.subTest(condition=row["condition"]):
                self.assertIn((KBR[row["condition"]], RDF.type, OWL.NamedIndividual), self.graph)
                self.assertTrue(list(self.graph.objects(KBR[row["condition"]], KBR["memengaruhiPenyakit"])))

    def test_varieties_and_phases(self) -> None:
        for row in self.report["varieties"]["items"]:
            with self.subTest(variety=row["local"]):
                self.assertIn((KBR[row["local"]], RDF.type, KBR["Varietas"]), self.graph)
                self.assertIn((KBR[row["plant"]], KBR["memilikiVarietas"], KBR[row["local"]]), self.graph)
        for row in self.report["phases"]["links"]:
            with self.subTest(phase=row["phase"]):
                self.assertIn((KBR[row["phase"]], RDF.type, OWL.NamedIndividual), self.graph)
                self.assertIn((KBR[row["disease"]], KBR["menyerangFase"], KBR[row["phase"]]), self.graph)


class OntologyAxiomTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.graph = Graph()
        cls.graph.parse(ARTIFACT, format="turtle")

    def test_top_classes_are_pairwise_disjoint(self) -> None:
        for i, left in enumerate(tbox.TOP_DOMAINS):
            for right in tbox.TOP_DOMAINS[i + 1:]:
                with self.subTest(pair=(left, right)):
                    self.assertIn((KBR[left], OWL.disjointWith, KBR[right]), self.graph)
                    self.assertIn((KBR[right], OWL.disjointWith, KBR[left]), self.graph)

    def test_all_disjoint_groups(self) -> None:
        self.assertEqual(
            disjoint_groups(self.graph),
            {frozenset(group) for group in tbox.ALL_DISJOINT_GROUPS},
        )

    def test_symptom_part_classes_are_not_disjoint(self) -> None:
        groups = disjoint_groups(self.graph)
        self.assertFalse(any("GejalaDaun" in group for group in groups))

    def test_subclass_taxonomy(self) -> None:
        for child, (_label, parent, _comment) in tbox.CLASSES.items():
            if not parent:
                continue
            with self.subTest(child=child):
                self.assertIn((KBR[child], RDFS.subClassOf, KBR[parent]), self.graph)

    def test_inverse_of_axioms(self) -> None:
        pairs = inverse_pairs()
        declared = {
            frozenset((local(sub), local(obj)))
            for sub, obj in self.graph.subject_objects(OWL.inverseOf)
        }
        self.assertEqual(declared, {frozenset(pair) for pair in pairs})

    def test_equivalent_classes_structure(self) -> None:
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

    def test_nominal_one_of(self) -> None:
        for cls_name, members in tbox.NOMINAL_CLASSES.items():
            with self.subTest(cls=cls_name):
                eq = list(self.graph.objects(KBR[cls_name], OWL.equivalentClass))
                self.assertEqual(len(eq), 1)
                colls = list(self.graph.objects(eq[0], OWL.oneOf))
                self.assertEqual(len(colls), 1)
                chain = list(Collection(self.graph, colls[0]))
                self.assertEqual(set(chain), {KBR[member] for member in members})

    def test_restrictions_exactly_as_designed(self) -> None:
        self.assertEqual(restriction_nodes(self.graph), set(tbox.RESTRICTIONS))

    def test_datatype_restriction(self) -> None:
        expected = set(tbox.DATATYPE_RESTRICTIONS)
        found: set[tuple[str, str, str, str]] = set()
        for cls_name, prop, datatype, quant in tbox.DATATYPE_RESTRICTIONS:
            for node in self.graph.objects(KBR[cls_name], RDFS.subClassOf):
                if (node, OWL.onProperty, KBR[prop]) not in self.graph:
                    continue
                if (node, OWL.onDatatype, XSD.integer) not in self.graph:
                    continue
                for value in self.graph.objects(node, OWL.cardinality):
                    if int(value) == 1:
                        found.add((cls_name, prop, "integer", "exactly1"))
        self.assertEqual(found, expected)

    def test_data_property_ranges(self) -> None:
        for name, spec in tbox.DATA_PROPERTIES.items():
            with self.subTest(prop=name):
                self.assertEqual(self.graph.value(KBR[name], RDFS.range), spec["range"])
                self.assertIn((KBR[name], RDF.type, OWL.DatatypeProperty), self.graph)

    def test_language_ranges_use_plain_literal(self) -> None:
        language_props = [
            name
            for name, spec in tbox.DATA_PROPERTIES.items()
            if spec["range"] == RDF.PlainLiteral
        ]
        self.assertTrue(language_props)
        for name in language_props:
            with self.subTest(prop=name):
                self.assertNotEqual(self.graph.value(KBR[name], RDFS.range), RDF.langString)
                for value in self.graph.objects(None, KBR[name]):
                    self.assertEqual(value.language, "id", f"{name}: {value!r}")

    def test_object_property_domain_range(self) -> None:
        for name, spec in tbox.OBJECT_PROPERTIES.items():
            with self.subTest(prop=name):
                if spec.get("domain"):
                    self.assertIn((KBR[name], RDFS.domain, KBR[spec["domain"]]), self.graph)
                else:
                    self.assertEqual(list(self.graph.objects(KBR[name], RDFS.domain)), [])
                self.assertIn((KBR[name], RDFS.range, KBR[spec["range"]]), self.graph)
        for uri, spec in tbox.EXTERNAL_OBJECT_PROPERTIES.items():
            self.assertIn((URIRef(uri), RDFS.domain, KBR[spec["domain"]]), self.graph)
            self.assertIn((URIRef(uri), RDFS.range, KBR[spec["range"]]), self.graph)

    def test_sroiq_d_features_present(self) -> None:
        self.assertTrue(list(self.graph.objects(None, OWL.propertyChainAxiom)), "R: property chain")
        for sub_prop, super_prop in tbox.SUBPROPERTY_OF:
            with self.subTest(sub=sub_prop):
                self.assertIn((KBR[sub_prop], RDFS.subPropertyOf, KBR[super_prop]), self.graph)
        for cls_name in tbox.NOMINAL_CLASSES:
            with self.subTest(nominal=cls_name):
                self.assertTrue(list(self.graph.objects(KBR[cls_name], OWL.equivalentClass)), "O: oneOf")
        inverse_count = len(list(self.graph.subject_objects(OWL.inverseOf)))
        self.assertEqual(inverse_count, len(inverse_pairs()), "I: inverseOf")
        self.assertTrue(
            any(
                (node, OWL.onProperty, KBR["memilikiReferensi"]) in self.graph
                and (node, OWL.onClass, KBR["Referensi"]) in self.graph
                and any(int(value) == 1 for value in self.graph.objects(node, OWL.minCardinality))
                for node in self.graph.objects(KBR["Penyakit"], RDFS.subClassOf)
            ),
            "Q: min 1 Referensi",
        )
        self.assertTrue(
            any(
                (node, OWL.onProperty, KBR["tahunTerbit"]) in self.graph
                and (node, OWL.onDatatype, XSD.integer) in self.graph
                and any(int(value) == 1 for value in self.graph.objects(node, OWL.cardinality))
                for node in self.graph.objects(KBR["Buku"], RDFS.subClassOf)
            ),
            "Q/D: exactly 1 xsd:integer tahunTerbit",
        )

    def test_property_chain_members(self) -> None:
        chains = list(self.graph.objects(None, OWL.propertyChainAxiom))
        self.assertEqual(len(chains), len(tbox.PROPERTY_CHAINS))
        for chain_names, super_prop in tbox.PROPERTY_CHAINS:
            with self.subTest(super_prop=super_prop):
                chain = list(Collection(self.graph, chains[0]))
                self.assertEqual(chain, [KBR[name] for name in chain_names])
                self.assertIn((KBR[super_prop], OWL.propertyChainAxiom, chains[0]), self.graph)

    def test_ontology_header(self) -> None:
        headers = list(self.graph.subjects(RDF.type, OWL.Ontology))
        self.assertEqual(len(headers), 1)
        self.assertEqual(str(headers[0]), str(tbox.ONTOLOGY_IRI))


class BuildGateTest(unittest.TestCase):
    def test_fresh_build_has_no_errors(self) -> None:
        graph, report, errors, _builder = bo.build()
        self.assertEqual(errors, [])
        self.assertEqual(len(graph), report["summary"]["triples"])
        self.assertEqual(
            sum(1 for _ in graph.subjects(RDF.type, OWL.NamedIndividual)),
            report["summary"]["named_individuals"],
        )


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
        cls.onto = cls.world.get_ontology(tbox.ONTOLOGY_IRI)
        with OWL_ARTIFACT.open("rb") as handle:
            cls.onto.load(fileobj=handle, format="rdfxml")
        sync_reasoner(cls.onto, debug=0)
        cls.report = read_json(REPORT)

    def test_ontology_is_consistent(self) -> None:
        nothing = [
            ind
            for ind in self.onto.individuals()
            if any(getattr(cls, "name", None) == "Nothing" for cls in ind.is_a if cls is not None)
        ]
        self.assertEqual(nothing, [], "tidak boleh ada individu owl:Nothing")

    def test_inferred_disease_categories_match_pathogen_links(self) -> None:
        expected: dict[str, set[str]] = defaultdict(set)
        for link in self.report["pathogen_links"]:
            category = TAXON_CATEGORY.get(link["taxon"])
            if category:
                expected[category].add(link["disease"])
        for category in TAXON_CATEGORY.values():
            with self.subTest(cls=category):
                actual = {ind.name for ind in getattr(self.onto, category).instances()}
                self.assertEqual(actual, expected.get(category, set()))

    def test_inferred_nominal_classes(self) -> None:
        for cls_name, members in tbox.NOMINAL_CLASSES.items():
            with self.subTest(cls=cls_name):
                actual = {ind.name for ind in getattr(self.onto, cls_name).instances()}
                self.assertEqual(actual, set(members))

    def test_inferred_categories_are_not_asserted(self) -> None:
        asserted = Graph()
        asserted.parse(ARTIFACT, format="turtle")
        for category in TAXON_CATEGORY.values():
            with self.subTest(cls=category):
                self.assertEqual(set(asserted.subjects(RDF.type, KBR[category])), set())


if __name__ == "__main__":
    unittest.main()
