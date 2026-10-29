"""Pembangun knowledge table DOC002 (Tahap 2).

Input bersifat read-only: ``02_extraction/extracted_text/DOC002.chunks.jsonl``
dan ``DOC002.blocks.jsonl``. Tidak ada proses yang menulis balik ke Tahap 1.

Aturan utama:
- Setiap teks yang masuk tabel harus muncul verbatim di chunk yang dirujuk.
- Field yang tidak tersedia di sumber dibiarkan kosong, bukan ditebak.
- Struktur bab yang berbeda ditangani lewat ``config/chapter_map.json``.

Jalankan: ``python 03_knowledge_tables/build_knowledge_tables.py``
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any, Iterable, Optional

TABLE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TABLE_DIR.parent
EXTRACTION_DIR = PROJECT_ROOT / "02_extraction" / "extracted_text"

CHUNKS_PATH = EXTRACTION_DIR / "DOC002.chunks.jsonl"
BLOCKS_PATH = EXTRACTION_DIR / "DOC002.blocks.jsonl"
CONFIG_PATH = TABLE_DIR / "config" / "chapter_map.json"

AUTO_DIR = TABLE_DIR / "auto"
REVIEW_DIR = TABLE_DIR / "review"
REPORTS_DIR = TABLE_DIR / "reports"

PLANT_COLUMNS = [
    "plant_id",
    "plant_name_id",
    "plant_name_en",
    "scientific_name",
    "scientific_name_page",
    "chapter_number",
    "chapter_title",
    "page_start",
    "page_end",
    "evidence_chunk_id",
]

DISEASE_COLUMNS = [
    "disease_id",
    "plant_id",
    "disease_name_verbatim",
    "disease_name_key",
    "name_en_verbatim",
    "chapter_title",
    "heading_level",
    "section",
    "subsection",
    "page_start",
    "page_end",
    "evidence_chunk_ids",
    "source_block_ids",
    "review_status",
    "notes",
]

WS_RE = re.compile(r"\s+")
NUMBERING_RE = re.compile(r"^\s*\d+(?:\.\d+)*\.?\s*")
NUMBERED_HEADING_RE = re.compile(r"^\s*\d+\.\d+(?:\.\d+)*\.?\s+\S")

# Heading grup: membawahi beberapa penyakit, bukan penyakit itu sendiri.
GROUP_PATTERNS = [
    re.compile(r"^pendahuluan$", re.IGNORECASE),
    re.compile(
        r"^penyakit(\s+tanaman)?\s+(padi|kedelai|kacang tanah|ubi jalar|ubi kayu|"
        r"jagung|kentang|kubis|cabai|tomat|kacang panjang|apel|lada|kopi|kelapa sawit)$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^penyakit\s+\w+\s+oleh\s+(jamur|bakteri|virus)$",
        re.IGNORECASE,
    ),
    re.compile(r"^arti penting\b", re.IGNORECASE),
    re.compile(r"^macam-macam\b", re.IGNORECASE),
    re.compile(r"^patogen pada\b", re.IGNORECASE),
    re.compile(r"^penyakit pada (daun|batang|akar)\b", re.IGNORECASE),
    re.compile(r"^deskripsi$", re.IGNORECASE),
]

COMPONENT_RE = re.compile(r"\b(penyebab|gejala|pengendalian)\b", re.IGNORECASE)

# Kata yang menandai nama penyakit berbahasa Inggris di dalam tanda kurung.
EN_MARKERS = {
    "mildew",
    "blight",
    "spot",
    "rot",
    "virus",
    "mottle",
    "stunt",
    "damping",
    "rust",
    "wilt",
    "leaf",
    "fruit",
    "bacterial",
    "mosaic",
    "downy",
    "powdery",
    "frogeye",
    "cowpea",
    "soybean",
    "ring",
    "canker",
    "anthracnose",
}


def norm(text: str) -> str:
    """Normalisasi spasi saja; kata dan tanda baca tidak diubah."""

    return WS_RE.sub(" ", str(text or "")).strip()


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(text or "").lower()).strip("_")


def strip_numbering(text: str) -> str:
    return NUMBERING_RE.sub("", str(text or "")).strip()


def is_group_heading(name: str) -> bool:
    return any(pattern.search(name) for pattern in GROUP_PATTERNS)


def is_component_heading(name: str) -> bool:
    return bool(COMPONENT_RE.search(name))


def split_parenthetical(name: str) -> tuple[str, list[str]]:
    """Pisahkan nama dari isi tanda kurung, urutan dipertahankan."""

    parts = re.findall(r"\(([^()]*)\)", name)
    base = re.sub(r"\s*\([^()]*\)", "", name).strip()
    return base, [part.strip() for part in parts]


def classify_parenthetical(value: str) -> str:
    """Tentukan peran isi kurung: nama Inggris, nama ilmiah, sitasi, atau lain."""

    if not value:
        return "empty"
    low = value.lower()
    if re.search(r"\bet al\b|\d{4}|,", low):
        return "citation"
    words = re.findall(r"[A-Za-z][A-Za-z-]+", value)
    if not words:
        return "other"
    if any(word.lower() in EN_MARKERS for word in words):
        return "en"
    if len(words) >= 2 and words[0][:1].isupper() and words[1][:1].islower():
        return "scientific"
    if len(words) == 1:
        return "other"
    return "en" if all(word.isascii() for word in words) else "other"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def write_csv(path: Path, rows: Iterable[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column) for column in columns})


def chapter_chunks(chunks: list[dict[str, Any]], chapter_title: str) -> list[dict[str, Any]]:
    return [chunk for chunk in chunks if chunk.get("chapter") == chapter_title]


def build_plants(
    config: dict[str, Any], chunks: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    problems: list[dict[str, Any]] = []
    chunk_by_id = {chunk["chunk_id"]: chunk for chunk in chunks}

    for chapter in config["chapters"]:
        scoped = chapter_chunks(chunks, chapter["chapter_title"])
        if not scoped:
            problems.append(
                {
                    "record_id": chapter["plant_id"],
                    "field": "chapter_chunks",
                    "reason": "chapter_has_no_chunks",
                    "candidate_text": chapter["chapter_title"],
                    "page": None,
                    "chunk_id": None,
                }
            )
            continue

        evidence = chapter.get("scientific_name_chunk_id")
        scientific_name = chapter.get("scientific_name")
        if scientific_name:
            if not evidence:
                problems.append(
                    {
                        "record_id": chapter["plant_id"],
                        "field": "scientific_name",
                        "reason": "missing_evidence_chunk",
                        "candidate_text": scientific_name,
                        "page": None,
                        "chunk_id": None,
                    }
                )
                scientific_name = None
            else:
                chunk = chunk_by_id.get(evidence)
                if chunk is None or norm(scientific_name) not in norm(chunk["plain_text"]):
                    problems.append(
                        {
                            "record_id": chapter["plant_id"],
                            "field": "scientific_name",
                            "reason": "not_verbatim_in_source",
                            "candidate_text": scientific_name,
                            "page": chapter.get("scientific_name_page"),
                            "chunk_id": evidence,
                        }
                    )
                    scientific_name = None
                    evidence = None
        else:
            evidence = None

        if evidence is None:
            evidence = min(scoped, key=lambda item: item["page_start"])["chunk_id"]

        rows.append(
            {
                "plant_id": chapter["plant_id"],
                "plant_name_id": chapter["plant_name_id"],
                "plant_name_en": chapter.get("plant_name_en") or "",
                "scientific_name": scientific_name or "",
                "scientific_name_page": chapter.get("scientific_name_page") or "",
                "chapter_number": chapter["chapter_number"],
                "chapter_title": chapter["chapter_title"],
                "page_start": chapter["page_start"],
                "page_end": chapter["page_end"],
                "evidence_chunk_id": evidence,
            }
        )
    return rows, problems


def heading_value(chunk: dict[str, Any], level: str) -> str:
    return str(chunk.get(level) or "").strip()


def collect_headings(
    scoped: list[dict[str, Any]], level: str
) -> list[tuple[str, list[dict[str, Any]]]]:
    """Kumpulkan heading unik pada satu level, urutan sesuai dokumen."""

    order: list[str] = []
    grouped: dict[str, list[dict[str, Any]]] = {}
    for chunk in scoped:
        raw = heading_value(chunk, level)
        if not raw or not NUMBERED_HEADING_RE.match(raw):
            continue
        if raw not in grouped:
            order.append(raw)
            grouped[raw] = []
        grouped[raw].append(chunk)
    return [(raw, grouped[raw]) for raw in order]


def build_diseases(
    config: dict[str, Any],
    chunks: list[dict[str, Any]],
    blocks: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    problems: list[dict[str, Any]] = []
    table_rows: list[dict[str, Any]] = []
    block_by_id = {block["block_id"]: block for block in blocks}

    for chapter in config["chapters"]:
        scoped = chapter_chunks(chunks, chapter["chapter_title"])
        level = chapter["disease_heading_level"]
        style = chapter["heading_style"]
        seen_keys: set[str] = set()

        if level == "table":
            groups = chapter.get("table_groups") or []
            for group in groups:
                parsed = parse_table_group(group, block_by_id)
                table_rows.extend(parsed)
                for item in parsed:
                    if item.get("status") == "continuation":
                        continue
                    key = slug(item["disease_name"])
                    if not key or key in seen_keys:
                        continue
                    seen_keys.add(key)
                    rows.append(
                        {
                            "disease_id": "",
                            "plant_id": chapter["plant_id"],
                            "disease_name_verbatim": item["disease_name"],
                            "disease_name_key": key,
                            "name_en_verbatim": "",
                            "chapter_title": chapter["chapter_title"],
                            "heading_level": "table",
                            "section": group["table_id"],
                            "subsection": item.get("table_title") or "",
                            "page_start": item["page"],
                            "page_end": item["page"],
                            "evidence_chunk_ids": "",
                            "source_block_ids": item["source_block_id"],
                            "review_status": "needs_review",
                            "notes": "from_table_5; struktur tabel terpotong antar halaman",
                        }
                    )
            continue

        headings = collect_headings(scoped, level)
        for raw, heading_chunks in headings:
            name = strip_numbering(raw)
            if not name:
                continue
            if is_group_heading(name) or is_component_heading(name):
                continue

            key = slug(name)
            if key in seen_keys:
                problems.append(
                    {
                        "record_id": f"{chapter['plant_id']}::{key}",
                        "field": "disease_name",
                        "reason": "duplicate_heading",
                        "candidate_text": name,
                        "page": heading_chunks[0]["page_start"],
                        "chunk_id": heading_chunks[0]["chunk_id"],
                    }
                )
                continue
            seen_keys.add(key)

            pages = [chunk["page_start"] for chunk in heading_chunks]
            section = (
                name
                if level == "section"
                else str(heading_chunks[0].get("section") or name)
            )
            subsection = "" if level == "section" else name

            if style == "pathogen":
                rows.append(
                    {
                        "disease_id": "",
                        "plant_id": chapter["plant_id"],
                        "disease_name_verbatim": "",
                        "disease_name_key": key,
                        "name_en_verbatim": "",
                        "chapter_title": chapter["chapter_title"],
                        "heading_level": level,
                        "section": section,
                        "subsection": subsection,
                        "page_start": min(pages),
                        "page_end": max(pages),
                        "evidence_chunk_ids": ";".join(
                            chunk["chunk_id"] for chunk in heading_chunks
                        ),
                        "source_block_ids": "",
                        "review_status": "needs_curation",
                        "notes": f"heading berisi nama patogen: {name}",
                    }
                )
                continue

            base, parentheses = split_parenthetical(name)
            name_en = ""
            extra_notes: list[str] = []
            for value in parentheses:
                kind = classify_parenthetical(value)
                if kind == "en" and not name_en:
                    name_en = value
                elif kind == "scientific":
                    extra_notes.append(f"nama ilmiah dalam heading: {value}")
            review = "needs_review" if len(base) < 10 else "auto_ok"

            rows.append(
                {
                    "disease_id": "",
                    "plant_id": chapter["plant_id"],
                    "disease_name_verbatim": name,
                    "disease_name_key": key,
                    "name_en_verbatim": name_en,
                    "chapter_title": chapter["chapter_title"],
                    "heading_level": level,
                    "section": section,
                    "subsection": subsection,
                    "page_start": min(pages),
                    "page_end": max(pages),
                    "evidence_chunk_ids": ";".join(
                        chunk["chunk_id"] for chunk in heading_chunks
                    ),
                    "source_block_ids": "",
                    "review_status": review,
                    "notes": "; ".join(extra_notes),
                }
            )

    rows.sort(key=lambda row: (row["plant_id"], row["page_start"], row["section"]))
    for index, row in enumerate(rows, start=1):
        row["disease_id"] = f"DIS_{index:03d}"
    return rows, problems, table_rows


def parse_table_group(
    group: dict[str, Any], block_by_id: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Baca satu grup tabel, gabungkan baris lanjutan, catat nomor yang hilang."""

    rows: list[dict[str, Any]] = []
    current: Optional[dict[str, Any]] = None

    def blank(value: Any) -> str:
        return "" if value is None else str(value).strip()

    for block_id in group["block_ids"]:
        block = block_by_id.get(block_id)
        if block is None:
            continue
        table = block.get("table") or {}
        for cells in table.get("cells") or []:
            if not isinstance(cells, list):
                continue
            padded = [blank(cell) for cell in cells[:4]]
            while len(padded) < 4:
                padded.append("")
            number, disease, pathogen, symptom = padded
            if disease.lower().startswith("penyakit tanaman") or number.lower() == "no.":
                continue
            if not number and not disease and not pathogen and not symptom:
                continue
            if not number and not disease and current is not None:
                # Baris lanjutan dari sel yang terpotong halaman.
                if pathogen and not symptom:
                    current["pathogen_name"] = (
                        f"{current['pathogen_name']} {pathogen}".strip()
                    )
                elif symptom and not pathogen:
                    current["symptom_text"] = (
                        f"{current['symptom_text']} {symptom}".strip()
                    )
                continue
            current = {
                "table_id": group["table_id"],
                "table_title": group.get("title") or "",
                "row_no": number,
                "disease_name": disease or pathogen,
                "pathogen_name": pathogen,
                "symptom_text": symptom,
                "page": block.get("page_number"),
                "source_block_id": block_id,
                "status": "complete" if number else "unnumbered",
                "note": "",
            }
            rows.append(current)

    numbered = [int(row["row_no"]) for row in rows if row["row_no"].isdigit()]
    if numbered:
        expected = range(1, max(numbered) + 1)
        for missing in sorted(set(expected) - set(numbered)):
            rows.append(
                {
                    "table_id": group["table_id"],
                    "table_title": group.get("title") or "",
                    "row_no": str(missing),
                    "disease_name": "",
                    "pathogen_name": "",
                    "symptom_text": "",
                    "page": "",
                    "source_block_id": "",
                    "status": "missing_row",
                    "note": "nomor baris tidak tercetak di sumber",
                }
            )
    return rows


def verify_verbatim(
    rows: list[dict[str, Any]], chunks: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Pastikan setiap nama penyakit muncul di chunk bukti yang dirujuk."""

    chunk_by_id = {chunk["chunk_id"]: norm(chunk["plain_text"]) for chunk in chunks}
    violations: list[dict[str, Any]] = []
    for row in rows:
        name = row["disease_name_verbatim"]
        if not name:
            continue
        evidence = [item for item in row["evidence_chunk_ids"].split(";") if item]
        if not evidence:
            continue
        if not any(norm(name) in chunk_by_id.get(item, "") for item in evidence):
            violations.append(
                {
                    "record_id": row["disease_id"],
                    "field": "disease_name_verbatim",
                    "reason": "not_verbatim_in_evidence",
                    "candidate_text": name,
                    "page": row["page_start"],
                    "chunk_id": row["evidence_chunk_ids"],
                }
            )
    return violations


def write_report(
    plants: list[dict[str, Any]],
    diseases: list[dict[str, Any]],
    problems: list[dict[str, Any]],
    table_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    by_plant: dict[str, int] = {}
    for row in diseases:
        by_plant[row["plant_id"]] = by_plant.get(row["plant_id"], 0) + 1

    statuses: dict[str, int] = {}
    for row in diseases:
        statuses[row["review_status"]] = statuses.get(row["review_status"], 0) + 1

    table_status: dict[str, int] = {}
    for row in table_rows:
        table_status[row["status"]] = table_status.get(row["status"], 0) + 1

    report = {
        "generated_by": "build_knowledge_tables.py",
        "plant_rows": len(plants),
        "disease_rows": len(diseases),
        "table_rows": len(table_rows),
        "diseases_by_plant": by_plant,
        "review_status": statuses,
        "table_status": table_status,
        "problems": problems,
    }
    (REPORTS_DIR / "build_report.json").parent.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "build_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    lines = [
        "# Build report — knowledge tables DOC002",
        "",
        f"- Baris tanaman: **{len(plants)}**",
        f"- Baris penyakit: **{len(diseases)}**",
        f"- Baris tabel ubi kayu: **{len(table_rows)}**",
        f"- Catatan masalah: **{len(problems)}**",
        "",
        "## Penyakit per tanaman",
        "",
        "| plant_id | jumlah |",
        "|---|---|",
    ]
    for plant_id in sorted(by_plant):
        lines.append(f"| {plant_id} | {by_plant[plant_id]} |")
    lines += ["", "## Status review", "", "| status | jumlah |", "|---|---|"]
    for status, count in sorted(statuses.items()):
        lines.append(f"| {status} | {count} |")
    (REPORTS_DIR / "build_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main() -> int:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    chunks = read_jsonl(CHUNKS_PATH)
    blocks = read_jsonl(BLOCKS_PATH)

    plants, plant_problems = build_plants(config, chunks)
    diseases, problems, table_rows = build_diseases(config, chunks, blocks)
    violations = verify_verbatim(diseases, chunks)
    problems = plant_problems + problems + violations

    write_csv(AUTO_DIR / "plants.csv", plants, PLANT_COLUMNS)
    write_csv(AUTO_DIR / "diseases.csv", diseases, DISEASE_COLUMNS)
    write_csv(
        AUTO_DIR / "ubi_kayu_table_rows.csv",
        table_rows,
        [
            "table_id",
            "table_title",
            "row_no",
            "disease_name",
            "pathogen_name",
            "symptom_text",
            "page",
            "source_block_id",
            "status",
            "note",
        ],
    )
    if problems:
        write_csv(
            REVIEW_DIR / "build_problems.csv",
            problems,
            ["record_id", "field", "reason", "candidate_text", "page", "chunk_id"],
        )
    report = write_report(plants, diseases, problems, table_rows)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if not violations else 2


if __name__ == "__main__":
    raise SystemExit(main())
