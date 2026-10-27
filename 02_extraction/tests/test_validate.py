"""Unit test validator dengan fixture sintetis (tanpa PDF asli)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from pdf_pipeline import config, output, validate
from pdf_pipeline.extract import sha256_file


def _page(page_number: int, raw_text: str, block_count: int, status: str, flags: list[str]) -> dict[str, Any]:
    return {
        "schema_version": config.SCHEMA_VERSION,
        "document_id": "DOC001",
        "page_number": page_number,
        "page_width": 600.0,
        "page_height": 800.0,
        "page_rotation": 0,
        "raw_text": raw_text,
        "text_char_count": len(raw_text),
        "block_count": block_count,
        "image_count": 0,
        "image_coverage_ratio": 0.0,
        "printed_page_number": None,
        "printed_page_number_source": None,
        "extraction_status": status,
        "flags": flags,
        "notes": [],
    }


def _block() -> dict[str, Any]:
    return {
        "schema_version": config.SCHEMA_VERSION,
        "block_id": "DOC001_P001_B001",
        "document_id": "DOC001",
        "page_number": 1,
        "printed_page_number": None,
        "chapter": None,
        "section": None,
        "subsection": None,
        "content_type": "paragraph",
        "sequence_number": 1,
        "text": "Teks.",
        "extraction_status": "extracted",
        "parsing_notes": [],
        "bbox": [50.0, 50.0, 100.0, 70.0],
        "cleaning_actions": [],
        "raw_text": None,
        "table": None,
    }


def _statistics() -> dict[str, Any]:
    return {
        "pages_with_text": 1,
        "pages_without_text": 1,
        "pages_with_errors": 0,
        "pages_flagged": 1,
        "blocks_total": 1,
        "blocks_by_content_type": {"paragraph": 1},
        "tables_detected": 0,
        "tables_needs_review": 0,
        "headings_detected": 0,
        "printed_page_numbers_detected": 0,
        "characters_total": 5,
    }


def _write_fixture(root: Path) -> tuple[config.ProjectPaths, dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    paths = config.build_paths(root)
    source = paths.pdf_dir / "test.pdf"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"%PDF-1.4 synthetic test file")
    source_hash = sha256_file(source)

    pages = [
        _page(1, "Teks.", 1, "text_extracted", []),
        _page(2, "", 0, "no_text_extracted", ["ocr_candidate"]),
    ]
    blocks = [_block()]

    document = {
        "schema_version": config.SCHEMA_VERSION,
        "document_id": "DOC001",
        "document_name": "test.pdf",
        "source_path": config.to_relative_posix(source, paths.root),
        "source_sha256": source_hash,
        "source_sha256_after": source_hash,
        "file_size_bytes": source.stat().st_size,
        "title": None,
        "authors": [],
        "publication_year": None,
        "publisher": None,
        "language": None,
        "total_pdf_pages": 2,
        "document_type": "pdf",
        "extraction_status": "completed_with_warnings",
        "notes": [],
        "pdf_metadata": {},
        "metadata_source": {},
        "statistics": _statistics(),
        "output_files": {
            "blocks": config.to_relative_posix(
                paths.extracted_text_dir / "DOC001.blocks.jsonl", paths.root
            ),
            "pages": config.to_relative_posix(
                paths.extracted_text_dir / "DOC001.pages.jsonl", paths.root
            ),
            "notes": config.to_relative_posix(
                paths.extraction_notes_dir / "DOC001.extraction_notes.json",
                paths.root,
            ),
        },
    }

    manifest = {
        "schema_version": config.SCHEMA_VERSION,
        "generated_at": "2026-01-01T00:00:00Z",
        "pipeline": {
            "name": config.PIPELINE_NAME,
            "version": config.PIPELINE_VERSION,
            "extractor": "PyMuPDF",
            "extractor_version": "test",
        },
        "settings": {},
        "notes": [],
        "documents": [document],
    }

    notes = {
        "schema_version": config.SCHEMA_VERSION,
        "document_id": "DOC001",
        "document_name": "test.pdf",
        "generated_at": "2026-01-01T00:00:00Z",
        "summary": _statistics(),
        "document_notes": [],
        "pages_with_issues": [pages[1]],
        "repeated_lines": {
            "threshold": 3,
            "header_candidates": [],
            "footer_candidates": [],
        },
        "table_issues": [],
        "structure_issues": {},
    }

    output.write_jsonl(paths.extracted_text_dir / "DOC001.pages.jsonl", pages)
    output.write_jsonl(paths.extracted_text_dir / "DOC001.blocks.jsonl", blocks)
    output.write_json(
        paths.extraction_notes_dir / "DOC001.extraction_notes.json", notes
    )
    output.write_json(paths.manifest, manifest)

    return paths, manifest, pages, blocks


class ValidationTests(unittest.TestCase):
    def test_valid_fixture_has_no_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths, _, _, _ = _write_fixture(Path(temp_dir))
            report = validate.validate_outputs(paths)
            self.assertEqual(report["summary"]["errors"], 0)
            self.assertGreater(report["summary"]["warnings"], 0)
            self.assertEqual(report["documents"][0]["status"], "warn")

    def test_duplicate_block_id_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths, manifest, pages, blocks = _write_fixture(Path(temp_dir))
            duplicate = dict(blocks[0])
            duplicate["sequence_number"] = 2
            blocks = blocks + [duplicate]
            pages[0]["block_count"] = 2
            manifest["documents"][0]["statistics"]["blocks_total"] = 2
            manifest["documents"][0]["statistics"]["blocks_by_content_type"] = {
                "paragraph": 2
            }
            output.write_jsonl(
                paths.extracted_text_dir / "DOC001.blocks.jsonl", blocks
            )
            output.write_jsonl(
                paths.extracted_text_dir / "DOC001.pages.jsonl", pages
            )
            output.write_json(paths.manifest, manifest)

            report = validate.validate_outputs(paths)
            errors = "\n".join(report["documents"][0]["errors"])
            self.assertIn("block_id_duplicate", errors)

    def test_missing_page_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths, manifest, pages, _ = _write_fixture(Path(temp_dir))
            pages = [pages[0]]
            manifest["documents"][0]["statistics"]["pages_without_text"] = 0
            manifest["documents"][0]["statistics"]["pages_flagged"] = 0
            output.write_jsonl(
                paths.extracted_text_dir / "DOC001.pages.jsonl", pages
            )
            output.write_json(paths.manifest, manifest)

            report = validate.validate_outputs(paths)
            errors = "\n".join(report["documents"][0]["errors"])
            self.assertIn("page_numbers_missing", errors)

    def test_source_hash_mismatch_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths, _, _, _ = _write_fixture(root)
            source = paths.pdf_dir / "test.pdf"
            source.write_bytes(b"%PDF-1.4 changed after extraction")

            report = validate.validate_outputs(paths)
            errors = "\n".join(report["documents"][0]["errors"])
            self.assertIn("source_hash_mismatch", errors)


if __name__ == "__main__":
    unittest.main()
