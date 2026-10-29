"""Gate test untuk knowledge table DOC002 (Tahap 2).

Semua test bersifat read-only terhadap sumber dan artefak ``auto/``.
Jalankan dari ``03_knowledge_tables``:

    python -m unittest discover -s tests -p "test_*.py"
"""

from __future__ import annotations

import csv
import json
import re
import unittest
from collections import Counter
from pathlib import Path

TABLE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = TABLE_DIR.parent
CHUNKS_PATH = PROJECT_ROOT / "02_extraction" / "extracted_text" / "DOC002.chunks.jsonl"
CONFIG_PATH = TABLE_DIR / "config" / "chapter_map.json"
SCHEMA_PATH = TABLE_DIR / "schema" / "knowledge_tables.schema.json"
AUTO_DIR = TABLE_DIR / "auto"

WS_RE = re.compile(r"\s+")

# Snapshot jumlah penyakit per tanaman pada build pertama yang stabil.
EXPECTED_DISEASES = {
    "PLANT_001": 5,
    "PLANT_002": 15,
    "PLANT_003": 3,
    "PLANT_004": 4,
    "PLANT_005": 16,
    "PLANT_006": 5,
    "PLANT_007": 8,
    "PLANT_008": 13,
    "PLANT_009": 7,
    "PLANT_010": 8,
    "PLANT_011": 4,
    "PLANT_012": 6,
    "PLANT_013": 5,
    "PLANT_014": 7,
    "PLANT_015": 3,
}


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


class KnowledgeTableTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.plants = read_csv(AUTO_DIR / "plants.csv")
        cls.diseases = read_csv(AUTO_DIR / "diseases.csv")
        cls.table_rows = read_csv(AUTO_DIR / "ubi_kayu_table_rows.csv")
        cls.chunks = read_jsonl(CHUNKS_PATH)
        cls.chunk_text = {
            chunk["chunk_id"]: norm(chunk["plain_text"]) for chunk in cls.chunks
        }

    # G1 — kelengkapan tanaman -------------------------------------------------
    def test_g1_all_plants_present(self) -> None:
        self.assertEqual(len(self.plants), 15)
        self.assertEqual(
            [row["plant_id"] for row in self.plants],
            [f"PLANT_{index:03d}" for index in range(1, 16)],
        )
        self.assertEqual(
            {row["chapter_number"] for row in self.plants},
            {str(index) for index in range(1, 16)},
        )

    def test_g1_chapter_map_matches_plants(self) -> None:
        chapters = self.config["chapters"]
        self.assertEqual(len(chapters), 15)
        self.assertEqual(
            [chapter["plant_id"] for chapter in chapters],
            [row["plant_id"] for row in self.plants],
        )
        for chapter, plant in zip(chapters, self.plants):
            self.assertLessEqual(chapter["page_start"], chapter["page_end"])
            self.assertEqual(plant["chapter_title"], chapter["chapter_title"])
            self.assertEqual(
                int(plant["page_start"]), chapter["page_start"]
            )

    def test_g1_scientific_name_verbatim(self) -> None:
        filled = 0
        for plant in self.plants:
            name = plant["scientific_name"]
            if not name:
                continue
            filled += 1
            evidence = self.chunk_text.get(plant["evidence_chunk_id"], "")
            self.assertIn(
                norm(name),
                evidence,
                msg=f"{plant['plant_id']} scientific_name tidak verbatim di bukti",
            )
        # 8 tanaman mencetak nama ilmiah di dalam bab; sisanya hanya di daftar pustaka.
        self.assertEqual(filled, 8)

    # G2 — setiap penyakit punya bukti ----------------------------------------
    def test_g2_disease_inventory(self) -> None:
        self.assertEqual(len(self.diseases), 109)
        self.assertEqual(len({row["disease_id"] for row in self.diseases}), 109)

    def test_g2_diseases_per_plant(self) -> None:
        counts = Counter(row["plant_id"] for row in self.diseases)
        self.assertEqual(dict(counts), EXPECTED_DISEASES)

    def test_g2_evidence_present(self) -> None:
        for row in self.diseases:
            if row["heading_level"] == "table":
                self.assertTrue(
                    row["source_block_ids"],
                    msg=f"{row['disease_id']} tidak punya block bukti",
                )
                continue
            self.assertTrue(
                row["evidence_chunk_ids"],
                msg=f"{row['disease_id']} tidak punya chunk bukti",
            )
            for chunk_id in row["evidence_chunk_ids"].split(";"):
                if chunk_id:
                    self.assertIn(chunk_id, self.chunk_text)

    def test_g2_pages_inside_chapter(self) -> None:
        chapter_pages = {
            chapter["plant_id"]: (chapter["page_start"], chapter["page_end"])
            for chapter in self.config["chapters"]
        }
        for row in self.diseases:
            start = int(row["page_start"])
            end = int(row["page_end"])
            low, high = chapter_pages[row["plant_id"]]
            self.assertLessEqual(start, end)
            self.assertGreaterEqual(start, low, msg=f"{row['disease_id']} di luar bab")
            self.assertLessEqual(end, high, msg=f"{row['disease_id']} di luar bab")

    # G3 — verbatim ------------------------------------------------------------
    def test_g3_disease_name_verbatim(self) -> None:
        violations = []
        for row in self.diseases:
            name = row["disease_name_verbatim"]
            if not name:
                continue
            evidence = [
                item for item in row["evidence_chunk_ids"].split(";") if item
            ]
            if not evidence:
                continue
            if not any(norm(name) in self.chunk_text.get(item, "") for item in evidence):
                violations.append(row["disease_id"])
        self.assertEqual(violations, [])

    def test_g3_name_en_verbatim(self) -> None:
        for row in self.diseases:
            name_en = row["name_en_verbatim"]
            if not name_en:
                continue
            evidence = [
                item for item in row["evidence_chunk_ids"].split(";") if item
            ]
            self.assertTrue(
                any(norm(name_en) in self.chunk_text.get(item, "") for item in evidence),
                msg=f"{row['disease_id']} name_en tidak verbatim",
            )

    # G5 — tidak ada duplikat liar --------------------------------------------
    def test_g5_no_duplicate_disease_key_per_plant(self) -> None:
        keys = Counter((row["plant_id"], row["disease_name_key"]) for row in self.diseases)
        duplicates = [key for key, count in keys.items() if count > 1]
        self.assertEqual(duplicates, [])

    def test_g5_group_headings_excluded(self) -> None:
        banned = (
            "pendahuluan",
            "arti penting",
            "macam-macam",
            "patogen pada",
            "penyebab",
            "gejala",
            "pengendalian",
        )
        for row in self.diseases:
            name = row["disease_name_verbatim"].lower()
            if not name:
                continue
            for prefix in banned:
                self.assertFalse(
                    name.startswith(prefix),
                    msg=f"{row['disease_id']} masih heading grup: {name}",
                )

    def test_g5_no_chapter_heading_as_disease(self) -> None:
        for row in self.diseases:
            self.assertNotEqual(
                row["disease_name_verbatim"],
                row["chapter_title"],
                msg=f"{row['disease_id']} memakai judul bab sebagai penyakit",
            )

    # Bab 5 — tabel ubi kayu ---------------------------------------------------
    def test_bab5_tables_stitched(self) -> None:
        self.assertEqual(len(self.table_rows), 19)
        by_table = Counter(row["table_id"] for row in self.table_rows)
        self.assertEqual(
            dict(by_table),
            {"T5.1_DAUN": 10, "T5.2_BATANG": 6, "T5.3_AKAR": 3},
        )
        by_status = Counter(row["status"] for row in self.table_rows)
        self.assertEqual(
            dict(by_status), {"complete": 15, "unnumbered": 2, "missing_row": 2}
        )

    def test_bab5_missing_rows_marked(self) -> None:
        missing = [
            (row["table_id"], row["row_no"])
            for row in self.table_rows
            if row["status"] == "missing_row"
        ]
        self.assertEqual(sorted(missing), [("T5.1_DAUN", "3"), ("T5.1_DAUN", "7")])

    def test_bab5_rows_have_content_or_gap(self) -> None:
        for row in self.table_rows:
            if row["status"] == "missing_row":
                self.assertEqual(row["disease_name"], "")
                continue
            self.assertTrue(
                row["disease_name"] or row["pathogen_name"],
                msg=f"{row['table_id']} baris {row['row_no']} kosong",
            )
            self.assertTrue(
                row["source_block_id"],
                msg=f"{row['table_id']} baris {row['row_no']} tanpa blok",
            )

    # Skema --------------------------------------------------------------------
    def test_schema_matches_csv_headers(self) -> None:
        pairs = {
            "plants": self.plants,
            "diseases": self.diseases,
            "ubi_kayu_tabel_5": self.table_rows,
        }
        for table_name, rows in pairs.items():
            expected = list(self.schema["tables"][table_name]["columns"])
            self.assertEqual(
                list(rows[0].keys()),
                expected,
                msg=f"kolom {table_name} tidak cocok dengan skema",
            )

    def test_schema_primary_keys_unique(self) -> None:
        for table_name, rows in (
            ("plants", self.plants),
            ("diseases", self.diseases),
        ):
            key = self.schema["tables"][table_name]["primary_key"]
            values = [row[key] for row in rows]
            self.assertEqual(len(values), len(set(values)), msg=f"{table_name} duplikat")


class CuratedTableTest(unittest.TestCase):
    """Lapisan curated harus bersih dari baris yang belum diputuskan."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.diseases = read_csv(TABLE_DIR / "curated" / "diseases.csv")
        cls.table_rows = read_csv(TABLE_DIR / "curated" / "ubi_kayu_tabel_5.csv")
        cls.log = read_csv(TABLE_DIR / "review" / "curation_log.csv")
        cls.chunks = read_jsonl(CHUNKS_PATH)
        cls.chunk_text = {
            chunk["chunk_id"]: norm(chunk["plain_text"]) for chunk in cls.chunks
        }
        cls.block_text = {}
        for block in read_jsonl(
            PROJECT_ROOT / "02_extraction" / "extracted_text" / "DOC002.blocks.jsonl"
        ):
            cells = []
            for row in (block.get("table") or {}).get("cells") or []:
                if isinstance(row, list):
                    cells.extend(norm(cell) for cell in row if cell)
            cls.block_text[block["block_id"]] = " | ".join(cells)

    def test_all_rows_decided(self) -> None:
        self.assertEqual(len(self.diseases), 110)
        flagged = [
            row["disease_id"]
            for row in self.diseases
            if row["review_status"] not in {"verified", "auto_ok"}
        ]
        self.assertEqual(flagged, [])

    def test_no_row_left_without_name(self) -> None:
        empty = [
            row["disease_id"]
            for row in self.diseases
            if not row["disease_name_verbatim"]
        ]
        self.assertEqual(empty, [])

    def test_curated_names_verbatim(self) -> None:
        violations = []
        for row in self.diseases:
            name = row["disease_name_verbatim"]
            if row["heading_level"] == "table":
                source = " | ".join(
                    self.block_text.get(block_id, "")
                    for block_id in row["source_block_ids"].split(";")
                    if block_id
                )
            else:
                source = " | ".join(
                    self.chunk_text.get(chunk_id, "")
                    for chunk_id in row["evidence_chunk_ids"].split(";")
                    if chunk_id
                )
            if norm(name) not in source:
                violations.append(row["disease_id"])
        self.assertEqual(violations, [])

    def test_every_verified_row_has_log_entry(self) -> None:
        logged = {
            entry["record_id"]
            for entry in self.log
            if entry["record_type"] == "disease"
        }
        for row in self.diseases:
            if row["review_status"] == "verified":
                self.assertIn(
                    row["disease_id"],
                    logged,
                    msg=f"{row['disease_id']} diverifikasi tanpa catatan log",
                )

    def test_table_gaps_kept(self) -> None:
        self.assertEqual(len(self.table_rows), 19)
        missing = sorted(
            (row["table_id"], row["row_no"])
            for row in self.table_rows
            if row["status"] == "missing_row"
        )
        self.assertEqual(missing, [("T5.1_DAUN", "3"), ("T5.1_DAUN", "7")])


class ExtendedTableTest(unittest.TestCase):
    """Tabel patogen, gejala, dan pengendalian (Blok B/C/D)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.plants = read_csv(AUTO_DIR / "plants.csv")
        cls.diseases = read_csv(TABLE_DIR / "curated" / "diseases.csv")
        cls.pathogens = read_csv(TABLE_DIR / "curated" / "pathogens.csv")
        cls.links = read_csv(TABLE_DIR / "curated" / "disease_pathogen.csv")
        cls.symptoms = read_csv(TABLE_DIR / "curated" / "symptoms.csv")
        cls.controls = read_csv(TABLE_DIR / "curated" / "controls.csv")
        cls.table_rows = read_csv(TABLE_DIR / "curated" / "ubi_kayu_tabel_5.csv")
        cls.chunks = {
            row["chunk_id"]: norm(row["plain_text"])
            for row in read_jsonl(CHUNKS_PATH)
        }
        cls.block_text = {}
        for block in read_jsonl(
            PROJECT_ROOT / "02_extraction" / "extracted_text" / "DOC002.blocks.jsonl"
        ):
            cells = []
            for row in (block.get("table") or {}).get("cells") or []:
                if isinstance(row, list):
                    cells.extend(norm(cell) for cell in row if cell)
            cls.block_text[block["block_id"]] = " | ".join(cells)
        cls.disease_by_id = {row["disease_id"]: row for row in cls.diseases}
        cls.pathogen_by_id = {row["pathogen_id"]: row for row in cls.pathogens}

    def test_table_sizes(self) -> None:
        self.assertEqual(len(self.diseases), 110)
        self.assertEqual(len(self.pathogens), 105)
        self.assertEqual(len(self.links), 132)
        self.assertEqual(len(self.symptoms), 601)
        self.assertEqual(len(self.controls), 528)

    def test_pathogen_review_status_final(self) -> None:
        pending = [
            row["pathogen_id"]
            for row in self.pathogens
            if row["review_status"] not in {"auto_ok", "verified"}
        ]
        self.assertEqual(pending, [])

    def test_pathogen_names_verbatim(self) -> None:
        violations = []
        for pathogen in self.pathogens:
            sources = []
            chunk_id = pathogen["chunk_id"]
            if chunk_id in self.chunks:
                sources.append(self.chunks[chunk_id])
            for link in self.links:
                if link["pathogen_id"] != pathogen["pathogen_id"]:
                    continue
                disease = self.disease_by_id[link["disease_id"]]
                heading = norm(disease["subsection"] or disease["section"])
                if heading:
                    sources.append(heading)
                for block_id in disease["source_block_ids"].split(";"):
                    if block_id in self.block_text:
                        sources.append(self.block_text[block_id])
            if not any(norm(pathogen["verbatim_text"]) in source for source in sources):
                violations.append(pathogen["pathogen_id"])
        self.assertEqual(violations, [])

    def test_pathogen_foreign_keys_and_orphans(self) -> None:
        disease_ids = set(self.disease_by_id)
        pathogen_ids = set(self.pathogen_by_id)
        for link in self.links:
            self.assertIn(link["disease_id"], disease_ids)
            self.assertIn(link["pathogen_id"], pathogen_ids)
        self.assertEqual(pathogen_ids, {link["pathogen_id"] for link in self.links})

    def test_taxon_evidence_verbatim(self) -> None:
        for pathogen in self.pathogens:
            self.assertIn(
                pathogen["taxon_group"], self.schema["tables"]["pathogens"]["columns"]["taxon_group"]["values"]
            )
            quote = pathogen["taxon_evidence_quote"]
            if not quote:
                continue
            ref = pathogen["taxon_evidence_chunk_id"]
            self.assertIn(ref, self.chunks)
            self.assertIn(norm(quote), self.chunks[ref])

    def test_rejected_pathogens_absent(self) -> None:
        names = {row["scientific_name"] for row in self.pathogens}
        for rejected in (
            "Lebih lanjut",
            "Perubahan ketahanan",
            "Similis menimbulkan",
            "Kerusakan parah",
            "Bekas tusukan",
            "Misalnya pemberian",
            "Memangkas bagian",
            "Fusarium",
        ):
            self.assertNotIn(rejected, names)

    def test_sentence_offsets_exact(self) -> None:
        for name, rows in (("symptoms", self.symptoms), ("controls", self.controls)):
            for row in rows:
                text = self.chunks[row["chunk_id"]]
                start = int(row["char_start"])
                end = int(row["char_end"])
                self.assertEqual(
                    text[start:end],
                    row["verbatim_text"],
                    msg=f"{name} {row['chunk_id']}@{start} tidak cocok",
                )

    def test_sentence_foreign_keys(self) -> None:
        disease_ids = set(self.disease_by_id)
        plant_ids = {row["plant_id"] for row in self.plants}
        for row in self.symptoms:
            self.assertIn(row["disease_id"], disease_ids)
            self.assertIn(row["plant_id"], plant_ids)
        for row in self.controls:
            self.assertIn(row["plant_id"], plant_ids)
            if row["scope"] == "disease":
                self.assertIn(row["disease_id"], disease_ids)
            else:
                self.assertEqual(row["scope"], "chapter")
                self.assertEqual(row["disease_id"], "")

    def test_every_disease_has_symptom(self) -> None:
        symptom_diseases = {row["disease_id"] for row in self.symptoms}
        table_keys = {
            (row["table_id"], row["disease_name"])
            for row in self.table_rows
            if row["symptom_text"].strip() and row["status"] != "missing_row"
        }
        missing = [
            row["disease_id"]
            for row in self.diseases
            if row["disease_id"] not in symptom_diseases
            and (row["section"], row["disease_name_verbatim"]) not in table_keys
        ]
        self.assertEqual(missing, [])

    def test_validation_report_passes(self) -> None:
        validation = json.loads(
            (TABLE_DIR / "reports" / "validation.json").read_text(encoding="utf-8")
        )
        self.assertTrue(validation["gate_passed"])
        self.assertEqual(len(validation["gates"]), 7)
        for name, gate in validation["gates"].items():
            self.assertTrue(gate["passed"], msg=name)

    def test_schema_headers_match_extended_tables(self) -> None:
        pairs = {
            "pathogens": self.pathogens,
            "disease_pathogen": self.links,
            "symptoms": self.symptoms,
            "controls": self.controls,
        }
        for table_name, rows in pairs.items():
            expected = list(self.schema["tables"][table_name]["columns"])
            self.assertEqual(
                list(rows[0].keys()),
                expected,
                msg=f"kolom {table_name} tidak cocok dengan skema",
            )


if __name__ == "__main__":
    unittest.main()
