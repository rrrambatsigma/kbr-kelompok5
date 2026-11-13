"""Bangun ontology_md.ttl dari ontology.ttl + fakta enrichment 7 tanaman."""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

from rdflib import Graph, Literal
from rdflib.namespace import OWL, RDF, RDFS

ONTO_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = ONTO_DIR.parent
sys.path.insert(0, str(ONTO_DIR))

from tbox import KBR, build_md_tbox  # noqa: E402

TABLE_DIR = PROJECT_ROOT / "03_knowledge_tables"
FACTS_CSV = TABLE_DIR / "auto" / "DOC002_md" / "DOC002_enrichment_facts.csv"
ENTITIES_CSV = TABLE_DIR / "auto" / "DOC002_md" / "DOC002_enrichment_entities.csv"
DESCRIPTIONS_CSV = TABLE_DIR / "auto" / "DOC002_md" / "DOC002_descriptions.csv"
BASE_TTL = ONTO_DIR / "ontology.ttl"
OUTPUT_TTL = ONTO_DIR / "ontology_md.ttl"
OUTPUT_OWL = ONTO_DIR / "ontology_md.owl"
REPORT_JSON = ONTO_DIR / "extraction_report_md.json"

SCOPE_PLANTS = ["Padi", "Kedelai", "Jagung", "UbiJalar", "UbiKayu", "KacangTanah", "KacangHijau"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


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
        graph.add((subject, prop, Literal(literal_value, lang=lang)))


def add_descriptions(graph: Graph, rows: list[dict[str, str]]) -> None:
    for row in rows:
        subject_local = (row.get("subject_local") or "").strip()
        literal_value = _nl(row.get("literal_value") or "").strip()
        if not subject_local or not literal_value:
            continue
        lang = (row.get("literal_lang") or "").strip() or "id"
        graph.add((KBR[subject_local], RDFS.comment, Literal(literal_value, lang=lang)))


def build() -> tuple[Graph, dict]:
    base = Graph()
    base.parse(BASE_TTL, format="turtle")
    base_triples = set(base)

    graph = Graph()
    for triple in base_triples:
        graph.add(triple)
    build_md_tbox(graph)

    entities = read_csv(ENTITIES_CSV)
    facts = read_csv(FACTS_CSV)
    descriptions = read_csv(DESCRIPTIONS_CSV)
    add_entities(graph, entities)
    add_facts(graph, facts)
    add_descriptions(graph, descriptions)

    added = len(set(graph) - base_triples)
    predicate_counts = Counter(row["predicate"] for row in facts)
    entity_counts = Counter(row["entity_class"] for row in entities)
    description_counts = Counter(row["subject_class"] for row in descriptions)
    description_status = Counter(row["review_status"] for row in descriptions)
    report = {
        "base": str(BASE_TTL.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "output": str(OUTPUT_TTL.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "base_triples": len(base),
        "added_triples": added,
        "total_triples": len(graph),
        "facts": len(facts),
        "predicate_counts": dict(sorted(predicate_counts.items())),
        "entities": len(entities),
        "entity_counts": dict(sorted(entity_counts.items())),
        "descriptions": len(descriptions),
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
        "canonical_untouched": True,
    }
    return graph, report


def main() -> int:
    graph, report = build()
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
