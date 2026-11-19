"""Bangun ontology_md.ttl dari ontology.ttl + fakta enrichment 7 tanaman."""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import OWL, RDF, RDFS, XSD

SWRL = Namespace("http://www.w3.org/2003/11/swrl#")

ONTO_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = ONTO_DIR.parent
sys.path.insert(0, str(ONTO_DIR))

from tbox import (  # noqa: E402
    CLASSES,
    DATA_PROPERTIES,
    KBR,
    MD_OBJECT_PROPERTIES,
    OBJECT_PROPERTIES,
    build_md_tbox,
)

TABLE_DIR = PROJECT_ROOT / "03_knowledge_tables"
FACTS_CSV = TABLE_DIR / "auto" / "DOC002_md" / "DOC002_enrichment_facts.csv"
ENTITIES_CSV = TABLE_DIR / "auto" / "DOC002_md" / "DOC002_enrichment_entities.csv"
DESCRIPTIONS_CSV = TABLE_DIR / "auto" / "DOC002_md" / "DOC002_descriptions.csv"
EXT_FACTS_CSV = TABLE_DIR / "auto" / "EXTERNAL_ENV" / "EXTERNAL_ENV_facts.csv"
EXT_ENTITIES_CSV = TABLE_DIR / "auto" / "EXTERNAL_ENV" / "EXTERNAL_ENV_entities.csv"
EXT_DESCRIPTIONS_CSV = TABLE_DIR / "auto" / "EXTERNAL_ENV" / "EXTERNAL_ENV_descriptions.csv"
GROWTH_CSV = TABLE_DIR / "curated" / "EXTERNAL_ENV" / "plant_growth_conditions.csv"
SWRL_RULES_TTL = ONTO_DIR / "swrl_rules.ttl"
EXT_REPORT_JSON = TABLE_DIR / "reports" / "EXTERNAL_ENV" / "external_env_report.json"
SOURCE_REGISTRY_CSV = PROJECT_ROOT / "01_knowledge_sources" / "external" / "source_registry.csv"
BASE_TTL = ONTO_DIR / "ontology.ttl"
OUTPUT_TTL = ONTO_DIR / "ontology_md.ttl"
OUTPUT_OWL = ONTO_DIR / "ontology_md.owl"
REPORT_JSON = ONTO_DIR / "extraction_report_md.json"

SCOPE_PLANTS = ["Padi", "Kedelai", "Jagung", "UbiJalar", "UbiKayu", "KacangTanah", "KacangHijau"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_csv_optional(path: Path) -> list[dict[str, str]]:
    return read_csv(path) if path.exists() else []


def add_entities(graph: Graph, rows: list[dict[str, str]]) -> None:
    for row in rows:
        local = (row.get("entity_local") or "").strip()
        class_name = (row.get("entity_class") or "").strip()
        if not local or not class_name:
            continue
        uri = KBR[local]
        graph.add((uri, RDF.type, KBR[class_name]))
        graph.add((uri, RDF.type, OWL.NamedIndividual))
        label = (row.get("label") or "").strip()
        if label:
            graph.add((uri, RDFS.label, Literal(label, lang="id")))


def _nl(text: str) -> str:
    """Samakan gaya akhir baris literal (CSV/Git bisa memakai CRLF)."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def add_swrl_rules(graph: Graph) -> int:
    if not SWRL_RULES_TTL.exists():
        return 0
    rules = Graph()
    rules.parse(SWRL_RULES_TTL, format="turtle")
    for triple in rules:
        graph.add(triple)
    return len(list(rules.subjects(RDF.type, SWRL.Imp)))


def growth_condition_facts() -> list[dict[str, str]]:
    facts: list[dict[str, str]] = []
    for row in read_csv_optional(GROWTH_CSV):
        plant = (row.get("plant") or "").strip()
        condition = (row.get("condition_local") or "").strip()
        source_id = (row.get("source_id") or "").strip()
        quote = (row.get("quote") or "").strip()
        if not plant or not condition or not source_id or not quote:
            continue
        facts.append(
            {
                "fact_id": (row.get("condition_id") or "").strip(),
                "subject_local": plant,
                "subject_class": "TanamanPangan",
                "predicate": "memilikiKondisiTumbuh",
                "object_local": condition,
                "object_class": "FaktorLingkungan",
                "literal_value": "",
                "literal_lang": "",
                "source_document": source_id,
                "source_type": "external_growth_condition",
                "source_id": source_id,
                "evidence_quote": quote,
                "page": "",
                "line_start": "",
                "line_end": "",
                "confidence": (row.get("confidence") or "medium").strip(),
                "review_status": (row.get("review_status") or "verified").strip(),
                "notes": (row.get("locator") or "").strip(),
            }
        )
    return facts


def add_facts(graph: Graph, rows: list[dict[str, str]]) -> None:
    for row in rows:
        subject_local = (row.get("subject_local") or "").strip()
        predicate = (row.get("predicate") or "").strip()
        if not subject_local or not predicate:
            continue
        subject = KBR[subject_local]
        prop = KBR[predicate]
        object_local = (row.get("object_local") or "").strip()
        if object_local:
            graph.add((subject, prop, KBR[object_local]))
            continue
        literal_value = _nl(row.get("literal_value") or "").strip()
        if not literal_value:
            continue
        lang = (row.get("literal_lang") or "").strip() or None
        if predicate in {"nilaiMin", "nilaiMaks", "nilaiTunggal"}:
            graph.add((subject, prop, Literal(float(literal_value), datatype=XSD.decimal)))
            continue
        graph.add((subject, prop, Literal(literal_value, lang=lang)))


def add_descriptions(graph: Graph, rows: list[dict[str, str]]) -> None:
    for row in rows:
        subject_local = (row.get("subject_local") or "").strip()
        literal_value = _nl(row.get("literal_value") or "").strip()
        if not subject_local or not literal_value:
            continue
        lang = (row.get("literal_lang") or "").strip() or "id"
        graph.add((KBR[subject_local], RDFS.comment, Literal(literal_value, lang=lang)))


def validate(
    graph: Graph,
    base_triples: set,
    entities: list[dict[str, str]],
    facts: list[dict[str, str]],
    descriptions: list[dict[str, str]],
) -> list[str]:
    errors: list[str] = []
    named = set(graph.subjects(RDF.type, OWL.NamedIndividual))
    classes = set(graph.subjects(RDF.type, OWL.Class))
    known_classes = set(CLASSES)
    allowed_predicates = (
        set(OBJECT_PROPERTIES) | set(DATA_PROPERTIES) | set(MD_OBJECT_PROPERTIES)
    )

    missing_base = base_triples - set(graph)
    if missing_base:
        errors.append(f"{len(missing_base)} triple kanonik hilang dari hasil enrichment")

    for row in entities:
        local = (row.get("entity_local") or "").strip()
        class_name = (row.get("entity_class") or "").strip()
        if not local:
            errors.append("entitas tanpa entity_local")
            continue
        if class_name not in known_classes:
            errors.append(f"kelas entitas tidak dikenal: {local} -> {class_name}")
        uri = KBR[local]
        if uri not in named:
            errors.append(f"entitas bukan NamedIndividual: {local}")
        if not graph.value(uri, RDFS.label):
            errors.append(f"entitas tanpa label: {local}")

    for row in facts:
        subject_local = (row.get("subject_local") or "").strip()
        predicate = (row.get("predicate") or "").strip()
        object_local = (row.get("object_local") or "").strip()
        literal_value = _nl(row.get("literal_value") or "").strip()
        literal_lang = (row.get("literal_lang") or "").strip()
        if not subject_local or predicate not in allowed_predicates:
            errors.append(f"fakta dengan subjek/predikat tidak valid: {subject_local} {predicate}")
            continue
        subject = KBR[subject_local]
        if subject not in named:
            errors.append(f"subjek fakta bukan NamedIndividual: {subject_local}")
        if object_local:
            obj = KBR[object_local]
            if obj not in named:
                errors.append(f"objek fakta bukan NamedIndividual: {object_local}")
        elif not literal_value:
            errors.append(f"fakta tanpa objek/literal: {subject_local} {predicate}")
        if literal_lang and literal_lang != "id":
            errors.append(f"tag bahasa fakta bukan id: {subject_local} {predicate}")

    for row in descriptions:
        subject_local = (row.get("subject_local") or "").strip()
        literal_value = _nl(row.get("literal_value") or "").strip()
        literal_lang = (row.get("literal_lang") or "").strip() or "id"
        if not subject_local or not literal_value:
            errors.append("deskripsi tanpa subjek/literal")
            continue
        subject = KBR[subject_local]
        if subject not in named and subject not in classes:
            errors.append(f"subjek deskripsi tidak dikenal: {subject_local}")
        if literal_lang != "id":
            errors.append(f"tag bahasa deskripsi bukan id: {subject_local}")
    return errors


def build() -> tuple[Graph, dict, list[str]]:
    base = Graph()
    base.parse(BASE_TTL, format="turtle")
    base_triples = set(base)

    graph = Graph()
    for triple in base_triples:
        graph.add(triple)
    build_md_tbox(graph)

    internal_entities = read_csv(ENTITIES_CSV)
    internal_facts = read_csv(FACTS_CSV)
    ext_entities = read_csv_optional(EXT_ENTITIES_CSV)
    growth_facts = growth_condition_facts()
    ext_facts = read_csv_optional(EXT_FACTS_CSV) + growth_facts
    ext_descriptions = read_csv_optional(EXT_DESCRIPTIONS_CSV)
    entities = internal_entities + ext_entities
    facts = internal_facts + ext_facts
    descriptions = read_csv(DESCRIPTIONS_CSV) + ext_descriptions
    add_entities(graph, entities)
    add_facts(graph, facts)
    add_descriptions(graph, descriptions)
    swrl_rule_count = add_swrl_rules(graph)
    errors = validate(graph, base_triples, entities, facts, descriptions)

    added = len(set(graph) - base_triples)
    predicate_counts = Counter(
        str(prop).rsplit("#", 1)[-1]
        for _, prop, _ in graph
        if str(prop).startswith(str(KBR))
    )
    entity_counts = Counter(row["entity_class"] for row in entities)
    description_counts = Counter(row["subject_class"] for row in descriptions)
    description_status = Counter(row["review_status"] for row in descriptions)
    external_sources = read_csv_optional(SOURCE_REGISTRY_CSV)
    external_report = (
        json.loads(EXT_REPORT_JSON.read_text(encoding="utf-8"))
        if EXT_REPORT_JSON.exists()
        else {}
    )
    report = {
        "base": str(BASE_TTL.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "output": str(OUTPUT_TTL.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "base_triples": len(base),
        "added_triples": added,
        "total_triples": len(graph),
        "facts": len(facts),
        "internal_facts": len(internal_facts),
        "external_facts": len(ext_facts),
        "predicate_counts": dict(sorted(predicate_counts.items())),
        "entities": len(entities),
        "internal_entities": len(internal_entities),
        "external_entities": len(ext_entities),
        "growth_condition_facts": len(growth_facts),
        "swrl_rules": swrl_rule_count,
        "entity_counts": dict(sorted(entity_counts.items())),
        "descriptions": len(descriptions),
        "internal_descriptions": len(descriptions) - len(ext_descriptions),
        "external_descriptions": len(ext_descriptions),
        "description_counts": dict(sorted(description_counts.items())),
        "description_status": dict(sorted(description_status.items())),
        "named_individuals": sum(
            1 for _ in graph.subjects(RDF.type, OWL.NamedIndividual)
        ),
        "classes_with_comment": sum(
            1
            for cls in graph.subjects(RDF.type, OWL.Class)
            if (cls, RDFS.comment, None) in graph
        ),
        "scope_plants": SCOPE_PLANTS,
        "canonical_untouched": not (base_triples - set(graph)),
        "external": {
            "source_registry": str(SOURCE_REGISTRY_CSV.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "source_count": len(external_sources),
            "sources": [row.get("source_id", "") for row in external_sources],
            "facts": len(ext_facts),
            "growth_condition_facts": len(growth_facts),
            "entities": len(ext_entities),
            "descriptions": len(ext_descriptions),
            "observations_generated": external_report.get("observations_generated", 0),
            "report": str(EXT_REPORT_JSON.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        },
        "validation_errors": errors,
    }
    return graph, report, errors


def main() -> int:
    graph, report, errors = build()
    if errors:
        print("VALIDASI GAGAL:")
        for error in errors:
            print(f"  - {error}")
        return 1
    OUTPUT_TTL.write_text(
        graph.serialize(format="turtle"), encoding="utf-8", newline=""
    )
    OUTPUT_OWL.write_text(
        graph.serialize(format="xml"), encoding="utf-8", newline=""
    )
    REPORT_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="",
    )
    print(f"output: {OUTPUT_TTL}")
    print(f"output: {OUTPUT_OWL}")
    print(f"triples: {report['total_triples']} (base {report['base_triples']}, added {report['added_triples']})")
    print(f"facts: {report['facts']} entities: {report['entities']}")
    print(
        f"descriptions: {report['descriptions']} "
        f"(individuals {report['named_individuals']}, classes with comment {report['classes_with_comment']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
