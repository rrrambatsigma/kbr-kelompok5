"""Validasi kualitas hasil LlamaParse sebelum dan sesudah normalisasi."""

from __future__ import annotations

import logging
import re
import statistics
from collections import Counter
from typing import Any, Optional

from pdf_pipeline.output import read_jsonl, utc_now, write_json, write_jsonl

from . import config, store


LOGGER = logging.getLogger("kbr_llamaparse")

MIN_PAGE_CHARS = 40
LOW_CONFIDENCE = 0.80
EXPECTED_PRINTED_OFFSET = 24  # PDF 25 = halaman cetak 1 untuk DOC002


def _expected_pages(manifest: dict[str, Any]) -> list[int]:
    page_ranges = (manifest.get("options") or {}).get("page_ranges") or {}
    target = page_ranges.get("target_pages")
    total = int(manifest.get("total_pdf_pages") or 0)
    if not target:
        return list(range(1, total + 1))

    selected: set[int] = set()
    for part in str(target).split(","):
        piece = part.strip()
        if not piece:
            continue
        if "-" in piece:
            start_text, end_text = piece.split("-", 1)
            selected.update(range(int(start_text), int(end_text) + 1))
        else:
            selected.add(int(piece))
    return sorted(page for page in selected if 1 <= page <= total)


def evaluate_run(run_id: str) -> dict[str, Any]:
    manifest = store.load_manifest(run_id)
    normalized = store.ensure_normalized(run_id)
    pages = normalized["pages"]
    blocks = normalized["blocks"]
    chunks = normalized["chunks"]

    expected = _expected_pages(manifest)
    present = [int(page["page_number"]) for page in pages]
    missing = sorted(set(expected) - set(present))
    unexpected = sorted(set(present) - set(expected))

    review: list[dict[str, Any]] = []
    issues: list[str] = []

    if missing:
        issues.append(f"missing_pages:{len(missing)}")
        for page_number in missing:
            review.append(
                {
                    "scope": "page",
                    "page_number": page_number,
                    "reason": "page_missing",
                    "detail": "Halaman tidak ada pada hasil parser",
                }
            )
    if unexpected:
        issues.append(f"unexpected_pages:{len(unexpected)}")

    page_stats: list[dict[str, Any]] = []
    confidences: list[float] = []
    offsets: Counter[int] = Counter()

    for page in pages:
        page_number = int(page["page_number"])
        char_count = int(page.get("text_char_count") or 0)
        confidence = page.get("parser_confidence")
        status = page.get("extraction_status")
        reasons: list[str] = []

        if status == "extraction_error":
            reasons.append("extraction_error")
        elif status == "no_text_extracted":
            reasons.append("no_text_extracted")
        elif char_count < MIN_PAGE_CHARS:
            reasons.append("page_text_too_short")

        if confidence is not None:
            confidences.append(float(confidence))
            if float(confidence) < LOW_CONFIDENCE:
                reasons.append("low_parser_confidence")

        if "possible_multi_column_layout" in (page.get("flags") or []):
            reasons.append("possible_multi_column_layout")
        if "layout_conflict_table_text" in (page.get("flags") or []):
            reasons.append("layout_conflict_table_text")

        if page.get("notes"):
            reasons.extend(
                note for note in page["notes"] if note.startswith("substance_changed")
            )

        printed = page.get("printed_page_number")
        if printed is not None:
            offsets[page_number - int(printed)] += 1

        page_stats.append(
            {
                "page_number": page_number,
                "extraction_status": status,
                "char_count": char_count,
                "block_count": int(page.get("block_count") or 0),
                "confidence": confidence,
                "printed_page_number": printed,
                "reasons": reasons,
            }
        )

        for reason in reasons:
            review.append(
                {
                    "scope": "page",
                    "page_number": page_number,
                    "reason": reason,
                    "detail": f"char={char_count} confidence={confidence}",
                }
            )

    # Nomor halaman cetak: cek konsistensi offset dominan.
    dominant_offset: Optional[int] = None
    if offsets:
        dominant_offset, _ = offsets.most_common(1)[0]
        for page in pages:
            printed = page.get("printed_page_number")
            if printed is None:
                continue
            offset = int(page["page_number"]) - int(printed)
            if offset != dominant_offset:
                review.append(
                    {
                        "scope": "page",
                        "page_number": int(page["page_number"]),
                        "reason": "printed_page_offset_mismatch",
                        "detail": f"offset={offset} dominan={dominant_offset}",
                    }
                )

    if expected and len(present) < len(expected):
        issues.append("incomplete_page_set")

    # Blok dan tabel.
    chapter_blocks = [
        block
        for block in blocks
        if block.get("content_type") == "chapter_heading" and block.get("chapter")
    ]
    numbered_content = [
        block
        for block in blocks
        if block.get("content_type")
        in {"paragraph", "list_item", "table", "figure_caption"}
        and re.match(
            r"^(?:BAB|BAGIAN|CHAPTER)\s+\d+\b",
            str(block.get("chapter") or ""),
            re.IGNORECASE,
        )
    ]
    body_start = min(
        (int(block["page_number"]) for block in numbered_content), default=1
    )
    reference_pages = [
        int(block["page_number"])
        for block in chapter_blocks
        if "daftar pustaka" in str(block.get("chapter")).lower()
    ]
    body_end = (min(reference_pages) - 1) if reference_pages else max(
        (int(block["page_number"]) for block in blocks), default=body_start
    )

    context_missing = 0
    substance_changed = 0
    table_concerns = 0
    for block in blocks:
        page_number = int(block["page_number"])
        if block.get("extraction_status") == "needs_manual_review":
            for note in block.get("parsing_notes") or []:
                review.append(
                    {
                        "scope": "block",
                        "page_number": page_number,
                        "block_id": block.get("block_id"),
                        "reason": note,
                        "detail": str(block.get("text") or "")[:160],
                    }
                )
                if note.startswith("substance"):
                    substance_changed += 1
                if note.startswith("table"):
                    table_concerns += 1
        if (
            block.get("content_type") not in {"chapter_heading"}
            and body_start <= page_number <= body_end
            and not block.get("chapter")
        ):
            context_missing += 1

    if context_missing:
        issues.append(f"blocks_context_missing:{context_missing}")
    if substance_changed:
        issues.append(f"blocks_substance_changed:{substance_changed}")
    if table_concerns:
        issues.append(f"tables_with_concerns:{table_concerns}")

    # Chunk tanpa sumber halaman.
    chunks_without_pages = sum(
        1 for chunk in chunks if not chunk.get("source_block_ids")
    )
    if chunks_without_pages:
        issues.append(f"chunks_without_sources:{chunks_without_pages}")

    confidence_summary = {
        "count": len(confidences),
        "mean": round(statistics.fmean(confidences), 4) if confidences else None,
        "min": round(min(confidences), 4) if confidences else None,
        "median": round(statistics.median(confidences), 4) if confidences else None,
    }

    printed_detected = sum(1 for page in pages if page.get("printed_page_number") is not None)
    printed_coverage = (
        round(printed_detected / len(pages), 4) if pages else 0.0
    )

    errors = len(missing) + sum(
        1 for page in pages if page.get("extraction_status") == "extraction_error"
    )
    status = "pass"
    if errors:
        status = "fail"
    elif issues or review:
        status = "warning"

    report = {
        "schema_version": "1.0.0",
        "document_id": config.DOCUMENT_ID,
        "run_id": run_id,
        "generated_at": utc_now(),
        "tier": (manifest.get("options") or {}).get("tier"),
        "version": (manifest.get("options") or {}).get("version"),
        "job_status": manifest.get("job_status"),
        "job_error": manifest.get("job_error"),
        "credits_used": manifest.get("credits_used"),
        "pages_expected": len(expected),
        "pages_present": len(present),
        "pages_missing": missing,
        "pages_unexpected": unexpected,
        "pages_failed": sum(
            1 for page in pages if page.get("extraction_status") == "extraction_error"
        ),
        "pages_empty": sum(
            1 for page in pages if page.get("extraction_status") == "no_text_extracted"
        ),
        "pages_short": sum(1 for page in pages if int(page.get("text_char_count") or 0) < MIN_PAGE_CHARS),
        "blocks_total": len(blocks),
        "blocks_needs_review": sum(
            1 for block in blocks if block.get("extraction_status") == "needs_manual_review"
        ),
        "blocks_context_missing": context_missing,
        "chunks_total": len(chunks),
        "chunks_needs_review": sum(
            1 for chunk in chunks if chunk.get("validation_status") == "needs_manual_review"
        ),
        "tables_detected": sum(
            1 for block in blocks if block.get("content_type") == "table"
        ),
        "characters_total": sum(int(page.get("text_char_count") or 0) for page in pages),
        "confidence": confidence_summary,
        "printed_page_numbers_detected": printed_detected,
        "printed_page_number_coverage": printed_coverage,
        "printed_page_offset_distribution": dict(sorted(offsets.items())),
        "dominant_printed_page_offset": dominant_offset,
        "expected_printed_page_offset": EXPECTED_PRINTED_OFFSET,
        "issues": issues,
        "status": status,
        "page_stats": page_stats,
    }

    write_json(config.report_paths()["quality"], report)
    for item in review:
        item.setdefault("source", "quality")
    write_jsonl(config.report_paths()["manual_review"], review)
    LOGGER.info(
        "Quality: status=%s halaman=%s/%s review=%s",
        status,
        len(present),
        len(expected),
        len(review),
    )
    return report


def append_review(
    entries: list[dict[str, Any]], source: str = "comparison"
) -> int:
    """Menambahkan temuan review, mengganti temuan lama dari sumber yang sama.

    Tanpa penggantian, detail lama (mis. CER sebelum perbaikan cleaning) akan
    tertinggal di antrean meski angkanya sudah berubah.
    """

    if not entries:
        return 0
    path = config.report_paths()["manual_review"]
    existing: list[dict[str, Any]] = []
    if path.exists():
        try:
            existing = read_jsonl(path)
        except (OSError, ValueError):
            existing = []

    def key(item: dict[str, Any]) -> tuple[Any, ...]:
        return (
            item.get("scope"),
            item.get("page_number"),
            item.get("block_id"),
            item.get("reason"),
        )

    merged = {
        key(item): item
        for item in existing
        if (item.get("source") or "quality") != source
    }
    added = 0
    for item in entries:
        item.setdefault("source", source)
        merged[key(item)] = item
        added += 1
    write_jsonl(path, list(merged.values()))
    return added
