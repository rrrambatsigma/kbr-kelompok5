"""Gate test untuk chunk-level CSV DOC002 hasil konversi Markdown.

Fokus: keunikan ID, traceability baris, verbatim teks, konsistensi part,
dan cakupan tanaman. Jalankan dari root repo::

    python -m unittest discover -s 03_knowledge_tables/tests -p "test_*.py"
"""

from __future__ import annotations

import csv
import sys
import unittest
from pathlib import Path

TABLE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = TABLE_DIR.parent
sys.path.insert(0, str(TABLE_DIR / "src"))

from build_md_chunks import COLUMNS, DOCUMENT_ID, MAX_CHUNK_CHARS  # noqa: E402

SOURCE_MD = PROJECT_ROOT / "00_sumber_data" / "02_PenyakitTanamanPangan.md"
PLANTS_CSV = TABLE_DIR / "auto" / "plants.csv"
CHUNKS_CSV = TABLE_DIR / "auto" / "DOC002_md" / "DOC002_md_chunks.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


class TestMdChunks(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = SOURCE_MD.read_text(encoding="utf-8").replace("\r\n", "\n")
        cls.source_lines = cls.source.splitlines()
        cls.rows = read_csv(CHUNKS_CSV)
        plants = read_csv(PLANTS_CSV)
        cls.plant_names = {
            (row.get("plant_name_id") or "").strip()
            for row in plants
            if (row.get("plant_name_id") or "").strip()
        }

    def test_output_exists_and_has_columns(self) -> None:
        self.assertTrue(CHUNKS_CSV.exists(), CHUNKS_CSV)
        self.assertGreater(len(self.rows), 0)
        self.assertEqual(list(self.rows[0].keys()), COLUMNS)

    def test_chunk_id_unique(self) -> None:
        ids = [row["chunk_id"] for row in self.rows]
        self.assertEqual(len(ids), len(set(ids)))

    def test_document_id(self) -> None:
        self.assertTrue(all(row["document_id"] == DOCUMENT_ID for row in self.rows))

    def test_line_ranges_valid(self) -> None:
        total = len(self.source_lines)
        for row in self.rows:
            start = int(row["line_start"])
            end = int(row["line_end"])
            self.assertGreaterEqual(start, 1, row["chunk_id"])
            self.assertLessEqual(start, end, row["chunk_id"])
            self.assertLessEqual(end, total, row["chunk_id"])

    def test_text_nonempty_and_verbatim(self) -> None:
        for row in self.rows:
            text = row["text_markdown"]
            self.assertTrue(text.strip(), row["chunk_id"])
            self.assertEqual(int(row["char_count"]), len(text), row["chunk_id"])
            self.assertIn(text, self.source, row["chunk_id"])

    def test_part_consistency(self) -> None:
        groups: dict[str, list[dict[str, str]]] = {}
        for row in self.rows:
            base = row["chunk_id"].rsplit("_", 1)[0]
            groups.setdefault(base, []).append(row)
        for base, group in groups.items():
            total = int(group[0]["part_total"])
            self.assertEqual(len(group), total, base)
            self.assertEqual(
                sorted(int(row["part_index"]) for row in group),
                list(range(1, total + 1)),
                base,
            )
            for row in group:
                if row["content_type"] != "table":
                    self.assertLessEqual(int(row["char_count"]), MAX_CHUNK_CHARS, row["chunk_id"])

    def test_plants_known(self) -> None:
        for row in self.rows:
            name = row["plant_name"]
            if name:
                self.assertIn(name, self.plant_names, row["chunk_id"])
            if row["doc_part"] == "body":
                self.assertTrue(name, row["chunk_id"])

    def test_table_chunks_contain_table_markup(self) -> None:
        for row in self.rows:
            if row["content_type"] == "table":
                self.assertIn("|", row["text_markdown"], row["chunk_id"])


if __name__ == "__main__":
    unittest.main()
