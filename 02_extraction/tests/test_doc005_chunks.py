"""Gate test chunk DOC005 dari Markdown."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

EXTRACTION_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(EXTRACTION_DIR))

import build_doc005_chunks as doc  # noqa: E402

EXPECTED = [
    ("DOC005_C017_01", "KEDELAI", "Kedelai", "KARAT", 17, 26, 13316),
    ("DOC005_C026_01", "KEDELAI", "Kedelai", "EMBUN BULU", 26, 31, 6030),
    ("DOC005_C031_01", "KEDELAI", "Kedelai", "ANTRAKNOSA", 31, 38, 10568),
    ("DOC005_C038_01", "KACANG TANAH", "KacangTanah", "KARAT", 38, 44, 8989),
    ("DOC005_C044_01", "KACANG TANAH", "KacangTanah", "BERCAK DAUN", 44, 52, 12428),
    ("DOC005_C052_01", "KACANG HIJAU", "KacangHijau", "EMBUN TEPUNG", 52, 59, 8860),
    ("DOC005_C059_01", "KACANG HIJAU", "KacangHijau", "BERCAK DAUN", 59, 64, 7534),
    ("DOC005_C064_01", "KACANG HIJAU", "KacangHijau", "LAYU", 64, 84, 34063),
]


class TestDoc005Chunks(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.chunks = doc.build_chunks()

    def test_expected_chunk_metadata(self) -> None:
        self.assertEqual(len(self.chunks), len(EXPECTED))
        actual = [
            (
                row["chunk_id"],
                row["chapter"],
                row["plant_name"],
                row["disease_name"],
                row["page_start"],
                row["page_end"],
                len(row["text_markdown"]),
            )
            for row in self.chunks
        ]
        self.assertEqual(actual, EXPECTED)

    def test_plain_text_matches_markdown(self) -> None:
        for row in self.chunks:
            self.assertEqual(row["text_markdown"], row["plain_text"], row["chunk_id"])

    def test_page_markers_are_removed(self) -> None:
        for row in self.chunks:
            self.assertNotIn("<!-- page:", row["text_markdown"], row["chunk_id"])

    def test_output_is_valid_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "DOC005.chunks.jsonl"
            doc.write_chunks(self.chunks, output)
            rows = [
                json.loads(line)
                for line in output.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        self.assertEqual(rows, self.chunks)

    def test_source_reference_matches_pages(self) -> None:
        for row in self.chunks:
            self.assertEqual(
                row["source_reference"],
                f"DOC005 PDF hlm. {row['page_start']}-{row['page_end']}",
            )


if __name__ == "__main__":
    unittest.main()
