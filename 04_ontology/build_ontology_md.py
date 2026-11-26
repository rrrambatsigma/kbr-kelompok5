"""Bangun ontology_md.ttl dari ontology.ttl + fakta enrichment 7 tanaman."""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from rdflib import BNode, Graph, Literal, Namespace
from rdflib.namespace import OWL, RDF, RDFS, XSD

SWRL = Namespace("http://www.w3.org/2003/11/swrl#")
SWRLA = Namespace("http://swrl.stanford.edu/ontologies/3.3/swrla.owl#")

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
PHASE_CSV = TABLE_DIR / "curated" / "EXTERNAL_ENV" / "plant_growth_phases.csv"
EXT_VARIETY_CSV = TABLE_DIR / "curated" / "EXTERNAL_ENV" / "external_varieties.csv"
SWRL_RULES_TTL = ONTO_DIR / "swrl_rules.ttl"
EXT_REPORT_JSON = TABLE_DIR / "reports" / "EXTERNAL_ENV" / "external_env_report.json"
SOURCE_REGISTRY_CSV = PROJECT_ROOT / "01_knowledge_sources" / "external" / "source_registry.csv"
BASE_TTL = ONTO_DIR / "ontology.ttl"
OUTPUT_TTL = ONTO_DIR / "ontology_md.ttl"
OUTPUT_OWL = ONTO_DIR / "ontology_md.owl"
REPORT_JSON = ONTO_DIR / "extraction_report_md.json"

SCOPE_PLANTS = ["Padi", "Kedelai", "Jagung", "UbiJalar", "UbiKayu", "KacangTanah", "KacangHijau"]


def condition_class(local: str, default: str) -> str:
    if local.startswith("KondisiCahaya"):
        return "IntensitasCahaya"
    if local.startswith("KondisiDataran"):
        return "KetinggianTempat"
    if local.startswith("KondisiDrainase"):
        return "KondisiDrainase"
    if local.startswith(("KondisiTanahGembur", "KondisiTanahBerpasir", "KondisiTanahLiat")):
        return "TeksturTanah"
    if local.startswith("KondisiTanah"):
        return "KondisiTanah"
    if local.startswith("KondisiKelembapanTanah"):
        return "KelembapanTanah"
    if local.startswith("KondisiSuhu"):
        return "Suhu"
    if local.startswith("KondisiCurahHujan"):
        return "CurahHujan"
    if local.startswith("KondisiKelembapanUdara"):
        return "KelembapanUdara"
    if local.startswith("KondisiMusim"):
        return "Musim"
    if local.startswith("KondisiIklim"):
        return "Iklim"
    return default


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
        class_name = condition_class(local, class_name)
        uri = KBR[local]
        graph.add((uri, RDF.type, KBR[class_name]))
        graph.add((uri, RDF.type, OWL.NamedIndividual))
        label = (row.get("label") or "").strip()
        if label:
            graph.add((uri, RDFS.label, Literal(label, lang="id")))
        comment = (row.get("comment") or "").strip()
        if comment:
            graph.add((uri, RDFS.comment, Literal(comment, lang="id")))


def _nl(text: str) -> str:
    """Samakan gaya akhir baris literal (CSV/Git bisa memakai CRLF)."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _mark_swrl_atom_list(graph: Graph, node) -> None:
    seen = set()
    while node and node != RDF.nil and node not in seen:
        seen.add(node)
        graph.add((node, RDF.type, SWRL.AtomList))
        node = next(graph.objects(node, RDF.rest), None)


def _local_name(iri) -> str:
    text = str(iri)
    for sep in ("#", "/"):
        if sep in text:
            text = text.rsplit(sep, 1)[-1]
    return text


def add_swrl_rules(graph: Graph) -> int:
    if not SWRL_RULES_TTL.exists():
        return 0
    rules = Graph()
    rules.parse(SWRL_RULES_TTL, format="turtle")
    imps = list(rules.subjects(RDF.type, SWRL.Imp))
    named = set(imps)
    for subject, predicate, obj in rules:
        if subject in named:
            continue
        graph.add((subject, predicate, obj))
    for imp in imps:
        node = BNode()
        graph.add((node, RDF.type, SWRL.Imp))
        for predicate in (SWRL.body, SWRL.head):
            for atom_list in rules.objects(imp, predicate):
                graph.add((node, predicate, atom_list))
                _mark_swrl_atom_list(graph, atom_list)
        graph.add((node, RDFS.label, Literal(_local_name(imp))))
        for label in rules.objects(imp, RDFS.label):
            graph.add((node, RDFS.comment, Literal(str(label))))
        graph.add((node, SWRLA.isRuleEnabled, Literal(True)))
    return len(imps)


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


def plant_phase_rows() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    entities: list[dict[str, str]] = []
    facts: list[dict[str, str]] = []
    for row in read_csv_optional(PHASE_CSV):
        plant = (row.get("plant") or "").strip()
        local = (row.get("phase_local") or "").strip()
        label = (row.get("phase_label") or "").strip()
        phase_class = (row.get("phase_class") or "").strip()
        source_id = (row.get("source_id") or "").strip()
        quote = (row.get("quote") or "").strip()
        if not (plant and local and label and phase_class and source_id and quote):
            continue
        locator = (row.get("locator") or "").strip()
        entities.append(
            {
                "entity_local": local,
                "entity_class": phase_class,
                "label": label,
                "source_document": source_id,
                "source_id": source_id,
                "notes": locator,
                "comment": "Fase pertumbuhan tanaman yang disebut pada sumber.",
            }
        )
        facts.append(
            {
                "fact_id": (row.get("phase_id") or "").strip(),
                "subject_local": plant,
                "subject_class": "TanamanPangan",
                "predicate": "memilikiFasePertumbuhan",
                "object_local": local,
                "object_class": "FasePertumbuhan",
                "literal_value": "",
                "literal_lang": "",
                "source_document": source_id,
                "source_type": "external_growth_phase",
                "source_id": source_id,
                "evidence_quote": quote,
                "page": "",
                "line_start": "",
                "line_end": "",
                "confidence": (row.get("confidence") or "medium").strip(),
                "review_status": (row.get("review_status") or "verified").strip(),
                "notes": locator,
            }
        )
    return entities, facts


def external_variety_rows() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    entities: list[dict[str, str]] = []
    facts: list[dict[str, str]] = []
    for row in read_csv_optional(EXT_VARIETY_CSV):
        plant = (row.get("plant") or "").strip()
        local = (row.get("variety_local") or "").strip()
        label = (row.get("variety_label") or "").strip()
        disease = (row.get("disease_local") or "").strip()
        relation = (row.get("relation") or "").strip().lower()
        source_id = (row.get("source_id") or "").strip()
        quote = (row.get("quote") or "").strip()
        if not (plant and local and label and disease and source_id and quote):
            continue
        if relation not in {"tahan", "rentan"}:
            continue
        locator = (row.get("locator") or "").strip()
        base = {
            "source_document": source_id,
            "source_id": source_id,
            "evidence_quote": quote,
            "page": "",
            "line_start": "",
            "line_end": "",
            "confidence": (row.get("confidence") or "medium").strip(),
            "review_status": (row.get("review_status") or "verified").strip(),
            "notes": locator,
        }
        entities.append(
            {
                "entity_local": local,
                "entity_class": "Varietas",
                "label": label,
                "source_document": source_id,
                "source_id": source_id,
                "notes": locator,
                "comment": "Varietas tanaman yang disebut pada sumber.",
            }
        )
        facts.append(
            {
                "fact_id": (row.get("variety_id") or "").strip() + "_plant",
                "subject_local": plant,
                "subject_class": "TanamanPangan",
                "predicate": "memilikiVarietas",
                "object_local": local,
                "object_class": "Varietas",
                "literal_value": "",
                "literal_lang": "",
                "source_type": "external_variety",
                **base,
            }
        )
        facts.append(
            {
                "fact_id": (row.get("variety_id") or "").strip() + "_resistance",
                "subject_local": local,
                "subject_class": "Varietas",
                "predicate": f"{relation}Terhadap",
                "object_local": disease,
                "object_class": "Penyakit",
                "literal_value": "",
                "literal_lang": "",
                "source_type": "external_variety",
                **base,
            }
        )
    return entities, facts


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


def _local(node) -> str:
    return str(node).split("#")[-1]


def add_demo_diagnoses(graph: Graph, report: dict) -> int:
    diseases = sorted(set(graph.subjects(RDF.type, KBR.Penyakit)), key=_local)
    count = 0
    for disease in diseases:
        plants = sorted(set(graph.objects(disease, KBR.menyerangTanaman)), key=_local)
        if not plants:
            continue
        plant = plants[0]
        by_canonical: dict = defaultdict(list)
        for observation in graph.objects(disease, KBR.memilikiGejala):
            for canonical in graph.objects(observation, KBR.memilikiGejalaKanonik):
                by_canonical[canonical].append(observation)

        chosen = []
        canonical_keys = sorted(by_canonical, key=_local)
        if canonical_keys:
            chosen.append(by_canonical[canonical_keys[0]][0])
            if len(canonical_keys) > 1:
                for observation in by_canonical[canonical_keys[1]]:
                    if observation not in chosen:
                        chosen.append(observation)
                        break

        environmental_values = []
        for condition in graph.objects(disease, KBR.dipengaruhiOleh):
            if (condition, RDF.type, KBR.ObservasiLingkungan) in graph:
                environmental_values.extend(graph.objects(condition, KBR.klasifikasiTurunan))

        if not chosen and not environmental_values:
            continue

        disease_label = graph.value(disease, RDFS.label) or _local(disease)
        plant_label = graph.value(plant, RDFS.label) or _local(plant)
        local = "Diagnosis" + _local(disease)
        uri = KBR[local]
        graph.add((uri, RDF.type, KBR.Diagnosis))
        graph.add((uri, RDF.type, OWL.NamedIndividual))
        graph.add((uri, RDFS.label, Literal(f"Kasus demo: {plant_label} - {disease_label}", lang="id")))
        graph.add((uri, RDFS.comment, Literal("Kasus observasi demo; diagnosis dan rekomendasi dihasilkan oleh Pellet dari SWRL.", lang="id")))
        graph.add((uri, KBR.memilikiTanaman, plant))
        for observation in chosen:
            graph.add((uri, KBR.memilikiObservasi, observation))

        if environmental_values:
            env_local = "ObservasiLingkungan" + _local(disease)
            env_uri = KBR[env_local]
            graph.add((env_uri, RDF.type, KBR.ObservasiLingkungan))
            graph.add((env_uri, RDF.type, OWL.NamedIndividual))
            graph.add((env_uri, RDFS.label, Literal(f"Observasi lingkungan demo: {disease_label}", lang="id")))
            graph.add((env_uri, RDFS.comment, Literal(f"Observasi lingkungan untuk kasus demo {disease_label}.", lang="id")))
            graph.add((env_uri, KBR.klasifikasiTurunan, environmental_values[0]))
            graph.add((uri, KBR.memilikiObservasi, env_uri))
        count += 1
    report["diagnoses"] = count
    return count


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
    phase_entities, phase_facts = plant_phase_rows()
    variety_entities, variety_facts = external_variety_rows()
    ext_facts = read_csv_optional(EXT_FACTS_CSV) + growth_facts
    ext_descriptions = read_csv_optional(EXT_DESCRIPTIONS_CSV)
    entities = internal_entities + ext_entities + phase_entities + variety_entities
    facts = internal_facts + ext_facts + phase_facts + variety_facts
    descriptions = read_csv(DESCRIPTIONS_CSV) + ext_descriptions
    add_entities(graph, entities)
    add_facts(graph, facts)
    add_descriptions(graph, descriptions)
    diagnosis_count = add_demo_diagnoses(graph, {})
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
        "plant_phase_entities": len(phase_entities),
        "plant_phase_facts": len(phase_facts),
        "external_variety_entities": len(variety_entities),
        "external_variety_facts": len(variety_facts),
        "swrl_rules": swrl_rule_count,
        "diagnoses": diagnosis_count,
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
