"""Konfigurasi pipeline LlamaParse.

Modul ini hanya berisi path, konstanta, dan builder opsi API. Tidak ada
pemanggilan jaringan dan tidak ada pembacaan nilai API key.

Dokumen aktif dipilih lewat :func:`activate`; seluruh path dan konstanta
diturunkan dari ``profiles.DocumentProfile`` sehingga DOC002-DOC005 memakai
kode yang sama tanpa nilai hard-code per dokumen.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Optional

from pdf_pipeline import config as base_config

from . import profiles


PIPELINE_NAME = "kbr-llamaparse-extraction"
PIPELINE_VERSION = "0.1.0"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXTRACTION_DIR = PROJECT_ROOT / "02_extraction"

LLAMAPARSE_DIR = EXTRACTION_DIR / "llamaparse"
RAW_DIR = LLAMAPARSE_DIR / "raw"
NORMALIZED_DIR = LLAMAPARSE_DIR / "normalized"
REPORTS_DIR = LLAMAPARSE_DIR / "reports"
BASELINE_DIR = LLAMAPARSE_DIR / "baseline"
BASELINE_MANIFEST = BASELINE_DIR / "baseline_manifest.json"

EXTRACTED_TEXT_DIR = EXTRACTION_DIR / "extracted_text"

PROFILE = profiles.get(profiles.DEFAULT_DOCUMENT_ID)
DOCUMENT_ID = PROFILE.document_id
PDF_PATH = PROJECT_ROOT / "01_knowledge_sources" / PROFILE.source_dir / PROFILE.filename
PILOT_PAGES = PROFILE.pilot_pages
MAX_FULL_PAGES = PROFILE.expected_pages

ENV_PATH = PROJECT_ROOT / ".env"
API_KEY_ENV = "LLAMA_CLOUD_API_KEY"
API_KEY_ALIASES = ("LLAMA_KEY", "LLAMA_CLOUD_API_KEY", "LLAMAPARSE_API_KEY")

TIERS = ("fast", "cost_effective", "agentic")
DEFAULT_TIER = "agentic"
DEFAULT_VERSION = "latest"

EXPAND = ("markdown", "items", "metadata", "images_content_metadata", "usage")


def activate(document_id: str) -> profiles.DocumentProfile:
    """Mengaktifkan profil dokumen untuk pemanggilan berikutnya."""

    global PROFILE, DOCUMENT_ID, PDF_PATH, PILOT_PAGES, MAX_FULL_PAGES
    profile = profiles.get(document_id)
    PROFILE = profile
    DOCUMENT_ID = profile.document_id
    PDF_PATH = PROJECT_ROOT / "01_knowledge_sources" / profile.source_dir / profile.filename
    PILOT_PAGES = profile.pilot_pages
    MAX_FULL_PAGES = profile.expected_pages
    return profile


def profile() -> profiles.DocumentProfile:
    return PROFILE


def document_ids() -> tuple[str, ...]:
    return profiles.document_ids()
JOB_TIMEOUT_BASE_SECONDS = 900
JOB_TIMEOUT_PER_PAGE_SECONDS = 5
ALLOWED_PAGE_FAILURE_RATIO = 0.02

# Tipe konten tambahan khusus keluaran LlamaParse.
FIGURE_CONTENT_TYPES = ("figure_caption",)
LLAMAPARSE_CONTENT_TYPES = tuple(base_config.CONTENT_TYPES) + FIGURE_CONTENT_TYPES

# Kategori chunk yang didukung heading sumber.
CHUNK_TYPES = (
    "chapter_intro",
    "overview",
    "symptoms",
    "pathogen",
    "host",
    "epidemiology",
    "control",
    "table",
    "figure_caption",
    "reference",
    "unclassified",
)


def run_root(run_id: str) -> Path:
    return RAW_DIR / DOCUMENT_ID / run_id


def run_paths(run_id: str) -> dict[str, Path]:
    root = run_root(run_id)
    return {
        "root": root,
        "manifest": root / "run_manifest.json",
        "response": root / "response.json",
        "markdown_full": root / "markdown_full.md",
        "pages_dir": root / "pages",
        "tables_dir": root / "tables",
        "images_dir": root / "images",
    }


def normalized_paths() -> dict[str, Path]:
    return {
        "pages": NORMALIZED_DIR / f"{DOCUMENT_ID}.pages.jsonl",
        "blocks": NORMALIZED_DIR / f"{DOCUMENT_ID}.blocks.jsonl",
        "chunks": NORMALIZED_DIR / f"{DOCUMENT_ID}.chunks.jsonl",
        "metadata": NORMALIZED_DIR / f"{DOCUMENT_ID}.metadata.json",
    }


def report_paths() -> dict[str, Path]:
    return {
        "quality": REPORTS_DIR / f"{DOCUMENT_ID}.quality.json",
        "manual_review": REPORTS_DIR / f"{DOCUMENT_ID}.manual_review.jsonl",
        "comparison": REPORTS_DIR / f"{DOCUMENT_ID}.comparison.json",
        "validation": REPORTS_DIR / f"{DOCUMENT_ID}.validation.json",
        "cost": REPORTS_DIR / f"{DOCUMENT_ID}.cost.json",
        "reconciliations": REPORTS_DIR / f"{DOCUMENT_ID}.reconciliations.json",
        "reconciliation_events": REPORTS_DIR / f"{DOCUMENT_ID}.reconciliations.jsonl",
        "report": REPORTS_DIR / f"{DOCUMENT_ID}.extraction_report.md",
    }


def canonical_paths() -> dict[str, Path]:
    return {
        "pages": EXTRACTED_TEXT_DIR / f"{DOCUMENT_ID}.pages.jsonl",
        "blocks": EXTRACTED_TEXT_DIR / f"{DOCUMENT_ID}.blocks.jsonl",
        "chunks": EXTRACTED_TEXT_DIR / f"{DOCUMENT_ID}.chunks.jsonl",
        "markdown": EXTRACTED_TEXT_DIR / f"{DOCUMENT_ID}.md",
        "notes": EXTRACTION_DIR / "extraction_notes" / f"{DOCUMENT_ID}.extraction_notes.json",
    }


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_output_options(
    with_images: bool = True,
    extract_printed_page_number: bool = True,
) -> dict[str, Any]:
    options: dict[str, Any] = {
        "markdown": {
            "tables": {
                "output_tables_as_markdown": True,
                "merge_continued_tables": True,
            }
        }
    }
    if extract_printed_page_number:
        options["extract_printed_page_number"] = True
    if with_images:
        options["images_to_save"] = ["embedded"]
    return options


def build_processing_options(ocr_languages: Optional[list[str]] = None) -> dict[str, Any]:
    languages = ocr_languages or ["id", "en"]
    return {"ocr_parameters": {"languages": languages}}


def build_processing_control(page_count: int) -> dict[str, Any]:
    base = JOB_TIMEOUT_BASE_SECONDS + JOB_TIMEOUT_PER_PAGE_SECONDS * max(page_count, 0)
    return {
        "timeouts": {
            "base_in_seconds": min(base, 7200),
            "extra_time_per_page_in_seconds": JOB_TIMEOUT_PER_PAGE_SECONDS,
        },
        "job_failure_conditions": {
            "allowed_page_failure_ratio": ALLOWED_PAGE_FAILURE_RATIO,
        },
    }


def build_parse_options(
    tier: str,
    version: str,
    page_ranges: Optional[dict[str, str]] = None,
    page_count: Optional[int] = None,
    with_images: bool = True,
) -> dict[str, Any]:
    """Menyusun seluruh argumen ``parsing.parse`` yang reproducible."""

    options: dict[str, Any] = {
        "tier": tier,
        "version": version,
        "expand": list(EXPAND),
        "output_options": build_output_options(with_images=with_images),
        "processing_options": build_processing_options(),
        "processing_control": build_processing_control(
            MAX_FULL_PAGES if page_count is None else page_count
        ),
        "disable_cache": False,
    }
    if page_ranges:
        options["page_ranges"] = page_ranges
    return options


def options_fingerprint(options: dict[str, Any]) -> str:
    """Hash kanonik opsi parse untuk idempotensi run."""

    payload = json.dumps(options, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def make_run_id(
    source_sha256: str,
    options: dict[str, Any],
    label: Optional[str] = None,
) -> str:
    tier = str(options.get("tier", "unknown"))
    fingerprint = options_fingerprint(options)[:8]
    prefix = f"{label}-" if label else ""
    return f"{DOCUMENT_ID}_{tier}_{prefix}{source_sha256[:8]}_{fingerprint}"
