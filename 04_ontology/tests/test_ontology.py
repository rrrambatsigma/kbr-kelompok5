"""Gate test untuk ontologi OWL 2 Penyakit Tanaman Pangan Indonesia.

Sebagian test bersifat read-only terhadap artefak ``ontology.ttl``; satu test
gerbang membangun ulang ontologi lewat ``build_ontology.build()``; satu test
menjalankan reasoner Pellet lewat owlready2 bila Java tersedia.
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
import definitions as defs  # noqa: E402
import tbox  # noqa: E402
from tbox import DCTERMS, KBR, PROV, SKOS  # noqa: E402

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
        for _subj, predicate, obj in self.graph:
            if isinstance(obj, Literal) and obj.language:
                if predicate in (SKOS.prefLabel, SKOS.altLabel, SKOS.definition):
                    self.assertIn(obj.language, {"id", "en"}, f"literal @{obj.language}: {obj}")
                else:
                    self.assertEqual(obj.language, "id", f"literal @{obj.language}: {obj}")

    def test_labels_do_not_expose_internal_pengamatan_wording(self) -> None:
        for predicate in (RDFS.label, KBR["prefLabel"]):
            for node, value in self.graph.subject_objects(predicate):
                with self.subTest(node=local(node), predicate=local(predicate)):
                    self.assertNotIn("pengamatan", str(value).lower())

    def test_all_scope_plants_have_scientific_names(self) -> None:
        for plant in self.plants:
            with self.subTest(plant=local(plant)):
                values = list(self.graph.objects(plant, KBR["namaIlmiah"]))
                self.assertEqual(len(values), 1)
                self.assertTrue(str(values[0]).strip())

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
        for cls_name in {cls for cls, _ in tbox.EQUIVALENT_CLASSES}:
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
                canonical = local(self.graph.value(observation, KBR["memilikiGejalaKanonik"]))
                if bo.CANONICAL_SYMPTOMS[canonical]["part"]:
                    self.assertTrue(list(self.graph.objects(observation, KBR["terdapatPada"])))

    def test_mapping_expansions(self) -> None:
        self.assertEqual(
            bo.match_canonical_symptoms("Bintil berbentuk bulat atau oval dan dapat saling bergabung."),
            ["BercakTanaman"],
        )
        self.assertEqual(
            bo.match_canonical_symptoms(
                "Kadang-kadang gejala oleh PStV berupa garis putus-putus berwarna hijau gelap."
            ),
            ["BelangTanaman"],
        )
        self.assertIn(
            "PertumbuhanAbnormal",
            bo.match_canonical_symptoms(
                "Tepi bergelombang atau penggulungan yang terlihat jelas pada helaian daun."
            ),
        )
        self.assertIn(
            "KematianTanaman",
            bo.match_canonical_symptoms("Benih tidak akan berkecambah atau mati."),
        )
        self.assertIn(
            "PengendalianVektor",
            bo.match_control_actions(
                "Selain mengendalikan patogennya, vektornya pun harus dikendalikan.",
                "",
                "DOC002",
            ),
        )

    def test_unmapped_symptoms_match_report(self) -> None:
        symptom_observations = set(self.graph.objects(None, KBR["memilikiGejala"]))
        mapped = set(self.graph.subjects(KBR["memilikiGejalaKanonik"], None))
        self.assertEqual(len(symptom_observations - mapped), self.report["data_quality"]["unmapped_symptoms"])
        self.assertEqual(len(symptom_observations), self.report["canonical_symptoms"]["total"])

    def test_no_unmapped_symptoms(self) -> None:
        symptom_observations = set(self.graph.objects(None, KBR["memilikiGejala"]))
        mapped = set(self.graph.subjects(KBR["memilikiGejalaKanonik"], None))
        self.assertEqual(symptom_observations - mapped, set())

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

    def test_environment_control_context_excluded(self) -> None:
        for node in (
            "ObservasiPenyakitHawarDaunBakteriPadiSuhuSamaDengan55Celsius",
            "ObservasiLayuFusariumUbiJalarSuhu13Sampai16Celsius",
            "ObservasiLayuFusariumUbiJalarKelembapanSamaDengan85Persen",
            "ObservasiLayuFusariumUbiJalarSuhu29Sampai32Celsius",
        ):
            with self.subTest(node=node):
                self.assertNotIn(
                    (KBR[node], RDF.type, KBR["ObservasiLingkungan"]), self.graph
                )
        self.assertNotIn(
            (
                KBR["PenyakitLayuFusariumKedelai"],
                KBR["dipengaruhiOleh"],
                KBR["KondisiCurahHujanTinggi"],
            ),
            self.graph,
        )

    def test_varieties_and_phases(self) -> None:
        for row in self.report["varieties"]["items"]:
            with self.subTest(variety=row["local"]):
                self.assertIn((KBR[row["local"]], RDF.type, KBR["Varietas"]), self.graph)
                self.assertIn((KBR[row["plant"]], KBR["memilikiVarietas"], KBR[row["local"]]), self.graph)
        for row in self.report["phases"]["links"]:
            with self.subTest(phase=row["phase"]):
                self.assertIn((KBR[row["phase"]], RDF.type, OWL.NamedIndividual), self.graph)
                self.assertIn((KBR[row["disease"]], KBR["menyerangFase"], KBR[row["phase"]]), self.graph)

    def test_curated_metadata_applied(self) -> None:
        for row in self.report["metadata"]:
            disease = KBR[row["disease"]]
            gap = row["gap"]
            value = row["value"]
            with self.subTest(gap=gap, disease=row["disease"], value=value):
                if gap == "severity":
                    self.assertIn(value, {str(item) for item in self.graph.objects(disease, KBR["tingkatKeparahan"])})
                    self.assertTrue(list(self.graph.objects(disease, KBR["didukungOleh"])))
                elif gap == "english":
                    self.assertIn(value, {str(item) for item in self.graph.objects(disease, KBR["namaInggrisPenyakit"])})
                    self.assertTrue(list(self.graph.objects(disease, KBR["didukungOleh"])))
                elif gap == "phase":
                    self.assertIn((disease, KBR["menyerangFase"], KBR[value]), self.graph)
                    self.assertTrue(list(self.graph.objects(KBR[value], KBR["didukungOleh"])))
                elif gap == "variety":
                    local = "Varietas" + bo.pascal(value)
                    self.assertTrue(
                        (KBR[local], KBR["tahanTerhadap"], disease) in self.graph
                        or (KBR[local], KBR["rentanTerhadap"], disease) in self.graph
                    )
                    self.assertTrue(list(self.graph.objects(KBR[local], KBR["didukungOleh"])))


    def test_all_target_concepts_have_definitions(self) -> None:
        target_types = [
            "GejalaKanonik",
            "FasePembibitan",
            "FaseVegetatif",
            "FaseGeneratif",
            "FaseAnakan",
            "FasePemasakan",
            "FasePanen",
            "BagianTanaman",
            "Serealia",
            "Legum",
            "UmbiUmbian",
            "Jamur",
            "Bakteri",
            "Virus",
            "Oomycete",
            "Fitoplasma",
            "Nematoda",
            "PengendalianKulturTeknis",
            "PengendalianMekanis",
            "PengendalianBiologis",
            "PengendalianKimiawi",
            "PengendalianFisik",
            "PengendalianTerpadu",
            "Varietas",
            "Penyakit",
            "ObservasiLingkungan",
            "FaktorRisiko",
            "Suhu",
            "KelembapanUdara",
            "KelembapanTanah",
            "CurahHujan",
            "Musim",
            "Iklim",
            "KondisiTanah",
            "TeksturTanah",
            "IntensitasCahaya",
            "KetinggianTempat",
            "KondisiDrainase",
        ]
        for type_name in target_types:
            for node in self.graph.subjects(RDF.type, KBR[type_name]):
                if not isinstance(node, URIRef) or not str(node).startswith(tbox.PTP):
                    continue
                with self.subTest(type=type_name, node=local(node)):
                    self.assertTrue(
                        list(self.graph.objects(node, SKOS.definition)),
                        f"{type_name} {local(node)} tanpa skos:definition",
                    )

    def test_gejala_are_skos_concepts(self) -> None:
        for node in self.graph.subjects(RDF.type, KBR["GejalaKanonik"]):
            with self.subTest(node=local(node)):
                self.assertIn((node, RDF.type, SKOS.Concept), self.graph)

    def test_symptom_categories_use_skos_broader(self) -> None:
        for node in self.graph.subjects(RDF.type, KBR["GejalaKanonik"]):
            with self.subTest(node=local(node)):
                categories = list(self.graph.objects(node, SKOS.broader))
                self.assertTrue(categories)
                for category in categories:
                    self.assertIn(local(category), defs.CATEGORY_CONCEPTS)
                    self.assertIn((category, RDF.type, SKOS.Concept), self.graph)

    def test_phase_chain_is_complete(self) -> None:
        for left, right in defs.PHASE_CHAIN:
            with self.subTest(left=left, right=right):
                self.assertIn((KBR[left], KBR["diikutiOleh"], KBR[right]), self.graph)
                self.assertIn((KBR[right], KBR["didahuluiOleh"], KBR[left]), self.graph)

    def test_phase_order_values(self) -> None:
        phase_types = (
            "FasePembibitan",
            "FaseVegetatif",
            "FaseGeneratif",
            "FaseAnakan",
            "FasePemasakan",
            "FasePanen",
        )
        for type_name in phase_types:
            for node in self.graph.subjects(RDF.type, KBR[type_name]):
                with self.subTest(type=type_name, node=local(node)):
                    values = list(self.graph.objects(node, KBR["urutanFase"]))
                    self.assertEqual(len(values), 1)
                    self.assertEqual(values[0].datatype, XSD.integer)
                    self.assertGreaterEqual(int(values[0]), 1)
                    self.assertLessEqual(int(values[0]), 6)

    def test_partonomy_is_transitive(self) -> None:
        self.assertIn((KBR["bagianDari"], RDF.type, OWL.TransitiveProperty), self.graph)
        self.assertNotIn(
            (KBR["Daun"], KBR["bagianDari"], KBR["Batang"]),
            self.graph,
            "Daun bagianDari Batang redundan karena bagianDari transitive",
        )
        for child, parent in defs.PART_PARENTS:
            with self.subTest(child=child, parent=parent):
                self.assertIn((KBR[child], KBR["bagianDari"], KBR[parent]), self.graph)

    def test_no_truncated_or_template_labels(self) -> None:
        symptom_nodes = set(self.graph.objects(None, KBR["memilikiGejala"]))
        symptom_nodes |= set(self.graph.subjects(RDF.type, KBR["GejalaKanonik"]))
        for predicate in (RDFS.label, SKOS.prefLabel):
            for node in symptom_nodes:
                for value in self.graph.objects(node, predicate):
                    text = str(value)
                    with self.subTest(node=local(node), predicate=local(predicate)):
                        self.assertFalse(text.endswith("..."), text)
                        self.assertNotIn(" pada Penyakit ", text)

    def test_non_symptom_rows_not_gejala(self) -> None:
        texts = {str(value) for value in self.graph.objects(None, KBR["deskripsiGejala"])}
        for needle in (
            "Kecepatan angin",
            "Kejadian penyakit yang disebabkan penyakit bulai",
        ):
            with self.subTest(needle=needle):
                self.assertFalse(any(needle in text for text in texts))

    def test_doc006_reference(self) -> None:
        book = KBR["BukuDOC006"]
        self.assertIn((book, RDF.type, KBR["Buku"]), self.graph)
        self.assertTrue(list(self.graph.objects(book, KBR["judulReferensi"])))
        self.assertEqual(
            int(self.graph.value(book, KBR["tahunTerbit"])),
            1994,
        )

    def test_controls_have_definitions(self) -> None:
        for type_name in (name for name in tbox.CLASSES if name.startswith("Pengendalian")):
            for node in self.graph.subjects(RDF.type, KBR[type_name]):
                if not isinstance(node, URIRef) or not str(node).startswith(tbox.PTP):
                    continue
                with self.subTest(type=type_name, node=local(node)):
                    self.assertTrue(list(self.graph.objects(node, SKOS.definition)))

    def test_varieties_have_definitions(self) -> None:
        for node in self.graph.subjects(RDF.type, KBR["Varietas"]):
            with self.subTest(node=local(node)):
                self.assertTrue(list(self.graph.objects(node, SKOS.definition)))

    def test_pathogens_have_definitions(self) -> None:
        for type_name in ("Jamur", "Bakteri", "Virus", "Oomycete", "Fitoplasma", "Nematoda"):
            for node in self.graph.subjects(RDF.type, KBR[type_name]):
                with self.subTest(type=type_name, node=local(node)):
                    self.assertTrue(list(self.graph.objects(node, SKOS.definition)))

    def test_environment_conditions_have_definitions(self) -> None:
        for type_name in (
            "ObservasiLingkungan",
            "FaktorRisiko",
            "Suhu",
            "KelembapanUdara",
            "KelembapanTanah",
            "CurahHujan",
            "Musim",
            "Iklim",
            "KondisiTanah",
            "TeksturTanah",
            "IntensitasCahaya",
            "KetinggianTempat",
            "KondisiDrainase",
        ):
            for node in self.graph.subjects(RDF.type, KBR[type_name]):
                if not isinstance(node, URIRef) or not str(node).startswith(tbox.PTP):
                    continue
                with self.subTest(type=type_name, node=local(node)):
                    self.assertTrue(list(self.graph.objects(node, SKOS.definition)))

    def test_class_and_property_definitions(self) -> None:
        for name in tbox.CLASSES:
            with self.subTest(class_name=name):
                self.assertTrue(list(self.graph.objects(KBR[name], SKOS.definition)))
        for name in tbox.OBJECT_PROPERTIES:
            with self.subTest(object_property=name):
                self.assertTrue(list(self.graph.objects(KBR[name], SKOS.definition)))
        for name in tbox.DATA_PROPERTIES:
            with self.subTest(data_property=name):
                self.assertTrue(list(self.graph.objects(KBR[name], SKOS.definition)))

    def test_definition_sources_present(self) -> None:
        for node in set(self.graph.subjects(SKOS.definition, None)):
            with self.subTest(node=local(node)):
                self.assertTrue(list(self.graph.objects(node, DCTERMS.source)))

    def test_disease_english_labels(self) -> None:
        for node in self.graph.subjects(RDF.type, KBR["Penyakit"]):
            local_name = local(node)
            english = [
                value
                for value in self.graph.objects(node, SKOS.prefLabel)
                if isinstance(value, Literal) and value.language == "en"
            ]
            with self.subTest(disease=local_name):
                self.assertTrue(english, f"{local_name} tanpa skos:prefLabel@en")

    def test_disease_definitions_are_informative(self) -> None:
        for disease in self.diseases:
            definitions = [str(value) for value in self.graph.objects(disease, SKOS.definition)]
            with self.subTest(disease=local(disease)):
                self.assertTrue(definitions)
                text = definitions[0]
                self.assertGreater(len(text), 40)
                self.assertTrue(text.startswith("Penyakit "))
                self.assertNotIn("Penyakit Penyakit", text)
                self.assertTrue(
                    "disebabkan oleh" in text or "gejala" in text,
                    text,
                )


class OntologyMdDefinitionsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        artifact = ONTO_DIR / "ontology_md.ttl"
        if not artifact.exists():
            raise unittest.SkipTest("ontology_md.ttl belum dibuat")
        cls.graph = Graph()
        cls.graph.parse(artifact, format="turtle")

    def test_md_phase_durations(self) -> None:
        starts = list(self.graph.subject_objects(KBR["mulaiFase"]))
        ends = list(self.graph.subject_objects(KBR["selesaiFase"]))
        units = list(self.graph.subject_objects(KBR["satuanFase"]))
        self.assertTrue(starts)
        self.assertEqual(len(starts), len(ends))
        self.assertEqual(len(starts), len(units))
        for _subject, value in starts + ends:
            self.assertIsInstance(value, Literal)
            self.assertEqual(value.datatype, XSD.decimal)
        for _subject, value in units:
            self.assertIsInstance(value, Literal)
            self.assertIsNone(value.language)

    def test_md_phase_orders(self) -> None:
        phase_types = (
            "FasePembibitan",
            "FaseVegetatif",
            "FaseGeneratif",
            "FaseAnakan",
            "FasePemasakan",
            "FasePanen",
        )
        for type_name in phase_types:
            for node in self.graph.subjects(RDF.type, KBR[type_name]):
                with self.subTest(type=type_name, node=local(node)):
                    values = list(self.graph.objects(node, KBR["urutanFase"]))
                    self.assertEqual(len(values), 1)
                    self.assertGreaterEqual(int(values[0]), 1)
                    self.assertLessEqual(int(values[0]), 6)

    def test_ubikayu_diseases_have_controls_or_general(self) -> None:
        diseases = set(self.graph.subjects(KBR["menyerangTanaman"], KBR["UbiKayu"]))
        general = set(self.graph.objects(KBR["UbiKayu"], KBR["pengendalianUmum"]))
        self.assertEqual(len(diseases), 17)
        for disease in diseases:
            with self.subTest(disease=local(disease)):
                controls = list(self.graph.objects(disease, KBR["dikendalikanDengan"]))
                self.assertTrue(controls or general, f"{local(disease)} tanpa kontrol")

    def test_external_controls_have_source_url(self) -> None:
        external = [
            node
            for node in self.graph.subjects(RDF.type, KBR["BuktiPengendalian"])
            if any(
                str(value).startswith("SRC_EXT_")
                for value in self.graph.objects(node, KBR["dokumenSumber"])
            )
        ]
        self.assertTrue(external)
        for node in external:
            with self.subTest(node=local(node)):
                self.assertTrue(list(self.graph.objects(node, KBR["kutipanSumber"])))
                self.assertTrue(list(self.graph.objects(node, KBR["identifierSumber"])))
                references = list(self.graph.objects(node, PROV.wasDerivedFrom))
                self.assertTrue(references, f"{local(node)} tanpa prov:wasDerivedFrom")
                self.assertTrue(
                    any(
                        list(self.graph.objects(reference, KBR["urlReferensi"]))
                        for reference in references
                    ),
                    f"{local(node)} tanpa URL referensi",
                )

    def test_md_target_concepts_have_definitions(self) -> None:
        target_types = [
            "GejalaKanonik",
            "FasePembibitan",
            "FaseVegetatif",
            "FaseGeneratif",
            "FaseAnakan",
            "FasePemasakan",
            "FasePanen",
            "BagianTanaman",
            "Serealia",
            "Legum",
            "UmbiUmbian",
            "Jamur",
            "Bakteri",
            "Virus",
            "Oomycete",
            "Fitoplasma",
            "Nematoda",
            "Varietas",
            "Penyakit",
            "ObservasiLingkungan",
            "FaktorRisiko",
            "Suhu",
            "KelembapanUdara",
            "KelembapanTanah",
            "CurahHujan",
            "Musim",
            "Iklim",
            "KondisiTanah",
            "TeksturTanah",
            "IntensitasCahaya",
            "KetinggianTempat",
            "KondisiDrainase",
        ]
        for type_name in target_types:
            for node in self.graph.subjects(RDF.type, KBR[type_name]):
                if not isinstance(node, URIRef) or not str(node).startswith(tbox.PTP):
                    continue
                with self.subTest(type=type_name, node=local(node)):
                    self.assertTrue(
                        list(self.graph.objects(node, SKOS.definition)),
                        f"{type_name} {local(node)} tanpa skos:definition di ontology_md.ttl",
                    )


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
                if spec.get("range"):
                    self.assertIn((KBR[name], RDFS.range, KBR[spec["range"]]), self.graph)
                else:
                    self.assertEqual(list(self.graph.objects(KBR[name], RDFS.range)), [])
        for uri, spec in tbox.EXTERNAL_OBJECT_PROPERTIES.items():
            if spec.get("domain"):
                self.assertIn((URIRef(uri), RDFS.domain, KBR[spec["domain"]]), self.graph)
            else:
                self.assertEqual(list(self.graph.objects(URIRef(uri), RDFS.domain)), [])
            if spec.get("range"):
                self.assertIn((URIRef(uri), RDFS.range, KBR[spec["range"]]), self.graph)
            else:
                self.assertEqual(list(self.graph.objects(URIRef(uri), RDFS.range)), [])

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

    def test_transitive_bagian_dari(self) -> None:
        prop = KBR["bagianDari"]
        self.assertIn((prop, RDF.type, OWL.TransitiveProperty), self.graph)
        self.assertIn((KBR["Daun"], prop, KBR["Pucuk"]), self.graph)
        self.assertIn((KBR["Pucuk"], prop, KBR["Batang"]), self.graph)

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


@unittest.skipUnless(shutil.which("java"), "Java tidak tersedia untuk Pellet")
class PelletReasoningTest(unittest.TestCase):
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
        from owlready2 import World

        from reasoner_utils import sync_reasoner_for_tests

        cls.world = World()
        cls.onto = cls.world.get_ontology(tbox.ONTOLOGY_IRI)
        with OWL_ARTIFACT.open("rb") as handle:
            cls.onto.load(fileobj=handle, format="rdfxml")
        sync_reasoner_for_tests(cls.onto)
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
