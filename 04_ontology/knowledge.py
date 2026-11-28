"""Loader katalog dan mapping pengetahuan dari RDF.

Katalog domain (gejala kanonik, pengendalian, fase, bagian, tanaman, takson,
kondisi lingkungan) dan mapping eksplisit sumber → konsep dibaca dari
``kb/catalog.ttl`` dan ``kb/mappings.ttl``. Tidak ada katalog domain di Python.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, RDFS, SKOS

ONTO_DIR = Path(__file__).resolve().parent
CATALOG_TTL = ONTO_DIR / "kb" / "catalog.ttl"
MAPPINGS_TTL = ONTO_DIR / "kb" / "mappings.ttl"
KBR = Namespace("http://kbr.kelompok5.org/penyakit-tanaman-pangan#")
DCT = Namespace("http://purl.org/dc/terms/")
ENTITY_DEFINITIONS_TTL = ONTO_DIR / "kb" / "entity_definitions.ttl"


def _load(path: Path) -> Graph:
    if not path.exists():
        raise FileNotFoundError(f"Knowledge RDF tidak ditemukan: {path}")
    graph = Graph()
    graph.parse(path, format="turtle")
    return graph


def _local(node) -> str:
    return str(node).split("#")[-1]


def _kind(graph: Graph, node) -> str:
    value = graph.value(node, KBR["knowledgeType"])
    return str(value) if value is not None else ""


def _literal(graph: Graph, node, prop) -> str:
    value = graph.value(node, prop)
    return str(value) if value is not None else ""


CATALOG = _load(CATALOG_TTL)

CANONICAL_SYMPTOMS: dict[str, dict[str, str]] = {}
CONTROL_ACTIONS: dict[str, dict] = {}
PHASE_DEFS: dict[str, dict[str, str]] = {}
QUALITATIVE_RULES: list[tuple[str, str, str, re.Pattern[str]]] = []
ENV_FACTORS: dict[str, dict] = {}

PLANT_LOCAL: dict[str, str] = {}
PLANT_CLASS: dict[str, str] = {}
PLANT_LABELS: dict[str, str] = {}
PLANT_ORDER: list[str] = []
PLANT_SCIENTIFIC_FALLBACK: dict[str, tuple[str, str]] = {}
TAXON_CLASS: dict[str, str] = {}
TAXON_PRIORITY: dict[str, int] = {}
PART_WORDS: dict[str, str] = {}
PART_LABELS: dict[str, str] = {}
PART_OF: dict[str, str] = {}
PART_SUBCLASS: dict[str, str] = {}
TABLE_PART: dict[str, str] = {}
DEFAULT_PART: str = ""
TEXT_FILTERS: dict[str, re.Pattern[str]] = {}
VARIETY_STOPWORDS: set[str] = set()
PLANT_WORDS: set[str] = set()
VARIETY_PATTERNS: dict[str, str] = {}
CONDITION_CLASS_RULES: list[tuple[str, str]] = []

_plant_order_items: list[tuple[int, str]] = []
for node in set(CATALOG.subjects(KBR["knowledgeType"], None)):
    kind = _kind(CATALOG, node)
    local = _local(node)
    if kind == "canonical_symptom":
        CANONICAL_SYMPTOMS[local] = {
            "label": _literal(CATALOG, node, RDFS.label) or local,
            "comment": _literal(CATALOG, node, RDFS.comment),
            "part": _literal(CATALOG, node, KBR["canonicalPart"]).split("#")[-1],
        }
    elif kind == "control_action":
        CONTROL_ACTIONS[local] = {
            "label": _literal(CATALOG, node, RDFS.label) or local,
            "category": _literal(CATALOG, node, KBR["controlCategory"]).split("#")[-1],
            "comment": _literal(CATALOG, node, RDFS.comment),
        }
    elif kind == "phase_def":
        PHASE_DEFS[local] = {
            "label": _literal(CATALOG, node, RDFS.label) or local,
            "class": _literal(CATALOG, node, KBR["phaseClass"]).split("#")[-1],
        }
    elif kind == "qualitative_rule":
        pattern_text = _literal(CATALOG, node, KBR["pattern"])
        pattern = re.compile(pattern_text, re.I) if pattern_text else re.compile(r"$^")
        QUALITATIVE_RULES.append(
            (local, _literal(CATALOG, node, KBR["qualitativeClass"]).split("#")[-1], _literal(CATALOG, node, RDFS.label), pattern)
        )
    elif kind == "env_factor":
        ENV_FACTORS[_literal(CATALOG, node, KBR["factorName"]) or local] = {
            "terms": tuple(str(value) for value in CATALOG.objects(node, KBR["factorTerm"])),
            "class": _literal(CATALOG, node, KBR["factorClass"]).split("#")[-1],
            "unit": _literal(CATALOG, node, KBR["factorUnit"]),
        }
    elif kind == "plant_config":
        label = _literal(CATALOG, node, RDFS.label) or local
        PLANT_LABELS[local] = label
        PLANT_CLASS[local] = _literal(CATALOG, node, KBR["plantClass"]).split("#")[-1]
        for plant_id in CATALOG.objects(node, KBR["plantId"]):
            PLANT_LOCAL[str(plant_id)] = local
        scientific = _literal(CATALOG, node, KBR["fallbackScientificName"])
        if scientific:
            PLANT_SCIENTIFIC_FALLBACK[local] = (scientific, _literal(CATALOG, node, KBR["fallbackSourceUrl"]))
    elif kind == "plant_order":
        _plant_order_items.append((int(CATALOG.value(node, KBR["order"])), _literal(CATALOG, node, KBR["plantTarget"]).split("#")[-1]))
    elif kind == "taxon_mapping":
        group = _literal(CATALOG, node, KBR["taxonGroup"])
        TAXON_CLASS[group] = _literal(CATALOG, node, KBR["taxonClass"]).split("#")[-1]
        TAXON_PRIORITY[group] = int(CATALOG.value(node, KBR["taxonPriority"]))
    elif kind == "part_config":
        PART_LABELS[local] = _literal(CATALOG, node, RDFS.label) or local
        subclass = _literal(CATALOG, node, KBR["partSubclass"])
        if subclass:
            PART_SUBCLASS[local] = subclass.split("#")[-1]
        parent = _literal(CATALOG, node, KBR["partParent"])
        if parent:
            PART_OF[local] = _local(parent)
    elif kind == "part_word":
        PART_WORDS[_literal(CATALOG, node, KBR["partWord"])] = _local(CATALOG.value(node, KBR["partTarget"]))
    elif kind == "table_part":
        TABLE_PART[_literal(CATALOG, node, KBR["tableId"])] = _local(CATALOG.value(node, KBR["partTarget"]))
    elif kind == "part_default":
        DEFAULT_PART = _local(CATALOG.value(node, KBR["defaultPart"]))
    elif kind == "text_filter":
        name = _literal(CATALOG, node, KBR["filterName"])
        pattern_text = _literal(CATALOG, node, KBR["pattern"])
        if name and pattern_text:
            TEXT_FILTERS[name] = re.compile(pattern_text, re.I)
    elif kind == "variety_config":
        for word in CATALOG.objects(node, KBR["stopword"]):
            VARIETY_STOPWORDS.add(str(word))
        for word in CATALOG.objects(node, KBR["plantWord"]):
            PLANT_WORDS.add(str(word))
        for name in ("resistMarker", "vulnMarker", "primaryRegex", "fallbackRegex"):
            value = _literal(CATALOG, node, KBR[name])
            if value:
                VARIETY_PATTERNS[name] = value
    elif kind == "condition_class":
        prefix = _literal(CATALOG, node, KBR["prefix"])
        cls = _literal(CATALOG, node, KBR["conditionClass"]).split("#")[-1]
        if prefix and cls:
            CONDITION_CLASS_RULES.append((prefix, cls))

PLANT_ORDER = [local for _order, local in sorted(_plant_order_items)]
ENV_PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    (local, cls, pattern) for local, cls, _label, pattern in QUALITATIVE_RULES
]
ENV_CONTROL_CONTEXT_RE = TEXT_FILTERS.get("env_control_context", re.compile(r"$^"))
ENV_NEGATIVE_CONTEXT_RE = TEXT_FILTERS.get("env_negative_context", re.compile(r"$^"))
RESIST_MARKERS = re.compile(VARIETY_PATTERNS.get("resistMarker", r"$^"), re.I)
VULN_MARKERS = re.compile(VARIETY_PATTERNS.get("vulnMarker", r"$^"), re.I)
VARIETY_PRIMARY_RE = re.compile(VARIETY_PATTERNS.get("primaryRegex", r"$^"), re.I)
VARIETY_FALLBACK_RE = re.compile(VARIETY_PATTERNS.get("fallbackRegex", r"$^"), re.UNICODE)


def condition_class(local: str, default: str) -> str:
    for prefix, class_name in CONDITION_CLASS_RULES:
        if local.startswith(prefix):
            return class_name
    return default


def _norm(text: str | None) -> str:
    value = (text or "").replace("\r", " ").replace("\n", " ")
    value = value.replace("\u2013", "-").replace("\u2014", "-").replace("\u00ad", "")
    return re.sub(r"\s+", " ", value).strip().lower()


MAPPINGS = _load(MAPPINGS_TTL)
_TEXT_MAP: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))
_SOURCE_MAP: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))


def _add(mapping: dict[str, set], key: str, value) -> None:
    if key:
        mapping[key].add(value)


for node in set(MAPPINGS.subjects(KBR["knowledgeType"], None)):
    text = _norm(_literal(MAPPINGS, node, KBR["sourceText"]))
    source_id = _literal(MAPPINGS, node, KBR["sourceId"])
    keys = [("text", text), ("source", source_id)]
    for mode, key in keys:
        bucket = _TEXT_MAP if mode == "text" else _SOURCE_MAP
        if not key:
            continue
        for canonical in MAPPINGS.objects(node, KBR["canonicalGejala"]):
            _add(bucket["canonical"], key, _local(canonical))
        for part in MAPPINGS.objects(node, KBR["bagianTanaman"]):
            _add(bucket["part"], key, _local(part))
        for action in MAPPINGS.objects(node, KBR["controlAction"]):
            _add(bucket["control"], key, _local(action))
        for phase in MAPPINGS.objects(node, KBR["phase"]):
            _add(bucket["phase"], key, _local(phase))
        for condition in MAPPINGS.objects(node, KBR["condition"]):
            _add(
                bucket["condition"],
                key,
                (
                    _local(condition),
                    _literal(MAPPINGS, node, KBR["conditionClass"]),
                    _literal(MAPPINGS, node, KBR["conditionLabel"]),
                ),
            )


def _strip_parenthetical(text: str) -> str:
    return re.sub(r"\s*\([^)]*\)", "", text).strip()


def _lookup(kind: str, text: str | None) -> list:
    key = _norm(text)
    values = set(_TEXT_MAP[kind].get(key, set()))
    if not values and key:
        # Fallback toleran terhadap perbedaan pemotongan awal/akhir.
        for candidate, mapped in _TEXT_MAP[kind].items():
            if candidate and (candidate in key or key in candidate):
                values.update(mapped)
    if not values and key:
        # Catatan sumber dalam tanda kurung, mis. "(stripe)", tidak boleh
        # menggagalkan pencocokan teks utama.
        stripped_key = _strip_parenthetical(key)
        for candidate, mapped in _TEXT_MAP[kind].items():
            stripped_candidate = _strip_parenthetical(candidate)
            if stripped_candidate and (
                stripped_candidate == stripped_key
                or stripped_candidate in stripped_key
                or stripped_key in stripped_candidate
            ):
                values.update(mapped)
    return sorted(values)


def match_canonical_symptoms(text: str | None) -> list[str]:
    return _lookup("canonical", text)


def match_control_actions(text: str | None) -> list[str]:
    return _lookup("control", text)


def text_parts(text: str | None) -> list[str]:
    return _lookup("part", text)


def extract_phases(text: str | None) -> list[str]:
    return _lookup("phase", text)


def qualitative_matches(text: str | None) -> list[tuple[str, str, str]]:
    # Mapping kondisi juga mencatat observasi numerik; fungsi ini khusus
    # kondisi kualitatif (individu ``Kondisi*``).
    return [
        item
        for item in _lookup("condition", text)
        if item[0].startswith("Kondisi")
    ]


ENTITY_DEFINITIONS: dict[str, tuple[str, str]] = {}
_ENTITY_GRAPH = _load(ENTITY_DEFINITIONS_TTL)
for node in set(_ENTITY_GRAPH.subjects(KBR["knowledgeType"], None)):
    if _kind(_ENTITY_GRAPH, node) != "entity_definition":
        continue
    definition = _literal(_ENTITY_GRAPH, node, SKOS.definition)
    source = _literal(_ENTITY_GRAPH, node, DCT.source)
    if definition:
        ENTITY_DEFINITIONS[_local(node)] = (definition, source)
