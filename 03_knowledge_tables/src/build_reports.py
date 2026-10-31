"""Laporan cakupan dan validasi knowledge table DOC002 (Tahap 2.5 / Blok D).

Input (read-only):
- ``curated/*.csv``
- ``review/ambiguous_sentences.csv``
- ``02_extraction/extracted_text/DOC002.chunks.jsonl``
- ``02_extraction/extracted_text/DOC002.blocks.jsonl``

Output:
- ``reports/coverage.json``, ``reports/coverage.md``
- ``reports/validation.json`` (gate G1-G7)
- ``review/unresolved.csv`` (gabungan butir yang belum tuntas)

Jalankan: ``python 03_knowledge_tables/build_reports.py``
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

TABLE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TABLE_DIR.parent
EXTRACTION_DIR = PROJECT_ROOT / "02_extraction" / "extracted_text"
CHUNKS_PATH = EXTRACTION_DIR / "DOC002.chunks.jsonl"
BLOCKS_PATH = EXTRACTION_DIR / "DOC002.blocks.jsonl"

CURATED_DIR = TABLE_DIR / "curated"
REVIEW_DIR = TABLE_DIR / "review"
REPORTS_DIR = TABLE_DIR / "reports"

WS_RE = re.compile(r"\s+")
TAXON_VALUES = {
    "jamur",
    "bakteri",
    "virus",
    "nematoda",
    "fitoplasma",
    "oomycete",
    "unknown",
}

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


def main() -> int:
    plants = read_csv(TABLE_DIR / "auto" / "plants.csv")
    diseases = read_csv(CURATED_DIR / "diseases.csv")
    pathogens = read_csv(CURATED_DIR / "pathogens.csv")
    links = read_csv(CURATED_DIR / "disease_pathogen.csv")
    symptoms = read_csv(CURATED_DIR / "symptoms.csv")
    controls = read_csv(CURATED_DIR / "controls.csv")
    table_rows = read_csv(CURATED_DIR / "ubi_kayu_tabel_5.csv")

    chunks = {
        row["chunk_id"]: norm(row["plain_text"]) for row in read_jsonl(CHUNKS_PATH)
    }
    block_text: dict[str, str] = {}
    for block in read_jsonl(BLOCKS_PATH):
        cells: list[str] = []
        table = block.get("table") or {}
        for row in table.get("cells") or []:
            if isinstance(row, list):
                cells.extend(norm(cell) for cell in row if cell)
        block_text[block["block_id"]] = " | ".join(cells)

    plant_by_id = {row["plant_id"]: row for row in plants}
    disease_by_id = {row["disease_id"]: row for row in diseases}
    pathogen_by_id = {row["pathogen_id"]: row for row in pathogens}

    symptom_diseases = {row["disease_id"] for row in symptoms}
    control_diseases = {row["disease_id"] for row in controls if row["disease_id"]}
    pathogen_diseases = {row["disease_id"] for row in links}
    chapter_control_plants = {
        row["plant_id"] for row in controls if row["scope"] == "chapter"
    }
    table_symptom_keys = {
        (row["table_id"], row["disease_name"])
        for row in table_rows
        if row["symptom_text"].strip() and row["status"] != "missing_row"
    }

    # ---------- cakupan ----------
    per_plant: dict[str, dict[str, Any]] = {}
    for disease in diseases:
        plant_id = disease["plant_id"]
        entry = per_plant.setdefault(
            plant_id,
            {
                "diseases": 0,
                "with_pathogen": 0,
                "with_symptom": 0,
                "with_control": 0,
                "has_chapter_control": plant_id in chapter_control_plants,
            },
        )
        entry["diseases"] += 1
        if disease["disease_id"] in pathogen_diseases:
            entry["with_pathogen"] += 1
        if (
            disease["disease_id"] in symptom_diseases
            or (
                disease["heading_level"] == "table"
                and (disease["section"], disease["disease_name_verbatim"])
                in table_symptom_keys
            )
        ):
            entry["with_symptom"] += 1
        if disease["disease_id"] in control_diseases:
            entry["with_control"] += 1

    coverage_rows: list[dict[str, Any]] = []
    for plant in plants:
        entry = per_plant.get(plant["plant_id"], {})
        total = entry.get("diseases", 0)
        row = {
            "plant_id": plant["plant_id"],
            "plant_name": plant["plant_name_id"],
            "diseases": total,
            "with_pathogen": entry.get("with_pathogen", 0),
            "with_symptom": entry.get("with_symptom", 0),
            "with_control": entry.get("with_control", 0),
            "has_chapter_control": entry.get("has_chapter_control", False),
        }
        row["pathogen_pct"] = round(100 * row["with_pathogen"] / total, 1) if total else 0.0
        row["symptom_pct"] = round(100 * row["with_symptom"] / total, 1) if total else 0.0
        row["control_pct"] = round(100 * row["with_control"] / total, 1) if total else 0.0
        coverage_rows.append(row)

    totals = {
        "plants": len(plants),
        "diseases": len(diseases),
        "pathogens": len(pathogens),
        "disease_pathogen_links": len(links),
        "symptom_rows": len(symptoms),
        "control_rows": len(controls),
        "control_rows_disease_scope": sum(
            1 for row in controls if row["scope"] == "disease"
        ),
        "control_rows_chapter_scope": sum(
            1 for row in controls if row["scope"] == "chapter"
        ),
        "ubi_kayu_table_rows": len(table_rows),
        "diseases_with_pathogen": len(pathogen_diseases),
        "diseases_with_symptom": sum(
            row["with_symptom"] for row in coverage_rows
        ),
        "diseases_with_control": sum(
            row["with_control"] for row in coverage_rows
        ),
    }

    coverage = {
        "generated_by": "build_reports.py",
        "denominator": {
            "diseases": (
                "109 baris penyakit dari 15 tanaman; gejala ubi kayu dihitung "
                "dari tabel 5.1-5.3, bukan dari symptoms.csv"
            ),
            "controls": (
                "kendali tingkat penyakit dihitung dari controls.csv scope=disease; "
                "kendali tingkat bab dilaporkan terpisah"
            ),
        },
        "totals": totals,
        "per_plant": coverage_rows,
        "taxon_groups": dict(
            sorted(Counter(row["taxon_group"] for row in pathogens).items())
        ),
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "coverage.json").write_text(
        json.dumps(coverage, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    def pct(value: int, total: int) -> str:
        return f"{100 * value / total:.0f}%" if total else "-"

    lines = [
        "# Cakupan knowledge table DOC002",
        "",
        "Dokumen: `Penyakit Tanaman dan Pengendaliannya` (DOC002), 15 tanaman pangan.",
        "",
        "## Ringkasan",
        "",
        f"- Penyakit: **{totals['diseases']}**",
        f"- Patogen unik: **{totals['pathogens']}**",
        f"- Relasi penyakit-patogen: **{totals['disease_pathogen_links']}**",
        f"- Baris gejala: **{totals['symptom_rows']}**",
        f"- Baris pengendalian: **{totals['control_rows']}** "
        f"({totals['control_rows_disease_scope']} tingkat penyakit, "
        f"{totals['control_rows_chapter_scope']} tingkat bab)",
        "",
        "## Cakupan per tanaman",
        "",
        "| Tanaman | Penyakit | Patogen | Gejala | Kendali penyakit | Kendali bab |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in coverage_rows:
        lines.append(
            "| {name} | {total} | {pat} ({patp}) | {sym} ({symp}) | "
            "{ctl} ({ctlp}) | {chapter} |".format(
                name=row["plant_name"],
                total=row["diseases"],
                pat=row["with_pathogen"],
                patp=pct(row["with_pathogen"], row["diseases"]),
                sym=row["with_symptom"],
                symp=pct(row["with_symptom"], row["diseases"]),
                ctl=row["with_control"],
                ctlp=pct(row["with_control"], row["diseases"]),
                chapter="ya" if row["has_chapter_control"] else "tidak",
            )
        )

    without_pathogen = [
        disease
        for disease in diseases
        if disease["disease_id"] not in pathogen_diseases
    ]
    without_control = [
        disease
        for disease in diseases
        if disease["disease_id"] not in control_diseases
    ]
    lines += [
        "",
        "## Penyakit tanpa patogen",
        "",
        f"Jumlah: **{len(without_pathogen)}**",
        "",
    ]
    for disease in without_pathogen:
        lines.append(
            f"- `{disease['disease_id']}` ({disease['plant_id']}) "
            f"{disease['disease_name_verbatim']}"
        )
    lines += [
        "",
        "## Penyakit tanpa pengendalian tingkat penyakit",
        "",
        f"Jumlah: **{len(without_control)}**",
        "",
        "Penyakit ubi kayu (PLANT_005) memakai pengendalian tingkat bab 5.3; "
        "penyakit lain di bawah ini tidak memiliki teks pengendalian yang dapat "
        "diekstraksi dari bagian penyakitnya.",
        "",
    ]
    for disease in without_control:
        suffix = " (ada kendali bab)" if disease["plant_id"] in chapter_control_plants else ""
        lines.append(
            f"- `{disease['disease_id']}` ({disease['plant_id']}) "
            f"{disease['disease_name_verbatim']}{suffix}"
        )

    (REPORTS_DIR / "coverage.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ---------- validasi ----------
    plant_ids = set(plant_by_id)
    disease_ids = set(disease_by_id)
    pathogen_ids = set(pathogen_by_id)

    def evidence_sources(pathogen: dict[str, str]) -> list[str]:
        sources: list[str] = []
        if pathogen["chunk_id"] and pathogen["chunk_id"] in chunks:
            sources.append(chunks[pathogen["chunk_id"]])
        for link in links:
            if link["pathogen_id"] != pathogen["pathogen_id"]:
                continue
            disease = disease_by_id.get(link["disease_id"])
            if not disease:
                continue
            heading = norm(disease.get("subsection") or disease.get("section") or "")
            if heading:
                sources.append(heading)
            for block_id in (disease.get("source_block_ids") or "").split(";"):
                if block_id and block_id in block_text:
                    sources.append(block_text[block_id])
        return sources

    offset_problems: list[str] = []
    for name, rows in (("symptoms", symptoms), ("controls", controls)):
        for row in rows:
            text = chunks.get(row["chunk_id"])
            if text is None:
                offset_problems.append(f"{name}:{row.get(name[:-1] + '_id', '')}:chunk")
                continue
            start = int(row["char_start"])
            end = int(row["char_end"])
            if text[start:end] != row["verbatim_text"]:
                offset_problems.append(f"{name}:{row['chunk_id']}@{start}")

    verbatim_problems = [
        row["pathogen_id"]
        for row in pathogens
        if not any(
            norm(row["verbatim_text"]) in source for source in evidence_sources(row)
        )
    ]

    fk_problems: list[str] = []
    for row in diseases:
        if row["plant_id"] not in plant_ids:
            fk_problems.append(f"diseases:{row['disease_id']}:plant")
    for row in links:
        if row["disease_id"] not in disease_ids:
            fk_problems.append(f"links:{row['disease_id']}")
        if row["pathogen_id"] not in pathogen_ids:
            fk_problems.append(f"links:{row['pathogen_id']}")
    for row in symptoms:
        if row["disease_id"] not in disease_ids:
            fk_problems.append(f"symptoms:{row['symptom_id']}:disease")
        if row["plant_id"] not in plant_ids:
            fk_problems.append(f"symptoms:{row['symptom_id']}:plant")
    for row in controls:
        if row["plant_id"] not in plant_ids:
            fk_problems.append(f"controls:{row['control_id']}:plant")
        if row["scope"] == "disease" and row["disease_id"] not in disease_ids:
            fk_problems.append(f"controls:{row['control_id']}:disease")
        if row["scope"] == "chapter" and row["disease_id"]:
            fk_problems.append(f"controls:{row['control_id']}:chapter-has-disease")
        if row["scope"] not in {"disease", "chapter"}:
            fk_problems.append(f"controls:{row['control_id']}:scope")

    taxon_problems: list[str] = []
    for row in pathogens:
        if row["taxon_group"] not in TAXON_VALUES:
            taxon_problems.append(f"{row['pathogen_id']}:enum")
        quote = row.get("taxon_evidence_quote") or ""
        ref = row.get("taxon_evidence_chunk_id") or ""
        if quote:
            if ref not in chunks or norm(quote) not in chunks[ref]:
                taxon_problems.append(f"{row['pathogen_id']}:quote")

    duplicates = Counter(
        (row["plant_id"], row["disease_name_key"], row["section"])
        for row in diseases
    )
    duplicate_names = [key for key, count in duplicates.items() if count > 1]
    unnamed_duplicates = [
        row["disease_id"]
        for row in diseases
        if any(
            (row["plant_id"], row["disease_name_key"]) == (other["plant_id"], other["disease_name_key"])
            and row["disease_id"] != other["disease_id"]
            and not row.get("notes")
            for other in diseases
        )
    ]

    linked_ids = {row["pathogen_id"] for row in links}
    orphan_pathogens = sorted(pathogen_ids - linked_ids)
    chapter_numbers = sorted({int(row["chapter_number"]) for row in plants})

    gates = {
        "G1_plants_complete": {
            "passed": len(plants) == 15
            and chapter_numbers == list(range(1, 16))
            and all(row["diseases"] > 0 for row in coverage_rows),
            "detail": (
                f"plants={len(plants)} chapters={len(chapter_numbers)} "
                f"plants_without_disease="
                f"{[row['plant_id'] for row in coverage_rows if not row['diseases']]}"
            ),
        },
        "G2_disease_uniqueness": {
            "passed": not duplicate_names
            and not unnamed_duplicates
            and all(row["disease_name_verbatim"] for row in diseases),
            "detail": (
                f"diseases={len(diseases)} duplicates={duplicate_names[:10]} "
                f"unnamed_duplicates={unnamed_duplicates[:10]}"
            ),
        },
        "G3_pathogen_integrity": {
            "passed": len(pathogen_ids) == len(pathogens)
            and not orphan_pathogens
            and not any(item.startswith("links:") for item in fk_problems),
            "detail": (
                f"pathogens={len(pathogens)} links={len(links)} "
                f"orphans={orphan_pathogens[:10]}"
            ),
        },
        "G4_pathogen_verbatim": {
            "passed": not verbatim_problems,
            "detail": f"violations={verbatim_problems[:10]}",
        },
        "G5_sentence_offsets": {
            "passed": not offset_problems,
            "detail": (
                f"symptoms={len(symptoms)} controls={len(controls)} "
                f"mismatches={offset_problems[:10]}"
            ),
        },
        "G6_sentence_foreign_keys": {
            "passed": not fk_problems,
            "detail": f"problems={fk_problems[:10]}",
        },
        "G7_taxon_evidence": {
            "passed": not taxon_problems,
            "detail": (
                f"unknown={sum(1 for row in pathogens if row['taxon_group'] == 'unknown')} "
                f"problems={taxon_problems[:10]}"
            ),
        },
    }
    validation = {
        "schema_version": "1.1.0",
        "document_id": "DOC002",
        "generated_by": "build_reports.py",
        "gate_passed": all(gate["passed"] for gate in gates.values()),
        "gates": gates,
        "counts": totals,
    }
    (REPORTS_DIR / "validation.json").write_text(
        json.dumps(validation, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    # ---------- unresolved gabungan ----------
    unresolved: list[dict[str, str]] = []
    for row in read_csv(REVIEW_DIR / "pathogen_unresolved.csv"):
        unresolved.append(
            {
                "kind": row["kind"],
                "entity_id": row["entity_id"],
                "plant_id": row["plant_id"],
                "label": row["label"],
                "detail": row["detail"],
            }
        )
    for disease in without_control:
        unresolved.append(
            {
                "kind": "disease_without_control",
                "entity_id": disease["disease_id"],
                "plant_id": disease["plant_id"],
                "label": disease["disease_name_verbatim"],
                "detail": (
                    "Ada pengendalian tingkat bab."
                    if disease["plant_id"] in chapter_control_plants
                    else "Tidak ada teks pengendalian pada bagian penyakit maupun bab."
                ),
            }
        )
    for row in read_csv(REVIEW_DIR / "ambiguous_sentences.csv"):
        unresolved.append(
            {
                "kind": "ambiguous_sentence",
                "entity_id": row["chunk_id"],
                "plant_id": "",
                "label": row["sentence"][:160],
                "detail": (
                    f"Penyakit {row['disease_id']}: kalimat memuat isyarat gejala "
                    "dan pengendalian sekaligus; tidak dimasukkan ke tabel."
                ),
            }
        )
    write_csv(REVIEW_DIR / "unresolved.csv", unresolved, UNRESOLVED_COLUMNS)

    print(
        json.dumps(
            {
                "gate_passed": validation["gate_passed"],
                "gates": {key: value["passed"] for key, value in gates.items()},
                "coverage": totals,
                "unresolved_rows": len(unresolved),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0 if validation["gate_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
