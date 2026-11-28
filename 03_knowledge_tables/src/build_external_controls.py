"""Bangun fakta pengendalian eksternal untuk penyakit Ubi Kayu.

Input kurasi: ``03_knowledge_tables/curated/EXTERNAL_ENV/external_controls.csv``.
Output: entities/facts CSV yang dibaca oleh ``04_ontology/build_ontology_md.py``.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TABLE_DIR = PROJECT_ROOT / "03_knowledge_tables"
ONTO_DIR = PROJECT_ROOT / "04_ontology"
sys.path.insert(0, str(ONTO_DIR))

import build_ontology as bo  # noqa: E402

SOURCE_REGISTRY = PROJECT_ROOT / "01_knowledge_sources" / "external" / "source_registry.csv"
CONTROLS_CSV = TABLE_DIR / "curated" / "EXTERNAL_ENV" / "external_controls.csv"
OUT_DIR = TABLE_DIR / "auto" / "EXTERNAL_ENV"
REPORT_JSON = TABLE_DIR / "reports" / "EXTERNAL_ENV" / "external_controls_report.json"

ENTITY_COLUMNS = [
    "entity_local",
    "entity_class",
    "label",
    "comment",
    "source_document",
    "source_id",
    "notes",
]
FACT_COLUMNS = [
    "fact_id",
    "subject_local",
    "subject_class",
    "predicate",
    "object_local",
    "object_class",
    "literal_value",
    "literal_lang",
    "source_document",
    "source_type",
    "source_id",
    "evidence_quote",
    "page",
    "line_start",
    "line_end",
    "confidence",
    "review_status",
    "notes",
]
CONTROL_ID_RE = "control_id"
CONFIDENCES = {"high", "medium", "low"}
REVIEW_STATUSES = {"verified", "needs_review", "auto_ok"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build() -> tuple[list[dict[str, str]], list[dict[str, str]], dict, list[str]]:
    sources = {row["source_id"].strip() for row in read_csv(SOURCE_REGISTRY)}
    entries = bo.penyakit_entries()
    diseases = {
        entry["local"]: (entry.get("label") or entry.get("nama") or entry["local"])
        for entry in entries
    }
    actions = bo.CONTROL_ACTIONS
    control_rows = read_csv(CONTROLS_CSV)

    entities: list[dict[str, str]] = []
    facts: list[dict[str, str]] = []
    errors: list[str] = []
    skipped: list[dict[str, str]] = []
    used_controls: set[str] = set()
    used_pairs: set[tuple[str, str]] = set()
    action_counts: Counter[str] = Counter()
    disease_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()

    def add_fact(
        subject_local: str,
        subject_class: str,
        predicate: str,
        row: dict[str, str],
        object_local: str = "",
        object_class: str = "",
        literal_value: str = "",
        literal_lang: str = "",
    ) -> None:
        facts.append(
            {
                "fact_id": f"EXT_CTL_F_{len(facts) + 1:04d}",
                "subject_local": subject_local,
                "subject_class": subject_class,
                "predicate": predicate,
                "object_local": object_local,
                "object_class": object_class,
                "literal_value": literal_value,
                "literal_lang": literal_lang,
                "source_document": row["source_id"],
                "source_type": "external_control",
                "source_id": row["control_id"],
                "evidence_quote": row["quote"],
                "page": "",
                "line_start": "",
                "line_end": "",
                "confidence": row["confidence"],
                "review_status": row["review_status"],
                "notes": row["notes"],
            }
        )

    for row in control_rows:
        control_id = (row.get("control_id") or "").strip()
        disease = (row.get("disease_local") or "").strip()
        action = (row.get("action_local") or "").strip()
        source_id = (row.get("source_id") or "").strip()
        locator = (row.get("locator") or "").strip()
        quote = (row.get("quote") or "").strip()
        confidence = (row.get("confidence") or "").strip().lower()
        review = (row.get("review_status") or "").strip().lower()
        notes = (row.get("notes") or "").strip()

        if not control_id or not disease or not action or not source_id or not locator or not quote:
            errors.append(f"baris kontrol tidak lengkap: {control_id or '(tanpa id)'}")
            continue
        if control_id in used_controls:
            errors.append(f"control_id duplikat: {control_id}")
            continue
        if (disease, action) in used_pairs:
            skipped.append({"control_id": control_id, "reason": "pasangan disease-action duplikat"})
            continue
        if source_id not in sources:
            errors.append(f"{control_id}: source_id tidak ada di registry: {source_id}")
            continue
        if disease not in diseases:
            errors.append(f"{control_id}: disease_local tidak dikenal: {disease}")
            continue
        if action not in actions:
            errors.append(f"{control_id}: action_local tidak dikenal: {action}")
            continue
        if confidence not in CONFIDENCES:
            errors.append(f"{control_id}: confidence tidak dikenal: {confidence}")
            continue
        if review not in REVIEW_STATUSES:
            errors.append(f"{control_id}: review_status tidak dikenal: {review}")
            continue

        used_controls.add(control_id)
        used_pairs.add((disease, action))
        action_counts[action] += 1
        disease_counts[disease] += 1
        source_counts[source_id] += 1

        disease_label = diseases[disease]
        action_label = actions[action]["label"]
        evidence_local = "Bukti" + bo.pascal(control_id)
        entities.append(
            {
                "entity_local": evidence_local,
                "entity_class": "BuktiPengendalian",
                "label": f"Bukti pengendalian {disease_label} - {action_label}",
                "comment": "Bukti sumber untuk tindakan pengendalian eksternal.",
                "source_document": source_id,
                "source_id": control_id,
                "notes": notes,
            }
        )

        add_fact(disease, "Penyakit", "dikendalikanDengan", row, object_local=action, object_class="Pengendalian")
        add_fact(disease, "Penyakit", "didukungOleh", row, object_local=evidence_local, object_class="BuktiPengendalian")
        add_fact(action, "Pengendalian", "didukungOleh", row, object_local=evidence_local, object_class="BuktiPengendalian")
        add_fact(evidence_local, "BuktiPengendalian", "kutipanSumber", row, literal_value=quote)
        add_fact(evidence_local, "BuktiPengendalian", "kutipanNormalisasi", row, literal_value=bo.normalize_quote(quote))
        add_fact(evidence_local, "BuktiPengendalian", "dokumenSumber", row, literal_value=source_id)
        add_fact(evidence_local, "BuktiPengendalian", "identifierSumber", row, literal_value=locator)
        add_fact(
            evidence_local,
            "BuktiPengendalian",
            "catatanKualitas",
            row,
            literal_value=f"confidence={confidence}; review_status={review}; relation_type={notes or 'direct'}",
            literal_lang="id",
        )

    report = {
        "controls": len(control_rows),
        "generated": len(used_controls),
        "entities_generated": len(entities),
        "facts_generated": len(facts),
        "diseases_covered": len(disease_counts),
        "disease_counts": dict(sorted(disease_counts.items())),
        "action_counts": dict(sorted(action_counts.items())),
        "source_counts": dict(sorted(source_counts.items())),
        "skipped": skipped,
        "validation_errors": errors,
    }
    return entities, facts, report, errors


def main() -> int:
    entities, facts, report, errors = build()
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="",
    )
    if errors:
        print("VALIDASI GAGAL:")
        for error in errors:
            print(f"  - {error}")
        return 1

    write_csv(OUT_DIR / "EXTERNAL_ENV_controls_entities.csv", entities, ENTITY_COLUMNS)
    write_csv(OUT_DIR / "EXTERNAL_ENV_controls_facts.csv", facts, FACT_COLUMNS)
    print(f"output: {OUT_DIR / 'EXTERNAL_ENV_controls_entities.csv'}")
    print(f"output: {OUT_DIR / 'EXTERNAL_ENV_controls_facts.csv'}")
    print(f"controls: {report['generated']} entities: {report['entities_generated']} facts: {report['facts_generated']}")
    print(f"report: {REPORT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
