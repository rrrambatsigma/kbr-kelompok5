"""Unit test untuk pipeline LlamaParse (tanpa jaringan dan tanpa API key)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from llamaparse_pipeline import (
    baseline,
    chunk,
    clean,
    compare,
    normalize,
    promote,
    reconcile,
    structure,
)


def naive_levenshtein(first: str, second: str) -> int:
    previous = list(range(len(second) + 1))
    for i, char_first in enumerate(first, start=1):
        current = [i]
        for j, char_second in enumerate(second, start=1):
            insert = current[j - 1] + 1
            delete = previous[j] + 1
            substitute = previous[j - 1] + (char_first != char_second)
            current.append(min(insert, delete, substitute))
        previous = current
    return previous[-1]


class CleanTests(unittest.TestCase):
    def test_collapses_whitespace_without_changing_tokens(self) -> None:
        text = "Hawar  daun\tbakteri\n(Xanthomonas oryzae)  "
        cleaned, actions = clean.clean_block_text(text)
        self.assertEqual(cleaned, "Hawar daun bakteri (Xanthomonas oryzae)")
        self.assertIn("collapsed_whitespace", actions)
        self.assertEqual(
            clean.substance_tokens(text), clean.substance_tokens(cleaned)
        )

    def test_page_number_detection(self) -> None:
        self.assertTrue(clean.is_standalone_page_number("67"))
        self.assertTrue(clean.is_standalone_page_number(" - 67 - "))
        self.assertFalse(clean.is_standalone_page_number("67 tanaman"))

    def test_printed_page_number(self) -> None:
        self.assertEqual(clean.parse_printed_page_number("67"), (67, "arabic"))
        self.assertEqual(clean.parse_printed_page_number("xii"), (None, "roman:xii"))

    def test_strip_markdown_removes_syntax_only(self) -> None:
        value = "## **Gejala**\n\nLihat [sumber](https://example.com)."
        self.assertEqual(clean.strip_markdown(value), "Gejala Lihat sumber.")

    def test_strip_syntax_keeps_link_label_and_numeric_angles(self) -> None:
        value = "Lihat [sumber](https://example.com) dan <u>gejala</u>."
        cleaned, changed = clean.strip_syntax(value)
        self.assertTrue(changed)
        self.assertEqual(cleaned, "Lihat sumber dan  gejala .")
        self.assertEqual(
            clean.strip_syntax("suhu <30 °C dan >40 °C")[0], "suhu <30 °C dan >40 °C"
        )

    def test_running_edge_line_requires_page_number_and_edge(self) -> None:
        header_bbox = [66.0, 79.99, 390.0, 91.0]
        body_bbox = [66.0, 200.0, 390.0, 210.0]
        self.assertTrue(
            clean.is_running_edge_line("Bab 1 Penyakit Padi 3", header_bbox, 649.2)
        )
        self.assertTrue(
            clean.is_running_edge_line("16 Penyakit Tanaman dan Pengendaliannya", header_bbox, 649.2)
        )
        self.assertFalse(
            clean.is_running_edge_line("Bab 1 Penyakit Padi 3", body_bbox, 649.2)
        )
        self.assertFalse(
            clean.is_running_edge_line("Gambar 1.2: Gejala penyakit", header_bbox, 649.2)
        )

    def test_layout_conflict_flags_overlapping_table(self) -> None:
        overlapping = [
            {"type": "table", "bbox": {"x": 175.0, "y": 150.0, "w": 170.0, "h": 360.0}},
            {"type": "text", "bbox": {"x": 82.0, "y": 150.0, "w": 300.0, "h": 400.0}},
        ]
        separate = [
            {"type": "table", "bbox": {"x": 66.0, "y": 100.0, "w": 300.0, "h": 200.0}},
            {"type": "text", "bbox": {"x": 66.0, "y": 400.0, "w": 300.0, "h": 200.0}},
        ]
        self.assertTrue(clean.detect_layout_conflict(overlapping))
        self.assertFalse(clean.detect_layout_conflict(separate))

    def test_bbox_edges_accepts_llamaparse_shapes(self) -> None:
        self.assertEqual(
            clean.bbox_edges({"x": 1, "y": 2, "w": 3, "h": 4}), (1.0, 2.0, 4.0, 6.0)
        )
        self.assertEqual(
            clean.bbox_edges(
                [
                    {"x": 10, "y": 10, "w": 5, "h": 5},
                    {"x": 20, "y": 20, "w": 5, "h": 5},
                ]
            ),
            (10.0, 10.0, 25.0, 25.0),
        )

    def test_derive_printed_page_number_from_header(self) -> None:
        self.assertEqual(
            clean.derive_printed_page_number("Bab 1 Penyakit Padi  3", None),
            (3, "header", "Bab 1 Penyakit Padi 3"),
        )
        self.assertEqual(
            clean.derive_printed_page_number(
                "16 Penyakit Tanaman dan Pengendaliannya", None
            ),
            (16, "header", "16 Penyakit Tanaman dan Pengendaliannya"),
        )
        self.assertEqual(
            clean.derive_printed_page_number(None, None), (None, None, None)
        )


class StructureTests(unittest.TestCase):
    def test_chapter_label_and_title_are_combined(self) -> None:
        context = structure.DocumentContext()
        self.assertEqual(
            structure.update_for_heading(context, "Bab 1", 1), "chapter_heading"
        )
        self.assertEqual(
            structure.update_for_heading(context, "Penyakit Padi", 1),
            "chapter_heading",
        )
        self.assertEqual(context.chapter, "Bab 1 — Penyakit Padi")
        self.assertEqual(context.plant_name, "Padi")

    def test_section_and_subsection(self) -> None:
        context = structure.DocumentContext()
        structure.update_for_heading(context, "Bab 2 — Penyakit Kedelai", 1)
        structure.update_for_heading(context, "2.2 Penyakit Antraknosa", 2)
        self.assertEqual(context.disease_name, "Antraknosa")
        structure.update_for_heading(context, "2.2.1 Gejala", 3)
        self.assertEqual(context.subsection, "2.2.1 Gejala")
        self.assertEqual(context.chunk_type, "symptoms")

    def test_generic_heading_is_not_a_disease(self) -> None:
        disease, source = structure.disease_from_section("1.1 Pendahuluan")
        self.assertIsNone(disease)
        self.assertIsNone(source)

    def test_plant_not_guessed_for_multi_crop_title(self) -> None:
        plant, source = structure.plant_from_chapter("Penyakit Padi dan Kedelai")
        self.assertIsNone(plant)
        self.assertIsNone(source)

    def test_heading_level_comes_from_numbering(self) -> None:
        self.assertEqual(structure.resolve_heading_level("Bab 5", 5), 1)
        self.assertEqual(structure.resolve_heading_level("5.2 Penyakit Batang", 1), 2)
        self.assertEqual(
            structure.resolve_heading_level("5.2.1 Penyakit Daun", 1), 3
        )
        self.assertEqual(structure.resolve_heading_level("Pendahuluan", 2), 2)

    def test_caption_kind(self) -> None:
        self.assertEqual(
            structure.caption_kind("Gambar 2.3: Siklus Penyakit"), "figure"
        )
        self.assertEqual(
            structure.caption_kind("Tabel 5.1: Penyakit Pada Daun"), "table"
        )
        self.assertIsNone(structure.caption_kind("Pengendalian Penyakit"))

    def test_unknown_level_one_heading_keeps_chapter(self) -> None:
        context = structure.DocumentContext()
        structure.update_for_heading(context, "Bab 2 — Penyakit Kedelai", 1)
        result = structure.update_for_heading(context, "Tanaman akan layu", 1)
        self.assertEqual(result, "heading_unclassified")
        self.assertEqual(context.chapter, "Bab 2 — Penyakit Kedelai")

    def test_subsection_derives_section_number(self) -> None:
        context = structure.DocumentContext()
        structure.update_for_heading(context, "Bab 5 — Penyakit Ubi Kayu", 1)
        structure.update_for_heading(context, "5.2.1 Penyakit Pada Daun", 1)
        self.assertEqual(context.subsection, "5.2.1 Penyakit Pada Daun")
        self.assertEqual(context.section, "5.2")
        self.assertEqual(context.section_source, "derived_from_subsection_number")


class NormalizeTests(unittest.TestCase):
    def test_bbox_dict_to_list(self) -> None:
        self.assertEqual(
            normalize._bbox_to_list({"x": 1, "y": 2, "w": 3, "h": 4}),
            [1.0, 2.0, 4.0, 6.0],
        )

    def test_union_bboxes(self) -> None:
        result = normalize._union_bboxes(
            [
                {"x": 10, "y": 10, "w": 5, "h": 5},
                {"x": 20, "y": 30, "w": 5, "h": 5},
            ]
        )
        self.assertEqual(result, [10.0, 10.0, 25.0, 35.0])

    def test_spurious_table_detects_layout_disagreement(self) -> None:
        payload = normalize._table_payload(
            {
                "md": "| a | b |",
                "parse_concerns": [
                    {
                        "type": "layout_lvm_disagreement",
                        "details": (
                            "layout detected [text, chart, caption] but no "
                            "table/form"
                        ),
                    }
                ],
            }
        )
        self.assertTrue(normalize._is_spurious_table(payload))
        real_table = normalize._table_payload({"md": "| a | b |"})
        self.assertFalse(normalize._is_spurious_table(real_table))

    def test_image_placeholder_is_dropped(self) -> None:
        context = structure.DocumentContext()
        items = [
            {
                "type": "text",
                "value": "Image",
                "bbox": {"x": 60, "y": 120, "w": 40, "h": 12},
            },
            {
                "type": "text",
                "value": "Ankardiansyah Pandu Pradana lahir di Banyumas.",
                "bbox": {"x": 60, "y": 200, "w": 300, "h": 12},
            },
        ]
        blocks, counters = normalize.build_blocks_for_page(
            272,
            items,
            {"header": None, "footer": None},
            context,
        )
        self.assertEqual(
            [block["text"] for block in blocks],
            ["Ankardiansyah Pandu Pradana lahir di Banyumas."],
        )
        self.assertEqual(counters["removed_image_placeholder"], 1)


class ChunkTests(unittest.TestCase):
    def _block(self, **overrides):
        block = {
            "block_id": "DOC002_P025_B001",
            "page_number": 25,
            "printed_page_number": None,
            "chapter": "Bab 1 — Penyakit Padi",
            "section": "1.2 Hawar Daun Bakteri",
            "subsection": "1.2.1 Gejala",
            "content_type": "paragraph",
            "chunk_type": "symptoms",
            "text": "Daun menunjukkan gejala hawar.",
            "parser_confidence": 0.9,
            "extraction_status": "extracted",
            "parsing_notes": [],
        }
        block.update(overrides)
        return block

    def test_chunk_keeps_source_blocks(self) -> None:
        builder = chunk.ChunkBuilder("run-test")
        builder.add(self._block())
        builder.add(self._block(block_id="DOC002_P025_B002"))
        chunks = builder.finish()
        self.assertEqual(len(chunks), 1)
        self.assertEqual(len(chunks[0]["source_block_ids"]), 2)
        self.assertEqual(chunks[0]["chunk_type"], "symptoms")

    def test_section_change_starts_new_chunk(self) -> None:
        builder = chunk.ChunkBuilder("run-test")
        builder.add(self._block())
        builder.add(
            self._block(
                block_id="DOC002_P026_B001",
                page_number=26,
                section="1.3 Blas",
                subsection="1.3.1 Gejala",
                chunk_type="symptoms",
            )
        )
        chunks = builder.finish()
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[1]["section"], "1.3 Blas")

    def test_no_chunk_is_dropped_for_short_heading(self) -> None:
        builder = chunk.ChunkBuilder("run-test")
        builder.add(
            self._block(
                content_type="chapter_heading",
                chunk_type="chapter_intro",
                section=None,
                subsection=None,
                text="Bab 1",
            )
        )
        chunks = builder.finish()
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["text_markdown"], "Bab 1")


class LevenshteinTests(unittest.TestCase):
    def test_matches_naive_implementation(self) -> None:
        pairs = [
            ("kucing", "kucing"),
            ("gejala", "gejala"),
            ("", "abc"),
            ("abc", ""),
            ("hawar daun bakteri", "hawar daun blas"),
            ("x" * 130, "x" * 129 + "y"),
        ]
        for first, second in pairs:
            with self.subTest(first=first[:10], second=second[:10]):
                self.assertEqual(
                    compare.levenshtein(first, second),
                    naive_levenshtein(first, second),
                )


class ComparisonTests(unittest.TestCase):
    def test_edge_noise_removes_header_lines_only_at_edges(self) -> None:
        repeated = {"penyakit tanaman dan pengendaliannya"}
        page = "\n".join(
            [
                "16",
                "Penyakit Tanaman dan Pengendaliannya",
                "Pengendalian patogen dengan rotasi tanaman.",
                "Bab 2 Penyakit Kedelai",
                "Tanaman akan layu akibat akar busuk.",
                "Gejala muncul pada pangkal batang.",
                "Pengendalian dilakukan dengan rotasi.",
            ]
        )
        cleaned = compare._strip_edge_noise(page, repeated, set())
        self.assertNotIn("16", cleaned.split("\n"))
        self.assertNotIn("Penyakit Tanaman dan Pengendaliannya", cleaned)
        self.assertIn("rotasi tanaman", cleaned)
        # Baris bab di tengah halaman tidak dibuang.
        self.assertIn("Bab 2 Penyakit Kedelai", cleaned)

    def test_content_loss_ignores_parser_additions(self) -> None:
        baseline = "hawar daun bakteri menyerang padi".split()
        added = "hawar daun bakteri menyerang padi diagram akar".split()
        self.assertEqual(compare.content_loss_cer(baseline, added), 0.0)
        missing = "hawar daun menyerang".split()
        self.assertGreater(compare.content_loss_cer(baseline, missing), 0.0)


class BaselineSnapshotTests(unittest.TestCase):
    def _write(self, directory: Path, records: list[dict]) -> Path:
        import json

        path = directory / "DOC002.pages.jsonl"
        with path.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record) + "\n")
        return path

    def test_pymupdf_page_without_text_source_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self._write(Path(temp), [{"page_number": 1, "raw_text": "x"}])
            self.assertTrue(baseline._looks_like_pymupdf(path))

    def test_llamaparse_page_is_rejected_as_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self._write(
                Path(temp),
                [{"page_number": 1, "text_source": "llamaparse", "raw_text": "x"}],
            )
            self.assertFalse(baseline._looks_like_pymupdf(path))

    def test_edit_distance_helper(self) -> None:
        self.assertTrue(reconcile._edit_distance_one("coklat", "cokelat"))
        self.assertTrue(reconcile._edit_distance_one("heningsii", "henningsii"))
        self.assertFalse(reconcile._edit_distance_one("jember", "image"))
        self.assertFalse(reconcile._edit_distance_one("sama", "sama"))


class TableReconcileTests(unittest.TestCase):
    def _baseline_blocks(self) -> list[dict]:
        cells = [
            ["No.", "Penyakit Tanaman", "Patogen", "Gejala"],
            [
                "1",
                "Bercak daun Coklat",
                "Cercospora henningsii (Miarti et al. 2020) atau "
                "Cercosporidium henningsii",
                "bercak daun berwarna cokelat, berbentuk bulat kecil",
            ],
        ]
        return [
            {
                "block_id": "DOC002_P091_B008",
                "content_type": "table",
                "text": "tabel baseline",
                "bbox": [56.0, 300.0, 500.0, 500.0],
                "table": {"cells": cells, "row_count": 2, "column_count": 4},
            }
        ]

    def _table_block(self) -> dict:
        cells = [
            ["No.", "Penyakit Tanaman", "Patogen", "Gejala"],
            [
                "1",
                "Bercak daun Coklat",
                "Cercospora heningsii (Miarti et al. 2020) atau "
                "Cercosporidium heningsii",
                "bercak daun berwarna coklat, berbentuk bulat kecil",
            ],
        ]
        md = (
            "| No. | Penyakit Tanaman | Patogen | Gejala |\n"
            "| --- | --- | --- | --- |\n"
            "| 1 | Bercak daun Coklat | Cercospora heningsii atau "
            "Cercosporidium heningsii | bercak daun berwarna coklat |"
        )
        csv = (
            '"No.","Penyakit Tanaman","Patogen","Gejala"\n'
            '"1","Bercak daun Coklat","Cercospora heningsii",'
            '"bercak daun berwarna coklat"'
        )
        return {
            "block_id": "DOC002_P091_B007",
            "page_number": 91,
            "content_type": "table",
            "sequence_number": 7,
            "text": md,
            "raw_text": None,
            "parsing_notes": [],
            "text_source": "llamaparse",
            "table": {"cells": cells, "rows": cells, "md": md, "csv": csv},
        }

    def test_table_typos_restored_consistently(self) -> None:
        block = self._table_block()
        restored, edits = reconcile.restore_table_tokens(
            block, self._baseline_blocks()
        )
        self.assertEqual(len(edits), 3)
        cells = restored["table"]["cells"]
        self.assertIn("henningsii", cells[1][2])
        self.assertNotIn("heningsii", cells[1][2])
        self.assertIn("cokelat", cells[1][3])
        self.assertIn("henningsii", restored["table"]["md"])
        self.assertIn("cokelat", restored["table"]["md"])
        self.assertIn("henningsii", restored["table"]["csv"])
        self.assertEqual(restored["text"], restored["table"]["md"])
        self.assertIn("henningsii", restored["text"])
        self.assertIn("henningsii", restored["table"]["rows"][1][2])
        # Teks parser asli tetap tersimpan untuk audit.
        self.assertIn("heningsii", restored["raw_text"])

    def test_table_rejects_implausible_substitution(self) -> None:
        block = self._table_block()
        block["table"]["cells"][1][2] = (
            "Cercospora image (Miarti et al. 2020) atau image"
        )
        restored, edits = reconcile.restore_table_tokens(
            block, self._baseline_blocks()
        )
        for edit in edits:
            self.assertNotEqual(edit["after"].lower(), "henningsii")
        self.assertIn("image", restored["table"]["cells"][1][2])


class ReconcileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.context = structure.DocumentContext()
        self.context.chapter = "Bab 6 Penyakit Jagung"
        self.context.section = "6.4 Pengendalian"
        self.page_meta = {
            "confidence": 0.9,
            "printed_page_number_parsed": 85,
            "parser_tier": "cost_effective",
            "parser_version": "2026-09-28",
        }

    def _baseline(self, texts: list[str], height: float = 649.2) -> dict:
        return {
            "height": height,
            "blocks": [
                {
                    "block_id": f"BASE_{index}",
                    "content_type": "paragraph",
                    "text": text,
                    "bbox": [66.0, 100.0 + index * 20, 390.0, 110.0 + index * 20],
                }
                for index, text in enumerate(texts, start=1)
            ],
        }

    def _block(self, text: str, index: int = 1) -> dict:
        return {
            "block_id": f"DOC002_P110_B{index:03d}",
            "page_number": 110,
            "content_type": "paragraph",
            "sequence_number": index,
            "text": text,
            "parsing_notes": [],
            "extraction_status": "extracted",
            "text_source": "llamaparse",
            "table": None,
        }

    def test_restores_tokens_rewritten_by_parser(self) -> None:
        baseline = self._baseline(
            ["Corticium salmonicolor mengeleminasi infeksi pada tanaman"]
        )
        tokens = reconcile._baseline_tokens(
            reconcile._usable_baseline_blocks(baseline["blocks"], baseline["height"])
        )
        text, edits = reconcile.restore_block_tokens(
            "Corticiurn salmonicolor menghilangkan infeksi pada tanaman", tokens
        )
        self.assertEqual(
            text, "Corticium salmonicolor mengeleminasi infeksi pada tanaman"
        )
        self.assertEqual(len(edits), 2)

    def test_does_not_touch_numbers_or_short_tokens(self) -> None:
        baseline = self._baseline(["suhu 55 c dan ph 6 pada tanah"])
        tokens = reconcile._baseline_tokens(
            reconcile._usable_baseline_blocks(baseline["blocks"], baseline["height"])
        )
        text, edits = reconcile.restore_block_tokens("suhu 57 c dan ph 6 pada tanah", tokens)
        self.assertEqual(text, "suhu 57 c dan ph 6 pada tanah")
        self.assertEqual(edits, [])

    def test_skips_block_without_alignment(self) -> None:
        baseline = self._baseline(["gejala layu pada tanaman cabai merah"])
        tokens = reconcile._baseline_tokens(
            reconcile._usable_baseline_blocks(baseline["blocks"], baseline["height"])
        )
        text, edits = reconcile.restore_block_tokens(
            "daftar pustaka buku ini diterbitkan tahun lalu", tokens
        )
        self.assertEqual(
            text, "daftar pustaka buku ini diterbitkan tahun lalu"
        )
        self.assertEqual(edits, [])

    def test_skips_implausible_substitution(self) -> None:
        baseline = self._baseline(
            ["dosen di universitas jember program studi proteksi tanaman"]
        )
        tokens = reconcile._baseline_tokens(
            reconcile._usable_baseline_blocks(baseline["blocks"], baseline["height"])
        )
        llama = "dosen di universitas image program studi proteksi tanaman"
        text, edits = reconcile.restore_block_tokens(llama, tokens)
        self.assertEqual(text, llama)
        self.assertEqual(edits, [])

    def test_page_fallback_when_parser_lost_text(self) -> None:
        body = "Soenartiningsih menggunakan mikoriza untuk menekan busuk pelepah " * 4
        baseline = self._baseline([body])
        blocks, summary, events = reconcile.reconcile_page(
            page_number=110,
            blocks=[self._block("a b")],
            baseline=baseline,
            context=self.context,
            page_meta=self.page_meta,
            options={},
        )
        self.assertTrue(summary["fallback"])
        self.assertEqual(summary["blocks_recovered"], 1)
        self.assertTrue(blocks)
        self.assertEqual(blocks[0]["text_source"], "pymupdf_text_layer")
        self.assertIn("page_text_recovered_from_baseline", blocks[0]["parsing_notes"])
        self.assertEqual(events[0]["action"], "page_fallback")

    def test_recovers_trailing_block_missing_from_parser(self) -> None:
        first = "Purnama, R.G.S. dan Tondok menulis tentang asap cair untuk benih padi."
        last = "Purwanto, D. S. dan Nirwanto menulis model epidemi penyakit bulai pada jagung."
        baseline = self._baseline([first, last])
        blocks, summary, events = reconcile.reconcile_page(
            page_number=250,
            blocks=[self._block(first)],
            baseline=baseline,
            context=self.context,
            page_meta=self.page_meta,
            options={},
        )
        self.assertFalse(summary["fallback"])
        self.assertEqual(summary["blocks_recovered"], 1)
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[-1]["text"], last)
        self.assertEqual(blocks[-1]["text_source"], "pymupdf_text_layer")
        self.assertEqual(events[-1]["action"], "block_recover")


class CanonicalAdaptTests(unittest.TestCase):
    def test_page_text_becomes_canonical_raw_text(self) -> None:
        page = {
            "page_number": 110,
            "raw_text": "a\nb",
            "text": "Soenartiningsih menggunakan mikoriza Glomus sp.",
            "printed_page_number": 85,
            "printed_page_number_text": "85 Penyakit Tanaman dan Pengendaliannya",
            "printed_page_number_source": "pymupdf_text_layer",
            "flags": ["layout_conflict_table_text"],
            "notes": [],
            "text_source": "pymupdf_text_layer",
        }
        adapted = promote._adapt_page(page)
        self.assertEqual(adapted["raw_text"], page["text"])
        self.assertEqual(adapted["parser_raw_text"], "a\nb")
        self.assertEqual(adapted["text_char_count"], len(page["text"]))
        self.assertEqual(adapted["printed_page_number"], "85")
        self.assertEqual(adapted["printed_page_number_source"], "text_sequence")
        self.assertIn("layout_conflict_table_text", adapted["flags"])

    def test_block_sequence_is_global_and_bbox_filled(self) -> None:
        block = {
            "block_id": "DOC002_P005_B003",
            "content_type": "paragraph",
            "sequence_number": 3,
            "bbox": None,
            "printed_page_number": 5,
            "parsing_notes": [],
            "table": None,
        }
        adapted = promote._adapt_block(block, 42)
        self.assertEqual(adapted["sequence_number"], 42)
        self.assertEqual(adapted["printed_page_number"], "5")
        self.assertEqual(adapted["bbox"], [0.0, 0.0, 0.0, 0.0])
        self.assertIn("bbox_unavailable", adapted["parsing_notes"])

    def test_table_payload_gets_validator_fields(self) -> None:
        block = {
            "block_id": "DOC002_P091_B007",
            "content_type": "table",
            "sequence_number": 7,
            "bbox": [1.0, 2.0, 3.0, 4.0],
            "printed_page_number": None,
            "parsing_notes": [],
            "table": {
                "rows": [["No.", "Penyakit"], ["1", "Antraknosa"]],
                "parse_concerns": [],
            },
        }
        adapted = promote._adapt_block(block, 7)
        table = adapted["table"]
        self.assertEqual(table["row_count"], 2)
        self.assertEqual(table["column_count"], 2)
        self.assertFalse(table["review_required"])
        self.assertEqual(table["cells"], block["table"]["rows"])


    def test_global_notes_keep_only_latest_backup(self) -> None:
        notes = promote._merge_global_notes(
            [
                "catatan-lain",
                "backup_baseline:lambda/lama",
                "backup_baseline:lambda/lama",
            ],
            "baru/lokasi",
        )
        self.assertEqual(
            notes,
            [
                "catatan-lain",
                "DOC002 dipromosikan dari LlamaParse setelah gate perbandingan lolos",
                "backup_baseline:baru/lokasi",
            ],
        )


if __name__ == "__main__":
    unittest.main()
