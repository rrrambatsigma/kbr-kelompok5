"""Bangun ontology_md.ttl dari ontology.ttl + fakta enrichment 7 tanaman."""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

import definitions as defs  # noqa: E402
import knowledge  # noqa: E402

SWRL = Namespace("http://www.w3.org/2003/11/swrl#")
SWRLA = Namespace("http://swrl.stanford.edu/ontologies/3.3/swrla.owl#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
DCTERMS = Namespace("http://purl.org/dc/terms/")
PROV = Namespace("http://www.w3.org/ns/prov#")

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
EXT_CONTROL_ENTITIES_CSV = TABLE_DIR / "auto" / "EXTERNAL_ENV" / "EXTERNAL_ENV_controls_entities.csv"
EXT_CONTROL_FACTS_CSV = TABLE_DIR / "auto" / "EXTERNAL_ENV" / "EXTERNAL_ENV_controls_facts.csv"
GROWTH_CSV = TABLE_DIR / "curated" / "EXTERNAL_ENV" / "plant_growth_conditions.csv"
PHASE_CSV = TABLE_DIR / "curated" / "EXTERNAL_ENV" / "plant_growth_phases.csv"
EXT_VARIETY_CSV = TABLE_DIR / "curated" / "EXTERNAL_ENV" / "external_varieties.csv"
SWRL_RULES_TTL = ONTO_DIR / "swrl_rules.ttl"
ALIGNMENTS_CSV = TABLE_DIR / "curated" / "external_ontology" / "alignments.csv"
EXT_REPORT_JSON = TABLE_DIR / "reports" / "EXTERNAL_ENV" / "external_env_report.json"
SOURCE_REGISTRY_CSV = PROJECT_ROOT / "01_knowledge_sources" / "external" / "source_registry.csv"
BASE_TTL = ONTO_DIR / "ontology.ttl"
DEMO_CASES_TTL = ONTO_DIR / "demo_cases.ttl"
OUTPUT_TTL = ONTO_DIR / "ontology_md.ttl"
OUTPUT_OWL = ONTO_DIR / "ontology_md.owl"
REPORT_JSON = ONTO_DIR / "extraction_report_md.json"

SCOPE_PLANTS = knowledge.PLANT_ORDER


def condition_class(local: str, default: str) -> str:
    return knowledge.condition_class(local, default)


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
            graph.add((node, RDFS.comment, Literal(str(label), lang="id")))
        graph.add((node, SWRLA.isRuleEnabled, Literal(True)))
    return len(imps)


RELATION_SPECS = {
    "equivalentClass": (OWL.equivalentClass, {"Class"}, {"Class"}),
    "sameAs": (OWL.sameAs, {"Individual"}, {"Individual"}),
    "subClassOf": (RDFS.subClassOf, {"Class"}, {"Class"}),
    "subPropertyOf": (RDFS.subPropertyOf, {"Property"}, {"Property"}),
    "exactMatch": (SKOS.exactMatch, None, None),
    "closeMatch": (SKOS.closeMatch, None, None),
}


def add_external_alignments(graph: Graph) -> tuple[Counter, list[str]]:
    rows = read_csv_optional(ALIGNMENTS_CSV)
    errors: list[str] = []
    counts: Counter = Counter()
    for row in rows:
        local = (row.get("kbr_local") or "").strip()
        external = (row.get("external_iri") or "").strip()
        relation = (row.get("relation") or "").strip()
        source_id = (row.get("source_id") or "").strip()
        kind = (row.get("kbr_kind") or "").strip()
        external_kind = (row.get("external_kind") or "").strip()
        spec = RELATION_SPECS.get(relation)
        if spec is None:
            errors.append(f"alignment relation tidak valid: {local} {relation!r}")
            continue
        if not local or not external or not source_id:
            errors.append(
                f"alignment tidak lengkap: {local!r} {external!r} {source_id!r}"
            )
            continue
        predicate, local_kinds, external_kinds = spec
        if local_kinds and kind not in local_kinds:
            errors.append(
                f"alignment kbr_kind tidak cocok untuk {relation}: {local} {kind!r}"
            )
            continue
        if external_kinds and external_kind not in external_kinds:
            errors.append(
                f"alignment external_kind tidak cocok untuk {relation}: "
                f"{local} {external_kind!r}"
            )
            continue
        subject = KBR[local]
        if subject not in set(graph.subjects(RDF.type, None)):
            errors.append(f"alignment subjek tidak ada: {local}")
            continue
        if kind == "Class" and (subject, RDF.type, OWL.Class) not in graph:
            errors.append(f"alignment kbr_kind Class tidak cocok: {local}")
            continue
        if kind == "Individual" and (subject, RDF.type, OWL.NamedIndividual) not in graph:
            errors.append(f"alignment kbr_kind Individual tidak cocok: {local}")
            continue
        if kind == "Property" and not (
            (subject, RDF.type, OWL.ObjectProperty) in graph
            or (subject, RDF.type, OWL.DatatypeProperty) in graph
        ):
            errors.append(f"alignment kbr_kind Property tidak cocok: {local}")
            continue
        graph.add((subject, predicate, URIRef(external)))
        counts[relation] += 1
    return counts, errors


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
        phase_id = (row.get("phase_id") or "").strip()
        confidence = (row.get("confidence") or "medium").strip()
        review_status = (row.get("review_status") or "verified").strip()
        facts.append(
            {
                "fact_id": phase_id,
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
                "confidence": confidence,
                "review_status": review_status,
                "notes": locator,
            }
        )
        base = {
            "subject_local": local,
            "subject_class": phase_class,
            "source_type": "external_growth_phase",
            "source_document": source_id,
            "source_id": source_id,
            "evidence_quote": quote,
            "page": "",
            "line_start": "",
            "line_end": "",
            "confidence": confidence,
            "review_status": review_status,
            "notes": locator,
        }
        for predicate, key, suffix in (
            ("mulaiFase", "start", "_start"),
            ("selesaiFase", "end", "_end"),
        ):
            value = (row.get(key) or "").strip()
            if not value:
                continue
            facts.append(
                {
                    "fact_id": phase_id + suffix,
                    "predicate": predicate,
                    "literal_value": value,
                    "literal_lang": "",
                    **base,
                }
            )
        unit = (row.get("unit") or "").strip()
        if unit:
            facts.append(
                {
                    "fact_id": phase_id + "_unit",
                    "predicate": "satuanFase",
                    "literal_value": unit,
                    "literal_lang": "",
                    **base,
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
        if predicate in {"nilaiMin", "nilaiMaks", "nilaiTunggal", "mulaiFase", "selesaiFase"}:
            graph.add((subject, prop, Literal(float(literal_value), datatype=XSD.decimal)))
            continue
        graph.add((subject, prop, Literal(literal_value, lang=lang)))


def add_descriptions(graph: Graph, rows: list[dict[str, str]]) -> int:
    skipped = 0
    for row in rows:
        subject_local = (row.get("subject_local") or "").strip()
        literal_value = _nl(row.get("literal_value") or "").strip()
        if not subject_local or not literal_value:
            continue
        subject = KBR[subject_local]
        # Konsep yang sudah punya definisi tidak perlu komentar kutipan sumber;
        # kutipan tetap tersimpan pada deskripsi/Bukti.
        if any(graph.objects(subject, SKOS.definition)):
            skipped += 1
            continue
        lang = (row.get("literal_lang") or "").strip() or "id"
        graph.add((subject, RDFS.comment, Literal(literal_value, lang=lang)))
    return skipped


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


def apply_entity_definitions(graph: Graph) -> None:
    """Terapkan definisi entity dari katalog RDF untuk subjek yang sudah ada."""
    for local, (definition, source) in knowledge.ENTITY_DEFINITIONS.items():
        node = KBR[local]
        if (node, RDF.type, OWL.NamedIndividual) not in graph:
            continue
        if any(graph.objects(node, SKOS.definition)):
            continue
        graph.add((node, SKOS.definition, Literal(definition, lang="id")))
        if source:
            graph.add((node, DCTERMS.source, Literal(source, lang="id")))


def apply_phase_metadata(graph: Graph) -> None:
    """Terapkan urutan, label Inggris, dan sinonim fase dari katalog RDF."""
    for node in graph.subjects(RDF.type, OWL.NamedIndividual):
        types = [
            str(item).split("#")[-1]
            for item in graph.objects(node, RDF.type)
            if isinstance(item, URIRef) and str(item).startswith(str(KBR))
        ]
        phase_type = next((item for item in types if item in defs.PHASE_DEFINITIONS), None)
        if phase_type is None:
            continue
        spec = defs.PHASE_DEFINITIONS[phase_type]
        english = spec.get("english")
        if english:
            graph.add((node, SKOS.prefLabel, Literal(english, lang="en")))
        for synonym in spec.get("synonyms", []):
            graph.add((node, SKOS.altLabel, Literal(synonym, lang="id")))
        rank = defs.PHASE_STAGE_ORDER.get(phase_type)
        if rank is not None:
            graph.add((node, KBR["urutanFase"], Literal(rank, datatype=XSD.integer)))


def add_external_source_links(graph: Graph) -> int:
    """Hubungkan node bukti ke referensi eksternal yang menyimpan URL."""
    ref_by_source: dict[str, URIRef] = {}
    for ref in graph.subjects(KBR["identifierSumber"], None):
        for value in graph.objects(ref, KBR["identifierSumber"]):
            text = str(value)
            if text.startswith(("SRC_EXT_", "SRC_ONTO_")):
                ref_by_source[text] = ref
    linked = 0
    for subject in set(graph.subjects(KBR["dokumenSumber"], None)):
        for value in graph.objects(subject, KBR["dokumenSumber"]):
            ref = ref_by_source.get(str(value))
            if ref is None:
                continue
            triple = (subject, PROV.wasDerivedFrom, ref)
            if triple not in graph:
                graph.add(triple)
                linked += 1
    return linked


def build() -> tuple[Graph, dict, list[str]]:
    base = Graph()
    base.parse(BASE_TTL, format="turtle")
    base_triples = set(base)

    graph = Graph()
    for triple in base_triples:
        graph.add(triple)
    build_md_tbox(graph)
    if DEMO_CASES_TTL.exists():
        graph.parse(DEMO_CASES_TTL, format="turtle")
    diagnosis_count = len(set(graph.subjects(RDF.type, KBR.Diagnosis)))

    internal_entities = read_csv(ENTITIES_CSV)
    internal_facts = read_csv(FACTS_CSV)
    ext_entities = read_csv_optional(EXT_ENTITIES_CSV)
    growth_facts = growth_condition_facts()
    phase_entities, phase_facts = plant_phase_rows()
    variety_entities, variety_facts = external_variety_rows()
    ext_facts = read_csv_optional(EXT_FACTS_CSV) + growth_facts
    ext_descriptions = read_csv_optional(EXT_DESCRIPTIONS_CSV)
    ext_control_entities = read_csv_optional(EXT_CONTROL_ENTITIES_CSV)
    ext_control_facts = read_csv_optional(EXT_CONTROL_FACTS_CSV)
    entities = (
        internal_entities
        + ext_entities
        + phase_entities
        + variety_entities
        + ext_control_entities
    )
    facts = internal_facts + ext_facts + phase_facts + variety_facts + ext_control_facts
    descriptions = read_csv(DESCRIPTIONS_CSV) + ext_descriptions
    add_entities(graph, entities)
    add_facts(graph, facts)
    external_source_links = add_external_source_links(graph)
    apply_entity_definitions(graph)
    apply_phase_metadata(graph)
    skipped_descriptions = add_descriptions(graph, descriptions)
    swrl_rule_count = add_swrl_rules(graph)
    alignment_counts, alignment_errors = add_external_alignments(graph)
    errors = validate(graph, base_triples, entities, facts, descriptions) + alignment_errors

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
        "external_control_entities": len(ext_control_entities),
        "external_control_facts": len(ext_control_facts),
        "external_source_links": external_source_links,
        "swrl_rules": swrl_rule_count,
        "external_alignments": sum(alignment_counts.values()),
        "external_alignments_equivalent_class": alignment_counts.get("equivalentClass", 0),
        "external_alignments_same_as": alignment_counts.get("sameAs", 0),
        "external_alignments_subclass": alignment_counts.get("subClassOf", 0),
        "external_alignments_subproperty": alignment_counts.get("subPropertyOf", 0),
        "external_alignments_exact": alignment_counts.get("exactMatch", 0),
        "external_alignments_close": alignment_counts.get("closeMatch", 0),
        "diagnoses": diagnosis_count,
        "entity_counts": dict(sorted(entity_counts.items())),
        "descriptions": len(descriptions),
        "skipped_descriptions": skipped_descriptions,
        "definitions_md": sum(1 for _ in graph.subjects(SKOS.definition, None)),
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
