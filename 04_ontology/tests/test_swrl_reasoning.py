"""Gate test SWRL + Pellet pada ontology_md.owl."""

from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.namespace import RDF

ONTO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ONTO_DIR))

OWL_ARTIFACT = ONTO_DIR / "ontology_md.owl"
TTL_ARTIFACT = ONTO_DIR / "ontology_md.ttl"
CANONICAL_ARTIFACT = ONTO_DIR / "ontology.ttl"
SWRL_IMP = URIRef("http://www.w3.org/2003/11/swrl#Imp")


def inferred_names(world, individual, prop_name: str) -> set[str]:
    """Ambil objek hasil inferensi langsung dari graf owlready2.

    Attribute access bermasalah pada owlready2 0.51 setelah
    ``infer_property_values=True``; graf tetap menyimpan triple hasil Pellet.
    """
    prop = world._props.get(prop_name)
    if prop is None:
        return set()
    return {
        world._get_by_storid(storid).name
        for storid in world._get_obj_triples_sp_o(individual.storid, prop.storid)
    }


@unittest.skipUnless(shutil.which("java"), "Java tidak tersedia untuk Pellet")
class TestSwrlReasoning(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            from owlready2 import World, locstr
        except ImportError as exc:  # pragma: no cover
            raise unittest.SkipTest(f"owlready2 tidak terpasang: {exc}")
        if not OWL_ARTIFACT.exists():
            raise AssertionError(
                f"artefak hilang: {OWL_ARTIFACT} - jalankan build_ontology_md.py dulu"
            )

        from reasoner_utils import sync_reasoner_for_tests

        cls.world = World()
        cls.onto = cls.world.get_ontology("http://kbr.kelompok5.org/penyakit-tanaman-pangan")
        with OWL_ARTIFACT.open("rb") as handle:
            cls.onto.load(fileobj=handle, format="rdfxml")

        cls.blas_diagnosis = cls.onto.Diagnosis("DiagnosisUjiBlas")
        cls.blas_diagnosis.memilikiTanaman = [cls.onto.Padi]
        cls.blas_diagnosis.memilikiObservasi = [
            cls.onto.PengamatanPenyakitBlasPadiBercakDaun
        ]

        cls.fallback_diagnosis = cls.onto.Diagnosis("DiagnosisUjiUbiKayu")
        cls.fallback_diagnosis.menghasilkanPenyakit = [
            cls.onto.TanamanKerdilStuntUbiKayu
        ]

        cls.environment_diagnosis = cls.onto.Diagnosis("DiagnosisUjiLingkungan")
        cls.environment_diagnosis.memilikiTanaman = [cls.onto.UbiKayu]
        observation = cls.onto.ObservasiLingkungan("ObservasiUjiSuhu")
        observation.klasifikasiTurunan = [locstr("Suhu", "id")]
        cls.environment_diagnosis.memilikiObservasi = [observation]

        sync_reasoner_for_tests(cls.onto, infer_property_values=True)

    def test_swrl_rules_are_loaded(self) -> None:
        rules = list(self.onto.rules())
        self.assertEqual(len(rules), 4)
        self.assertTrue(any("gejala" in str(rule).lower() for rule in rules))

    def test_symptom_rule_infers_candidate_disease(self) -> None:
        inferred = inferred_names(
            self.world, self.blas_diagnosis, "menghasilkanPenyakit"
        )
        self.assertIn("PenyakitBlasPadi", inferred)
        self.assertNotIn("PenyakitBulaiJagung", inferred)

    def test_environment_rule_infers_candidate_disease(self) -> None:
        inferred = inferred_names(
            self.world, self.environment_diagnosis, "menghasilkanPenyakit"
        )
        self.assertIn("HawarDaunBakteriUbiKayu", inferred)

    def test_specific_control_rule_infers_recommendation(self) -> None:
        inferred = inferred_names(
            self.world, self.blas_diagnosis, "merekomendasikanPengendalian"
        )
        self.assertTrue(inferred)

    def test_general_control_fallback_rule(self) -> None:
        inferred = inferred_names(
            self.world, self.fallback_diagnosis, "merekomendasikanPengendalian"
        )
        self.assertIn("PemupukanBerimbang", inferred)

    def test_swrl_rules_only_in_md_artifact(self) -> None:
        self.assertTrue(TTL_ARTIFACT.exists())
        md = Graph()
        md.parse(TTL_ARTIFACT, format="turtle")
        self.assertEqual(len(list(md.subjects(RDF.type, SWRL_IMP))), 4)

        canonical = Graph()
        canonical.parse(CANONICAL_ARTIFACT, format="turtle")
        self.assertEqual(list(canonical.subjects(RDF.type, SWRL_IMP)), [])


if __name__ == "__main__":
    unittest.main()
