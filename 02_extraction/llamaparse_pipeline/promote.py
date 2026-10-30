"""Promosi hasil LlamaParse ke namespace canonical setelah gate lolos."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

from pdf_pipeline import config as base_config
from pdf_pipeline import output as base_output
from pdf_pipeline import validate as base_validate
from pdf_pipeline.output import read_json, read_jsonl, utc_now, write_json, write_jsonl, write_text

from . import config, md_export, store


LOGGER = logging.getLogger("kbr_llamaparse")

CHUNK_REQUIRED_KEYS = (
    "chunk_id",
    "document_id",
    "chunk_type",
    "page_start",
    "page_end",
    "text_markdown",
    "source_block_ids",
    "source_reference",
)

# Halaman boleh berasal dari parser murni atau hasil rekonsiliasi verbatim
# dengan text layer PyMuPDF.
PAGE_TEXT_SOURCES = frozenset(
    {"llamaparse", "llamaparse+baseline", "pymupdf_text_layer"}
)


def _merge_global_notes(notes: list[Any], backup_relative: str) -> list[str]:
    """Menyimpan hanya catatan backup terbaru untuk dokumen yang dipromosikan."""

    if config.DOCUMENT_ID == "DOC002":
        prefix = "backup_baseline:"
        backup_note = f"backup_baseline:{backup_relative}"
    else:
        # Dokumen lain memakai namespace sendiri agar catatan backup DOC002
        # tetap utuh di manifest global.
        prefix = f"backup_baseline:{config.DOCUMENT_ID}:"
        backup_note = f"{prefix}{backup_relative}"
    kept = [
        str(note)
        for note in notes
        if not str(note).startswith(prefix)
    ]
    gate_label = (
        "perbandingan"
        if config.profile().gate_mode == "baseline"
        else "verifikasi internal"
    )
    merged = kept + [
        f"{config.DOCUMENT_ID} dipromosikan dari LlamaParse setelah gate {gate_label} lolos",
        backup_note,
    ]
    return list(dict.fromkeys(merged))


def _adapt_page(page: dict[str, Any]) -> dict[str, Any]:
    """Menyelaraskan record halaman LlamaParse dengan skema canonical.

    Jalur LlamaParse menyimpan teks parser di ``raw_text`` dan teks hasil
    normalisasi/rekonsiliasi di ``text``. Kontrak canonical memakai
    ``raw_text`` sebagai teks halaman, jadi teks final dipindah ke sana dan
    teks parser asli dipertahankan sebagai ``parser_raw_text``.
    """

    adapted = dict(page)
    text = str(page.get("text") or page.get("raw_text") or "")
    adapted["parser_raw_text"] = page.get("raw_text")
    adapted["raw_text"] = text
    adapted["text_char_count"] = len(text)

    printed = page.get("printed_page_number")
    if printed is None:
        adapted["printed_page_number"] = None
        adapted["printed_page_number_source"] = None
    else:
        adapted["printed_page_number"] = str(int(printed))
        source = page.get("printed_page_number_source")
        adapted["printed_page_number_source"] = (
            source
            if source in ("pdf_page_labels", "text_sequence")
            else "text_sequence"
        )

    notes = list(page.get("notes") or [])
    flags: list[str] = []
    for flag in page.get("flags") or []:
        if flag in base_config.PAGE_FLAG_SET:
            flags.append(flag)
        else:
            note = f"flag:{flag}"
            if note not in notes:
                notes.append(note)
    adapted["flags"] = flags
    adapted["notes"] = notes
    return adapted


def _adapt_block(block: dict[str, Any], sequence: int) -> dict[str, Any]:
    """Menyelaraskan record blok dengan kontrak canonical."""

    adapted = dict(block)
    adapted["sequence_number"] = sequence

    printed = block.get("printed_page_number")
    adapted["printed_page_number"] = None if printed is None else str(printed)

    notes = list(block.get("parsing_notes") or [])
    bbox = block.get("bbox")
    if not (
        isinstance(bbox, (list, tuple))
        and len(bbox) == 4
        and all(
            isinstance(value, (int, float)) and not isinstance(value, bool)
            for value in bbox
        )
    ):
        adapted["bbox"] = [0.0, 0.0, 0.0, 0.0]
        if "bbox_unavailable" not in notes:
            notes.append("bbox_unavailable")
    adapted["parsing_notes"] = notes

    table = block.get("table")
    if adapted.get("content_type") == "table" and isinstance(table, dict):
        table = dict(table)
        cells = table.get("cells")
        if not isinstance(cells, list):
            rows = table.get("rows")
            cells = rows if isinstance(rows, list) else []
        table["cells"] = cells
        table["row_count"] = len(cells)
        table["column_count"] = max(
            (len(row) for row in cells if isinstance(row, list)), default=0
        )
        table["review_required"] = bool(
            table.get("review_required")
            or table.get("parse_concerns")
            or table.get("merged_from_pages")
            or table.get("merged_into_page")
        )
        adapted["table"] = table
    return adapted


def adapt_for_canonical(
    pages: list[dict[str, Any]], blocks: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Mengubah pages/blocks hasil normalisasi agar lolos validator canonical."""

    adapted_blocks = [
        _adapt_block(block, index) for index, block in enumerate(blocks, start=1)
    ]
    adapted_pages = [_adapt_page(page) for page in pages]
    return adapted_pages, adapted_blocks


def _existing_manifest_entry() -> dict[str, Any]:
    paths = base_config.build_paths()
    if not paths.manifest.exists():
        return {}
    try:
        manifest = read_json(paths.manifest)
    except (OSError, ValueError):
        return {}
    for entry in manifest.get("documents", []):
        if entry.get("document_id") == config.DOCUMENT_ID:
            return entry
    return {}


def _build_entry(
    manifest: dict[str, Any],
    metadata: dict[str, Any],
    statistics: dict[str, Any],
    quality: dict[str, Any],
    output_files: dict[str, Path],
) -> dict[str, Any]:
    paths = base_config.build_paths()
    existing = _existing_manifest_entry()
    status = "completed" if quality.get("status") == "pass" else "completed_with_warnings"

    notes = [
        "extracted_with_llamaparse",
        f"parser_tier:{(manifest.get('options') or {}).get('tier')}",
        f"parser_version:{(manifest.get('options') or {}).get('version')}",
        f"parser_run_id:{manifest.get('run_id')}",
        f"quality_status:{quality.get('status')}",
    ]
    notes.extend(quality.get("issues") or [])

    relative_outputs = {
        key: base_config.to_relative_posix(path, paths.root)
        for key, path in output_files.items()
    }

    return {
        "document_id": config.DOCUMENT_ID,
        "document_name": manifest.get("source_file"),
        "source_path": manifest.get("source_path"),
        "source_sha256": manifest.get("source_sha256"),
        "source_sha256_after": config.sha256_file(config.PDF_PATH),
        "file_size_bytes": manifest.get("file_size_bytes"),
        "title": metadata.get("title"),
        "authors": metadata.get("authors") or [],
        "publication_year": metadata.get("publication_year"),
        "publisher": metadata.get("publisher"),
        "language": metadata.get("language"),
        "total_pdf_pages": manifest.get("total_pdf_pages"),
        "document_type": existing.get("document_type", "pdf"),
        "extraction_status": status,
        "notes": notes,
        "pdf_metadata": existing.get("pdf_metadata") or {},
        "metadata_source": metadata.get("metadata_source") or {},
        "statistics": statistics,
        "output_files": relative_outputs,
    }


def validate_promoted() -> dict[str, Any]:
    paths = base_config.build_paths()
    normalized = config.normalized_paths()
    profile = config.profile()
    pages = read_jsonl(paths.extracted_text_dir / f"{config.DOCUMENT_ID}.pages.jsonl")
    blocks = read_jsonl(paths.extracted_text_dir / f"{config.DOCUMENT_ID}.blocks.jsonl")
    chunks_path = paths.extracted_text_dir / f"{config.DOCUMENT_ID}.chunks.jsonl"
    chunks = read_jsonl(chunks_path) if chunks_path.exists() else []

    errors: list[str] = []
    warnings: list[str] = []

    page_numbers = [int(page.get("page_number")) for page in pages]
    if page_numbers != list(range(1, profile.expected_pages + 1)):
        errors.append(f"page_sequence_not_1_{profile.expected_pages}")

    block_ids = {str(block.get("block_id")) for block in blocks}
    for block in blocks:
        missing = [
            key
            for key in ("schema_version", "block_id", "document_id", "page_number", "text")
            if key not in block
        ]
        if missing:
            errors.append(f"block_missing_keys:{block.get('block_id')}:{missing}")
            break

    for page in pages:
        source = page.get("text_source")
        if source not in PAGE_TEXT_SOURCES:
            errors.append(
                f"page_text_source_invalid:{page.get('page_number')}:{source}"
            )
            break

    for chunk in chunks:
        missing = [key for key in CHUNK_REQUIRED_KEYS if key not in chunk]
        if missing:
            errors.append(f"chunk_missing_keys:{chunk.get('chunk_id')}:{missing}")
            break
        unknown = [sid for sid in chunk.get("source_block_ids") or [] if sid not in block_ids]
        if unknown:
            errors.append(f"chunk_unknown_source_blocks:{chunk.get('chunk_id')}:{unknown[:3]}")
            break

    if not chunks:
        warnings.append("no_chunks")

    text_sources: dict[str, int] = {}
    for page in pages:
        source = str(page.get("text_source"))
        text_sources[source] = text_sources.get(source, 0) + 1

    report = {
        "schema_version": "1.0.0",
        "document_id": config.DOCUMENT_ID,
        "generated_at": utc_now(),
        "pages": len(pages),
        "blocks": len(blocks),
        "chunks": len(chunks),
        "text_sources": text_sources,
        "errors": errors,
        "warnings": warnings,
        "status": "pass" if not errors else "fail",
        "normalized_pages": str(normalized["pages"]),
    }
    write_json(config.report_paths()["validation"], report)
    return report


def promote(run_id: str, quality: dict[str, Any], comparison: dict[str, Any]) -> dict[str, Any]:
    if not comparison.get("gate_passed"):
        raise RuntimeError(
            f"Gate {config.DOCUMENT_ID} belum lolos; promosi dibatalkan. "
            f"Periksa reports/{config.DOCUMENT_ID}.comparison.json"
        )
    if not comparison.get("is_full_run"):
        raise RuntimeError(
            "Promosi hanya boleh untuk full run "
            f"{config.profile().expected_pages} halaman"
        )

    manifest = store.load_manifest(run_id)
    if str(manifest.get("document_id")) != config.DOCUMENT_ID:
        raise RuntimeError(
            "Manifest run bukan milik dokumen aktif "
            f"({manifest.get('document_id')} != {config.DOCUMENT_ID})"
        )
    current_sha = config.sha256_file(config.PDF_PATH)
    if current_sha != manifest.get("source_sha256"):
        raise RuntimeError(
            "SHA-256 PDF sumber berubah sejak parsing; promosi dibatalkan"
        )

    paths = base_config.build_paths()
    stamp = utc_now().replace(":", "").replace("-", "")
    targets = {
        "pages": paths.extracted_text_dir / f"{config.DOCUMENT_ID}.pages.jsonl",
        "blocks": paths.extracted_text_dir / f"{config.DOCUMENT_ID}.blocks.jsonl",
        "chunks": paths.extracted_text_dir / f"{config.DOCUMENT_ID}.chunks.jsonl",
        "markdown": config.canonical_paths()["markdown"],
        "notes": paths.extraction_notes_dir / f"{config.DOCUMENT_ID}.extraction_notes.json",
    }

    backup_files = [
        targets["pages"],
        targets["blocks"],
        targets["chunks"],
        targets["markdown"],
        targets["notes"],
        paths.manifest,
        paths.report,
        paths.validation_report,
    ]
    backup_root = base_output.backup_files(
        paths, backup_files, stamp=f"pre_llamaparse_{stamp}"
    )
    LOGGER.info("Backup baseline dibuat di %s", backup_root)

    normalized = store.ensure_normalized(run_id)
    pages, blocks = adapt_for_canonical(
        normalized["pages"], normalized["blocks"]
    )
    chunks = normalized["chunks"]
    metadata = read_json(config.normalized_paths()["metadata"])

    write_jsonl(targets["pages"], pages)
    write_jsonl(targets["blocks"], blocks)
    write_jsonl(targets["chunks"], chunks)
    md_export.write_markdown(targets["markdown"], pages, blocks)

    # Statistik dihitung dari record yang benar-benar ditulis agar cocok
    # dengan validator lintas-pipeline.
    statistics = base_validate._expected_statistics(pages, blocks)
    entry = _build_entry(manifest, metadata, statistics, quality, targets)

    document_notes = list(entry.get("notes") or [])
    pages_with_issues = [
        {
            "page_number": page.get("page_number"),
            "extraction_status": page.get("extraction_status"),
            "flags": page.get("flags"),
            "notes": page.get("notes"),
        }
        for page in pages
        if page.get("flags")
        or page.get("notes")
        or page.get("extraction_status") != "text_extracted"
    ]
    table_issues = [
        {
            "block_id": block.get("block_id"),
            "page_number": block.get("page_number"),
            "reason": "table_needs_review",
        }
        for block in blocks
        if block.get("content_type") == "table"
        and (block.get("table") or {}).get("review_required")
    ]

    notes_payload = {
        "schema_version": "1.0.0",
        "document_id": config.DOCUMENT_ID,
        "document_name": manifest.get("source_file"),
        "generated_at": utc_now(),
        "summary": statistics,
        "document_notes": document_notes,
        "pages_with_issues": pages_with_issues,
        "repeated_lines": {
            "threshold": 0,
            "header_candidates": [],
            "footer_candidates": [],
            "source": "llamaparse",
        },
        "table_issues": table_issues,
        "structure_issues": {
            "chapter_count": comparison.get("headings", {}).get(
                "llamaparse_chapter_count"
            ),
            "unclassified_headings": statistics.get("blocks_by_content_type", {}).get(
                "heading_unclassified", 0
            ),
        },
        "extractor": "LlamaParse",
        "run_id": run_id,
        "tier": (manifest.get("options") or {}).get("tier"),
        "version": (manifest.get("options") or {}).get("version"),
        "quality": {
            "status": quality.get("status"),
            "issues": quality.get("issues"),
            "pages_missing": quality.get("pages_missing"),
            "blocks_needs_review": quality.get("blocks_needs_review"),
        },
        "structure": {
            "chapter_headings": comparison.get("headings", {}).get(
                "llamaparse_chapter_headings"
            ),
            "chapter_count": comparison.get("headings", {}).get(
                "llamaparse_chapter_count"
            ),
        },
        "text_similarity": comparison.get("text_similarity"),
        "reconciliation": (metadata.get("extraction") or {}).get(
            "reconciliation"
        ),
        "tables": comparison.get("tables"),
        "printed_page_numbers": comparison.get("printed_page_numbers"),
        "backup": base_config.to_relative_posix(backup_root, paths.root),
    }
    write_json(targets["notes"], notes_payload)

    if paths.manifest.exists():
        existing = read_json(paths.manifest)
        settings = existing.get("settings") or {}
        global_notes = list(existing.get("notes") or [])
    else:
        settings = {}
        global_notes = []
    run_settings = {
        "run_id": run_id,
        "tier": (manifest.get("options") or {}).get("tier"),
        "version": (manifest.get("options") or {}).get("version"),
        "job_id": manifest.get("job_id"),
        "credits_used": manifest.get("credits_used"),
    }
    settings = {**settings, "llamaparse": run_settings}
    per_document = dict(settings.get("llamaparse_runs") or {})
    per_document[config.DOCUMENT_ID] = run_settings
    settings["llamaparse_runs"] = per_document
    # Hanya backup terakhir yang relevan; catatan lama dibuang agar tidak
    # menunjuk direktori yang sudah dihapus.
    global_notes = _merge_global_notes(
        global_notes,
        base_config.to_relative_posix(backup_root, paths.root),
    )

    manifest_payload = base_output.build_manifest(
        paths,
        entries=[entry],
        settings=settings,
        extractor_version=str((manifest.get("options") or {}).get("version")),
        global_notes=global_notes,
        merge_existing=True,
    )
    manifest_payload["pipeline"]["extractor"] = "LlamaParse"
    write_json(paths.manifest, manifest_payload)
    write_text(
        paths.report,
        base_output.build_report(manifest_payload, global_notes=global_notes),
    )

    validation = validate_promoted()
    if validation.get("status") != "pass":
        raise RuntimeError(
            "Validasi setelah promosi gagal; lihat "
            f"reports/{config.DOCUMENT_ID}.validation.json"
        )

    return {
        "run_id": run_id,
        "backup": str(backup_root),
        "outputs": {key: str(value) for key, value in targets.items()},
        "validation": validation,
    }
