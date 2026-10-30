"""Normalisasi respons LlamaParse menjadi pages/blocks JSONL.

Skema record mengikuti pipeline PyMuPDF yang sudah ada, ditambah field
traceability parser. Tidak ada nilai tanaman/penyakit yang ditebak.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Optional

from pdf_pipeline import config as base_config
from pdf_pipeline import output as base_output
from pdf_pipeline.output import read_json

from . import clean, config, reconcile, store, structure


LOGGER = logging.getLogger("kbr_llamaparse")


def _bbox_to_list(bbox: Any) -> Optional[list[float]]:
    """Mengubah bbox LlamaParse (dict x/y/w/h) menjadi [x0, y0, x1, y1]."""

    if isinstance(bbox, list) and bbox and isinstance(bbox[0], dict):
        return _union_bboxes(bbox)
    if isinstance(bbox, dict) and {"x", "y", "w", "h"} <= set(bbox):
        x = float(bbox.get("x") or 0)
        y = float(bbox.get("y") or 0)
        w = float(bbox.get("w") or 0)
        h = float(bbox.get("h") or 0)
        return [round(x, 3), round(y, 3), round(x + w, 3), round(y + h, 3)]
    if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
        return [round(float(value), 3) for value in bbox]
    return None


def _union_bboxes(bboxes: Any) -> Optional[list[float]]:
    if not isinstance(bboxes, list) or not bboxes:
        return None
    converted = [item for item in (_bbox_to_list(bbox) for bbox in bboxes) if item]
    if not converted:
        return None
    return [
        round(min(item[0] for item in converted), 3),
        round(min(item[1] for item in converted), 3),
        round(max(item[2] for item in converted), 3),
        round(max(item[3] for item in converted), 3),
    ]


def _table_payload(item: dict[str, Any]) -> dict[str, Any]:
    concerns = []
    for concern in item.get("parse_concerns") or []:
        if isinstance(concern, dict):
            concerns.append(
                {
                    "type": concern.get("type"),
                    "details": concern.get("details"),
                }
            )
    rows = item.get("rows")
    cells = rows if isinstance(rows, list) else []
    column_count = max(
        (len(row) for row in cells if isinstance(row, list)), default=0
    )
    return {
        "rows": rows,
        # Alias yang dipakai validator lintas-pipeline.
        "cells": cells,
        "row_count": len(cells),
        "column_count": column_count,
        "review_required": bool(
            concerns or item.get("merged_from_pages") or item.get("merged_into_page")
        ),
        "html": item.get("html"),
        "csv": item.get("csv"),
        "md": item.get("md"),
        "bbox": _union_bboxes(item.get("bbox")),
        "merged_from_pages": item.get("merged_from_pages"),
        "merged_into_page": item.get("merged_into_page"),
        "parse_concerns": concerns,
    }


def _is_spurious_table(payload: dict[str, Any]) -> bool:
    """True bila model layout justru tidak menemukan tabel di area itu.

    Tabel yang masih membawa sel berisi tidak pernah dibuang; peringatan
    layout bisa muncul bersamaan dengan hasil tabel yang valid (mis. tiga
    tabel data pada satu halaman).
    """

    rows = payload.get("rows") or []
    has_content = any(
        str(cell).strip()
        for row in rows
        if isinstance(row, list)
        for cell in row
    )
    if has_content:
        return False
    for concern in payload.get("parse_concerns") or []:
        details = str(concern.get("details") or "").lower()
        if "no table/form" in details:
            return True
    return False


def _is_page_number_table(payload: dict[str, Any], page_number: int) -> bool:
    """True bila "tabel" hanya berisi nomor halaman cetak.

    Parser kadang membungkus nomor halaman di tepi sebagai tabel satu sel.
    Nomor hanya diterima bila cocok dengan offset dokumen, jadi angka lain di
    dalam tabel asli tidak ikut terbuang.
    """

    cells = payload.get("cells") or []
    if len(cells) != 1 or not isinstance(cells[0], list) or len(cells[0]) != 1:
        return False
    value = str(cells[0][0] or "").strip()
    match = re.fullmatch(r"\|?\s*(\d{1,4})\s*\|?", value)
    if not match:
        return False
    return int(match.group(1)) == page_number - config.profile().printed_offset


def _item_text_and_markdown(item: dict[str, Any]) -> tuple[str, Optional[str], bool]:
    item_type = item.get("type")
    if item_type in {"text", "heading", "code"}:
        value = item.get("value") or ""
        md = item.get("md")
        return value, md if md and md != value else None, True
    if item_type == "list":
        md = item.get("md") or ""
        pieces: list[str] = []
        for child in item.get("items") or []:
            if isinstance(child, dict):
                pieces.append(str(child.get("value") or child.get("md") or "").strip())
        text = " ".join(piece for piece in pieces if piece) or md
        return text, md if md and md != text else None, True
    if item_type == "table":
        md = item.get("md") or ""
        return md, None, False
    if item_type == "image":
        return item.get("caption") or "", item.get("md"), True
    return item.get("md") or item.get("value") or "", None, False


def _content_type(
    item: dict[str, Any],
    heading_content_type: Optional[str],
) -> Optional[str]:
    item_type = item.get("type")
    if item_type == "heading":
        return heading_content_type
    if item_type == "text":
        return "paragraph"
    if item_type == "list":
        return "list_item"
    if item_type == "table":
        return "table"
    if item_type == "image":
        return "figure_caption"
    if item_type == "code":
        return "paragraph"
    return None


def build_blocks_for_page(
    page_number: int,
    items: list[dict[str, Any]],
    page_meta: dict[str, Any],
    context: structure.DocumentContext,
    edge_templates: Optional[set[str]] = None,
    page_height: float = 0.0,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    counters = {
        "removed_standalone_page_number": 0,
        "removed_repeated_edge": 0,
        "removed_image_placeholder": 0,
        "removed_page_number_table": 0,
        "removed_chapter_label_line": 0,
        "empty_items": 0,
        "substance_changed": 0,
    }
    removed_edge_lines: list[str] = []

    edges = [page_meta.get("header"), page_meta.get("footer")]
    templates = edge_templates or set()
    sequence = 0

    for item in items:
        item_type = item.get("type")
        if item_type in {"header", "footer"}:
            counters["removed_repeated_edge"] += 1
            continue
        if item_type == "link":
            continue

        raw_text, markdown_text, emphasize = _item_text_and_markdown(item)
        if emphasize:
            raw_text, had_emphasis = clean.strip_emphasis(raw_text)
        else:
            had_emphasis = False
        raw_text, had_syntax = clean.strip_syntax(raw_text)
        if had_syntax:
            raw_text = clean.collapse_whitespace(raw_text)
        text, cleaning_actions = clean.clean_block_text(raw_text)
        if had_emphasis:
            cleaning_actions.append("removed_markdown_emphasis")
        if had_syntax:
            cleaning_actions.append("removed_markdown_syntax")
        substance_source = raw_text
        header_removed = False

        if not text:
            counters["empty_items"] += 1
            continue

        if clean.is_standalone_page_number(text):
            counters["removed_standalone_page_number"] += 1
            continue

        # Alt-text bawaan gambar dari parser bukan isi dokumen.
        if item_type == "text" and text.strip().lower() == "image":
            counters["removed_image_placeholder"] += 1
            continue

        if item_type == "text" and clean.looks_like_running_edge(text, edges):
            counters["removed_repeated_edge"] += 1
            continue

        if item_type in {"text", "heading"} and templates:
            if clean.line_template(text) in templates:
                bbox_value = _bbox_to_list(item.get("bbox"))
                at_edge = (
                    bbox_value is None
                    or bbox_value[1] <= 95.0
                    or (page_height and bbox_value[3] >= page_height - 75.0)
                )
                if at_edge:
                    counters["removed_repeated_edge"] += 1
                    removed_edge_lines.append(text)
                    continue

        if item_type == "heading" and structure.is_book_title(
            text, config.profile().ignored_headings
        ):
            counters["removed_repeated_edge"] += 1
            removed_edge_lines.append(text)
            continue

        if item_type in {"text", "heading"}:
            bbox_value = _bbox_to_list(item.get("bbox"))
            if clean.is_running_edge_line(text, bbox_value, page_height):
                counters["removed_repeated_edge"] += 1
                removed_edge_lines.append(text)
                continue

        heading_content_type: Optional[str] = None
        caption = structure.caption_kind(text) if len(text) <= 250 else None
        extra_notes: list[str] = []
        level = None
        bbox_value = _bbox_to_list(item.get("bbox"))

        if item_type == "text":
            remainder, merged_heading = clean.split_merged_running_header(
                text, bbox_value, page_height
            )
            if merged_heading:
                text = remainder
                header_removed = True
                structure.update_for_heading(context, merged_heading, 1)
                extra_notes.append("running_header_merged_by_parser")
                removed_edge_lines.append(merged_heading)

        if caption == "figure" and item_type in {"heading", "text", "image"}:
            content_type = "figure_caption"
            extra_notes.append("caption_reclassified_from_heading")
        elif caption == "table" and item_type in {"heading", "text", "image"}:
            content_type = "paragraph"
            extra_notes.append("table_caption_detected")
        else:
            if item_type == "heading":
                level = int(item.get("level") or 1)
                heading_content_type = structure.update_for_heading(
                    context, text, level
                )
                content_type = _content_type(item, heading_content_type)
            elif item_type == "text" and structure.is_known_chapter(
                text, context.known_chapters
            ):
                # Sebagian parser mengirim judul bab HURUF BESAR sebagai teks
                # biasa; judul yang cocok dengan daftar isi diangkat menjadi
                # heading tanpa menebak.
                level = 1
                content_type = structure.update_for_heading(context, text, 1)
            else:
                content_type = _content_type(item, heading_content_type)
        if content_type is None:
            counters["empty_items"] += 1
            continue

        if content_type == "chapter_heading" and structure.is_bare_chapter_label(text):
            # "BAB 7" hanya nomor bab; judulnya ada di baris berikutnya dan
            # sudah masuk konteks. Menyimpannya sebagai heading akan menghitung
            # satu bab dua kali.
            counters["removed_chapter_label_line"] = (
                counters.get("removed_chapter_label_line", 0) + 1
            )
            continue

        if item_type == "image" and not text.strip():
            counters["empty_items"] += 1
            continue

        sequence += 1
        bbox = (
            _union_bboxes(item.get("bbox"))
            if item_type == "table"
            else _bbox_to_list(item.get("bbox"))
        )
        if bbox is None:
            # Sebagian item (mis. alt-text gambar) tidak membawa koordinat.
            # Bbox kosong menandai geometri tidak tersedia, bukan isi.
            bbox = [0.0, 0.0, 0.0, 0.0]
            extra_notes.append("bbox_unavailable")

        parsing_notes: list[str] = list(extra_notes)
        extraction_status = "extracted"

        substance_before = clean.substance_tokens(substance_source)
        substance_after = clean.substance_tokens(text)
        if substance_before != substance_after and not header_removed:
            counters["substance_changed"] += 1
            parsing_notes.append("substance_tokens_changed_by_cleaning")
            extraction_status = "needs_manual_review"

        if item_type == "table":
            payload = _table_payload(item)
            if _is_page_number_table(payload, page_number):
                counters["removed_page_number_table"] = (
                    counters.get("removed_page_number_table", 0) + 1
                )
                continue
            if _is_spurious_table(payload):
                # Layout model tidak menemukan tabel; LVM/VLM mengarang tabel
                # (mis. diagram alur pada halaman 41). Teksnya tetap disimpan,
                # tetapi tidak diklaim sebagai tabel.
                content_type = "paragraph"
                text = clean.collapse_whitespace(text.replace("|", " "))
                cleaning_actions.append("flattened_table_to_text")
                parsing_notes.append("spurious_table_reclassified")
                extraction_status = "needs_manual_review"
            elif payload.get("parse_concerns"):
                parsing_notes.append("table_parse_concerns")
                extraction_status = "needs_manual_review"
            if payload.get("merged_from_pages"):
                parsing_notes.append("table_merged_from_pages")
        else:
            payload = None

        block = {
            "schema_version": base_config.SCHEMA_VERSION,
            "block_id": f"{config.DOCUMENT_ID}_P{page_number:03d}_B{sequence:03d}",
            "document_id": config.DOCUMENT_ID,
            "page_number": page_number,
            "printed_page_number": page_meta.get("printed_page_number_parsed"),
            "chapter": context.chapter,
            "section": context.section,
            "section_source": context.section_source,
            "subsection": context.subsection,
            "content_type": content_type,
            "sequence_number": sequence,
            "text": text,
            "extraction_status": extraction_status,
            "parsing_notes": parsing_notes,
            "bbox": bbox,
            "cleaning_actions": cleaning_actions,
            "raw_text": markdown_text if markdown_text and markdown_text != text else None,
            "table": payload,
            "text_source": "llamaparse",
            "parser_engine": "LlamaParse",
            "parser_tier": page_meta.get("parser_tier"),
            "parser_version": page_meta.get("parser_version"),
            "parser_confidence": page_meta.get("confidence"),
            "parser_item_type": item_type,
            "heading_level": level,
            "plant_name": context.plant_name,
            "plant_name_source": context.plant_source,
            "disease_name": context.disease_name,
            "disease_name_source": context.disease_source,
            "chunk_type": structure.chunk_type_for_block(context, content_type),
        }
        if content_type == "paragraph" and caption == "table":
            block["chunk_type"] = "table"
        blocks.append(block)

    counters["removed_edge_lines"] = removed_edge_lines[:5]
    return blocks, counters


def normalize_run(run_id: str) -> dict[str, Any]:
    manifest = store.load_manifest(run_id)
    response = store.load_response(run_id)
    options = manifest.get("options") or {}

    markdown_pages = {
        int(page.get("page_number")): page
        for page in ((response.get("markdown") or {}).get("pages") or [])
        if page.get("page_number") is not None
    }
    items_pages = {
        int(page.get("page_number")): page
        for page in ((response.get("items") or {}).get("pages") or [])
        if page.get("page_number") is not None
    }
    metadata_pages = {
        int(page.get("page_number")): page
        for page in ((response.get("metadata") or {}).get("pages") or [])
        if page.get("page_number") is not None
    }

    stored_meta: dict[int, dict[str, Any]] = {}
    pages_dir = config.run_paths(run_id)["pages_dir"]
    for path in sorted(pages_dir.glob("page_*.meta.json")):
        try:
            payload = read_json(path)
        except Exception:
            payload = None
        if isinstance(payload, dict) and payload.get("page_number") is not None:
            stored_meta[int(payload["page_number"])] = payload

    page_numbers = sorted(set(markdown_pages) | set(items_pages) | set(metadata_pages))
    if not page_numbers:
        raise ValueError(f"Run {run_id} tidak memiliki halaman")

    image_counts: dict[int, int] = {}
    images_index_path = config.run_paths(run_id)["images_dir"] / "index.json"
    if images_index_path.exists():
        try:
            for image in read_json(images_index_path):
                page = image.get("page_number")
                if page is not None:
                    image_counts[int(page)] = image_counts.get(int(page), 0) + 1
        except (OSError, ValueError):
            image_counts = {}

    context = structure.DocumentContext(
        config.profile().chapter_titles,
        config.profile().lettered_subsections,
    )
    page_records: list[dict[str, Any]] = []
    block_records: list[dict[str, Any]] = []
    baseline_pages = (
        reconcile.load_baseline() if config.profile().gate_mode == "baseline" else {}
    )
    reconciliation_pages: list[dict[str, Any]] = []
    reconciliation_events: list[dict[str, Any]] = []

    templates = clean.edge_templates(
        [
            str((markdown_pages.get(page) or {}).get("markdown") or "")
            for page in page_numbers
        ]
    )

    for page_number in page_numbers:
        markdown_page = markdown_pages.get(page_number, {})
        items_page = items_pages.get(page_number, {})
        metadata_page = metadata_pages.get(page_number, {})
        stored = stored_meta.get(page_number, {})
        markdown_text = markdown_page.get("markdown") or ""

        printed_raw = metadata_page.get("printed_page_number")
        printed_number, printed_source = clean.parse_printed_page_number(printed_raw)
        header_text = markdown_page.get("header")
        footer_text = markdown_page.get("footer")
        if printed_number is None:
            derived, derived_source, derived_raw = clean.derive_printed_page_number(
                header_text, footer_text
            )
            if derived is not None:
                printed_number = derived
                printed_source = derived_source
                printed_raw = derived_raw
        if printed_number is None:
            candidate, candidate_source, candidate_raw = (
                clean.derive_page_number_from_text(markdown_text)
            )
            expected_printed = page_number - config.profile().printed_offset
            if candidate is not None and candidate == expected_printed:
                printed_number = candidate
                printed_source = candidate_source
                printed_raw = candidate_raw
        if printed_number is None:
            derived_printed = reconcile.baseline_printed_page_number(
                baseline_pages.get(page_number)
            )
            if derived_printed is not None:
                printed_number = derived_printed
                printed_source = "pymupdf_text_layer"
                printed_raw = str(derived_printed)

        success = bool(markdown_page.get("success", items_page.get("success", True)))
        items = items_page.get("items") or []
        page_width = float(items_page.get("page_width") or 0.0)
        page_height = float(items_page.get("page_height") or 0.0)

        image_items = [item for item in items if item.get("type") == "image"]
        image_area = sum(
            clean.bbox_area(_bbox_to_list(item.get("bbox"))) for item in image_items
        )
        page_area = page_width * page_height if page_width and page_height else 0.0
        coverage = min(image_area / page_area, 1.0) if page_area else 0.0

        page_meta = {
            "confidence": metadata_page.get("confidence"),
            "printed_page_number_parsed": printed_number,
            "printed_page_number_source": printed_source,
            "printed_page_number_text": printed_raw,
            "header": markdown_page.get("header"),
            "footer": markdown_page.get("footer"),
            "parser_tier": options.get("tier"),
            "parser_version": options.get("version"),
        }

        blocks, counters = build_blocks_for_page(
            page_number,
            items,
            page_meta,
            context,
            edge_templates=templates,
            page_height=page_height,
        )
        blocks, reconciliation, recon_events = reconcile.reconcile_page(
            page_number=page_number,
            blocks=blocks,
            baseline=baseline_pages.get(page_number),
            context=context,
            page_meta=page_meta,
            options=options,
        )
        reconciliation_pages.append(reconciliation)
        reconciliation_events.extend(recon_events)
        block_records.extend(blocks)

        flags: list[str] = []
        notes: list[str] = []
        if clean.detect_possible_multi_column(items):
            flags.append("possible_multi_column_layout")
        if clean.detect_layout_conflict(items):
            flags.append("layout_conflict_table_text")
        if markdown_page.get("header"):
            flags.append("repeated_header_candidate")
        if markdown_page.get("footer"):
            flags.append("repeated_footer_candidate")
        if counters["removed_standalone_page_number"]:
            notes.append(
                f"removed_standalone_page_number:{counters['removed_standalone_page_number']}"
            )
        if counters["removed_repeated_edge"]:
            notes.append(
                f"removed_repeated_header_footer:{counters['removed_repeated_edge']}"
            )
        if counters["removed_image_placeholder"]:
            notes.append(
                f"removed_image_placeholder:{counters['removed_image_placeholder']}"
            )
        if counters["substance_changed"]:
            notes.append("substance_changed_by_cleaning")
        if reconciliation["tokens_restored"]:
            notes.append(
                f"verbatim_tokens_restored:{reconciliation['tokens_restored']}"
            )
        if reconciliation["blocks_recovered"]:
            notes.append(
                f"blocks_recovered_from_baseline:{reconciliation['blocks_recovered']}"
            )
        if reconciliation["fallback"]:
            notes.append("page_text_recovered_from_baseline")

        if reconciliation["fallback"]:
            page_text_source = "pymupdf_text_layer"
        elif (
            reconciliation["tokens_restored"]
            or reconciliation.get("table_tokens_restored")
            or reconciliation["blocks_recovered"]
        ):
            page_text_source = "llamaparse+baseline"
        else:
            page_text_source = "llamaparse"

        confidence = metadata_page.get("confidence")
        if confidence is not None and float(confidence) < 0.8:
            notes.append("parser_confidence_low")

        if not success:
            extraction_status = "extraction_error"
        elif not markdown_text.strip() and not blocks:
            extraction_status = "no_text_extracted"
        else:
            extraction_status = "text_extracted"

        page_text = "\n\n".join(block["text"] for block in blocks)
        page_record = {
            "schema_version": base_config.SCHEMA_VERSION,
            "document_id": config.DOCUMENT_ID,
            "page_number": page_number,
            "page_width": round(page_width, 3),
            "page_height": round(page_height, 3),
            "page_rotation": int(metadata_page.get("original_orientation_angle") or 0),
            "raw_text": markdown_text,
            "text": page_text,
            "text_char_count": len(page_text),
            "block_count": len(blocks),
            "image_count": max(len(image_items), image_counts.get(page_number, 0)),
            "image_coverage_ratio": round(coverage, 5),
            "printed_page_number": printed_number,
            "printed_page_number_source": printed_source,
            "printed_page_number_text": printed_raw,
            "extraction_status": extraction_status,
            "flags": flags,
            "notes": notes,
            "text_source": page_text_source,
            "parser_engine": "LlamaParse",
            "parser_tier": options.get("tier"),
            "parser_version": options.get("version"),
            "parser_confidence": confidence,
            "parser_cost_optimized": metadata_page.get("cost_optimized"),
            "header": markdown_page.get("header"),
            "footer": markdown_page.get("footer"),
            "removed_edge_lines": counters.get("removed_edge_lines") or [],
            "run_id": run_id,
        }
        page_records.append(page_record)

    statistics = build_statistics(page_records, block_records)
    metadata = build_document_metadata(manifest, statistics, run_id, options)
    reconciliation = reconcile.write_reports(
        run_id, reconciliation_pages, reconciliation_events
    )
    metadata["extraction"]["reconciliation"] = reconciliation

    paths = config.normalized_paths()
    store.dump_jsonl(paths["pages"], page_records)
    store.dump_jsonl(paths["blocks"], block_records)
    store.write_json(paths["metadata"], metadata)

    summary = {
        "run_id": run_id,
        "pages": len(page_records),
        "blocks": len(block_records),
        "statistics": statistics,
        "reconciliation": reconciliation,
        "outputs": {key: str(value) for key, value in paths.items()},
    }
    LOGGER.info(
        "Normalisasi selesai: %s halaman, %s blok", summary["pages"], summary["blocks"]
    )
    return summary


def build_statistics(
    pages: list[dict[str, Any]], blocks: list[dict[str, Any]]
) -> dict[str, Any]:
    blocks_by_type: dict[str, int] = {}
    for block in blocks:
        key = str(block.get("content_type"))
        blocks_by_type[key] = blocks_by_type.get(key, 0) + 1

    headings = sum(
        1
        for block in blocks
        if block.get("content_type") in base_config.HEADING_CONTENT_TYPES
    )
    tables = [block for block in blocks if block.get("content_type") == "table"]
    return {
        "pages_with_text": sum(
            1 for page in pages if page.get("extraction_status") == "text_extracted"
        ),
        "pages_without_text": sum(
            1 for page in pages if page.get("extraction_status") == "no_text_extracted"
        ),
        "pages_with_errors": sum(
            1 for page in pages if page.get("extraction_status") == "extraction_error"
        ),
        "pages_flagged": sum(1 for page in pages if page.get("flags")),
        "blocks_total": len(blocks),
        "blocks_by_content_type": dict(sorted(blocks_by_type.items())),
        "tables_detected": len(tables),
        "tables_needs_review": sum(
            1 for block in tables if block.get("extraction_status") == "needs_manual_review"
        ),
        "headings_detected": headings,
        "printed_page_numbers_detected": sum(
            1 for page in pages if page.get("printed_page_number") is not None
        ),
        "characters_total": sum(int(page.get("text_char_count") or 0) for page in pages),
    }


def build_document_metadata(
    manifest: dict[str, Any],
    statistics: dict[str, Any],
    run_id: str,
    options: dict[str, Any],
) -> dict[str, Any]:
    pdf_metadata: dict[str, Any] = {}
    manual_documents: dict[str, Any] = {}
    try:
        if config.base_config.build_paths().manifest.exists():
            existing = base_output.read_json(config.base_config.build_paths().manifest)
            for entry in existing.get("documents", []):
                if entry.get("document_id") == config.DOCUMENT_ID:
                    pdf_metadata = entry.get("pdf_metadata") or {}
                    break
    except (OSError, ValueError):
        pdf_metadata = {}
    manual_documents, _ = base_output.load_manual_metadata(
        config.base_config.build_paths().manual_metadata
    )
    metadata, metadata_source, metadata_notes = base_output.resolve_metadata(
        config.DOCUMENT_ID, pdf_metadata, manual_documents
    )
    return {
        "schema_version": base_config.SCHEMA_VERSION,
        "document_id": config.DOCUMENT_ID,
        "document_name": manifest.get("source_file"),
        "source_path": manifest.get("source_path"),
        "source_sha256": manifest.get("source_sha256"),
        "total_pdf_pages": manifest.get("total_pdf_pages"),
        "title": metadata["title"],
        "authors": metadata["authors"],
        "publication_year": metadata["publication_year"],
        "publisher": metadata["publisher"],
        "language": metadata["language"],
        "metadata_source": metadata_source,
        "metadata_notes": metadata_notes,
        "extraction": {
            "run_id": run_id,
            "engine": "LlamaParse",
            "tier": options.get("tier"),
            "version": options.get("version"),
            "extracted_pages": manifest.get("pages_expected"),
            "job_id": manifest.get("job_id"),
            "credits_used": manifest.get("credits_used"),
        },
        "statistics": statistics,
        "generated_at": base_output.utc_now(),
    }
