"""Gate test untuk fakta enrichment 7 tanaman utama."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

TABLE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TABLE_DIR / "src"))

import build_enrichment_facts as ef  # noqa: E402
import build_ontology as bo  # noqa: E402


class TestEnrichmentFacts(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows, cls.entities, cls.report = ef.build()
        cls.by_id = {row["fact_id"]: row for row in cls.rows}
        cls.entries = bo.penyakit_entries()

    def test_schema_and_traceability(self) -> None:
        self.assertTrue(self.rows)
        self.assertEqual(list(self.rows[0].keys()), ef.FACT_COLUMNS)
        self.assertEqual(len(self.by_id), len(self.rows))
        for row in self.rows:
            self.assertTrue(row["fact_id"], row)
            self.assertTrue(row["source_document"], row["fact_id"])
            self.assertTrue(row["source_type"], row["fact_id"])
            self.assertTrue(row["source_id"], row["fact_id"])
            self.assertTrue(row["evidence_quote"].strip(), row["fact_id"])
            self.assertIn(row["confidence"], {"high", "medium"}, row["fact_id"])
            self.assertIn(row["review_status"], {"auto_ok", "needs_review"}, row["fact_id"])

    def test_scope_is_seven_plants(self) -> None:
        plants = {
            row["subject_local"]
            for row in self.rows
            if row["subject_class"] == "TanamanPangan"
        }
        self.assertTrue(plants)
        self.assertTrue(plants <= set(ef.SCOPE_PLANTS))
        for plant in ef.SCOPE_PLANTS:
            self.assertIn(plant, plants)

    def test_kedelai_conditions(self) -> None:
        conditions = {
            row["object_local"]
            for row in self.rows
            if row["predicate"] == "memilikiKondisiTumbuh" and row["subject_local"] == "Kedelai"
        }
        self.assertIn("KondisiCahayaSedang", conditions)
        self.assertIn("KondisiSuhuDingin", conditions)
        self.assertIn("KondisiSuhuSedang", conditions)
        temp_quotes = [
            row["evidence_quote"]
            for row in self.rows
            if row["predicate"] == "memilikiKondisiTumbuh" and row["subject_local"] == "Kedelai"
        ]
        self.assertTrue(any("20-250C" in quote for quote in temp_quotes))

    def test_ubikayu_soil_condition(self) -> None:
        conditions = {
            row["object_local"]
            for row in self.rows
            if row["predicate"] == "memilikiKondisiTumbuh" and row["subject_local"] == "UbiKayu"
        }
        self.assertIn("KondisiTanahSubur", conditions)

    def test_plant_descriptions(self) -> None:
        described = {
            row["subject_local"]
            for row in self.rows
            if row["predicate"] == "deskripsiTanaman"
        }
        self.assertEqual(described, set(ef.SCOPE_PLANTS))
        for row in self.rows:
            if row["predicate"] == "deskripsiTanaman":
                self.assertGreater(len(row["literal_value"]), 80, row["fact_id"])
                self.assertEqual(row["literal_lang"], "id")

    def test_disease_descriptions(self) -> None:
        described = {
            row["subject_local"]
            for row in self.rows
            if row["predicate"] == "deskripsiPenyakit"
        }
        self.assertEqual(described, {entry["local"] for entry in self.entries})
        self.assertGreaterEqual(len(described), 57)
        self.assertIn("PenyakitBercakDaunMataKatakFrogeyeLeafSpotKedelai", described)
        self.assertIn("PenyakitSamarKacangTunggakCowpeaMildMottleVirusKedelai", described)
        self.assertIn("ANTRAKNOSAKedelai", described)
        self.assertIn("BERCAKDAUNKacangTanah", described)
        for row in self.rows:
            if row["predicate"] == "deskripsiPenyakit":
                self.assertEqual(row["subject_class"], "Penyakit", row["fact_id"])
                self.assertGreaterEqual(len(row["literal_value"]), 20, row["fact_id"])
                self.assertEqual(row["literal_lang"], "id", row["fact_id"])

    def test_ubikayu_table_descriptions(self) -> None:
        table_rows = [
            row
            for row in self.rows
            if "baris tabel gejala ubi kayu" in row["notes"]
        ]
        self.assertEqual(len(table_rows), 17)
        self.assertEqual({row["subject_class"] for row in table_rows}, {"Penyakit"})
        by_type: dict[str, int] = {}
        for row in table_rows:
            by_type[row["source_type"]] = by_type.get(row["source_type"], 0) + 1
            if row["source_type"] == "md_chunk":
                self.assertEqual(row["review_status"], "auto_ok", row["fact_id"])
            else:
                self.assertEqual(row["review_status"], "needs_review", row["fact_id"])
        self.assertEqual(by_type.get("md_chunk"), 15)
        self.assertEqual(by_type.get("table_row"), 2)
        self.assertEqual(
            {
                row["subject_local"]
                for row in table_rows
                if row["source_type"] == "table_row"
            },
            {"BercakDaunCoklatUbiKayu", "AntraknosaUbiKayuDIS110"},
        )

    def test_disease_assignment_edge_cases(self) -> None:
        units = ef.load_doc002_baseline() + ef.load_doc005_chunks()
        ef.assign_diseases(units, self.entries)
        assigned = {unit.disease for unit in units if unit.disease}
        for local in (
            "PenyakitBercakDaunMataKatakFrogeyeLeafSpotKedelai",
            "PenyakitSamarKacangTunggakCowpeaMildMottleVirusKedelai",
            "ANTRAKNOSAKedelai",
            "BERCAKDAUNKacangTanah",
        ):
            self.assertIn(local, assigned)

    def test_risk_factors_existing_and_clean(self) -> None:
        existing = {
            "KondisiKelembapanTinggi",
            "KondisiSuhu",
            "KondisiCurahHujan",
            "KondisiMusimHujan",
            "KondisiMusimKemarau",
        }
        for row in self.rows:
            if row["predicate"] != "dipengaruhiOleh":
                continue
            self.assertIn(row["object_local"], existing)
            self.assertNotIn("perlakuan panas", row["evidence_quote"].lower())
            self.assertNotIn("pengendalian", row["evidence_quote"].lower())

    def test_entities_cover_scope_and_vocabulary(self) -> None:
        by_entity = {(row["entity_local"], row["entity_class"]) for row in self.entities}
        for plant in ef.SCOPE_PLANTS:
            self.assertIn((plant, "TanamanPangan"), by_entity)
        for local in ef.CONDITION_LABELS:
            self.assertIn((local, "FaktorLingkungan"), by_entity)
        disease_entities = {row["entity_local"] for row in self.entities if row["entity_class"] == "Penyakit"}
        self.assertEqual(disease_entities, {entry["local"] for entry in self.entries})

    def test_baseline_and_doc005_evidence_verbatim(self) -> None:
        baseline = {
            (block.get("block_id") or "").strip(): ef.norm(block.get("text"))
            for block in ef.read_jsonl(ef.DOC002_BASELINE)
        }
        doc005 = {
            (chunk.get("chunk_id") or "").strip(): ef.norm(
                chunk.get("text_markdown") or chunk.get("plain_text")
            )
            for chunk in ef.read_jsonl(ef.DOC005_CHUNKS)
        }
        md: dict[str, list[str]] = {}
        for chunk in ef.read_csv(ef.DOC002_MD_CHUNKS):
            md.setdefault((chunk.get("chunk_id") or "").strip(), []).append(
                ef.norm(chunk.get("text_markdown"))
            )
        for unit in ef.load_doc005_md_units():
            md.setdefault(unit.source_id, []).append(ef.norm(unit.text))
        table_cells = {
            ef.norm(row.get("symptom_text")) for row in ef.read_csv(ef.UBI_KAYU_TABLE_CSV)
        }
        for row in self.rows:
            quote = ef.norm(row["evidence_quote"])
            if not quote:
                continue
            ids = [value for value in row["source_id"].split(";") if value]
            if row["source_type"] == "baseline_block":
                self.assertTrue(
                    any(quote in baseline.get(source_id, "") for source_id in ids),
                    row["fact_id"],
                )
            elif row["source_type"] == "doc005_chunk":
                self.assertTrue(
                    any(quote in doc005.get(source_id, "") for source_id in ids),
                    row["fact_id"],
                )
            elif row["source_type"] == "md_chunk":
                self.assertTrue(
                    any(
                        any(quote in text for text in md.get(source_id, []))
                        for source_id in ids
                    ),
                    row["fact_id"],
                )
            elif row["source_type"] == "table_row":
                self.assertIn(quote, table_cells, row["fact_id"])

    def test_gap_report(self) -> None:
        self.assertIn("Penyakit tanpa tautan patogen di curated", self.report)
        self.assertIn("Penyakit tanpa pengendalian tingkat penyakit", self.report)
        self.assertIn("DIS_005", self.report)
        self.assertIn("DIS_022", self.report)
        self.assertIn("DIS_039", self.report)
        self.assertIn("baris tabel", self.report)


if __name__ == "__main__":
    unittest.main()
