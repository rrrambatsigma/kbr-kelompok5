"""Parsing struktur dokumen dan pembersihan teks yang konservatif.

Modul ini tidak bergantung pada PyMuPDF. Inputnya adalah struktur data biasa
yang dihasilkan oleh ``extract.py``.
"""

from __future__ import annotations

import math
import re
import statistics
import unicodedata
from collections import Counter
from typing import Any, Optional

from . import config


CHAPTER_RE = re.compile(r"^(BAB|BAGIAN|CHAPTER)\s+([IVXLCDM]+|\d+)\b", re.IGNORECASE)
SUBSECTION_RE = re.compile(r"^(\d+)(?:\.\d+){2,}\s+\S")
SECTION_RE = re.compile(r"^(\d+)\.(\d+)\s+\S")
LIST_RE = re.compile(
    r"^(?:[-•●▪◦–—]\s+|[A-Za-z]\.\s+|\(?\d{1,3}\)[.)]?\s+|\d{1,3}\.\s+)\S"
)
PAGE_NUMBER_RE = re.compile(
    r"^(?:page\s*)?[-–—]?\s*(\d{1,4})\s*[-–—]?$", re.IGNORECASE
)


def clean_line(text: Optional[str]) -> tuple[str, list[str]]:
    """Membersihkan satu baris tanpa mengubah istilah atau angka.

    Tindakan yang dilakukan dicatat agar dapat ditelusuri.
    """

    actions: list[str] = []
    if not text:
        return "", actions

    normalized = unicodedata.normalize("NFC", text)
    if normalized != text:
        actions.append("normalized_unicode_nfc")

    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    if "\n" in normalized:
        actions.append("normalized_line_breaks")

    has_control = any(
        unicodedata.category(char) == "Cc" and char not in "\n\t"
        for char in normalized
    )
    if has_control:
        normalized = "".join(
            char
            for char in normalized
            if char in "\n\t" or unicodedata.category(char) != "Cc"
        )
        actions.append("removed_control_characters")

    collapsed = re.sub(r"\s+", " ", normalized).strip()
    if collapsed != normalized.strip():
        actions.append("collapsed_whitespace")
    if normalized != normalized.strip() and collapsed == normalized.strip():
        actions.append("trimmed_whitespace")

    return collapsed, actions


def join_text_lines(
    lines: list[str], dehyphenate: bool = False
) -> tuple[str, list[str], Optional[str]]:
    """Menggabungkan baris dalam satu paragraf.

    Dehyphenation bersifat opt-in karena tanpa kamus kita tidak dapat
    memastikan apakah tanda hubung di akhir baris merupakan soft hyphen atau
    bagian dari istilah majemuk.
    """

    actions: list[str] = []
    cleaned = [line for line in lines if line]
    if not cleaned:
        return "", actions, None
    if len(cleaned) > 1:
        actions.append("unwrapped_lines")

    result = cleaned[0]
    for line in cleaned[1:]:
        if result.endswith("-"):
            if dehyphenate and line[0].islower():
                result = result[:-1] + line
                actions.append("dehyphenated_line_break")
            else:
                result = result + " " + line
                actions.append("line_break_hyphen_preserved")
        else:
            result = result + " " + line

    raw_text: Optional[str] = None
    if "dehyphenated_line_break" in actions:
        raw_text = "\n".join(cleaned)
    return result, actions, raw_text


def _span_is_bold(font: str, flags: int) -> bool:
    if flags & 16:
        return True
    lowered = font.lower()
    return any(token in lowered for token in ("bold", "black", "heavy", "semibold"))


def _line_stats(line: dict[str, Any]) -> dict[str, Any]:
    spans = line.get("spans") or []
    total_chars = sum(len(span.get("text", "")) for span in spans)
    total_chars = max(total_chars, 1)
    weighted_size = sum(
        float(span.get("size", 0.0) or 0.0) * len(span.get("text", ""))
        for span in spans
    ) / total_chars
    max_size = max(
        (float(span.get("size", 0.0) or 0.0) for span in spans), default=0.0
    )
    bold_chars = sum(
        len(span.get("text", ""))
        for span in spans
        if _span_is_bold(
            str(span.get("font", "") or ""), int(span.get("flags", 0) or 0)
        )
    )
    return {
        "text": "".join(span.get("text", "") for span in spans),
        "font_size": max_size,
        "weighted_size": weighted_size,
        "bold_ratio": bold_chars / total_chars,
    }


def estimate_body_font_size(text_blocks: list[dict[str, Any]]) -> Optional[float]:
    """Menghitung median ukuran font terbobot jumlah karakter."""

    weights: dict[float, int] = {}
    for block in text_blocks:
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "")
                if not text.strip():
                    continue
                size = round(float(span.get("size", 0.0) or 0.0), 1)
                if size <= 0:
                    continue
                weights[size] = weights.get(size, 0) + len(text)

    if not weights:
        return None

    total_weight = sum(weights.values())
    cumulative = 0
    for size in sorted(weights):
        cumulative += weights[size]
        if cumulative >= total_weight / 2:
            return size
    return max(weights)


def _is_prominent(stats: dict[str, Any], body_size: Optional[float]) -> bool:
    if stats["bold_ratio"] >= 0.6:
        return True
    if body_size is not None and stats["font_size"] >= body_size * 1.12:
        return True
    return False


def _detect_heading_pattern(text: str) -> Optional[str]:
    if SUBSECTION_RE.match(text):
        return "subsection_heading"
    if SECTION_RE.match(text):
        return "section_heading"
    if CHAPTER_RE.match(text):
        return "chapter_heading"
    return None


def classify_heading(
    text: str,
    font_size: float,
    bold_ratio: float,
    body_size: Optional[float],
    max_words: int = 18,
) -> Optional[str]:
    """Mengklasifikasikan satu baris sebagai heading atau bukan.

    Mengembalikan nama content_type heading, atau ``None`` jika bukan heading.
    """

    text = text.strip()
    if not text or len(text) > 160:
        return None

    word_count = len(text.split())
    if word_count > max_words:
        return None
    if text[0].islower():
        return None
    if not any(char.isalpha() for char in text):
        return None

    stats = {
        "font_size": font_size,
        "bold_ratio": bold_ratio,
    }
    prominent = _is_prominent(stats, body_size)
    pattern = _detect_heading_pattern(text)

    if pattern is not None:
        if pattern == "chapter_heading":
            if text.isupper():
                return pattern
            match = CHAPTER_RE.match(text)
            remainder = (
                text[match.end() :].strip(" .,:;") if match is not None else ""
            )
            # Hindari kalimat tubuh seperti "BAB I membahas ..." yang diawali
            # pola bab tetapi tidak berbentuk judul.
            if remainder and not remainder[0].isupper():
                return None
            if text.endswith((".", ",", ";", ":")) and not prominent:
                return None
            if prominent or word_count <= 12:
                return pattern
            return None
        if prominent or text.isupper():
            return pattern
        return None

    if not prominent:
        return None
    if text.endswith((".", ",", ";", ":")):
        return None
    return "heading_unclassified"


def update_context(
    context: dict[str, Optional[str]], level: str, heading_text: str
) -> dict[str, Optional[str]]:
    """Memperbarui konteks bab/subbab berdasarkan heading yang dikenali."""

    updated = dict(context)
    if level == "chapter_heading":
        updated["chapter"] = heading_text
        updated["section"] = None
        updated["subsection"] = None
    elif level == "section_heading":
        updated["section"] = heading_text
        updated["subsection"] = None
    elif level == "subsection_heading":
        updated["subsection"] = heading_text
    return updated


def _union_bbox(lines: list[dict[str, Any]]) -> list[float]:
    boxes = [line.get("bbox") for line in lines if line.get("bbox")]
    if not boxes:
        return [0.0, 0.0, 0.0, 0.0]
    return [
        round(min(float(box[0]) for box in boxes), 3),
        round(min(float(box[1]) for box in boxes), 3),
        round(max(float(box[2]) for box in boxes), 3),
        round(max(float(box[3]) for box in boxes), 3),
    ]


def _heading_info(
    line: dict[str, Any], body_size: Optional[float]
) -> Optional[dict[str, Any]]:
    stats = _line_stats(line)
    text, _ = clean_line(stats["text"])
    if not text:
        return None
    level = classify_heading(
        text,
        font_size=stats["font_size"],
        bold_ratio=stats["bold_ratio"],
        body_size=body_size,
    )
    if level is None:
        return None
    return {"level": level, "text": text, "stats": stats}


def _split_leading_heading(
    lines: list[dict[str, Any]], body_size: Optional[float]
) -> tuple[Optional[dict[str, Any]], list[dict[str, Any]]]:
    """Memisahkan heading di awal blok dari sisa barisnya."""

    if not lines:
        return None, lines

    first = _heading_info(lines[0], body_size)
    if first is None:
        return None, lines

    heading_lines = [lines[0]]
    heading_text = first["text"]

    # Hanya judul bab yang boleh terdiri atas beberapa baris, dan hanya jika
    # baris lanjutan benar-benar pendek serta sebagian besar huruf kapital.
    if first["level"] == "chapter_heading":
        for line in lines[1:3]:
            stats = _line_stats(line)
            text, _ = clean_line(stats["text"])
            if not text:
                break
            if len(text) > 120 or len(text.split()) > 12:
                break
            if text.endswith((".", ",", ";", ":")):
                break
            if not _is_prominent(stats, body_size):
                break
            letters = [char for char in text if char.isalpha()]
            if not letters:
                break
            uppercase_ratio = sum(1 for char in letters if char.isupper()) / len(letters)
            if uppercase_ratio < 0.6:
                break
            heading_lines.append(line)
            heading_text = heading_text + " " + text

    return (
        {
            "level": first["level"],
            "text": heading_text,
            "bbox": _union_bbox(heading_lines),
        },
        lines[len(heading_lines) :],
    )


def _split_paragraph_segments(
    lines: list[dict[str, Any]],
) -> list[tuple[str, list[dict[str, Any]]]]:
    """Memecah baris blok menjadi paragraf atau list item.

    Pemecahan hanya dilakukan pada celah vertikal yang jelas atau awal list.
    """

    if not lines:
        return []

    heights = [
        float(line["bbox"][3]) - float(line["bbox"][1])
        for line in lines
        if line.get("bbox") and float(line["bbox"][3]) > float(line["bbox"][1])
    ]
    median_height = statistics.median(heights) if heights else 0.0
    gap_threshold = max(1.8 * median_height, 8.0)

    segments: list[tuple[str, list[dict[str, Any]]]] = []
    current: list[dict[str, Any]] = []
    current_type = "paragraph"
    previous: Optional[dict[str, Any]] = None

    for line in lines:
        text, _ = clean_line(_line_stats(line)["text"])
        if not text:
            continue
        is_list = bool(LIST_RE.match(text))

        should_flush = False
        if current and previous is not None:
            gap = float(line["bbox"][1]) - float(previous["bbox"][3])
            if is_list or gap > gap_threshold:
                should_flush = True

        if should_flush:
            segments.append((current_type, current))
            current = []
            current_type = "paragraph"

        if not current:
            current_type = "list_item" if is_list else "paragraph"

        current.append(line)
        previous = line

    if current:
        segments.append((current_type, current))

    return segments


def _render_table(cells: list[list[Optional[str]]]) -> str:
    rendered: list[str] = []
    for row in cells:
        values = []
        for cell in row:
            if cell is None:
                values.append("")
            else:
                values.append(str(cell).replace("\n", " / "))
        rendered.append(" | ".join(values))
    return "\n".join(rendered)


def _make_block(
    document_id: str,
    page_number: int,
    page_sequence: int,
    sequence_number: int,
    content_type: str,
    text: str,
    bbox: list[float],
    context: dict[str, Optional[str]],
    printed_page_number: Optional[str],
    extraction_status: str,
    parsing_notes: list[str],
    cleaning_actions: Optional[list[str]] = None,
    raw_text: Optional[str] = None,
    table: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    notes: list[str] = []
    for note in parsing_notes:
        if note and note not in notes:
            notes.append(note)

    return {
        "schema_version": config.SCHEMA_VERSION,
        "block_id": (
            f"{document_id}_P{page_number:03d}_B{page_sequence:03d}"
        ),
        "document_id": document_id,
        "page_number": page_number,
        "printed_page_number": printed_page_number,
        "chapter": context.get("chapter"),
        "section": context.get("section"),
        "subsection": context.get("subsection"),
        "content_type": content_type,
        "sequence_number": sequence_number,
        "text": text,
        "extraction_status": extraction_status,
        "parsing_notes": notes,
        "bbox": [round(float(value), 3) for value in bbox],
        "cleaning_actions": list(cleaning_actions or []),
        "raw_text": raw_text,
        "table": table,
    }


def _build_segment_block(
    lines: list[dict[str, Any]],
    dehyphenate: bool,
) -> Optional[dict[str, Any]]:
    cleaned_lines: list[str] = []
    raw_lines: list[str] = []
    cleaning_actions: set[str] = set()

    for line in lines:
        raw_line = str(_line_stats(line)["text"])
        text, actions = clean_line(raw_line)
        if not text:
            continue
        cleaned_lines.append(text)
        raw_lines.append(raw_line)
        cleaning_actions.update(actions)

    if not cleaned_lines:
        return None

    joined, join_actions, _ = join_text_lines(
        cleaned_lines, dehyphenate=dehyphenate
    )
    cleaning_actions.update(join_actions)

    raw_text: Optional[str] = None
    if (
        "dehyphenated_line_break" in cleaning_actions
        or "removed_control_characters" in cleaning_actions
    ):
        raw_text = "\n".join(raw_lines)

    return {
        "text": joined,
        "bbox": _union_bbox(lines),
        "cleaning_actions": sorted(cleaning_actions),
        "raw_text": raw_text,
    }


def _bbox_overlap_ratio(inner: list[float], outer: list[float]) -> float:
    width = max(0.0, min(inner[2], outer[2]) - max(inner[0], outer[0]))
    height = max(0.0, min(inner[3], outer[3]) - max(inner[1], outer[1]))
    intersection = width * height
    inner_area = max(
        0.0, (inner[2] - inner[0]) * (inner[3] - inner[1])
    )
    if inner_area <= 0:
        return 0.0
    return intersection / inner_area


def _merge_page_items(
    text_blocks: list[dict[str, Any]],
    table_blocks: list[dict[str, Any]],
) -> tuple[list[tuple[str, dict[str, Any]]], int]:
    """Menggabungkan blok teks dan tabel menurut posisi vertikal.

    Blok teks hanya dibuang jika hampir seluruhnya berada di dalam tabel yang
    memiliki struktur memadai. Jika tabel meragukan, teks tetap dipertahankan
    agar tidak ada isi yang hilang.
    """

    filtered: list[dict[str, Any]] = []
    excluded = 0
    for block in text_blocks:
        remove = False
        for table in table_blocks:
            if table.get("row_count", 0) < 2 or table.get("column_count", 0) < 2:
                continue
            if _bbox_overlap_ratio(block["bbox"], table["bbox"]) >= 0.85:
                remove = True
                break
        if remove:
            excluded += 1
        else:
            filtered.append(block)

    tables = sorted(
        table_blocks,
        key=lambda item: (
            item["bbox"][1],
            item["bbox"][0],
            item.get("table_index", 0),
        ),
    )

    items: list[tuple[str, dict[str, Any]]] = []
    table_index = 0
    for block in filtered:
        block_top = float(block["bbox"][1])
        while (
            table_index < len(tables)
            and float(tables[table_index]["bbox"][1]) <= block_top
        ):
            items.append(("table", tables[table_index]))
            table_index += 1
        items.append(("text", block))

    while table_index < len(tables):
        items.append(("table", tables[table_index]))
        table_index += 1

    return items, excluded


def _edge_line(page: dict[str, Any], where: str) -> Optional[str]:
    height = float(page.get("page_height", 0.0) or 0.0)
    if height <= 0:
        return None

    best_key: Optional[tuple[float, float]] = None
    best_text: Optional[str] = None

    for block in page.get("text_blocks", []):
        for line in block.get("lines", []):
            text, _ = clean_line(_line_stats(line)["text"])
            if not text:
                continue
            bbox = line.get("bbox") or [0, 0, 0, 0]
            if where == "top" and float(bbox[1]) <= height * 0.15:
                key = (float(bbox[1]), float(bbox[0]))
                if best_key is None or key < best_key:
                    best_key = key
                    best_text = text
            elif where == "bottom" and float(bbox[3]) >= height * 0.85:
                key = (float(bbox[3]), float(bbox[0]))
                if best_key is None or key > best_key:
                    best_key = key
                    best_text = text

    return best_text


def _parse_page_number(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    match = PAGE_NUMBER_RE.match(text.strip())
    if not match:
        return None
    try:
        value = int(match.group(1))
    except (TypeError, ValueError):
        return None
    if value < 1 or value > 9999:
        return None
    return value


def detect_printed_page_number_sequence(
    candidates: dict[int, int],
) -> dict[int, str]:
    """Mendeteksi urutan nomor halaman tercetak yang konsisten.

    Hanya urutan minimal tiga halaman berturut-turut dengan selisih konstan
    yang dianggap dapat dipercaya.
    """

    result: dict[int, str] = {}
    run: list[tuple[int, int]] = []

    def flush() -> None:
        if len(run) >= 3:
            for page_number, value in run:
                result[page_number] = str(value)

    for page_number in sorted(candidates):
        value = candidates[page_number]
        if run:
            previous_page, previous_value = run[-1]
            same_offset = (value - page_number) == (previous_value - previous_page)
            if page_number == previous_page + 1 and same_offset:
                run.append((page_number, value))
                continue
        flush()
        run = [(page_number, value)]
    flush()
    return result


def _page_number_candidate(page: dict[str, Any]) -> Optional[int]:
    bottom = _parse_page_number(_edge_line(page, "bottom"))
    top = _parse_page_number(_edge_line(page, "top"))
    if bottom is not None and top is not None and bottom != top:
        return None
    return bottom if bottom is not None else top


def _normalize_edge_text(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    cleaned, _ = clean_line(text)
    cleaned = cleaned.strip()
    if len(cleaned) < 3:
        return None
    if PAGE_NUMBER_RE.match(cleaned):
        return None
    return re.sub(r"\s+", " ", cleaned)


def _detect_repeated_lines(
    raw_pages: list[dict[str, Any]],
) -> dict[str, Any]:
    header_counts: Counter[str] = Counter()
    footer_counts: Counter[str] = Counter()
    header_pages: dict[str, set[int]] = {}
    footer_pages: dict[str, set[int]] = {}
    header_examples: dict[str, str] = {}
    footer_examples: dict[str, str] = {}
    text_page_count = 0

    for page in raw_pages:
        if not str(page.get("raw_text", "")).strip():
            continue
        text_page_count += 1

        header = _normalize_edge_text(_edge_line(page, "top"))
        if header is not None:
            header_counts[header] += 1
            header_pages.setdefault(header, set()).add(int(page["page_number"]))
            header_examples.setdefault(header, header)

        footer = _normalize_edge_text(_edge_line(page, "bottom"))
        if footer is not None:
            footer_counts[footer] += 1
            footer_pages.setdefault(footer, set()).add(int(page["page_number"]))
            footer_examples.setdefault(footer, footer)

    threshold = max(3, math.ceil(0.2 * text_page_count)) if text_page_count else 3

    def build(
        counts: Counter[str],
        pages: dict[str, set[int]],
        examples: dict[str, str],
    ) -> list[dict[str, Any]]:
        candidates = []
        for key, count in counts.most_common():
            if count < threshold:
                continue
            candidates.append(
                {
                    "text": examples.get(key, key),
                    "count": count,
                    "pages": sorted(pages.get(key, set())),
                }
            )
            if len(candidates) >= 10:
                break
        return candidates

    return {
        "threshold": threshold,
        "header_candidates": build(header_counts, header_pages, header_examples),
        "footer_candidates": build(footer_counts, footer_pages, footer_examples),
    }


def _is_multi_column(
    text_blocks: list[dict[str, Any]], page_width: float
) -> bool:
    if page_width <= 0 or len(text_blocks) < 4:
        return False

    left: list[dict[str, Any]] = []
    right: list[dict[str, Any]] = []
    for block in text_blocks:
        bbox = block.get("bbox") or [0, 0, 0, 0]
        center = (float(bbox[0]) + float(bbox[2])) / 2
        if center < page_width * 0.45:
            left.append(block)
        elif center > page_width * 0.55:
            right.append(block)

    if len(left) < 2 or len(right) < 2:
        return False

    overlapping_pairs = 0
    for left_block in left:
        left_bbox = left_block.get("bbox") or [0, 0, 0, 0]
        left_height = max(0.0, float(left_bbox[3]) - float(left_bbox[1]))
        for right_block in right:
            right_bbox = right_block.get("bbox") or [0, 0, 0, 0]
            right_height = max(0.0, float(right_bbox[3]) - float(right_bbox[1]))
            overlap = min(float(left_bbox[3]), float(right_bbox[3])) - max(
                float(left_bbox[1]), float(right_bbox[1])
            )
            if overlap > 0.3 * min(left_height, right_height):
                overlapping_pairs += 1
                break

    return overlapping_pairs >= 2


def build_statistics(
    pages: list[dict[str, Any]],
    blocks: list[dict[str, Any]],
) -> dict[str, Any]:
    by_type = Counter(block["content_type"] for block in blocks)
    pages_with_text = sum(
        1 for page in pages if page["extraction_status"] == "text_extracted"
    )
    pages_without_text = sum(
        1 for page in pages if page["extraction_status"] == "no_text_extracted"
    )
    pages_with_errors = sum(
        1 for page in pages if page["extraction_status"] == "extraction_error"
    )
    pages_flagged = sum(1 for page in pages if page.get("flags"))
    headings_detected = sum(
        1
        for block in blocks
        if block["content_type"] in config.HEADING_CONTENT_TYPES
    )
    tables = [block for block in blocks if block["content_type"] == "table"]
    printed = sum(
        1 for page in pages if page.get("printed_page_number") is not None
    )

    return {
        "pages_with_text": pages_with_text,
        "pages_without_text": pages_without_text,
        "pages_with_errors": pages_with_errors,
        "pages_flagged": pages_flagged,
        "blocks_total": len(blocks),
        "blocks_by_content_type": {
            key: by_type[key] for key in sorted(by_type)
        },
        "tables_detected": len(tables),
        "tables_needs_review": sum(
            1
            for block in tables
            if block.get("extraction_status") == "needs_manual_review"
        ),
        "headings_detected": headings_detected,
        "printed_page_numbers_detected": printed,
        "characters_total": sum(int(page.get("text_char_count", 0)) for page in pages),
    }


def determine_document_status(
    pages: list[dict[str, Any]],
    blocks: list[dict[str, Any]],
    source_changed: bool = False,
) -> str:
    if source_changed:
        return "partial"
    if any(page["extraction_status"] == "extraction_error" for page in pages):
        return "partial"

    pages_with_text = sum(
        1 for page in pages if page["extraction_status"] == "text_extracted"
    )
    if pages_with_text == 0:
        return "no_text_extracted"

    warnings = False
    if any(page["extraction_status"] == "no_text_extracted" for page in pages):
        warnings = True
    if any(page.get("flags") for page in pages):
        warnings = True
    if any(
        block.get("extraction_status") == "needs_manual_review" for block in blocks
    ):
        warnings = True
    if not blocks:
        warnings = True

    return "completed_with_warnings" if warnings else "completed"


def parse_document(
    document: dict[str, Any],
    dehyphenate: bool = False,
    detect_printed_pages: bool = True,
) -> dict[str, Any]:
    """Mengubah hasil ekstraksi mentah menjadi halaman dan blok terstruktur."""

    raw_pages = sorted(
        document.get("pages", []), key=lambda item: int(item["page_number"])
    )

    printed_map: dict[int, tuple[str, str]] = {}
    candidate_pages: dict[int, int] = {}
    fallback: dict[int, str] = {}

    if detect_printed_pages:
        for page in raw_pages:
            page_number = int(page["page_number"])
            label = page.get("page_label")
            label_text = str(label).strip() if label is not None else ""
            if label_text:
                printed_map[page_number] = (label_text, "pdf_page_labels")
            else:
                candidate = _page_number_candidate(page)
                if candidate is not None:
                    candidate_pages[page_number] = candidate

        fallback = detect_printed_page_number_sequence(candidate_pages)
        for page_number, value in fallback.items():
            printed_map.setdefault(page_number, (value, "text_sequence"))

    repeated_lines = _detect_repeated_lines(raw_pages)
    header_pages: set[int] = set()
    footer_pages: set[int] = set()
    for candidate in repeated_lines["header_candidates"]:
        header_pages.update(candidate["pages"])
    for candidate in repeated_lines["footer_candidates"]:
        footer_pages.update(candidate["pages"])

    body_font_size = estimate_body_font_size(
        [
            block
            for page in raw_pages
            for block in page.get("text_blocks", [])
        ]
    )

    blocks: list[dict[str, Any]] = []
    pages: list[dict[str, Any]] = []
    context: dict[str, Optional[str]] = {
        "chapter": None,
        "section": None,
        "subsection": None,
    }
    sequence_number = 0
    paragraphs_before_chapter = 0
    unclassified_heading_ids: list[str] = []
    multi_column_pages: list[int] = []

    for page in raw_pages:
        page_number = int(page["page_number"])
        page_blocks_start = len(blocks)
        page_sequence = 0

        printed_value = None
        printed_source = None
        if page_number in printed_map:
            printed_value, printed_source = printed_map[page_number]
        elif (
            detect_printed_pages
            and page_number in candidate_pages
            and page_number not in fallback
        ):
            printed_source = None

        items, excluded_text_blocks = _merge_page_items(
            page.get("text_blocks", []), page.get("table_blocks", [])
        )

        for item_type, item in items:
            if item_type == "table":
                table = item
                preview = _render_table(table.get("cells", []))
                table_notes = ["table_detected"]
                if table.get("review_required"):
                    table_notes.append("table_requires_manual_review")
                    for reason in table.get("review_reasons", []):
                        table_notes.append(f"table_review_reason:{reason}")

                sequence_number += 1
                page_sequence += 1
                blocks.append(
                    _make_block(
                        document_id=document["document_id"],
                        page_number=page_number,
                        page_sequence=page_sequence,
                        sequence_number=sequence_number,
                        content_type="table",
                        text=preview,
                        bbox=table["bbox"],
                        context=context,
                        printed_page_number=printed_value,
                        extraction_status=(
                            "needs_manual_review"
                            if table.get("review_required")
                            else "extracted"
                        ),
                        parsing_notes=table_notes,
                        table=table,
                    )
                )
                continue

            heading, remaining_lines = _split_leading_heading(
                item.get("lines", []), body_font_size
            )
            if heading is not None:
                level = heading["level"]
                if level != "heading_unclassified":
                    context = update_context(context, level, heading["text"])

                heading_notes = ["heading_detected"]
                if level == "heading_unclassified":
                    heading_notes.append("heading_pattern_not_recognized")

                sequence_number += 1
                page_sequence += 1
                block = _make_block(
                    document_id=document["document_id"],
                    page_number=page_number,
                    page_sequence=page_sequence,
                    sequence_number=sequence_number,
                    content_type=level,
                    text=heading["text"],
                    bbox=heading["bbox"],
                    context=context,
                    printed_page_number=printed_value,
                    extraction_status=(
                        "needs_manual_review"
                        if level == "heading_unclassified"
                        else "extracted"
                    ),
                    parsing_notes=heading_notes,
                )
                blocks.append(block)
                if level == "heading_unclassified":
                    unclassified_heading_ids.append(block["block_id"])

            for segment_type, segment_lines in _split_paragraph_segments(
                remaining_lines
            ):
                built = _build_segment_block(segment_lines, dehyphenate=dehyphenate)
                if built is None:
                    continue

                paragraph_notes: list[str] = []
                if segment_type == "list_item":
                    paragraph_notes.append("list_item_detected")
                if "line_break_hyphen_preserved" in built["cleaning_actions"]:
                    paragraph_notes.append("line_break_hyphen_preserved")
                if "dehyphenated_line_break" in built["cleaning_actions"]:
                    paragraph_notes.append("dehyphenated_line_break")

                if context.get("chapter") is None and segment_type == "paragraph":
                    paragraphs_before_chapter += 1

                sequence_number += 1
                page_sequence += 1
                blocks.append(
                    _make_block(
                        document_id=document["document_id"],
                        page_number=page_number,
                        page_sequence=page_sequence,
                        sequence_number=sequence_number,
                        content_type=segment_type,
                        text=built["text"],
                        bbox=built["bbox"],
                        context=context,
                        printed_page_number=printed_value,
                        extraction_status="extracted",
                        parsing_notes=paragraph_notes,
                        cleaning_actions=built["cleaning_actions"],
                        raw_text=built["raw_text"],
                    )
                )

        block_count = len(blocks) - page_blocks_start
        has_text = bool(str(page.get("raw_text", "")).strip()) or bool(
            page.get("text_blocks")
        )
        if page.get("extraction_error"):
            page_status = "extraction_error"
        elif has_text:
            page_status = "text_extracted"
        else:
            page_status = "no_text_extracted"

        flags: list[str] = []
        page_notes: list[str] = list(page.get("table_notes", []))
        if page.get("extraction_error"):
            page_notes.append(str(page["extraction_error"]))
        if excluded_text_blocks:
            page_notes.append(
                f"table_text_excluded_from_paragraphs:{excluded_text_blocks}"
            )

        if page_status == "text_extracted":
            if _is_multi_column(
                page.get("text_blocks", []), float(page.get("page_width", 0.0))
            ):
                flags.append("possible_multi_column_layout")
                multi_column_pages.append(page_number)
        else:
            image_count = int(page.get("image_count", 0) or 0)
            coverage = float(page.get("image_coverage_ratio", 0.0) or 0.0)
            if image_count > 0:
                flags.append("ocr_candidate")
                if coverage >= 0.5:
                    flags.append("likely_scanned_image_only")

        if page_number in header_pages:
            flags.append("repeated_header_candidate")
        if page_number in footer_pages:
            flags.append("repeated_footer_candidate")

        if (
            detect_printed_pages
            and page_number in candidate_pages
            and page_number not in printed_map
        ):
            page_notes.append("printed_page_number_candidate_unconfirmed")

        pages.append(
            {
                "schema_version": config.SCHEMA_VERSION,
                "document_id": document["document_id"],
                "page_number": page_number,
                "page_width": float(page.get("page_width", 0.0) or 0.0),
                "page_height": float(page.get("page_height", 0.0) or 0.0),
                "page_rotation": int(page.get("page_rotation", 0) or 0),
                "raw_text": str(page.get("raw_text", "")),
                "text_char_count": len(str(page.get("raw_text", ""))),
                "block_count": block_count,
                "image_count": int(page.get("image_count", 0) or 0),
                "image_coverage_ratio": float(
                    page.get("image_coverage_ratio", 0.0) or 0.0
                ),
                "printed_page_number": printed_value,
                "printed_page_number_source": printed_source,
                "extraction_status": page_status,
                "flags": flags,
                "notes": page_notes,
            }
        )

    statistics = build_statistics(pages, blocks)
    source_changed = (
        document.get("source_sha256_after") is not None
        and document.get("source_sha256") != document.get("source_sha256_after")
    )
    document_notes = list(document.get("document_notes", []))
    if statistics["pages_with_text"] == 0:
        document_notes.append("no_text_layer_detected")
    if any("ocr_candidate" in page["flags"] for page in pages):
        document_notes.append("ocr_not_performed")
    if detect_printed_pages and statistics["printed_page_numbers_detected"] == 0:
        document_notes.append("printed_page_numbers_not_detected")
    if not detect_printed_pages:
        document_notes.append("printed_page_detection_disabled")
    if unclassified_heading_ids:
        document_notes.append("unclassified_headings_present")
    if source_changed:
        document_notes.append("source_changed_during_extraction")

    # Hilangkan duplikat tanpa mengubah urutan.
    document_notes = list(dict.fromkeys(document_notes))

    structure_issues = {
        "unclassified_heading_block_ids": unclassified_heading_ids,
        "paragraphs_before_first_chapter": paragraphs_before_chapter,
        "multi_column_pages": multi_column_pages,
        "printed_page_number_sources": {
            source: sum(
                1
                for page in pages
                if page.get("printed_page_number_source") == source
            )
            for source in ("pdf_page_labels", "text_sequence")
        },
    }

    table_issues = [
        {
            "block_id": block["block_id"],
            "page_number": block["page_number"],
            "review_reasons": block["table"].get("review_reasons", []),
        }
        for block in blocks
        if block["content_type"] == "table"
        and block.get("extraction_status") == "needs_manual_review"
    ]

    return {
        "pages": pages,
        "blocks": blocks,
        "document_notes": document_notes,
        "statistics": statistics,
        "structure_issues": structure_issues,
        "table_issues": table_issues,
        "repeated_lines": repeated_lines,
        "extraction_status": determine_document_status(
            pages, blocks, source_changed=source_changed
        ),
    }
