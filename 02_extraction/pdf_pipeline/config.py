"""Konfigurasi path, registry dokumen, dan konstanta skema.

Modul ini sengaja tidak mengimpor PyMuPDF agar dapat dipakai oleh parser,
validator, dan unit test tanpa dependensi ekstraksi.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Union


SCHEMA_VERSION = "1.0.0"
PIPELINE_NAME = "kbr-pdf-extraction"
PIPELINE_VERSION = "1.0.0"

# config.py berada di <root>/02_extraction/pdf_pipeline/config.py
PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class SourceDocument:
    """Satu PDF sumber yang terdaftar secara eksplisit."""

    document_id: str
    filename: str


SOURCE_DOCUMENTS = (
    SourceDocument("DOC001", "PenyakitTanamanHortikultura.pdf"),
    SourceDocument("DOC002", "PenyakitTanamanPangan.pdf"),
)


@dataclass(frozen=True)
class ProjectPaths:
    """Kumpulan path yang diturunkan dari root proyek."""

    root: Path
    pdf_dir: Path
    source_metadata_dir: Path
    extracted_text_dir: Path
    extraction_notes_dir: Path
    manual_metadata: Path
    manifest: Path
    report: Path
    validation_report: Path
    backup_dir: Path


def build_paths(root: Optional[Union[Path, str]] = None) -> ProjectPaths:
    """Membangun path proyek.

    Jika ``root`` tidak diberikan, root dihitung dari lokasi modul ini sehingga
    pipeline tidak bergantung pada current working directory.
    """

    root_path = Path(root).expanduser().resolve() if root is not None else PROJECT_ROOT
    source_metadata_dir = root_path / "01_knowledge_sources" / "source_metadata"
    extraction_notes_dir = root_path / "02_extraction" / "extraction_notes"
    return ProjectPaths(
        root=root_path,
        pdf_dir=root_path / "01_knowledge_sources" / "pdf_original",
        source_metadata_dir=source_metadata_dir,
        extracted_text_dir=root_path / "02_extraction" / "extracted_text",
        extraction_notes_dir=extraction_notes_dir,
        manual_metadata=source_metadata_dir / "manual_metadata.json",
        manifest=source_metadata_dir / "manifest.json",
        report=extraction_notes_dir / "extraction_report.md",
        validation_report=extraction_notes_dir / "validation_report.json",
        backup_dir=extraction_notes_dir / "_backups",
    )


# Nilai kontrol yang dipakai bersama oleh writer dan validator.
CONTENT_TYPES = (
    "chapter_heading",
    "section_heading",
    "subsection_heading",
    "heading_unclassified",
    "paragraph",
    "list_item",
    "table",
)
CONTENT_TYPE_SET = frozenset(CONTENT_TYPES)

HEADING_CONTENT_TYPES = frozenset(
    {
        "chapter_heading",
        "section_heading",
        "subsection_heading",
        "heading_unclassified",
    }
)

BLOCK_STATUSES = ("extracted", "needs_manual_review")
BLOCK_STATUS_SET = frozenset(BLOCK_STATUSES)

PAGE_STATUSES = ("text_extracted", "no_text_extracted", "extraction_error")
PAGE_STATUS_SET = frozenset(PAGE_STATUSES)

DOCUMENT_STATUSES = (
    "completed",
    "completed_with_warnings",
    "no_text_extracted",
    "partial",
    "failed",
)
DOCUMENT_STATUS_SET = frozenset(DOCUMENT_STATUSES)

PAGE_FLAGS = (
    "likely_scanned_image_only",
    "ocr_candidate",
    "possible_multi_column_layout",
    "repeated_header_candidate",
    "repeated_footer_candidate",
)
PAGE_FLAG_SET = frozenset(PAGE_FLAGS)

BLOCK_REQUIRED_KEYS = (
    "schema_version",
    "block_id",
    "document_id",
    "page_number",
    "printed_page_number",
    "chapter",
    "section",
    "subsection",
    "content_type",
    "sequence_number",
    "text",
    "extraction_status",
    "parsing_notes",
    "bbox",
    "cleaning_actions",
    "raw_text",
    "table",
)

PAGE_REQUIRED_KEYS = (
    "schema_version",
    "document_id",
    "page_number",
    "page_width",
    "page_height",
    "page_rotation",
    "raw_text",
    "text_char_count",
    "block_count",
    "image_count",
    "image_coverage_ratio",
    "printed_page_number",
    "printed_page_number_source",
    "extraction_status",
    "flags",
    "notes",
)

DOCUMENT_REQUIRED_KEYS = (
    "document_id",
    "document_name",
    "source_path",
    "source_sha256",
    "file_size_bytes",
    "title",
    "authors",
    "publication_year",
    "publisher",
    "language",
    "total_pdf_pages",
    "document_type",
    "extraction_status",
    "notes",
    "pdf_metadata",
    "metadata_source",
    "statistics",
    "output_files",
)


def document_ids() -> Iterable[str]:
    """Mengembalikan daftar document_id sesuai urutan registry."""

    return tuple(item.document_id for item in SOURCE_DOCUMENTS)


def to_relative_posix(path: Path, root: Path) -> str:
    """Menyimpan path relatif terhadap root dengan separator POSIX.

    Path di luar root disimpan sebagai path absolut POSIX agar tetap terlihat
    bahwa lokasinya berada di luar proyek.
    """

    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()
