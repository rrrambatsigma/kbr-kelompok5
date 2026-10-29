"""Bentuk lapisan ``curated`` untuk gejala dan pengendalian (Tahap 2.4).

Tidak ada perubahan isi: kalimat sudah diekstrak deterministik dan offset-nya
diverifikasi ulang di sini. Skrip ini hanya memindahkan ``auto/symptoms.csv``
dan ``auto/controls.csv`` ke ``curated/`` setelah memastikan setiap
``verbatim_text`` benar-benar substring chunk pada rentang offset yang tercatat.

Jalankan: ``python 03_knowledge_tables/curate_sentences.py``
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

TABLE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TABLE_DIR.parent
EXTRACTION_DIR = PROJECT_ROOT / "02_extraction" / "extracted_text"
CHUNKS_PATH = EXTRACTION_DIR / "DOC002.chunks.jsonl"

AUTO_DIR = TABLE_DIR / "auto"
CURATED_DIR = TABLE_DIR / "curated"
REVIEW_DIR = TABLE_DIR / "review"
REPORTS_DIR = TABLE_DIR / "reports"

WS_RE = re.compile(r"\s+")


def norm(text: Any) -> str:
    return WS_RE.sub(" ", str(text or "")).strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column) for column in columns})


def main() -> int:
    chunks = {
        row["chunk_id"]: norm(row["plain_text"]) for row in read_jsonl(CHUNKS_PATH)
    }

    summary: dict[str, Any] = {"generated_by": "curate_sentences.py", "tables": {}}
    problems: list[str] = []

    for name in ("symptoms", "controls"):
        rows = read_csv(AUTO_DIR / f"{name}.csv")
        columns = list(rows[0].keys())
        mismatches = 0
        for row in rows:
            text = chunks.get(row["chunk_id"])
            if text is None:
                problems.append(f"{name}: chunk {row['chunk_id']} tidak ditemukan")
                continue
            start = int(row["char_start"])
            end = int(row["char_end"])
            if text[start:end] != row["verbatim_text"]:
                mismatches += 1
                if mismatches <= 3:
                    problems.append(
                        f"{name}: offset tidak cocok pada {row['chunk_id']}"
                    )
        if mismatches:
            continue

        write_csv(CURATED_DIR / f"{name}.csv", rows, columns)
        summary["tables"][name] = {
            "rows": len(rows),
            "offset_mismatches": 0,
            "diseases": len({row["disease_id"] for row in rows if row["disease_id"]}),
            "plants": len({row["plant_id"] for row in rows if row["plant_id"]}),
            "by_plant": dict(Counter(row["plant_id"] for row in rows)),
        }
        if name == "controls":
            summary["tables"][name]["chapter_scope_rows"] = sum(
                1 for row in rows if row["scope"] == "chapter"
            )
            summary["tables"][name]["disease_scope_rows"] = sum(
                1 for row in rows if row["scope"] == "disease"
            )

    if problems:
        for problem in problems:
            print(f"GAGAL: {problem}", file=sys.stderr)
        return 2

    ambiguous = read_csv(REVIEW_DIR / "ambiguous_sentences.csv")
    summary["ambiguous_sentences"] = len(ambiguous)
    summary["policy"] = (
        "Kalimat yang memuat isyarat gejala sekaligus pengendalian tidak "
        "dimasukkan ke tabel mana pun; barisnya disimpan di "
        "review/ambiguous_sentences.csv untuk ditinjau."
    )
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "sentence_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
