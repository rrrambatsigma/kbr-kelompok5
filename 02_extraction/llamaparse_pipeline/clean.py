"""Pembersihan konservatif dan util teks untuk keluaran LlamaParse.

Prinsip: hanya membuang noise layout (spasi berlebih, nomor halaman berdiri
sendiri, header/footer yang sudah dipisahkan parser) dan tidak pernah
mengubah istilah, angka, atau tanda baca ilmiah.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Iterable, Optional


PAGE_NUMBER_LINE_RE = re.compile(r"^(?:hal(?:aman)?\.?\s*)?[-–—]?\s*(\d{1,4})\s*[-–—]?$", re.IGNORECASE)
ROMAN_PAGE_RE = re.compile(r"^[ivxlcdm]{1,7}$", re.IGNORECASE)
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]+\)")
MARKDOWN_EMPHASIS_RE = re.compile(r"(\*{1,3}|_{1,3})(?=\S)(.+?)(?<=\S)\1", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`([^`]+)`")
MERGED_HEADER_RE = re.compile(
    r"^((?:BAB|BAGIAN)\s+(?:\d+|[IVXLCDM]+)\s+.{3,70}?)\s+(\d{1,4})\s+(?=\S)",
    re.IGNORECASE,
)
HTML_TAG_RE = re.compile(
    r"</?(?:u|b|i|em|strong|sup|sub|span|br|p|div|table|thead|tbody|tr|td|th"
    r"|ul|ol|li|a|h[1-6]|img|code|pre|blockquote)\b[^>]*>",
    re.IGNORECASE,
)


def normalize_unicode(text: str) -> str:
    return unicodedata.normalize("NFC", text or "")


def collapse_whitespace(text: str) -> str:
    return re.sub(r"[ \t\u00a0]+", " ", text or "").strip()


def clean_block_text(text: Optional[str]) -> tuple[str, list[str]]:
    """Membersihkan teks blok dan mencatat aksi yang dilakukan."""

    actions: list[str] = []
    if not text:
        return "", actions

    normalized = normalize_unicode(text)
    if normalized != text:
        actions.append("normalized_unicode_nfc")

    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    if "\n" in normalized:
        actions.append("normalized_line_breaks")
        normalized = " ".join(part.strip() for part in normalized.split("\n"))

    collapsed = collapse_whitespace(normalized)
    if collapsed != normalized.strip():
        actions.append("collapsed_whitespace")

    return collapsed, actions


def strip_syntax(text: str) -> tuple[str, bool]:
    """Membuang sintaks markdown/HTML dari teks blok, bukan isinya.

    Tautan dipertahankan sebagai labelnya; tag HTML seperti ``<u>`` dibuang.
    Polaritas angka ("<30 °C") tidak tersentuh karena hanya tag bernama yang
    dikenali.
    """

    value = text or ""
    original = value
    value = MARKDOWN_IMAGE_RE.sub(" ", value)
    value = MARKDOWN_LINK_RE.sub(r"\1", value)
    value = INLINE_CODE_RE.sub(r"\1", value)
    value = HTML_TAG_RE.sub(" ", value)
    value = re.sub(r"^\s{0,3}#{1,6}\s+", "", value, flags=re.MULTILINE)
    return value, value != original


def strip_markdown(text: str) -> str:
    """Membuang sintaks markdown untuk perbandingan teks, bukan untuk output."""

    value = MARKDOWN_IMAGE_RE.sub(" ", text or "")
    value = MARKDOWN_LINK_RE.sub(r"\1", value)
    value = INLINE_CODE_RE.sub(r"\1", value)
    value = MARKDOWN_EMPHASIS_RE.sub(r"\2", value)
    value = re.sub(r"[*`]", "", value)
    value = HTML_TAG_RE.sub(" ", value)
    value = value.replace("|", " ")
    value = re.sub(r"^[#>\-\s]+", "", value, flags=re.MULTILINE)
    return re.sub(r"\s+", " ", value).strip()


def strip_emphasis(text: str) -> tuple[str, bool]:
    """Membuang penanda tebal/miring markdown tanpa mengubah kata di dalamnya."""

    value = INLINE_CODE_RE.sub(r"\1", text or "")
    previous = None
    while previous != value:
        previous = value
        value = MARKDOWN_EMPHASIS_RE.sub(r"\2", value)
    changed = value != text
    return value, changed


def substance_tokens(text: str) -> list[str]:
    """Token yang tidak boleh berubah karena cleaning.

    Hanya huruf dan angka yang dipertahankan; spasi dan tanda baca diabaikan
    karena keduanya memang boleh dinormalisasi.
    """

    return re.findall(r"[0-9A-Za-zÀ-ÖØ-öø-ÿ]+", normalize_unicode(text).lower())


def is_standalone_page_number(text: str) -> bool:
    value = collapse_whitespace(text)
    return bool(PAGE_NUMBER_LINE_RE.match(value))


def line_template(text: str) -> str:
    """Template baris untuk mendeteksi running header/footer.

    Angka diganti ``#`` agar header yang memuat nomor halaman tetap dikenali
    sebagai baris yang sama.
    """

    value = collapse_whitespace(normalize_unicode(text)).lower()
    value = re.sub(r"\d+", "#", value)
    value = re.sub(r"[^0-9a-zà-ÿ# ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def edge_templates(page_texts: list[str], min_ratio: float = 0.25) -> set[str]:
    """Mengumpulkan template baris yang muncul di tepi banyak halaman."""

    counts: dict[str, int] = {}
    for text in page_texts:
        lines = [line for line in (text or "").split("\n") if line.strip()]
        candidates = lines[:2] + lines[-2:]
        seen = {line_template(line) for line in candidates if line.strip()}
        for template in seen:
            counts[template] = counts.get(template, 0) + 1

    if not page_texts:
        return set()
    threshold = max(3, int(len(page_texts) * min_ratio))
    return {
        template
        for template, count in counts.items()
        if count >= threshold and (len(template) >= 12 or re.search(r"\d|#", template))
    }


def parse_printed_page_number(value: Any) -> tuple[Optional[int], Optional[str]]:
    """Mengubah nomor halaman cetak parser menjadi int + tipe sumber."""

    if value is None:
        return None, None
    text = collapse_whitespace(str(value))
    if not text:
        return None, None
    digits = re.sub(r"[^0-9]", "", text)
    if digits and len(digits) <= 4:
        return int(digits), "arabic"
    if ROMAN_PAGE_RE.match(text):
        return None, f"roman:{text.lower()}"
    return None, "unparsed"


def looks_like_running_edge(text: str, edges: Iterable[Optional[str]]) -> bool:
    """True bila teks identik dengan header/footer halaman menurut parser."""

    candidate = collapse_whitespace(text).lower()
    if not candidate:
        return False
    for edge in edges:
        if not edge:
            continue
        if collapse_whitespace(edge).lower() == candidate:
            return True
    return False


def is_running_edge_line(text: str, bbox: Any, page_height: float) -> bool:
    """Deteksi header/footer yang memuat nomor halaman pada posisi tepi."""

    if bbox is None or not page_height:
        return False
    try:
        y0 = float(bbox[1])
        y1 = float(bbox[3])
    except (TypeError, ValueError, IndexError):
        return False

    at_edge = y0 <= 95.0 or y1 >= page_height - 75.0
    if not at_edge:
        return False

    value = collapse_whitespace(text)
    if not value or len(value) > 110:
        return False
    if value.startswith("Gambar ") or value.startswith("Tabel "):
        return False

    if re.match(r"^(BAB|BAGIAN|CHAPTER)\b", value, re.IGNORECASE) and re.search(
        r"\d{1,4}\s*$", value
    ):
        return True
    if re.match(r"^\d{1,4}\s+\S", value):
        return True
    if re.match(r"^[A-Za-zÀ-ÿ].{10,}\s\d{1,4}$", value):
        return True
    return False


def detect_layout_conflict(items: list[dict[str, Any]]) -> bool:
    """True bila area tabel bertumpuk dengan blok teks (indikasi salah baca)."""

    tables = [
        edges
        for edges in (bbox_edges(item.get("bbox")) for item in items if item.get("type") == "table")
        if edges
    ]
    if not tables:
        return False

    texts = [
        edges
        for edges in (
            bbox_edges(item.get("bbox"))
            for item in items
            if item.get("type") in {"text", "heading"}
        )
        if edges
    ]

    for table in tables:
        table_area = max(table[2] - table[0], 0.0) * max(table[3] - table[1], 0.0)
        if table_area <= 0:
            continue
        for text in texts:
            width = max(min(table[2], text[2]) - max(table[0], text[0]), 0.0)
            height = max(min(table[3], text[3]) - max(table[1], text[1]), 0.0)
            if width * height / table_area >= 0.5:
                return True
    return False


def split_merged_running_header(
    text: str,
    bbox: Any,
    page_height: float,
) -> tuple[str, Optional[str]]:
    """Memisahkan running header yang tergabung ke paragraf (tier ``fast``).

    Hanya dilakukan pada blok di tepi atas halaman dan hanya bila polanya
    benar-benar header bab dengan nomor halaman.
    """

    edges = bbox_edges(bbox)
    if edges is None or not page_height or edges[1] > 95.0:
        return text, None

    value = collapse_whitespace(text)
    if len(value) < 120:
        return text, None

    match = MERGED_HEADER_RE.match(value)
    if not match:
        return text, None

    heading = match.group(1).strip(" .:;-–—")
    remainder = value[match.end() :].strip()
    if len(remainder) < 80 or not heading:
        return text, None
    return remainder, heading


LEADING_PAGE_NUMBER_RE = re.compile(r"^(\d{1,4})\s+\S")
TRAILING_PAGE_NUMBER_RE = re.compile(r"\S\s+(\d{1,4})\s*$")


def derive_printed_page_number(
    header: Optional[str], footer: Optional[str]
) -> tuple[Optional[int], Optional[str], Optional[str]]:
    """Mengambil nomor halaman cetak dari header/footer yang sudah dipisah parser.

    Mengembalikan ``(nomor, sumber, teks_asli)``; tidak menebak bila tidak ada
    pola angka yang jelas.
    """

    for source, value in (("header", header), ("footer", footer)):
        if not value:
            continue
        text = collapse_whitespace(value)
        for pattern in (LEADING_PAGE_NUMBER_RE, TRAILING_PAGE_NUMBER_RE):
            match = pattern.search(text)
            if match:
                number = int(match.group(1))
                if 1 <= number <= 9999:
                    return number, source, text
    return None, None, None


def bbox_area(bbox: Any) -> float:
    if not bbox:
        return 0.0
    if isinstance(bbox, dict):
        width = float(bbox.get("w") or 0)
        height = float(bbox.get("h") or 0)
        return max(width, 0.0) * max(height, 0.0)
    if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
        x0, y0, x1, y1 = (float(value) for value in bbox)
        return max(x1 - x0, 0.0) * max(y1 - y0, 0.0)
    return 0.0


def bbox_edges(bbox: Any) -> Optional[tuple[float, float, float, float]]:
    """Mengubah bbox dict LlamaParse atau list empat angka menjadi tuple tepi."""

    if isinstance(bbox, list) and bbox and isinstance(bbox[0], dict):
        parts = [bbox_edges(item) for item in bbox]
        parts = [part for part in parts if part]
        if not parts:
            return None
        return (
            min(part[0] for part in parts),
            min(part[1] for part in parts),
            max(part[2] for part in parts),
            max(part[3] for part in parts),
        )
    if isinstance(bbox, dict) and {"x", "y", "w", "h"} <= set(bbox):
        x = float(bbox.get("x") or 0)
        y = float(bbox.get("y") or 0)
        w = float(bbox.get("w") or 0)
        h = float(bbox.get("h") or 0)
        return (x, y, x + w, y + h)
    if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
        try:
            values = tuple(float(value) for value in bbox)
        except (TypeError, ValueError):
            return None
        return values  # type: ignore[return-value]
    return None


def detect_possible_multi_column(items: list[dict[str, Any]]) -> bool:
    """Heuristik sederhana: dua kolom teks yang tumpang tindih secara vertikal."""

    boxes: list[tuple[float, float, float, float]] = []
    for item in items:
        if item.get("type") not in {"text", "list"}:
            continue
        edges = bbox_edges(item.get("bbox"))
        if edges is None:
            continue
        x0, y0, x1, y1 = edges
        if x1 > x0 and y1 > y0:
            boxes.append((x0, y0, x1, y1))

    if len(boxes) < 4:
        return False

    overlaps = 0
    for index, first in enumerate(boxes):
        for second in boxes[index + 1 :]:
            vertical = min(first[3], second[3]) - max(first[1], second[1])
            horizontal_gap = max(first[0], second[0]) - min(first[2], second[2])
            if vertical > 0 and horizontal_gap > 0:
                overlaps += 1
    return overlaps >= 2
