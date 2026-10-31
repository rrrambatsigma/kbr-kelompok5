"""Ekspor Markdown kanonik dari hasil normalisasi LlamaParse.

Setiap halaman diberi penanda ``<!-- page: N -->`` agar tabel KB dapat
dirujuk kembali ke halaman PDF aslinya tanpa membuka respons API.

Isi blok diambil dari field ``text`` (sudah dibersihkan) supaya penanda
Markdown mentah dari parser tidak ikut tercetak dua kali. Tabel dirender
ulang dari ``table.rows`` agar selalu berbentuk tabel Markdown yang valid.
"""

from __future__ import annotations

from typing import Any

from pdf_pipeline.output import write_text


HEADING_PREFIX = {
    "chapter_heading": "# ",
    "section_heading": "## ",
    "subsection_heading": "### ",
    "heading_unclassified": "#### ",
}


def _cell(value: Any) -> str:
    text = " ".join(str(value or "").replace("<br/>", " ").replace("<br>", " ").split())
    return text.replace("|", "\\|")


def render_table(table: dict[str, Any] | None) -> str:
    rows = (table or {}).get("rows") or []
    rows = [row for row in rows if isinstance(row, list)]
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    padded = [
        [_cell(cell) for cell in row] + [""] * (width - len(row))
        for row in rows
    ]
    header, body = padded[0], padded[1:]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * width) + " |",
    ]
    for row in body:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def render_block(block: dict[str, Any]) -> str:
    content_type = str(block.get("content_type") or "")
    if content_type == "table":
        return render_table(block.get("table"))
    text = str(block.get("text") or block.get("raw_text") or "").strip()
    if not text:
        return ""
    prefix = HEADING_PREFIX.get(content_type, "")
    if prefix:
        return prefix + " ".join(text.split())
    return text


def render_page(page_number: int, blocks: list[dict[str, Any]]) -> str:
    lines = [f"<!-- page: {page_number} -->", ""]
    for block in blocks:
        rendered = render_block(block)
        if not rendered:
            continue
        lines.append(rendered)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_markdown(pages: list[dict[str, Any]], blocks: list[dict[str, Any]]) -> str:
    by_page: dict[int, list[dict[str, Any]]] = {}
    for block in blocks:
        by_page.setdefault(int(block.get("page_number") or 0), []).append(block)
    parts: list[str] = []
    for page in pages:
        number = int(page.get("page_number") or 0)
        page_blocks = sorted(
            by_page.get(number, []),
            key=lambda item: int(item.get("sequence_number") or 0),
        )
        parts.append(render_page(number, page_blocks))
    return "\n".join(parts)


def write_markdown(path: Any, pages: list[dict[str, Any]], blocks: list[dict[str, Any]]) -> str:
    content = build_markdown(pages, blocks)
    write_text(path, content)
    return content
