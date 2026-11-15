"""Konversi Markdown DOC002 menjadi chunk-level CSV.

Sumber tunggal adalah ``00_sumber_data/02_PenyakitTanamanPangan.md``.
Chunk dibentuk dari batas heading/tabel dan dipotong pada batas kalimat bila
melebihi ``MAX_CHUNK_CHARS``. Tidak ada parafrase: teks chunk adalah baris
sumber apa adanya.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any, Optional

TABLE_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = TABLE_DIR.parent
SOURCE_MD = PROJECT_ROOT / "00_sumber_data" / "02_PenyakitTanamanPangan.md"
PLANTS_CSV = TABLE_DIR / "auto" / "plants.csv"
OUTPUT_DIR = TABLE_DIR / "auto" / "DOC002_md"
OUTPUT_CSV = OUTPUT_DIR / "DOC002_md_chunks.csv"

DOCUMENT_ID = "DOC002"
MAX_CHUNK_CHARS = 2200

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
NUMBER_RE = re.compile(r"^(\d+(?:\.\d+)+)\.?\s+(.*)$")
BAB_RE = re.compile(r"^Bab\s+(\d+)\b", re.I)


COLUMNS = [
    "chunk_id",
    "document_id",
    "doc_part",
    "chapter",
    "section",
    "subsection",
    "table_title",
    "plant_name",
    "content_type",
    "line_start",
    "line_end",
    "part_index",
    "part_total",
    "char_count",
    "text_markdown",
    "source_file",
]


def clean_heading(text: str) -> str:
    return re.sub(r"\*+", "", text or "").strip()


def load_plants() -> dict[int, str]:
    plants: dict[int, str] = {}
    if not PLANTS_CSV.exists():
        return plants
    with open(PLANTS_CSV, encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            number = (row.get("chapter_number") or "").strip()
            name = (row.get("plant_name_id") or "").strip()
            if number.isdigit() and name:
                plants[int(number)] = name
    return plants


def split_long_text(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    parts: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            window = text[start:end]
            cut = window.rfind("\n")
            if cut <= max_chars // 2:
                cut = max(window.rfind(". "), window.rfind("! "), window.rfind("? "))
            if cut > max_chars // 2:
                end = start + cut + 1
            else:
                space = text.rfind(" ", start, end)
                if space > start:
                    end = space
        part = text[start:end].strip()
        if part:
            parts.append(part)
        start = end
    return parts


def read_blocks(lines: list[str]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    current: Optional[dict[str, Any]] = None

    def push(kind: str, number: int, text: str) -> None:
        nonlocal current
        if current is None or current["kind"] != kind:
            if current is not None:
                blocks.append(current)
            current = {
                "kind": kind,
                "lines": [],
                "line_start": number,
                "line_end": number,
            }
        current["lines"].append(text)
        current["line_end"] = number

    for number, raw in enumerate(lines, start=1):
        line = raw.rstrip("\r\n")
        if not line.strip():
            if current is not None:
                blocks.append(current)
                current = None
            continue
        if HEADING_RE.match(line):
            push("heading", number, line)
            blocks.append(current)  # type: ignore[arg-type]
            current = None
        elif line.lstrip().startswith("|"):
            push("table", number, line)
        else:
            push("paragraph", number, line)
    if current is not None:
        blocks.append(current)
    return blocks


class ChunkBuilder:
    def __init__(self, plants: dict[int, str], source_file: str) -> None:
        self.plants = plants
        self.source_file = source_file
        self.rows: list[dict[str, Any]] = []
        self.seq = 0
        self.buffer: list[str] = []
        self.buffer_start: Optional[int] = None
        self.buffer_end: Optional[int] = None
        self.has_heading = False
        self.has_paragraph = False
        self.has_table = False
        self.doc_part = "front_matter"
        self.chapter: Optional[str] = None
        self.chapter_number: Optional[int] = None
        self.section: Optional[str] = None
        self.subsection: Optional[str] = None
        self.table_title: Optional[str] = None
        self.plant_name: Optional[str] = None
        self.pending_chapter: Optional[int] = None
        self.pending_title = False

    def _reset_context(self) -> None:
        self.chapter = None
        self.chapter_number = None
        self.section = None
        self.subsection = None
        self.table_title = None
        self.plant_name = None
        self.pending_chapter = None
        self.pending_title = False

    def _append(self, block: dict[str, Any]) -> None:
        if self.buffer_start is None:
            self.buffer_start = int(block["line_start"])
        else:
            gap = int(block["line_start"]) - (self.buffer_end or 0) - 1
            if gap > 0:
                self.buffer.extend([""] * gap)
        self.buffer_end = int(block["line_end"])
        self.buffer.extend(block["lines"])
        if block["kind"] == "heading":
            self.has_heading = True
        elif block["kind"] == "table":
            self.has_table = True
        elif block["kind"] == "paragraph":
            self.has_paragraph = True

    def _content_type(self) -> str:
        if self.has_table:
            return "table"
        if self.doc_part in ("toc", "reference", "front_matter"):
            return self.doc_part
        if self.has_heading and self.has_paragraph:
            return "mixed"
        if self.has_paragraph:
            return "paragraph"
        return "heading"

    def _emit(self, text: str, part_index: int, part_total: int) -> None:
        self.seq += 1 if part_index == 1 else 0
        self.rows.append(
            {
                "chunk_id": f"{DOCUMENT_ID}_MD_C{self.seq:03d}_{part_index:02d}",
                "document_id": DOCUMENT_ID,
                "doc_part": self.doc_part,
                "chapter": self.chapter or "",
                "section": self.section or "",
                "subsection": self.subsection or "",
                "table_title": self.table_title or "",
                "plant_name": self.plant_name or "",
                "content_type": self._content_type(),
                "line_start": self.buffer_start,
                "line_end": self.buffer_end,
                "part_index": part_index,
                "part_total": part_total,
                "char_count": len(text),
                "text_markdown": text,
                "source_file": self.source_file,
            }
        )

    def _flush(self) -> None:
        if self.buffer_start is None or not self.buffer:
            self.buffer = []
            self.buffer_start = None
            self.buffer_end = None
            self.has_heading = False
            self.has_paragraph = False
            self.has_table = False
            return
        text = "\n".join(self.buffer).strip()
        if not text:
            self.buffer = []
            self.buffer_start = None
            self.buffer_end = None
            self.has_heading = False
            self.has_paragraph = False
            self.has_table = False
            return
        if len(text) > MAX_CHUNK_CHARS and not self.has_table:
            parts = split_long_text(text, MAX_CHUNK_CHARS)
        else:
            parts = [text]
        total = len(parts)
        for index, part in enumerate(parts, start=1):
            self._emit(part, index, total)
        self.buffer = []
        self.buffer_start = None
        self.buffer_end = None
        self.has_heading = False
        self.has_paragraph = False
        self.has_table = False

    def _update_heading(self, heading: str) -> None:
        bab = BAB_RE.match(heading)
        if bab:
            number = int(bab.group(1))
            remainder = heading[bab.end() :].strip()
            if self.doc_part in ("front_matter", "toc"):
                if remainder:
                    return
                self.doc_part = "body"
                self._reset_context()
            self.chapter_number = number
            self.chapter = f"Bab {number}"
            self.plant_name = self.plants.get(number)
            self.section = None
            self.subsection = None
            self.table_title = None
            if remainder:
                self.chapter = f"Bab {number} — {remainder}"
                self.pending_chapter = None
                self.pending_title = False
            else:
                self.pending_chapter = number
                self.pending_title = True
            return

        if self.pending_title and self.pending_chapter is not None:
            self.chapter = f"Bab {self.pending_chapter} — {heading}"
            self.plant_name = self.plants.get(self.pending_chapter)
            self.pending_title = False
            return

        lowered = heading.lower()
        if lowered.startswith("daftar isi") or lowered.startswith("daftar tabel"):
            self.doc_part = "toc"
            self._reset_context()
            return
        if lowered.startswith("daftar pustaka"):
            self.doc_part = "reference"
            self._reset_context()
            return

        if self.doc_part in ("front_matter", "toc", "reference"):
            return

        if lowered.startswith("tabel "):
            self.table_title = heading
            return

        numbered = NUMBER_RE.match(heading)
        if numbered:
            parts = numbered.group(1).split(".")
            chapter_number = int(parts[0])
            if chapter_number != self.chapter_number:
                self.chapter_number = chapter_number
                self.chapter = f"Bab {chapter_number}"
                self.plant_name = self.plants.get(chapter_number)
                self.section = None
                self.subsection = None
                self.table_title = None
            if len(parts) >= 3:
                self.subsection = heading
                parent = ".".join(parts[:2])
                if not self.section or not self.section.startswith(parent):
                    self.section = parent
            else:
                self.section = heading
                self.subsection = None
            return

        if self.section is None:
            self.section = heading
        else:
            self.subsection = heading

    def add(self, block: dict[str, Any]) -> None:
        if block["kind"] == "heading":
            if self.has_paragraph or self.has_table:
                self._flush()
            heading = clean_heading(HEADING_RE.match(block["lines"][0]).group(2))  # type: ignore[union-attr]
            self._update_heading(heading)
            self._append(block)
            return

        if block["kind"] == "table" and self.has_paragraph:
            self._flush()
        if block["kind"] == "paragraph" and self.has_table:
            self._flush()
        self._append(block)

    def finish(self) -> list[dict[str, Any]]:
        self._flush()
        return self.rows


def build_chunks(source: Path = SOURCE_MD, output: Path = OUTPUT_CSV) -> list[dict[str, Any]]:
    lines = source.read_text(encoding="utf-8").splitlines()
    plants = load_plants()
    builder = ChunkBuilder(plants, source.relative_to(PROJECT_ROOT).as_posix())
    for block in read_blocks(lines):
        builder.add(block)
    rows = builder.finish()
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return rows


def main() -> int:
    rows = build_chunks()
    by_type: dict[str, int] = {}
    by_part: dict[str, int] = {}
    for row in rows:
        by_type[row["content_type"]] = by_type.get(row["content_type"], 0) + 1
        by_part[row["doc_part"]] = by_part.get(row["doc_part"], 0) + 1
    print(f"chunks: {len(rows)}")
    print(f"content_type: {dict(sorted(by_type.items()))}")
    print(f"doc_part: {dict(sorted(by_part.items()))}")
    print(f"output: {OUTPUT_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
