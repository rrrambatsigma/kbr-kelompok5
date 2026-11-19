"""Bangun fakta lingkungan eksternal dari evidence card yang sudah diverifikasi."""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

from rdflib import Graph
from rdflib.namespace import RDF, RDFS

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TABLE_DIR = PROJECT_ROOT / "03_knowledge_tables"
ONTO_DIR = PROJECT_ROOT / "04_ontology"
sys.path.insert(0, str(ONTO_DIR))

from tbox import CLASSES, KBR  # noqa: E402

SOURCE_REGISTRY = PROJECT_ROOT / "01_knowledge_sources" / "external" / "source_registry.csv"
CARDS_CSV = TABLE_DIR / "curated" / "EXTERNAL_ENV" / "evidence_cards.csv"
OBSERVATIONS_CSV = TABLE_DIR / "curated" / "EXTERNAL_ENV" / "environment_observations.csv"
CONDITIONS_CSV = TABLE_DIR / "curated" / "EXTERNAL_ENV" / "observation_conditions.csv"
OUT_DIR = TABLE_DIR / "auto" / "EXTERNAL_ENV"
REPORT_JSON = TABLE_DIR / "reports" / "EXTERNAL_ENV" / "external_env_report.json"
ONTOLOGY_TTL = ONTO_DIR / "ontology_md.ttl"

SCOPE_PLANTS = {"Padi", "Kedelai", "Jagung", "UbiJalar", "UbiKayu", "KacangTanah", "KacangHijau"}
RELATION_TYPES = {"direct", "vector_mediated", "control_only"}
REVIEW_STATUSES = {"auto_ok", "needs_review", "verified", "rejected"}
CONFIDENCES = {"high", "medium", "low"}
VECTOR_EVIDENCE_RE = re.compile(
    r"\b(vektor|vektornya|ditularkan|menularkan|penularan|serangga|wereng|"
    r"aphid|afid|kutu|thrips|trips|whitefly|kutu kebul|leafhoppers?|"
    r"planthoppers?|flea beetles?|whitefl(?:y|ies)|aphids?|vectors?)\b",
    re.IGNORECASE,
)
ENVIRONMENT_EVIDENCE_RE = re.compile(
    r"\b(suhu|curah hujan|hujan|kelembapan|kelembaban|lembap|lembab|musim|"
    r"iklim|cuaca|angin|tanah|lahan|tegakan|sawah|agroforestri|habitat|"
    r"lingkungan|drainase|cahaya|naungan|ketinggian|"
    r"temperature|humidity|rainfall|rain|rainy|climate|climatic|seasons?|"
    r"weather|wind|soil|drought|flood|irrigation|tropical|winters?)\b",
    re.IGNORECASE,
)

OPERATOR_LABELS = {
    "=": "sama dengan",
    "sama dengan": "sama dengan",
    ">": ">",
    ">=": ">=",
    "<": "<",
    "<=": "<=",
    "range": "range",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_number(value: str) -> float | None:
    text = (value or "").strip()
    if not text:
        return None
    return float(text)


def format_number(value: float) -> str:
    return str(int(value)) if value.is_integer() else str(value)


def normalise_quote(value: str) -> str:
    return " ".join((value or "").split())


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def load_disease_labels() -> tuple[set[str], dict[str, str]]:
    graph = Graph()
    graph.parse(ONTOLOGY_TTL, format="turtle")
    labels: dict[str, str] = {}
    for subject in graph.subjects(RDF.type, KBR.Penyakit):
        local = str(subject).split("#")[-1]
        label = graph.value(subject, RDFS.label)
        labels[local] = str(label) if label else local
    return set(labels), labels


def validate(
    sources: list[dict[str, str]],
    cards: list[dict[str, str]],
    observations: list[dict[str, str]],
    diseases: set[str],
    conditions: list[dict[str, str]] | None = None,
) -> list[str]:
    errors: list[str] = []
    conditions = conditions or []
    known_classes = set(CLASSES)
    source_ids = {row.get("source_id", "").strip() for row in sources}
    card_ids = {row.get("card_id", "").strip() for row in cards}
    card_relations = {
        (row.get("card_id") or "").strip(): (row.get("relation_type") or "").strip()
        for row in cards
    }

    for row in sources:
        source_id = (row.get("source_id") or "").strip()
        if not source_id:
            errors.append("source_registry: source_id kosong")
        if not (row.get("title") or "").strip():
            errors.append(f"{source_id}: title kosong")
        if not (row.get("url") or "").strip():
            errors.append(f"{source_id}: url kosong")
        status = (row.get("verification_status") or "").strip()
        if status not in {"verified", "verified_access_vector_only", "blocked_403", "binary_pdf", "candidate"}:
            errors.append(f"{source_id}: verification_status tidak dikenal: {status}")

    for row in cards:
        card_id = (row.get("card_id") or "").strip()
        source_id = (row.get("source_id") or "").strip()
        disease = (row.get("disease_local") or "").strip()
        factor_class = (row.get("factor_class") or "").strip()
        relation = (row.get("relation_type") or "").strip()
        confidence = (row.get("confidence") or "").strip()
        review = (row.get("review_status") or "").strip()
        if source_id not in source_ids:
            errors.append(f"{card_id}: source_id tidak ada: {source_id}")
        if (row.get("plant") or "").strip() not in SCOPE_PLANTS:
            errors.append(f"{card_id}: plant di luar scope")
        if disease not in diseases:
            errors.append(f"{card_id}: disease_local tidak dikenal: {disease}")
        if factor_class not in known_classes:
            errors.append(f"{card_id}: factor_class tidak dikenal: {factor_class}")
        if relation not in RELATION_TYPES:
            errors.append(f"{card_id}: relation_type tidak dikenal: {relation}")
        if confidence not in CONFIDENCES:
            errors.append(f"{card_id}: confidence tidak dikenal: {confidence}")
        if review not in REVIEW_STATUSES:
            errors.append(f"{card_id}: review_status tidak dikenal: {review}")
        if not (row.get("quote") or "").strip():
            errors.append(f"{card_id}: quote kosong")
        quote = normalise_quote(row.get("quote", ""))
        if relation == "vector_mediated":
            if not VECTOR_EVIDENCE_RE.search(quote):
                errors.append(f"{card_id}: vector_mediated tanpa bukti vektor")
            if not ENVIRONMENT_EVIDENCE_RE.search(quote):
                errors.append(f"{card_id}: vector_mediated tanpa bukti faktor lingkungan")
        min_value = parse_number(row.get("min_value", ""))
        max_value = parse_number(row.get("max_value", ""))
        if min_value is not None and max_value is not None and min_value > max_value:
            errors.append(f"{card_id}: min_value > max_value")

    for row in observations:
        obs_id = (row.get("obs_id") or "").strip()
        card_id = (row.get("card_id") or "").strip()
        source_id = (row.get("source_id") or "").strip()
        disease = (row.get("disease_local") or "").strip()
        factor_class = (row.get("factor_class") or "").strip()
        confidence = (row.get("confidence") or "").strip()
        review = (row.get("review_status") or "").strip()
        if card_id not in card_ids:
            errors.append(f"{obs_id}: card_id tidak ada: {card_id}")
        if source_id not in source_ids:
            errors.append(f"{obs_id}: source_id tidak ada: {source_id}")
        if disease not in diseases:
            errors.append(f"{obs_id}: disease_local tidak dikenal: {disease}")
        if factor_class not in known_classes:
            errors.append(f"{obs_id}: factor_class tidak dikenal: {factor_class}")
        if confidence not in CONFIDENCES:
            errors.append(f"{obs_id}: confidence tidak dikenal: {confidence}")
        if review not in REVIEW_STATUSES:
            errors.append(f"{obs_id}: review_status tidak dikenal: {review}")
        if not (row.get("quote") or "").strip():
            errors.append(f"{obs_id}: quote kosong")
        quote = normalise_quote(row.get("quote", ""))
        if card_relations.get(card_id) == "vector_mediated":
            if not VECTOR_EVIDENCE_RE.search(quote):
                errors.append(f"{obs_id}: vector_mediated tanpa bukti vektor")
            if not ENVIRONMENT_EVIDENCE_RE.search(quote):
                errors.append(f"{obs_id}: vector_mediated tanpa bukti faktor lingkungan")
        min_value = parse_number(row.get("min_value", ""))
        max_value = parse_number(row.get("max_value", ""))
        if min_value is not None and max_value is not None and min_value > max_value:
            errors.append(f"{obs_id}: min_value > max_value")

    observation_ids = {(row.get("obs_id") or "").strip() for row in observations}
    seen_conditions: set[tuple[str, str]] = set()
    for row in conditions:
        obs_id = (row.get("obs_id") or "").strip()
        condition_local = (row.get("condition_local") or "").strip()
        label = (row.get("condition_label") or "").strip()
        confidence = (row.get("confidence") or "").strip()
        review = (row.get("review_status") or "").strip()
        if obs_id not in observation_ids:
            errors.append(f"{obs_id}: kondisi merujuk obs_id tidak dikenal")
        if not condition_local:
            errors.append(f"{obs_id}: condition_local kosong")
        if not label:
            errors.append(f"{obs_id}: condition_label kosong")
        if confidence not in CONFIDENCES:
            errors.append(f"{obs_id}: confidence kondisi tidak dikenal: {confidence}")
        if review not in REVIEW_STATUSES:
            errors.append(f"{obs_id}: review_status kondisi tidak dikenal: {review}")
        key = (obs_id, condition_local)
        if key in seen_conditions:
            errors.append(f"{obs_id}: kondisi duplikat: {condition_local}")
        seen_conditions.add(key)
    return errors


def build() -> tuple[
    list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], dict, list[str]
]:
    sources = read_csv(SOURCE_REGISTRY)
    cards = read_csv(CARDS_CSV)
    observations = read_csv(OBSERVATIONS_CSV)
    conditions = read_csv(CONDITIONS_CSV)
    diseases, disease_labels = load_disease_labels()
    errors = validate(sources, cards, observations, diseases, conditions)

    source_by_id = {(row.get("source_id") or "").strip(): row for row in sources}
    card_by_id = {(row.get("card_id") or "").strip(): row for row in cards}
    conditions_by_obs: dict[str, list[dict[str, str]]] = {}
    for row in conditions:
        conditions_by_obs.setdefault((row.get("obs_id") or "").strip(), []).append(row)

    entities: list[dict[str, str]] = []
    facts: list[dict[str, str]] = []
    descriptions: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    source_counts: Counter[str] = Counter()
    relation_counts: Counter[str] = Counter()
    condition_entities: set[str] = set()
    condition_links = 0
    conditions_used: set[str] = set()

    for obs in observations:
        obs_id = (obs.get("obs_id") or "").strip()
        card_id = (obs.get("card_id") or "").strip()
        disease = (obs.get("disease_local") or "").strip()
        factor_local = (obs.get("factor_local") or "").strip()
        factor_class = (obs.get("factor_class") or "").strip()
        source_id = (obs.get("source_id") or "").strip()
        quote = (obs.get("quote") or "").strip()
        confidence = (obs.get("confidence") or "").strip()
        review = (obs.get("review_status") or "").strip()
        card = card_by_id.get(card_id, {})
        relation = (card.get("relation_type") or "").strip()
        locator = (card.get("locator") or "").strip()

        if review != "verified":
            skipped.append({"obs_id": obs_id, "reason": f"review_status={review}"})
            continue
        if relation == "control_only":
            skipped.append({"obs_id": obs_id, "reason": "control_only"})
            continue
        if relation not in {"direct", "vector_mediated"}:
            skipped.append({"obs_id": obs_id, "reason": f"relation_type={relation}"})
            continue
        if source_id != (card.get("source_id") or "").strip():
            skipped.append({"obs_id": obs_id, "reason": "source_id tidak cocok dengan card"})
            continue
        if not errors and source_by_id.get(source_id, {}).get("verification_status") in {"blocked_403", "binary_pdf"}:
            skipped.append({"obs_id": obs_id, "reason": "sumber belum dapat dipakai"})
            continue

        relation_counts[relation] += 1
        disease_label = disease_labels.get(disease, disease)
        label = f"{factor_local} pada {disease_label}"
        evidence_id = obs_id.replace("OBS_EXT_", "BUKTI_EXT_", 1)
        evidence_label = f"Bukti sumber: {factor_local} pada {disease_label}"
        source_document = source_id
        source_type = "external_evidence"
        notes = f"relation_type={relation}; locator={locator}; plant={obs.get('plant', '')}"
        source_counts[source_id] += 1

        entities.append(
            {
                "entity_local": obs_id,
                "entity_class": "ObservasiLingkungan",
                "label": label,
                "source_document": source_document,
                "source_id": card_id,
                "notes": notes,
            }
        )
        entities.append(
            {
                "entity_local": obs_id,
                "entity_class": factor_class,
                "label": label,
                "source_document": source_document,
                "source_id": card_id,
                "notes": notes,
            }
        )
        entities.append(
            {
                "entity_local": evidence_id,
                "entity_class": "BuktiSumber",
                "label": evidence_label,
                "source_document": source_document,
                "source_id": card_id,
                "notes": notes,
            }
        )
        descriptions.append(
            {
                "subject_local": obs_id,
                "subject_class": "ObservasiLingkungan",
                "literal_value": f"Observasi lingkungan: {factor_local} pada {disease_label}.",
                "literal_lang": "id",
                "source_document": source_document,
                "source_id": card_id,
                "review_status": review,
            }
        )
        descriptions.append(
            {
                "subject_local": evidence_id,
                "subject_class": "BuktiSumber",
                "literal_value": f"Bukti sumber: {factor_local} pada {disease_label}; {source_id}.",
                "literal_lang": "id",
                "source_document": source_document,
                "source_id": card_id,
                "review_status": review,
            }
        )

        def add_fact(
            subject_local: str,
            predicate: str,
            *,
            object_local: str = "",
            object_class: str = "",
            literal_value: str = "",
            literal_lang: str = "id",
        ) -> None:
            facts.append(
                {
                    "fact_id": f"EXT_F_{len(facts) + 1:04d}",
                    "subject_local": subject_local,
                    "subject_class": "ObservasiLingkungan",
                    "predicate": predicate,
                    "object_local": object_local,
                    "object_class": object_class,
                    "literal_value": literal_value,
                    "literal_lang": literal_lang,
                    "source_document": source_document,
                    "source_type": source_type,
                    "source_id": card_id,
                    "evidence_quote": quote,
                    "page": "",
                    "line_start": "",
                    "line_end": "",
                    "confidence": confidence,
                    "review_status": review,
                    "notes": notes,
                }
            )

        add_fact(obs_id, "memengaruhiPenyakit", object_local=disease, object_class="Penyakit")
        add_fact(disease, "dipengaruhiOleh", object_local=obs_id, object_class="ObservasiLingkungan")
        add_fact(obs_id, "didukungOleh", object_local=evidence_id, object_class="BuktiSumber")
        for condition in conditions_by_obs.get(obs_id, []):
            condition_local = (condition.get("condition_local") or "").strip()
            condition_label = (condition.get("condition_label") or condition_local).strip()
            if condition_local not in condition_entities:
                condition_entities.add(condition_local)
                entities.append(
                    {
                        "entity_local": condition_local,
                        "entity_class": "FaktorLingkungan",
                        "label": condition_label,
                        "source_document": "derived",
                        "source_id": "",
                        "notes": "kondisi observasi eksternal",
                    }
                )
            add_fact(
                obs_id,
                "menggambarkanKondisi",
                object_local=condition_local,
                object_class="FaktorLingkungan",
            )
            condition_links += 1
            conditions_used.add(condition_local)

        min_value = parse_number(obs.get("min_value", ""))
        max_value = parse_number(obs.get("max_value", ""))
        if min_value is not None and max_value is not None and min_value == max_value:
            add_fact(obs_id, "nilaiTunggal", literal_value=format_number(min_value), literal_lang="")
        else:
            if min_value is not None:
                add_fact(obs_id, "nilaiMin", literal_value=format_number(min_value), literal_lang="")
            if max_value is not None:
                add_fact(obs_id, "nilaiMaks", literal_value=format_number(max_value), literal_lang="")
        unit = (obs.get("satuan") or obs.get("unit") or "").strip()
        if unit:
            add_fact(obs_id, "satuan", literal_value=unit, literal_lang="")
        if (obs.get("operator") or "").strip():
            operator = (obs.get("operator") or "").strip()
            add_fact(
                obs_id,
                "operatorNilai",
                literal_value=OPERATOR_LABELS.get(operator, operator),
                literal_lang="",
            )
        if (obs.get("condition") or "").strip():
            add_fact(obs_id, "kondisi", literal_value=(obs.get("condition") or "").strip())
        add_fact(obs_id, "klasifikasiTurunan", literal_value=factor_local)

        evidence_facts = [
            ("dokumenSumber", source_id, ""),
            ("identifierSumber", locator, ""),
            ("kutipanSumber", quote, ""),
            ("kutipanNormalisasi", normalise_quote(quote), ""),
            (
                "catatanKualitas",
                f"confidence={confidence}; review_status={review}; relation_type={relation}",
                "id",
            ),
        ]
        for predicate, literal_value, literal_lang in evidence_facts:
            facts.append(
                {
                    "fact_id": f"EXT_F_{len(facts) + 1:04d}",
                    "subject_local": evidence_id,
                    "subject_class": "BuktiSumber",
                    "predicate": predicate,
                    "object_local": "",
                    "object_class": "",
                    "literal_value": literal_value,
                    "literal_lang": literal_lang,
                    "source_document": source_document,
                    "source_type": source_type,
                    "source_id": card_id,
                    "evidence_quote": quote,
                    "page": "",
                    "line_start": "",
                    "line_end": "",
                    "confidence": confidence,
                    "review_status": review,
                    "notes": notes,
                }
            )

    report = {
        "source_registry": display_path(SOURCE_REGISTRY),
        "cards": display_path(CARDS_CSV),
        "observations": display_path(OBSERVATIONS_CSV),
        "conditions": display_path(CONDITIONS_CSV),
        "sources": len(sources),
        "cards_total": len(cards),
        "observations_total": len(observations),
        "observations_generated": sum(relation_counts.values()),
        "condition_rows": len(conditions),
        "condition_links": condition_links,
        "conditions_used": len(conditions_used),
        "entities_generated": len(entities),
        "facts_generated": len(facts),
        "descriptions_generated": len(descriptions),
        "predicate_counts": dict(sorted(Counter(row["predicate"] for row in facts).items())),
        "relation_counts": dict(sorted(relation_counts.items())),
        "source_counts": dict(sorted(source_counts.items())),
        "skipped": skipped,
        "validation_errors": errors,
    }
    return entities, facts, descriptions, report, errors


def main() -> int:
    entities, facts, descriptions, report, errors = build()
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

    write_csv(
        OUT_DIR / "EXTERNAL_ENV_entities.csv",
        entities,
        ["entity_local", "entity_class", "label", "source_document", "source_id", "notes"],
    )
    write_csv(
        OUT_DIR / "EXTERNAL_ENV_descriptions.csv",
        descriptions,
        [
            "subject_local",
            "subject_class",
            "literal_value",
            "literal_lang",
            "source_document",
            "source_id",
            "review_status",
        ],
    )
    write_csv(
        OUT_DIR / "EXTERNAL_ENV_facts.csv",
        facts,
        [
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
        ],
    )
    print(f"output: {OUT_DIR / 'EXTERNAL_ENV_entities.csv'}")
    print(f"output: {OUT_DIR / 'EXTERNAL_ENV_facts.csv'}")
    print(f"output: {OUT_DIR / 'EXTERNAL_ENV_descriptions.csv'}")
    print(
        f"entities: {report['entities_generated']} facts: {report['facts_generated']} "
        f"descriptions: {report['descriptions_generated']}"
    )
    print(f"report: {REPORT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
