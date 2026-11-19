"""Buat chunk DOC005 dari Markdown hasil ekstraksi secara deterministik."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_MD = PROJECT_ROOT / "02_extraction" / "extracted_text" / "DOC005.md"
OUTPUT_JSONL = PROJECT_ROOT / "02_extraction" / "extracted_text" / "DOC005.chunks.jsonl"

PAGE_RE = re.compile(r"^<!--\s*page:\s*(\d+)\s*-->\s*$")
PLANT_RE = re.compile(r"^#\s+(.+?)\s*$")
DISEASE_RE = re.compile(r"^##\s+(\d+)\.\s+(.+?)\s*$")
STOP_RE = re.compile(r"^##\s+SCIENCE\b", re.IGNORECASE)

PLANTS = {
    "KEDELAI": ("Kedelai", "KEDELAI"),
    "KACANG TANAH": ("KacangTanah", "KACANG TANAH"),
    "KACANG HIJAU": ("KacangHijau", "KACANG HIJAU"),
}


def _page_before(pages: list[tuple[int, int]], index: int) -> int | None:
    value = None
    for line_index, page in pages:
        if line_index > index:
            break
        value = page
    return value


def build_chunks(source: Path = SOURCE_MD) -> list[dict]:
    text = source.read_text(encoding="utf-8").replace("\r\n", "\n")
    lines = text.splitlines()
    pages = [
        (index, int(match.group(1)))
        for index, line in enumerate(lines)
        if (match := PAGE_RE.match(line))
    ]

    headings: list[tuple[int, int, str, tuple[str, str]]] = []
    plant: tuple[str, str] | None = None
    for index, line in enumerate(lines):
        plant_match = PLANT_RE.match(line)
        if plant_match:
            plant = PLANTS.get(plant_match.group(1).strip())
            continue
        if plant is None:
            continue
        disease_match = DISEASE_RE.match(line)
        if disease_match:
            headings.append(
                (
                    index,
                    int(disease_match.group(1)),
                    disease_match.group(2).strip(),
                    plant,
                )
            )

    chunks: list[dict] = []
    for position, (start, number, title, plant_info) in enumerate(headings):
        if position + 1 < len(headings):
            end = headings[position + 1][0]
        else:
            end = len(lines)
            for index in range(start, len(lines)):
                if STOP_RE.match(lines[index]):
                    end = index
                    break

        body = "\n".join(
            "" if PAGE_RE.match(line) else line for line in lines[start:end]
        ).strip()
        page_start = _page_before(pages, start)
        page_end = _page_before(pages, end - 1)
        if page_start is None or page_end is None:
            raise ValueError(f"penanda halaman tidak ditemukan untuk {title}")

        plant_name, chapter = plant_info
        disease_name = re.sub(r"^PENYAKIT\s+", "", title, flags=re.IGNORECASE).strip()
        chunks.append(
            {
                "chunk_id": f"DOC005_C{page_start:03d}_01",
                "document_id": "DOC005",
                "chunk_type": "prose",
                "content_type": "mixed",
                "chapter": chapter,
                "section": f"{number}. {title}",
                "subsection": "",
                "plant_name": plant_name,
                "disease_name": disease_name,
                "page_start": page_start,
                "page_end": page_end,
                "text_markdown": body,
                "plain_text": body,
                "source_block_ids": [],
                "source_reference": f"DOC005 PDF hlm. {page_start}-{page_end}",
            }
        )
    return chunks


def write_chunks(chunks: list[dict], output: Path = OUTPUT_JSONL) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8", newline="") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE_MD)
    parser.add_argument("--output", type=Path, default=OUTPUT_JSONL)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Bandingkan hasil build dengan file output tanpa menulis.",
    )
    args = parser.parse_args()

    chunks = build_chunks(args.source)
    if args.check:
        current = [
            json.loads(line)
            for line in args.output.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if chunks != current:
            print(f"TIDAK SAMA: {args.output}")
            return 1
        print(f"OK: {len(chunks)} chunk sama dengan {args.output}")
        return 0

    write_chunks(chunks, args.output)
    print(f"chunks: {len(chunks)}")
    print(f"output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
