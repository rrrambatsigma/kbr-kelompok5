"""Test ekstraksi deskripsi verbatim (DOC002_descriptions.csv)."""

from __future__ import annotations

import csv
import sys
import unittest
from pathlib import Path

TABLE_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = TABLE_DIR.parent
sys.path.insert(0, str(TABLE_DIR / "src"))
sys.path.insert(0, str(TABLE_DIR / "tests"))

import build_descriptions as bd  # noqa: E402
import build_enrichment_facts as ef  # noqa: E402

DESCRIPTIONS = TABLE_DIR / "auto" / "DOC002_md" / "DOC002_descriptions.csv"
GAPS = TABLE_DIR / "reports" / "DOC002_description_gaps.md"
SOURCE_DIR = PROJECT_ROOT / "00_sumber_data"

EXPECTED_MISSING_INDIVIDUALS = [
    "KondisiIklimBasah",
    "KondisiKelembapanUdaraRendah",
    "KondisiKelembapanUdaraSedang",
    "KondisiKelembapanUdaraTinggi",
    "KondisiTanahBasa",
    "KondisiTanahBerpasir",
    "KondisiTanahLiat",
    "KondisiTanahNetral",
    "PengamatanBercakDaunPutihUbiKayuKecilBulatBerwarnaPutih",
    "PengamatanPenyakitAntraknosaKedelaiTruncatumMelakukanPenetrasiJaringanMembentuk",
    "PengamatanPenyakitBercakDaunKacangTanahBerbedaBedaTergantungSpesiesPatogennya",
    "PengamatanPenyakitBusukHitamBlackRotUbiJalarFimbriataABPascapanenC",
    "PengamatanPenyakitEmbunPalsuDownyMildewKedelaiManshuricaAwalnyaTerdapatAdanya",
    "PengamatanPenyakitHawarBakteriBacterialBlightKedelaiAkibatMakaBenihDihasilkanMenjadi",
    "PengamatanPenyakitHawarBakteriBacterialBlightKedelaiGlycineDiawaliMunculnyaAwalnyaBerwarna",
    "PengamatanPenyakitKerdilKedelaiSoybeanStuntVirusKedelaiMenusukkanAlatMulutStyletSehat",
    "PengamatanPenyakitRebahKecambahKedelaiSolaniMakaBenihTidakBerkecambah",
]
EXPECTED_MISSING_CLASSES = [
    "ArtikelIlmiah",
    "BuktiGejala",
    "BuktiPatogen",
    "BuktiPengendalian",
    "BuktiSumber",
    "EntitasKBR",
    "FaktorRisiko",
    "FaktorSanitasiLahan",
    "GejalaKanonik",
    "JurnalIlmiah",
    "KandidatDiagnosis",
    "KetinggianTempat",
    "KondisiDrainase",
    "Observasi",
    "ObservasiLingkungan",
    "Oomycete",
    "OrganismeLain",
    "PengendalianBiologis",
    "PengendalianFisik",
    "PenyakitOomycete",
    "PenyakitPenyebabTidakDiketahui",
    "PublikasiInstansi",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


class TestDescriptionsCsv(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = read_csv(DESCRIPTIONS)
        cls.by_subject = {row["subject_local"]: row for row in cls.rows}
        cls.blocks = {
            block.get("block_id"): (block.get("text") or "")
            for block in ef.read_jsonl(ef.DOC002_BASELINE)
        }
        cls.doc005 = {
            chunk.get("chunk_id"): (
                (chunk.get("text_markdown") or "") + " " + (chunk.get("plain_text") or "")
            )
            for chunk in ef.read_jsonl(ef.DOC005_CHUNKS)
        }
        cls.md_chunks = {
            row.get("chunk_id"): (row.get("text_markdown") or "")
            for row in ef.read_csv(ef.DOC002_MD_CHUNKS)
        }
        cls.md_documents = {
            source_id: (SOURCE_DIR / filename).read_text(encoding="utf-8")
            for _, filename, source_id in bd.DOC_FILES
            if (SOURCE_DIR / filename).exists()
        }
        cls.facts = read_csv(ef.FACTS_CSV)
        cls.fact_literals = {
            (row["subject_local"], row["predicate"]): row.get("literal_value", "")
            for row in cls.facts
        }
        cls.fact_evidence = {}
        for row in cls.facts:
            cls.fact_evidence.setdefault(row.get("object_local", ""), row)
        cls.table_texts = {}
        for path in (bd.SYMPTOMS_CSV, bd.CONTROLS_CSV):
            for row in read_csv(path):
                cls.table_texts.setdefault(bd.norm(row.get("verbatim_text")), row)

    def test_columns_and_no_empty_literal(self) -> None:
        self.assertTrue(self.rows)
        self.assertEqual(set(self.rows[0]), set(bd.COLUMNS))
        for row in self.rows:
            self.assertTrue(row["literal_value"].strip(), row["subject_local"])
            self.assertEqual(row["predicate"], "rdfs:comment")
            self.assertEqual(row["literal_lang"], "id")

    def test_one_comment_per_subject(self) -> None:
        subjects = [row["subject_local"] for row in self.rows]
        self.assertEqual(len(subjects), len(set(subjects)))

    def test_status_vocabulary(self) -> None:
        for row in self.rows:
            self.assertIn(row["review_status"], {"auto_ok", "needs_review"}, row["subject_local"])
            self.assertIn(row["confidence"], {"high", "medium", "low"})

    def test_mirror_facts_are_identical(self) -> None:
        for row in self.rows:
            if row["notes"] != "disalin dari fakta enrichment":
                continue
            key = (row["subject_local"], "deskripsiPenyakit")
            if key not in self.fact_literals:
                key = (row["subject_local"], "deskripsiTanaman")
            self.assertIn(key, self.fact_literals, row["subject_local"])
            self.assertEqual(row["literal_value"], self.fact_literals[key])

    def test_mirror_canonical_is_identical(self) -> None:
        graph = bd.Graph()
        graph.parse(str(bd.ONTOLOGY_TTL), format="turtle")
        canonical: dict[str, set[str]] = {}
        for predicate in bd.MIRROR_CANONICAL:
            for subject, literal in graph.subject_objects(bd.URIRef(bd.KBR + predicate)):
                canonical.setdefault(bd.local_name(subject), set()).add(str(literal))
        for row in self.rows:
            if not row["notes"].startswith("disalin dari deskripsi kanonik"):
                continue
            self.assertIn(row["subject_local"], canonical, row["subject_local"])
            self.assertIn(row["literal_value"], canonical[row["subject_local"]])

    def test_mirror_table_rows_come_from_tables(self) -> None:
        for row in self.rows:
            if not row["notes"].startswith("disalin dari deskripsi kanonik"):
                continue
            if "tabel" not in row["notes"]:
                continue
            self.assertIn(
                bd.norm(row["literal_value"]), self.table_texts, row["subject_local"]
            )
            self.assertEqual(row["source_type"], "table_row")

    def test_verbatim_from_baseline_blocks(self) -> None:
        for row in self.rows:
            if row["source_type"] != "baseline_block":
                continue
            source = self.blocks.get(row["source_id"])
            self.assertIsNotNone(source, row["subject_local"])
            self.assertIn(
                bd.norm(row["evidence_quote"]), bd.norm(source), row["subject_local"]
            )

    def test_verbatim_from_doc005_chunks(self) -> None:
        for row in self.rows:
            if row["source_type"] != "doc005_chunk":
                continue
            for chunk_id in row["source_id"].split(";"):
                source = self.doc005.get(chunk_id.strip())
                if source and bd.norm(row["evidence_quote"]) in bd.norm(source):
                    break
            else:
                self.fail(f"{row['subject_local']}: bukti tidak ada di chunk {row['source_id']}")

    def test_verbatim_from_md_chunks(self) -> None:
        for row in self.rows:
            if row["source_type"] != "md_chunk":
                continue
            if row["source_id"] == "DOC005_MD_PENDAHULUAN":
                source = bd.ef.load_doc005_md_units()[0].text
            else:
                source = self.md_chunks.get(row["source_id"])
            self.assertIsNotNone(source, row["subject_local"])
            self.assertIn(
                bd.norm(row["evidence_quote"]), bd.norm(source), row["subject_local"]
            )

    def test_verbatim_from_md_documents(self) -> None:
        for row in self.rows:
            if row["source_type"] != "md_document":
                continue
            source = self.md_documents.get(row["source_id"])
            self.assertIsNotNone(source, row["source_id"])
            if row["notes"].startswith("paragraf pembuka"):
                self.assertIn(bd.norm(row["literal_value"]), bd.norm(source), row["subject_local"])
                continue
            lines = source.splitlines()
            start = int(row["line_start"] or 0)
            self.assertTrue(0 < start <= len(lines), row["subject_local"])
            if row["line_end"]:
                self.assertLessEqual(start, int(row["line_end"]))
            joined = "\n".join(lines[start - 1 : int(row["line_end"] or start)])
            self.assertIn(bd.norm(row["evidence_quote"]), bd.norm(joined), row["subject_local"])

    def test_table_row_cells_are_substrings_of_the_row(self) -> None:
        for row in self.rows:
            if row["source_type"] != "table_row" or row["source_id"] != "DOC002_MD_PENUH":
                continue
            source = self.md_documents[row["source_id"]]
            line = source.splitlines()[int(row["line_start"]) - 1]
            self.assertIn(bd.norm(row["evidence_quote"]), bd.norm(line), row["subject_local"])
            self.assertIn(bd.norm(row["literal_value"]), bd.norm(line), row["subject_local"])

    def test_condition_link_evidence_is_a_fact_quote(self) -> None:
        for row in self.rows:
            if row["notes"] != "bukti tautan kondisi; frasa label tidak ada di sumber":
                continue
            fact = self.fact_evidence.get(row["subject_local"])
            self.assertIsNotNone(fact, row["subject_local"])
            self.assertEqual(row["evidence_quote"], fact["evidence_quote"])

    def test_coverage_matches_expected_gaps(self) -> None:
        targets, classes = bd.load_targets()
        individual_targets = {
            local
            for local, target in targets.items()
            if any(
                name in bd.EXTRACT_CLASSES or name in bd.MIRROR_CLASSES
                for name in target.classes
            )
        }
        covered = set(self.by_subject)
        missing_individuals = sorted(individual_targets - covered)
        missing_classes = sorted(local for local, _ in classes if local not in covered)
        self.assertEqual(missing_individuals, EXPECTED_MISSING_INDIVIDUALS)
        self.assertEqual(missing_classes, EXPECTED_MISSING_CLASSES)

    def test_condition_labels_without_source_are_not_fabricated(self) -> None:
        for local in EXPECTED_MISSING_INDIVIDUALS:
            self.assertNotIn(local, self.by_subject)

    def test_gap_report_lists_every_missing_subject(self) -> None:
        text = GAPS.read_text(encoding="utf-8")
        for local in EXPECTED_MISSING_INDIVIDUALS + EXPECTED_MISSING_CLASSES:
            self.assertIn(local, text, local)

    def test_status_counts(self) -> None:
        auto = sum(1 for row in self.rows if row["review_status"] == "auto_ok")
        review = sum(1 for row in self.rows if row["review_status"] == "needs_review")
        self.assertEqual(auto + review, len(self.rows))
        self.assertGreater(auto, review)


if __name__ == "__main__":
    unittest.main()
