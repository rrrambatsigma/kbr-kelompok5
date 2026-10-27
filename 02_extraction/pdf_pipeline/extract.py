"""Penemuan PDF dan ekstraksi teks per halaman dengan PyMuPDF.

Modul ini hanya membaca PDF. Tidak ada OCR, tidak ada akses jaringan, dan
tidak ada penulisan ke folder PDF asli.

PyMuPDF diimpor secara lazy agar modul parser/validator dapat diuji tanpa
dependensi tersebut.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Callable, Optional

from . import config


class ExtractionError(RuntimeError):
    """Kesalahan yang dapat dilaporkan dengan jelas kepada pengguna."""


ProgressCallback = Callable[[int, int], None]


def _import_pymupdf() -> Any:
    try:
        import pymupdf as module  # type: ignore

        return module
    except ImportError:
        try:
            import fitz as module  # type: ignore

            return module
        except ImportError as exc:  # pragma: no cover - bergantung lingkungan
            raise ExtractionError(
                "PyMuPDF belum terpasang. Jalankan: "
                "python -m pip install -r 02_extraction\\requirements.txt"
            ) from exc


def get_extractor_version() -> str:
    """Mengembalikan versi PyMuPDF bila tersedia."""

    module = _import_pymupdf()
    return str(
        getattr(module, "__version__", None)
        or getattr(module, "VersionBind", None)
        or "unknown"
    )


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Menghitung SHA-256 secara streaming tanpa mengubah file."""

    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def discover_sources(
    paths: config.ProjectPaths, document_id: Optional[str] = None
) -> tuple[list[dict[str, Any]], list[str]]:
    """Menemukan PDF terdaftar dan melaporkan PDF yang tidak terdaftar.

    Pengembalian: (sources, unregistered_filenames)
    """

    if not paths.pdf_dir.is_dir():
        raise ExtractionError(f"Folder PDF tidak ditemukan: {paths.pdf_dir}")

    available: dict[str, Path] = {}
    for item in paths.pdf_dir.iterdir():
        if item.is_file() and item.suffix.lower() == ".pdf":
            available[item.name.lower()] = item

    registry = list(config.SOURCE_DOCUMENTS)
    if document_id is not None:
        registry = [item for item in registry if item.document_id == document_id]
        if not registry:
            raise ExtractionError(
                f"document_id tidak dikenal: {document_id}. "
                f"Pilihan: {', '.join(config.document_ids())}"
            )

    sources: list[dict[str, Any]] = []
    missing: list[str] = []
    seen_ids: set[str] = set()

    for item in registry:
        if item.document_id in seen_ids:
            raise ExtractionError(f"document_id duplikat di registry: {item.document_id}")
        seen_ids.add(item.document_id)

        source_path = available.get(item.filename.lower())
        if source_path is None:
            missing.append(item.filename)
            continue

        sources.append(
            {
                "document_id": item.document_id,
                "document_name": source_path.name,
                "filename": item.filename,
                "path": source_path,
            }
        )

    if missing:
        raise ExtractionError(
            "PDF sumber tidak ditemukan: " + ", ".join(missing)
        )

    registered_names = {item.filename.lower() for item in config.SOURCE_DOCUMENTS}
    unregistered = sorted(
        path.name for key, path in available.items() if key not in registered_names
    )

    return sources, unregistered


def _bbox(value: Any) -> list[float]:
    if value is None:
        return [0.0, 0.0, 0.0, 0.0]
    try:
        if len(value) != 4:
            return [0.0, 0.0, 0.0, 0.0]
        return [round(float(item), 3) for item in value]
    except (TypeError, ValueError):
        return [0.0, 0.0, 0.0, 0.0]


def _sanitize_metadata(raw: Any) -> dict[str, Optional[str]]:
    """Mengubah metadata PyMuPDF menjadi dictionary JSON-safe."""

    if not isinstance(raw, dict):
        return {}
    result: dict[str, Optional[str]] = {}
    for key, value in raw.items():
        if not isinstance(key, str):
            continue
        if value is None:
            result[key] = None
        else:
            result[key] = str(value)
    return result


def _int_to_roman(number: int) -> str:
    if number <= 0:
        return str(number)
    values = (
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    )
    result: list[str] = []
    remaining = number
    for value, symbol in values:
        while remaining >= value:
            result.append(symbol)
            remaining -= value
    return "".join(result)


def _int_to_alpha(number: int) -> str:
    if number <= 0:
        return str(number)
    result = ""
    remaining = number
    while remaining > 0:
        remaining -= 1
        result = chr(ord("a") + (remaining % 26)) + result
        remaining //= 26
    return result


def _format_page_label(number: int, style: Optional[str]) -> str:
    style = style or "D"
    if style == "D":
        return str(number)
    if style == "r":
        return _int_to_roman(number).lower()
    if style == "R":
        return _int_to_roman(number)
    if style == "a":
        return _int_to_alpha(number)
    if style == "A":
        return _int_to_alpha(number).upper()
    return str(number)


def _build_page_label_map(doc: Any) -> tuple[dict[int, str], Optional[str]]:
    """Membaca label halaman PDF (0-based) bila tersedia.

    Label halaman PDF lebih andal daripada menebak nomor tercetak dari teks.
    """

    getter = getattr(doc, "get_page_labels", None)
    if getter is None:
        return {}, "pdf_page_labels_api_not_available"

    try:
        entries = getter()
    except Exception as exc:  # pragma: no cover - bergantung isi PDF
        return {}, f"pdf_page_labels_error:{type(exc).__name__}"

    if not entries:
        return {}, "pdf_page_labels_not_present"

    try:
        page_count = int(doc.page_count)
    except Exception:
        return {}, "pdf_page_labels_page_count_error"

    normalized: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        try:
            start = int(entry.get("startpage", 0))
            raw_first = entry.get("firstpagenum", 1)
            first = 1 if raw_first is None else int(raw_first)
        except (TypeError, ValueError):
            continue
        normalized.append(
            {
                "startpage": start,
                "prefix": str(entry.get("prefix") or ""),
                "style": entry.get("style"),
                "firstpagenum": first,
            }
        )

    if not normalized:
        return {}, "pdf_page_labels_invalid"

    normalized.sort(key=lambda item: item["startpage"])
    mapping: dict[int, str] = {}
    for index, entry in enumerate(normalized):
        start = max(0, entry["startpage"])
        next_start = (
            normalized[index + 1]["startpage"]
            if index + 1 < len(normalized)
            else page_count
        )
        end = min(page_count, max(start, next_start))
        for page_index in range(start, end):
            sequence_number = entry["firstpagenum"] + (page_index - start)
            mapping[page_index] = (
                entry["prefix"]
                + _format_page_label(sequence_number, entry["style"])
            )

    if not mapping:
        return {}, "pdf_page_labels_empty"
    return mapping, "pdf_page_labels_available"


def _extract_text_blocks(page: Any) -> list[dict[str, Any]]:
    """Mengambil blok teks, baris, span, ukuran font, dan bbox."""

    data = page.get_text("dict", sort=False)
    blocks: list[dict[str, Any]] = []
    for block in data.get("blocks", []):
        if block.get("type", 0) != 0:
            continue
        lines: list[dict[str, Any]] = []
        for line in block.get("lines", []):
            spans: list[dict[str, Any]] = []
            for span in line.get("spans", []):
                text = span.get("text", "")
                if not text:
                    continue
                spans.append(
                    {
                        "text": text,
                        "size": float(span.get("size", 0.0) or 0.0),
                        "font": str(span.get("font", "") or ""),
                        "flags": int(span.get("flags", 0) or 0),
                        "bbox": _bbox(span.get("bbox")),
                    }
                )
            if not spans:
                continue
            lines.append(
                {
                    "bbox": _bbox(line.get("bbox")),
                    "text": "".join(span["text"] for span in spans),
                    "spans": spans,
                }
            )
        if lines:
            blocks.append({"bbox": _bbox(block.get("bbox")), "lines": lines})
    return blocks


def _image_stats(page: Any) -> tuple[int, float]:
    """Menghitung jumlah gambar dan perkiraan rasio area gambar."""

    try:
        image_count = len(page.get_images(full=True))
    except Exception:
        image_count = 0

    try:
        infos = page.get_image_info()
    except Exception:
        return image_count, 0.0

    rect = page.rect
    page_width = float(rect.width)
    page_height = float(rect.height)
    page_area = page_width * page_height
    if page_area <= 0:
        return image_count, 0.0

    total_area = 0.0
    for info in infos or []:
        if not isinstance(info, dict):
            continue
        bbox = info.get("bbox")
        if not bbox or len(bbox) != 4:
            continue
        try:
            x0 = max(float(bbox[0]), float(rect.x0))
            y0 = max(float(bbox[1]), float(rect.y0))
            x1 = min(float(bbox[2]), float(rect.x1))
            y1 = min(float(bbox[3]), float(rect.y1))
        except (TypeError, ValueError):
            continue
        if x1 > x0 and y1 > y0:
            total_area += (x1 - x0) * (y1 - y0)

    return image_count, round(min(total_area / page_area, 1.0), 6)


def _cell_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).replace("\r\n", "\n").replace("\r", "\n").strip()
    return text


def _extract_tables(page: Any) -> tuple[list[dict[str, Any]], list[str]]:
    """Ekstraksi tabel best-effort dengan API find_tables PyMuPDF."""

    if not hasattr(page, "find_tables"):
        return [], ["table_detection_not_supported_by_pymupdf"]

    try:
        finder = page.find_tables()
    except Exception as exc:  # pragma: no cover - bergantung isi PDF
        return [], [f"table_detection_error:{type(exc).__name__}"]

    tables = getattr(finder, "tables", None) or []
    results: list[dict[str, Any]] = []
    notes: list[str] = []
    page_height = float(page.rect.height)

    for index, table in enumerate(tables, start=1):
        try:
            extracted = table.extract()
        except Exception as exc:  # pragma: no cover - bergantung isi PDF
            notes.append(f"table_extract_error:{type(exc).__name__}")
            continue

        rows: list[list[Optional[str]]] = []
        for raw_row in extracted or []:
            rows.append([_cell_text(cell) for cell in raw_row])

        row_count = len(rows)
        column_count = max((len(row) for row in rows), default=0)
        column_lengths = {len(row) for row in rows}
        total_cells = row_count * column_count
        empty_cells = 0
        for row in rows:
            for cell in row:
                if cell is None or cell == "":
                    empty_cells += 1
        if total_cells > 0:
            # Kolom yang hilang juga dianggap sel kosong.
            empty_cells += total_cells - sum(len(row) for row in rows)

        review_reasons: list[str] = []
        if row_count < 2 or column_count < 2:
            review_reasons.append("few_rows_or_columns")
        if len(column_lengths) > 1:
            review_reasons.append("inconsistent_column_count")
        if total_cells > 0 and (empty_cells / total_cells) > 0.5:
            review_reasons.append("empty_cells_high")
        if any(
            cell is not None and len(cell) > 500
            for row in rows
            for cell in row
        ):
            review_reasons.append("long_cell_text")
        if not rows:
            review_reasons.append("empty_table")

        bbox = _bbox(getattr(table, "bbox", None))
        if bbox[1] <= 20.0 or bbox[3] >= page_height - 20.0:
            review_reasons.append("touches_page_edge_possible_cross_page")

        results.append(
            {
                "table_index": index,
                "bbox": bbox,
                "row_count": row_count,
                "column_count": column_count,
                "cells": rows,
                "review_required": bool(review_reasons),
                "review_reasons": review_reasons,
                "detection_method": "pymupdf_find_tables",
            }
        )

    results.sort(key=lambda item: (item["bbox"][1], item["bbox"][0], item["table_index"]))
    return results, notes


def extract_document(
    source: dict[str, Any],
    paths: config.ProjectPaths,
    tables_enabled: bool = True,
    progress: Optional[ProgressCallback] = None,
) -> dict[str, Any]:
    """Mengekstrak satu PDF tanpa mengubah file sumber."""

    module = _import_pymupdf()
    source_path = Path(source["path"])
    if not source_path.is_file():
        raise ExtractionError(f"PDF tidak ditemukan: {source_path}")

    hash_before = sha256_file(source_path)
    file_size = source_path.stat().st_size

    try:
        doc = module.open(str(source_path))
    except Exception as exc:
        raise ExtractionError(
            f"Gagal membuka PDF {source_path.name}: {exc}"
        ) from exc

    pages: list[dict[str, Any]] = []
    document_notes: list[str] = []
    extractor_version = str(
        getattr(module, "__version__", None)
        or getattr(module, "VersionBind", None)
        or "unknown"
    )

    try:
        if getattr(doc, "needs_pass", False):
            raise ExtractionError(
                f"PDF {source_path.name} terenkripsi dan memerlukan password; "
                "pipeline ini tidak menangani password."
            )

        try:
            page_count = int(doc.page_count)
        except Exception as exc:
            raise ExtractionError(
                f"Tidak dapat membaca jumlah halaman {source_path.name}: {exc}"
            ) from exc

        if page_count <= 0:
            raise ExtractionError(f"PDF {source_path.name} tidak memiliki halaman.")

        metadata = _sanitize_metadata(getattr(doc, "metadata", None) or {})
        labels, label_note = _build_page_label_map(doc)
        if label_note and label_note not in {
            "pdf_page_labels_not_present",
            "pdf_page_labels_api_not_available",
        }:
            document_notes.append(label_note)

        table_detection_supported = False

        for index in range(page_count):
            page_number = index + 1
            page_record: dict[str, Any] = {
                "page_number": page_number,
                "page_width": 0.0,
                "page_height": 0.0,
                "page_rotation": 0,
                "raw_text": "",
                "text_blocks": [],
                "image_count": 0,
                "image_coverage_ratio": 0.0,
                "page_label": labels.get(index),
                "extraction_error": None,
                "table_blocks": [],
                "table_notes": [],
            }

            try:
                page = doc.load_page(index)
            except Exception as exc:
                page_record["extraction_error"] = (
                    f"page_load_error:{type(exc).__name__}: {exc}"
                )
                pages.append(page_record)
                if progress is not None:
                    progress(page_number, page_count)
                continue

            try:
                page_record["page_width"] = round(float(page.rect.width), 3)
                page_record["page_height"] = round(float(page.rect.height), 3)
                page_record["page_rotation"] = int(getattr(page, "rotation", 0) or 0)
            except Exception:
                pass

            try:
                raw_text = page.get_text("text", sort=False)
                page_record["raw_text"] = raw_text or ""
            except Exception as exc:
                page_record["extraction_error"] = (
                    f"text_extraction_error:{type(exc).__name__}: {exc}"
                )
                raw_text = ""

            try:
                page_record["text_blocks"] = _extract_text_blocks(page)
            except Exception as exc:
                page_record["table_notes"].append(
                    f"text_block_extraction_error:{type(exc).__name__}"
                )

            try:
                image_count, coverage = _image_stats(page)
                page_record["image_count"] = image_count
                page_record["image_coverage_ratio"] = coverage
            except Exception:
                pass

            if hasattr(page, "find_tables"):
                table_detection_supported = True

            if (
                tables_enabled
                and page_record["extraction_error"] is None
                and raw_text.strip()
            ):
                tables, table_notes = _extract_tables(page)
                page_record["table_blocks"] = tables
                page_record["table_notes"].extend(table_notes)

            pages.append(page_record)
            if progress is not None:
                progress(page_number, page_count)

        if tables_enabled and not table_detection_supported:
            document_notes.append("table_detection_not_supported_by_pymupdf")

        hash_after = sha256_file(source_path)
        if hash_after != hash_before:
            document_notes.append("source_changed_during_extraction")

        return {
            "document_id": source["document_id"],
            "document_name": source_path.name,
            "source_path": config.to_relative_posix(source_path, paths.root),
            "source_sha256": hash_before,
            "source_sha256_after": hash_after,
            "file_size_bytes": file_size,
            "total_pdf_pages": page_count,
            "document_type": "pdf",
            "pdf_metadata": metadata,
            "pages": pages,
            "document_notes": document_notes,
            "extractor_version": extractor_version,
        }
    finally:
        try:
            doc.close()
        except Exception:
            pass
