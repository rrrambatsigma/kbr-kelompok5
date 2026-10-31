"""Gate test untuk knowledge table DOC003, DOC004, dan DOC005 (Tahap 2).

Test ini read-only terhadap sumber Tahap 1 dan artefak ``curated/DOC003``,
``curated/DOC004``, dan ``curated/DOC005``. Fokusnya: verbatim, traceability
blok/chunk, offset karakter, foreign key, dan keunikan ID.

Jalankan dari ``03_knowledge_tables``::

    python -m unittest discover -s tests -p "test_*.py"
"""

from __future__ import annotations

import csv
import json
import re
import sys
import unittest
from pathlib import Path

TABLE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = TABLE_DIR.parent
sys.path.insert(0, str(TABLE_DIR))

import build_document_tables as bdt  # noqa: E402

EXTRACTION_DIR = PROJECT_ROOT / "02_extraction" / "extracted_text"
CURATED_DIR = TABLE_DIR / "curated"
REPORTS_DIR = TABLE_DIR / "reports"

WS_RE = re.compile(r"\s+")

DOCUMENTS = {
    "DOC003": [
        "plants",
        "amorphophallus_spp_diseases",
        "pathogens",
        "disease_pathogen",
        "symptoms",
        "controls",
    ],
    "DOC004": ["nutrients", "fertilizers", "practices", "compost"],
    "DOC005": [
        "plants",
        "diseases",
        "pathogens",
        "disease_pathogen",
        "symptoms",
        "controls",
    ],
}


def source_artifact_paths(document_id: str) -> tuple[Path, Path]:
    return (
        EXTRACTION_DIR / f"{document_id}.blocks.jsonl",
        EXTRACTION_DIR / f"{document_id}.chunks.jsonl",
    )


def missing_source_artifacts(document_id: str) -> list[Path]:
    return [path for path in source_artifact_paths(document_id) if not path.exists()]


def norm(text: str) -> str:
    return WS_RE.sub(" ", str(text or "")).strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> list[dict]:
    records = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


class DocumentTableGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows: dict[str, dict[str, list[dict[str, str]]]] = {}
        cls.blocks: dict[str, dict[str, dict]] = {}
        cls.chunks: dict[str, dict[str, dict]] = {}
        cls.chunk_text: dict[str, dict[str, str]] = {}
        cls.missing_documents: dict[str, list[Path]] = {}
        for document_id, table_names in DOCUMENTS.items():
            missing = missing_source_artifacts(document_id)
            if missing:
                cls.missing_documents[document_id] = missing
                continue
            cls.rows[document_id] = {
                name: read_csv(CURATED_DIR / document_id / f"{name}.csv")
                for name in table_names
            }
            blocks_path, chunks_path = source_artifact_paths(document_id)
            blocks = read_jsonl(blocks_path)
            chunks = read_jsonl(chunks_path)
            cls.blocks[document_id] = {
                str(block["block_id"]): block for block in blocks
            }
            cls.chunks[document_id] = {
                str(chunk["chunk_id"]): chunk for chunk in chunks
            }
            cls.chunk_text[document_id] = {
                str(chunk["chunk_id"]): norm(chunk.get("plain_text") or "")
                for chunk in chunks
            }

    def require_document(self, document_id: str) -> None:
        if document_id in self.rows:
            return
        missing = self.missing_documents.get(document_id, [])
        if not missing:
            self.skipTest(f"{document_id} tidak tersedia di artefak uji")
        relative = ", ".join(
            str(path.relative_to(PROJECT_ROOT)) for path in missing
        )
        self.skipTest(
            f"{document_id} dilewati: artefak ekstraksi tidak tersedia "
            f"(gitignored, perlu regenerate): {relative}"
        )

    # ------------------------------------------------------------------
    # Laporan validator
    # ------------------------------------------------------------------
    def test_validation_reports_pass(self) -> None:
        if not self.rows:
            self.skipTest("tidak ada dokumen dengan artefak ekstraksi lengkap")
        for document_id in self.rows:
            report = json.loads(
                (REPORTS_DIR / f"{document_id}.tables.validation.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(report["status"], "pass", msg=document_id)
            self.assertEqual(report["errors"], [], msg=document_id)
            self.assertEqual(report["checks"]["verbatim_in_chunk"], "pass")

    # ------------------------------------------------------------------
    # Verbatin dan traceability
    # ------------------------------------------------------------------
    def test_every_text_is_verbatim_in_chunk(self) -> None:
        for document_id, tables in self.rows.items():
            for name, rows in tables.items():
                for row in rows:
                    quote = row.get("verbatim_text") or ""
                    if not quote:
                        continue
                    chunk_id = row.get("chunk_id") or row.get(
                        "evidence_chunk_id"
                    )
                    self.assertIn(
                        chunk_id,
                        self.chunk_text[document_id],
                        msg=f"{document_id}/{name} chunk {chunk_id}",
                    )
                    self.assertIn(
                        norm(quote),
                        bdt.chunk_evidence(
                            self.chunks[document_id][chunk_id]
                        ),
                        msg=f"{document_id}/{name} kutipan tidak ada di {chunk_id}",
                    )

    def test_source_blocks_exist_and_pages_match(self) -> None:
        for document_id, tables in self.rows.items():
            for name, rows in tables.items():
                for row in rows:
                    block_id = row.get("source_block_id") or ""
                    if not block_id:
                        continue
                    self.assertIn(
                        block_id,
                        self.blocks[document_id],
                        msg=f"{document_id}/{name} blok {block_id}",
                    )
                    block = self.blocks[document_id][block_id]
                    if document_id == "DOC004":
                        self.assertEqual(
                            int(row["page"]),
                            int(block["page_number"]),
                            msg=f"{document_id}/{name} halaman {block_id}",
                        )

    def test_sentence_offsets_exact(self) -> None:
        documents = [doc for doc in ("DOC003", "DOC005") if doc in self.rows]
        if not documents:
            self.skipTest("tidak ada dokumen gejala/pengendalian yang tersedia")
        for document_id in documents:
            for name in ("symptoms", "controls"):
                for row in self.rows[document_id][name]:
                    text = self.chunk_text[document_id][row["chunk_id"]]
                    start = int(row["char_start"])
                    end = int(row["char_end"])
                    self.assertEqual(
                        text[start:end],
                        norm(row["verbatim_text"]),
                        msg=f"{document_id}/{name} {row['chunk_id']}@{start}",
                    )

    def test_chunk_page_range_matches_row(self) -> None:
        documents = [doc for doc in ("DOC003", "DOC005") if doc in self.rows]
        if not documents:
            self.skipTest("tidak ada dokumen gejala/pengendalian yang tersedia")
        for document_id in documents:
            for name in ("symptoms", "controls"):
                for row in self.rows[document_id][name]:
                    chunk = self.chunks[document_id][row["chunk_id"]]
                    self.assertEqual(int(row["page_start"]), chunk["page_start"])
                    self.assertEqual(int(row["page_end"]), chunk["page_end"])

    # ------------------------------------------------------------------
    # ID dan foreign key
    # ------------------------------------------------------------------
    def test_ids_unique_and_well_formed(self) -> None:
        for document_id, tables in self.rows.items():
            for name, rows in tables.items():
                fields = bdt.PRIMARY_KEYS[name]
                keys = [
                    tuple(row[field] for field in fields) for row in rows
                ]
                self.assertEqual(
                    len(keys), len(set(keys)), msg=f"{document_id}/{name} duplikat"
                )
                for key in keys:
                    for field, value in zip(fields, key):
                        self.assertRegex(
                            value,
                            bdt.ID_PATTERNS[field],
                            msg=f"{document_id}/{name}",
                        )

    def test_foreign_keys_resolve(self) -> None:
        self.require_document("DOC003")
        tables = self.rows["DOC003"]
        plant_ids = {row["plant_id"] for row in tables["plants"]}
        disease_ids = {
            row["disease_id"] for row in tables["amorphophallus_spp_diseases"]
        }
        pathogen_ids = {row["pathogen_id"] for row in tables["pathogens"]}
        self.assertEqual(
            disease_ids,
            {row["disease_id"] for row in tables["disease_pathogen"]},
        )
        self.assertEqual(
            pathogen_ids,
            {row["pathogen_id"] for row in tables["disease_pathogen"]},
        )
        for row in tables["amorphophallus_spp_diseases"]:
            self.assertIn(row["plant_id"], plant_ids)
            self.assertIn(row["pathogen_id"], pathogen_ids)
        for name in ("symptoms", "controls"):
            for row in tables[name]:
                self.assertIn(row["plant_id"], plant_ids)
                self.assertIn(row["disease_id"], disease_ids)

    def test_doc005_foreign_keys_resolve(self) -> None:
        self.require_document("DOC005")
        tables = self.rows["DOC005"]
        plant_ids = {row["plant_id"] for row in tables["plants"]}
        disease_ids = {row["disease_id"] for row in tables["diseases"]}
        pathogen_ids = {row["pathogen_id"] for row in tables["pathogens"]}
        self.assertEqual(
            disease_ids,
            {row["disease_id"] for row in tables["disease_pathogen"]},
        )
        self.assertEqual(
            pathogen_ids,
            {row["pathogen_id"] for row in tables["disease_pathogen"]},
        )
        for row in tables["diseases"]:
            self.assertIn(row["plant_id"], plant_ids)
            self.assertIn(row["pathogen_id"], pathogen_ids)
        for name in ("symptoms", "controls"):
            for row in tables[name]:
                self.assertIn(row["plant_id"], plant_ids)
                self.assertIn(row["disease_id"], disease_ids)

    # ------------------------------------------------------------------
    # Aturan domain DOC005
    # ------------------------------------------------------------------
    def test_doc005_plants_and_diseases(self) -> None:
        self.require_document("DOC005")
        tables = self.rows["DOC005"]
        plants = {row["plant_id"]: row for row in tables["plants"]}
        self.assertEqual(
            {row["plant_name_id"] for row in plants.values()},
            {"Kedelai", "Kacang tanah", "Kacang hijau"},
        )
        self.assertEqual(len(tables["diseases"]), 8)
        pairs = {
            (row["plant_id"], row["disease_name_verbatim"])
            for row in tables["diseases"]
        }
        self.assertEqual(
            pairs,
            {
                ("PLANT_018", "KARAT"),
                ("PLANT_018", "EMBUN BULU"),
                ("PLANT_018", "ANTRAKNOSA"),
                ("PLANT_019", "KARAT"),
                ("PLANT_019", "BERCAK DAUN"),
                ("PLANT_020", "EMBUN TEPUNG"),
                ("PLANT_020", "BERCAK DAUN"),
                ("PLANT_020", "LAYU"),
            },
        )

    def test_doc005_every_disease_has_symptom_and_control(self) -> None:
        self.require_document("DOC005")
        tables = self.rows["DOC005"]
        disease_ids = {row["disease_id"] for row in tables["diseases"]}
        self.assertEqual(
            disease_ids,
            {row["disease_id"] for row in tables["symptoms"]},
        )
        self.assertEqual(
            disease_ids,
            {row["disease_id"] for row in tables["controls"]},
        )

    def test_doc005_duplicate_names_are_host_specific(self) -> None:
        self.require_document("DOC005")
        rows = self.rows["DOC005"]["diseases"]
        for name in ("KARAT", "BERCAK DAUN"):
            matching = [row for row in rows if row["disease_name_verbatim"] == name]
            self.assertEqual(len(matching), 2, msg=name)
            self.assertEqual(len({row["plant_id"] for row in matching}), 2, msg=name)

    def test_doc005_pathogen_links_cover_all_diseases(self) -> None:
        self.require_document("DOC005")
        tables = self.rows["DOC005"]
        links = tables["disease_pathogen"]
        self.assertEqual(len(links), 11)
        by_disease: dict[str, int] = {}
        for row in links:
            by_disease[row["disease_id"]] = by_disease.get(row["disease_id"], 0) + 1
        self.assertEqual(
            set(by_disease),
            {row["disease_id"] for row in tables["diseases"]},
        )
        self.assertEqual(by_disease["DIS_118"], 2)
        self.assertEqual(by_disease["DIS_122"], 2)
        self.assertEqual(by_disease["DIS_124"], 2)

    def test_doc005_disease_pathogen_quotes_are_traceable(self) -> None:
        self.require_document("DOC005")
        spec = json.loads(
            (TABLE_DIR / "config" / "DOC005_tables.json").read_text(
                encoding="utf-8"
            )
        )
        builder = bdt.Builder("DOC005")
        for row in spec["tables"]["disease_pathogen"]:
            block = builder.block_by_id[row["block_id"]]
            chunk_id = builder.chunks_by_block[row["block_id"]][0]
            chunk = builder.chunk_by_id[chunk_id]
            quote = norm(row["quote"])
            self.assertIn(quote, bdt.block_evidence(block), msg=row["disease_id"])
            self.assertIn(quote, bdt.chunk_evidence(chunk), msg=row["disease_id"])

    def test_doc005_plant_ranges_match_chapter_boundaries(self) -> None:
        self.require_document("DOC005")
        headings = [
            (int(block["page_number"]), str(block.get("text") or ""))
            for block in self.blocks["DOC005"].values()
            if block.get("content_type") == "chapter_heading"
            and 17 <= int(block["page_number"]) <= 71
        ]
        starts = sorted(page for page, _ in headings)
        for plant in self.rows["DOC005"]["plants"]:
            matching = [
                page for page, title in headings if title == plant["chapter_title"]
            ]
            self.assertEqual(len(matching), 1, msg=plant["plant_id"])
            self.assertEqual(int(plant["page_start"]), matching[0])
            later = [page for page in starts if page > matching[0]]
            if later:
                self.assertEqual(int(plant["page_end"]), min(later) - 1)

    # ------------------------------------------------------------------
    # Aturan domain DOC003
    # ------------------------------------------------------------------
    def test_doc003_diseases_belong_to_suweg_not_porang(self) -> None:
        self.require_document("DOC003")
        plants = {row["plant_id"]: row for row in self.rows["DOC003"]["plants"]}
        self.assertEqual(plants["PLANT_016"]["plant_name_id"], "Porang")
        self.assertEqual(plants["PLANT_017"]["plant_name_id"], "Suweg")
        for row in self.rows["DOC003"]["amorphophallus_spp_diseases"]:
            self.assertEqual(
                row["plant_id"],
                "PLANT_017",
                msg=f"{row['disease_id']} tidak boleh diatribusikan ke porang",
            )
            self.assertTrue(
                "Amorphophallus spp." in row["host_verbatim"]
                or "suweg" in row["host_verbatim"].casefold(),
                msg=row["disease_id"],
            )

    def test_doc003_plant_ranges_match_chapter_boundaries(self) -> None:
        self.require_document("DOC003")
        headings = [
            (int(block["page_number"]), str(block.get("text") or ""))
            for block in self.blocks["DOC003"].values()
            if block.get("content_type") == "chapter_heading"
            and 9 <= int(block["page_number"]) <= 55
        ]
        starts = sorted(page for page, _ in headings)
        for plant in self.rows["DOC003"]["plants"]:
            matching = [
                page for page, title in headings if title == plant["chapter_title"]
            ]
            self.assertEqual(len(matching), 1, msg=plant["plant_id"])
            self.assertEqual(int(plant["page_start"]), matching[0])
            later = [page for page in starts if page > matching[0]]
            if later:
                self.assertEqual(int(plant["page_end"]), min(later) - 1)

    def test_doc003_source_spelling_is_preserved(self) -> None:
        self.require_document("DOC003")
        pathogens = {
            row["pathogen_id"]: row for row in self.rows["DOC003"]["pathogens"]
        }
        self.assertEqual(
            pathogens["PAT_108"]["scientific_name"], "Pythium helicoides"
        )
        self.assertIn("Phytium", pathogens["PAT_108"]["note"])
        self.assertEqual(
            pathogens["PAT_112"]["scientific_name"], "Sclerotium rolfsii"
        )
        self.assertIn("Slerotium", pathogens["PAT_112"]["note"])

    # ------------------------------------------------------------------
    # Aturan domain DOC004
    # ------------------------------------------------------------------
    def test_doc004_values_are_substrings_of_verbatim(self) -> None:
        self.require_document("DOC004")
        for name in ("fertilizers", "compost"):
            for row in self.rows["DOC004"][name]:
                quote = norm(row["verbatim_text"])
                for field in ("value", "unit"):
                    value = norm(row[field])
                    if value:
                        self.assertIn(value, quote, msg=f"{row['record_id']}:{field}")

    def test_doc004_no_unprinted_dose(self) -> None:
        self.require_document("DOC004")
        quantified = {
            row["record_id"]
            for row in self.rows["DOC004"]["fertilizers"]
            if row["value"]
        }
        self.assertEqual(
            quantified, {"FER_601", "FER_602", "FER_603", "FER_605"}
        )
        for row in self.rows["DOC004"]["fertilizers"]:
            if row["record_id"] in quantified:
                self.assertRegex(row["value"], r"^\d+(?:-\d+)?$")

    def test_doc004_categories_and_notes(self) -> None:
        self.require_document("DOC004")
        rows = [
            row
            for name in ("nutrients", "fertilizers", "practices", "compost")
            for row in self.rows["DOC004"][name]
        ]
        self.assertEqual(len(rows), 39)
        for row in rows:
            self.assertTrue(row["category"], msg=row["record_id"])
            self.assertTrue(row["subject"], msg=row["record_id"])
            self.assertTrue(row["attribute"], msg=row["record_id"])
            self.assertEqual(row["document_id"], "DOC004")

    # ------------------------------------------------------------------
    # Skema
    # ------------------------------------------------------------------
    def test_doc003_headers_match_schema(self) -> None:
        self.require_document("DOC003")
        schema = json.loads(
            (TABLE_DIR / "schema" / "knowledge_tables_DOC003.schema.json").read_text(
                encoding="utf-8"
            )
        )
        for name, rows in self.rows["DOC003"].items():
            if not rows:
                continue
            expected = list(schema["tables"][name]["columns"])
            self.assertEqual(
                list(rows[0].keys()), expected, msg=f"kolom {name}"
            )

    def test_doc005_headers_match_schema(self) -> None:
        self.require_document("DOC005")
        schema = json.loads(
            (TABLE_DIR / "schema" / "knowledge_tables_DOC005.schema.json").read_text(
                encoding="utf-8"
            )
        )
        for name, rows in self.rows["DOC005"].items():
            self.assertTrue(rows, msg=f"{name} kosong")
            expected = list(schema["tables"][name]["columns"])
            self.assertEqual(
                list(rows[0].keys()), expected, msg=f"kolom {name}"
            )
            self.assertEqual(
                list(rows[0].keys()),
                bdt.COLUMNS["DOC005"][name],
                msg=f"kolom builder {name}",
            )

    def test_doc004_headers_match_builder(self) -> None:
        self.require_document("DOC004")
        schema = json.loads(
            (TABLE_DIR / "schema" / "production_tables.schema.json").read_text(
                encoding="utf-8"
            )
        )
        for name, rows in self.rows["DOC004"].items():
            self.assertEqual(
                list(rows[0].keys()),
                bdt.COLUMNS["DOC004"][name],
                msg=f"kolom {name}",
            )
            self.assertEqual(
                list(rows[0].keys()),
                schema["tables"][name]["columns"],
                msg=f"kolom skema {name}",
            )


@unittest.skipUnless(
    not missing_source_artifacts("DOC003"),
    "DOC003 dilewati: artefak ekstraksi tidak tersedia (gitignored, perlu regenerate)",
)
class ValidatorRejectionTest(unittest.TestCase):
    def test_validator_rejects_missing_quote(self) -> None:
        builder = bdt.Builder("DOC003")
        block = builder.block_by_id["DOC003_P009_B002"]
        chunk = builder.chunk_by_id["DOC003_C009_01"]
        builder.verify_quote(
            "plants", "TEST", "kalimat yang tidak ada di sumber", block, chunk
        )
        self.assertTrue(builder.errors)
        self.assertTrue(
            any("quote_not_in_block" in error for error in builder.errors)
        )

    def test_validator_accepts_exact_quote(self) -> None:
        builder = bdt.Builder("DOC003")
        block = builder.block_by_id["DOC003_P009_B002"]
        chunk = builder.chunk_by_id["DOC003_C009_01"]
        builder.verify_quote(
            "plants",
            "TEST",
            "Porang (Amorphophallus oncophyllus Prain.)",
            block,
            chunk,
        )
        self.assertEqual(builder.errors, [])


if __name__ == "__main__":
    unittest.main()
