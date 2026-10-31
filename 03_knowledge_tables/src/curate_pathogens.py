"""Terapkan keputusan kurasi manual ke tabel patogen (Tahap 2.3).

Input:
- ``auto/pathogens.csv``, ``auto/disease_pathogen.csv``
- ``curated/diseases.csv``
- ``review/pathogen_decisions.json`` (keputusan manusia + kutipan sumber)

Output:
- ``curated/pathogens.csv``, ``curated/disease_pathogen.csv``
- ``review/pathogen_log.csv`` (satu baris per perubahan)
- ``review/pathogen_unresolved.csv`` (penyakit tanpa patogen, takson tidak pasti)
- ``review/pathogen_summary.json``

Setiap kutipan bukti diverifikasi muncul verbatim di chunk/blok sumber. Bila
tidak, skrip berhenti dengan kode keluar 2 dan tidak menulis lapisan curated.

Jalankan: ``python 03_knowledge_tables/curate_pathogens.py``
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
BLOCKS_PATH = EXTRACTION_DIR / "DOC002.blocks.jsonl"

AUTO_DIR = TABLE_DIR / "auto"
CURATED_DIR = TABLE_DIR / "curated"
REVIEW_DIR = TABLE_DIR / "review"
DECISIONS_PATH = REVIEW_DIR / "pathogen_decisions.json"

WS_RE = re.compile(r"\s+")

PATHOGEN_COLUMNS = [
    "pathogen_id",
    "scientific_name",
    "verbatim_text",
    "taxon_group",
    "taxon_evidence_chunk_id",
    "taxon_evidence_quote",
    "page",
    "chunk_id",
    "note",
    "review_status",
]

LINK_COLUMNS = [
    "disease_id",
    "pathogen_id",
    "evidence_chunk_id",
    "relation_note",
    "review_status",
]

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

UNRESOLVED_COLUMNS = ["kind", "entity_id", "plant_id", "label", "detail"]


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

    pathogens = read_csv(AUTO_DIR / "pathogens.csv")
    links = read_csv(AUTO_DIR / "disease_pathogen.csv")
    diseases = read_csv(CURATED_DIR / "diseases.csv")

    by_name = {row["scientific_name"]: row for row in pathogens}
    if len(by_name) != len(pathogens):
        print("GAGAL: scientific_name tidak unik di auto/pathogens.csv", file=sys.stderr)
        return 2

    log: list[dict[str, str]] = []
    problems: list[str] = []
    rejected: set[str] = set()

    def check(
        label: str, ref: str, quote: str
    ) -> bool:
        source = evidence_text(chunks, blocks, ref)
        if not source:
            problems.append(f"{label}: bukti {ref} tidak ditemukan")
            return False
        if norm(quote) not in source:
            problems.append(f"{label}: kutipan tidak verbatim di {ref}")
            return False
        return True

    for decision in decisions.get("rejects", []):
        name = decision["scientific_name"]
        row = by_name.get(name)
        if row is None:
            problems.append(f"{decision['pathogen_id']}: {name} tidak ada di auto")
            continue
        if not check(name, decision["evidence_ref"], decision["evidence_quote"]):
            continue
        rejected.add(name)
        log.append(
            {
                "record_type": "pathogen",
                "record_id": row["pathogen_id"],
                "field": "scientific_name",
                "old_value": name,
                "new_value": "",
                "evidence_ref": decision["evidence_ref"],
                "evidence_quote": decision["evidence_quote"],
                "reason": decision["reason"],
            }
        )

    for decision in decisions.get("taxon_fixes", []):
        name = decision["scientific_name"]
        row = by_name.get(name)
        if row is None:
            problems.append(f"{decision['pathogen_id']}: {name} tidak ada di auto")
            continue
        if not check(name, decision["evidence_ref"], decision["evidence_quote"]):
            continue
        if decision["taxon_group"] not in {
            "bakteri",
            "jamur",
            "virus",
            "nematoda",
            "fitoplasma",
            "oomycete",
            "unknown",
        }:
            problems.append(f"{name}: taxon_group {decision['taxon_group']} tidak dikenal")
            continue
        old = row["taxon_group"]
        if old == decision["taxon_group"]:
            continue
        row["taxon_group"] = decision["taxon_group"]
        row["taxon_evidence_chunk_id"] = decision["evidence_ref"]
        row["taxon_evidence_quote"] = decision["evidence_quote"]
        log.append(
            {
                "record_type": "pathogen",
                "record_id": row["pathogen_id"],
                "field": "taxon_group",
                "old_value": old,
                "new_value": decision["taxon_group"],
                "evidence_ref": decision["evidence_ref"],
                "evidence_quote": decision["evidence_quote"],
                "reason": decision["reason"],
            }
        )

    for decision in decisions.get("notes", []):
        name = decision["scientific_name"]
        row = by_name.get(name)
        if row is None:
            problems.append(f"{decision['pathogen_id']}: {name} tidak ada di auto")
            continue
        if row.get("note"):
            problems.append(f"{name}: note sudah terisi")
            continue
        row["note"] = decision["note"]
        row["review_status"] = "verified"
        log.append(
            {
                "record_type": "pathogen",
                "record_id": row["pathogen_id"],
                "field": "note",
                "old_value": "",
                "new_value": decision["note"],
                "evidence_ref": "",
                "evidence_quote": "",
                "reason": "catatan kurasi",
            }
        )

    if problems:
        for problem in problems:
            print(f"GAGAL: {problem}", file=sys.stderr)
        return 2

    # Verifikasi manual: nama sudah dibaca manusia, isi tidak berubah. Dipakai
    # untuk menutup status needs_review pada nama yang memang tidak menyebut
    # kelompok takson di sumber (tetap unknown) atau yang berasal dari heading.
    disease_by_id = {row["disease_id"]: row for row in diseases}
    link_sources: dict[str, list[str]] = {}
    for link in links:
        disease = disease_by_id.get(link["disease_id"])
        if disease is None:
            continue
        parts = [
            norm(disease.get("subsection") or ""),
            norm(disease.get("section") or ""),
        ]
        for block_id in (disease.get("source_block_ids") or "").split(";"):
            block_text = blocks.get(block_id)
            if block_text:
                parts.append(block_text)
        source = norm(" ".join(part for part in parts if part))
        if source:
            link_sources.setdefault(link["pathogen_id"], []).append(source)

    for decision in decisions.get("verifications", []):
        name = decision["scientific_name"]
        row = by_name.get(name)
        if row is None:
            problems.append(f"{decision['pathogen_id']}: {name} tidak ada di auto")
            continue
        sources: list[str] = []
        if row["chunk_id"] in chunks:
            sources.append(chunks[row["chunk_id"]])
        sources.extend(link_sources.get(row["pathogen_id"], []))
        if not any(norm(row["verbatim_text"]) in source for source in sources):
            problems.append(f"{name}: nama tidak ditemukan di chunk/tabel bukti")
            continue
        if row["review_status"] == "verified":
            continue
        evidence_ref = row["chunk_id"]
        if not evidence_ref:
            for link in links:
                if link["pathogen_id"] != row["pathogen_id"]:
                    continue
                disease = disease_by_id.get(link["disease_id"])
                if disease is None:
                    continue
                for block_id in (disease.get("source_block_ids") or "").split(";"):
                    if block_id:
                        evidence_ref = block_id
                        break
                if evidence_ref:
                    break
        old = row["review_status"]
        row["review_status"] = "verified"
        log.append(
            {
                "record_type": "pathogen",
                "record_id": row["pathogen_id"],
                "field": "review_status",
                "old_value": old,
                "new_value": "verified",
                "evidence_ref": evidence_ref,
                "evidence_quote": row["verbatim_text"],
                "reason": decision["reason"],
            }
        )

    if problems:
        for problem in problems:
            print(f"GAGAL: {problem}", file=sys.stderr)
        return 2

    curated_pathogens = [row for row in pathogens if row["scientific_name"] not in rejected]

    rejected_ids = {
        row["pathogen_id"]
        for row in pathogens
        if row["scientific_name"] in rejected
    }
    curated_links = [row for row in links if row["pathogen_id"] not in rejected_ids]

    disease_ids = {row["disease_id"] for row in diseases}
    curated_links = [row for row in curated_links if row["disease_id"] in disease_ids]

    for row in curated_pathogens:
        row.setdefault("taxon_evidence_chunk_id", "")
        row.setdefault("taxon_evidence_quote", "")
        row.setdefault("note", "")
        row.setdefault("review_status", "auto_ok")

    write_csv(CURATED_DIR / "pathogens.csv", curated_pathogens, PATHOGEN_COLUMNS)
    write_csv(CURATED_DIR / "disease_pathogen.csv", curated_links, LINK_COLUMNS)
    write_csv(REVIEW_DIR / "pathogen_log.csv", log, LOG_COLUMNS)

    linked = {row["disease_id"] for row in curated_links}
    unresolved: list[dict[str, str]] = []
    for disease in diseases:
        if disease["disease_id"] in linked:
            continue
        unresolved.append(
            {
                "kind": "disease_without_pathogen",
                "entity_id": disease["disease_id"],
                "plant_id": disease["plant_id"],
                "label": disease["disease_name_verbatim"],
                "detail": (
                    "Tidak ada nama patogen yang dapat diekstraksi dari bagian "
                    "penyakit ini; lihat diseases.csv untuk bukti halaman."
                ),
            }
        )
    for row in curated_pathogens:
        if row["taxon_group"] == "unknown":
            unresolved.append(
                {
                    "kind": "pathogen_taxon_unknown",
                    "entity_id": row["pathogen_id"],
                    "plant_id": "",
                    "label": row["scientific_name"],
                    "detail": "Sumber tidak menyebut kelompok takson patogen ini.",
                }
            )
        if row.get("note"):
            unresolved.append(
                {
                    "kind": "pathogen_variant",
                    "entity_id": row["pathogen_id"],
                    "plant_id": "",
                    "label": row["scientific_name"],
                    "detail": row["note"],
                }
            )
    write_csv(REVIEW_DIR / "pathogen_unresolved.csv", unresolved, UNRESOLVED_COLUMNS)

    summary = {
        "curation_round": decisions.get("curation_round"),
        "auto_pathogen_rows": len(pathogens),
        "rejected_pathogen_rows": len(rejected),
        "curated_pathogen_rows": len(curated_pathogens),
        "taxon_fixes": len(decisions.get("taxon_fixes", [])),
        "notes": len(decisions.get("notes", [])),
        "verifications": len(decisions.get("verifications", [])),
        "pathogen_review_status": dict(
            sorted(Counter(row["review_status"] for row in curated_pathogens).items())
        ),
        "curated_link_rows": len(curated_links),
        "diseases_with_pathogen": len(linked),
        "diseases_without_pathogen": len(diseases) - len(linked),
        "pathogens_taxon_unknown": sum(
            1 for row in curated_pathogens if row["taxon_group"] == "unknown"
        ),
        "log_rows": len(log),
        "verbatim_violations": 0,
    }
    (REVIEW_DIR / "pathogen_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
