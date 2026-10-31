"""Terapkan keputusan kurasi manual ke lapisan ``auto`` (Tahap 2.2).

Input:
- ``auto/diseases.csv``, ``auto/ubi_kayu_table_rows.csv``
- ``review/curation_decisions.json`` (keputusan manusia + kutipan sumber)

Output:
- ``curated/diseases.csv``, ``curated/ubi_kayu_tabel_5.csv``
- ``review/curation_log.csv`` (satu baris per field yang berubah)

Setiap kutipan dan setiap nama yang diubah diverifikasi muncul verbatim di
chunk/blok bukti. Bila tidak, skrip berhenti dengan kode keluar 2.

Jalankan: ``python 03_knowledge_tables/curate.py``
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path
from typing import Any

TABLE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TABLE_DIR.parent
EXTRACTION_DIR = PROJECT_ROOT / "02_extraction" / "extracted_text"

CHUNKS_PATH = EXTRACTION_DIR / "DOC002.chunks.jsonl"
BLOCKS_PATH = EXTRACTION_DIR / "DOC002.blocks.jsonl"

AUTO_DIR = TABLE_DIR / "auto"
CURATED_DIR = TABLE_DIR / "curated"
REVIEW_DIR = TABLE_DIR / "review"
DECISIONS_PATH = REVIEW_DIR / "curation_decisions.json"

VERBATIM_FIELDS = {"disease_name_verbatim", "name_en_verbatim"}

LOG_COLUMNS = [
    "record_type",
    "record_id",
    "field",
    "old_value",
    "new_value",
    "evidence_ref",
    "evidence_quote",
    "reason",
]

WS_RE = re.compile(r"\s+")


def norm(text: Any) -> str:
    return WS_RE.sub(" ", str(text or "")).strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column) for column in columns})


def evidence_text(chunks: dict[str, str], blocks: dict[str, str], ref: str) -> str:
    if ref in chunks:
        return chunks[ref]
    return blocks.get(ref, "")


def main() -> int:
    decisions = json.loads(DECISIONS_PATH.read_text(encoding="utf-8"))

    chunks = {
        row["chunk_id"]: norm(row["plain_text"]) for row in read_jsonl(CHUNKS_PATH)
    }
    blocks: dict[str, str] = {}
    for block in read_jsonl(BLOCKS_PATH):
        cells: list[str] = []
        table = block.get("table") or {}
        for row in table.get("cells") or []:
            if isinstance(row, list):
                cells.extend(norm(cell) for cell in row if cell)
        blocks[block["block_id"]] = " | ".join(cells)

    diseases_path = AUTO_DIR / "diseases.csv"
    rows = read_csv(diseases_path)
    columns = list(rows[0].keys())
    by_id = {row["disease_id"]: row for row in rows}

    log: list[dict[str, str]] = []
    problems: list[str] = []

    for decision in decisions["decisions"]:
        record_id = decision["record_id"]
        if decision["record_type"] != "disease":
            problems.append(f"{record_id}: record_type tidak dikenal")
            continue
        row = by_id.get(record_id)
        if row is None:
            problems.append(f"{record_id}: tidak ada di auto/diseases.csv")
            continue

        ref = decision["evidence_ref"]
        quote = decision["evidence_quote"]
        source = evidence_text(chunks, blocks, ref)
        if not source:
            problems.append(f"{record_id}: bukti {ref} tidak ditemukan")
            continue
        if norm(quote) not in source:
            problems.append(f"{record_id}: kutipan tidak verbatim di {ref}")
            continue

        for field, new_value in decision["changes"].items():
            if field not in columns:
                problems.append(f"{record_id}: kolom {field} tidak ada di CSV")
                continue
            old_value = row.get(field, "")
            if norm(old_value) == norm(new_value):
                continue
            if field in VERBATIM_FIELDS and norm(new_value):
                if norm(new_value) not in source:
                    problems.append(
                        f"{record_id}: nilai baru {field} tidak verbatim di {ref}"
                    )
                    continue
            row[field] = new_value
            log.append(
                {
                    "record_type": decision["record_type"],
                    "record_id": record_id,
                    "field": field,
                    "old_value": old_value,
                    "new_value": new_value,
                    "evidence_ref": ref,
                    "evidence_quote": quote,
                    "reason": decision["reason"],
                }
            )

    if problems:
        for problem in problems:
            print(f"GAGAL: {problem}", file=sys.stderr)
        return 2

    # Baris yang sengaja ditambahkan lewat kurasi (mis. baris tabel yang
    # digabung oleh deduplikasi otomatis karena namanya sama).
    for addition in decisions.get("additions", []):
        ref = addition["evidence_ref"]
        quote = addition["evidence_quote"]
        source = evidence_text(chunks, blocks, ref)
        if not source:
            problems.append(f"addition: bukti {ref} tidak ditemukan")
            continue
        if norm(quote) not in source:
            problems.append(f"addition: kutipan tidak verbatim di {ref}")
            continue
        key = (addition["plant_id"], addition["section"], addition["disease_name_key"])
        if any(
            (row["plant_id"], row["section"], row["disease_name_key"]) == key
            for row in rows
        ):
            problems.append(f"addition: {key} sudah ada")
            continue
        next_number = max(int(row["disease_id"].split("_")[1]) for row in rows) + 1
        new_id = f"DIS_{next_number:03d}"
        row = {column: addition.get(column, "") for column in columns}
        row["disease_id"] = new_id
        row["review_status"] = "verified"
        rows.append(row)
        log.append(
            {
                "record_type": "disease",
                "record_id": new_id,
                "field": "disease_id",
                "old_value": "",
                "new_value": addition["disease_name_verbatim"],
                "evidence_ref": ref,
                "evidence_quote": quote,
                "reason": addition["reason"],
            }
        )

    if problems:
        for problem in problems:
            print(f"GAGAL: {problem}", file=sys.stderr)
        return 2

    remaining = [
        row["disease_id"]
        for row in rows
        if row["review_status"] not in {"verified", "auto_ok"}
    ]

    write_csv(CURATED_DIR / "diseases.csv", rows, columns)

    table_rows = read_csv(AUTO_DIR / "ubi_kayu_table_rows.csv")
    table_columns = list(table_rows[0].keys())
    write_csv(CURATED_DIR / "ubi_kayu_tabel_5.csv", table_rows, table_columns)

    for row in table_rows:
        if row["status"] == "missing_row":
            log.append(
                {
                    "record_type": "table_row",
                    "record_id": f"{row['table_id']}#{row['row_no']}",
                    "field": "status",
                    "old_value": "",
                    "new_value": "missing_row",
                    "evidence_ref": "",
                    "evidence_quote": "",
                    "reason": "nomor baris tidak tercetak di sumber; tidak diisi",
                }
            )

    write_csv(REVIEW_DIR / "curation_log.csv", log, LOG_COLUMNS)

    summary = {
        "curation_round": decisions.get("curation_round"),
        "decisions": len(decisions["decisions"]),
        "field_changes": len(log),
        "curated_disease_rows": len(rows),
        "curated_table_rows": len(table_rows),
        "still_flagged": remaining,
        "verbatim_violations": 0,
    }
    (REVIEW_DIR / "curation_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if not remaining else 1


if __name__ == "__main__":
    raise SystemExit(main())
