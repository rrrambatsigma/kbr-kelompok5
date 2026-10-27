"""Unit test untuk fungsi parsing murni (tanpa PDF dan tanpa PyMuPDF)."""

from __future__ import annotations

import unittest

from pdf_pipeline import parse


def make_line(
    text: str,
    size: float = 12.0,
    bold: bool = False,
    bbox: tuple[float, float, float, float] = (0.0, 0.0, 100.0, 12.0),
) -> dict:
    return {
        "bbox": list(bbox),
        "text": text,
        "spans": [
            {
                "text": text,
                "size": size,
                "font": "Helvetica-Bold" if bold else "Helvetica",
                "flags": 16 if bold else 0,
                "bbox": list(bbox),
            }
        ],
    }


class ParsingTests(unittest.TestCase):
    def test_clean_line_removes_control_and_collapses_whitespace(self) -> None:
        text, actions = parse.clean_line("  Teks\x00   penting\tsekali  ")
        self.assertEqual(text, "Teks penting sekali")
        self.assertIn("removed_control_characters", actions)
        self.assertIn("collapsed_whitespace", actions)

    def test_join_preserves_hyphen_by_default(self) -> None:
        text, actions, raw_text = parse.join_text_lines(["penya-", "kit"])
        self.assertEqual(text, "penya- kit")
        self.assertIn("line_break_hyphen_preserved", actions)
        self.assertIsNone(raw_text)

    def test_join_dehyphenates_when_enabled(self) -> None:
        text, actions, raw_text = parse.join_text_lines(
            ["penya-", "kit"], dehyphenate=True
        )
        self.assertEqual(text, "penyakit")
        self.assertIn("dehyphenated_line_break", actions)
        self.assertIsNotNone(raw_text)

    def test_classify_heading_patterns(self) -> None:
        self.assertEqual(
            parse.classify_heading("BAB I PENDAHULUAN", 12.0, 0.0, 12.0),
            "chapter_heading",
        )
        self.assertEqual(
            parse.classify_heading("1.2 Gejala Penyakit", 16.0, 1.0, 12.0),
            "section_heading",
        )
        self.assertEqual(
            parse.classify_heading("1.2.3 Faktor Lingkungan", 16.0, 1.0, 12.0),
            "subsection_heading",
        )
        self.assertIsNone(
            parse.classify_heading("Paragraf biasa tanpa penekanan.", 12.0, 0.0, 12.0)
        )
        self.assertIsNone(
            parse.classify_heading("BAB I membahas gejala penyakit.", 12.0, 0.0, 12.0)
        )
        self.assertEqual(
            parse.classify_heading("BAB I Pendahuluan", 12.0, 0.0, 12.0),
            "chapter_heading",
        )

    def test_update_context(self) -> None:
        context = {"chapter": None, "section": None, "subsection": None}
        context = parse.update_context(context, "chapter_heading", "BAB I")
        self.assertEqual(context["chapter"], "BAB I")

        context = parse.update_context(context, "section_heading", "1.1 Latar")
        self.assertEqual(context["section"], "1.1 Latar")

        context = parse.update_context(
            context, "subsection_heading", "1.1.1 Detail"
        )
        self.assertEqual(context["subsection"], "1.1.1 Detail")

        context = parse.update_context(context, "chapter_heading", "BAB II")
        self.assertEqual(context["chapter"], "BAB II")
        self.assertIsNone(context["section"])
        self.assertIsNone(context["subsection"])

    def test_detect_printed_page_number_sequence(self) -> None:
        detected = parse.detect_printed_page_number_sequence(
            {1: 1, 2: 2, 3: 3, 7: 7, 8: 8}
        )
        self.assertEqual(detected, {1: "1", 2: "2", 3: "3"})
        self.assertNotIn(7, detected)

    def test_parse_minimal_document(self) -> None:
        document = {
            "document_id": "DOCX",
            "source_sha256": "a",
            "source_sha256_after": "a",
            "pages": [
                {
                    "page_number": 1,
                    "page_width": 600.0,
                    "page_height": 800.0,
                    "page_rotation": 0,
                    "raw_text": "BAB I\nPENDAHULUAN\n\nTeks paragraf.",
                    "text_blocks": [
                        {
                            "bbox": [50.0, 50.0, 550.0, 92.0],
                            "lines": [
                                make_line(
                                    "BAB I", 18.0, True, (50.0, 50.0, 550.0, 70.0)
                                ),
                                make_line(
                                    "PENDAHULUAN",
                                    18.0,
                                    True,
                                    (50.0, 72.0, 550.0, 92.0),
                                ),
                            ],
                        },
                        {
                            "bbox": [50.0, 120.0, 550.0, 140.0],
                            "lines": [
                                make_line(
                                    "Teks paragraf.",
                                    12.0,
                                    False,
                                    (50.0, 120.0, 550.0, 140.0),
                                )
                            ],
                        },
                    ],
                    "image_count": 0,
                    "image_coverage_ratio": 0.0,
                    "page_label": None,
                    "extraction_error": None,
                    "table_blocks": [],
                    "table_notes": [],
                }
            ],
        }

        parsed = parse.parse_document(document)
        self.assertEqual(parsed["extraction_status"], "completed")
        self.assertEqual(len(parsed["blocks"]), 2)
        self.assertEqual(parsed["blocks"][0]["content_type"], "chapter_heading")
        self.assertEqual(parsed["blocks"][0]["chapter"], "BAB I PENDAHULUAN")
        self.assertEqual(parsed["blocks"][1]["content_type"], "paragraph")
        self.assertEqual(parsed["blocks"][1]["chapter"], "BAB I PENDAHULUAN")
        self.assertEqual(parsed["blocks"][1]["sequence_number"], 2)


if __name__ == "__main__":
    unittest.main()
