"""Loader katalog pengetahuan dari RDF.

Semua definisi, sinonim, nama Inggris, kategori, urutan fase, partonomy, dan
override pemetaan dibaca dari ``kb/definitions.ttl``. Tidak ada katalog domain
yang ditulis di Python.
"""

from __future__ import annotations

from pathlib import Path

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, RDFS, SKOS

ONTO_DIR = Path(__file__).resolve().parent
KNOWLEDGE_TTL = ONTO_DIR / "kb" / "definitions.ttl"
KBR = Namespace("http://kbr.kelompok5.org/penyakit-tanaman-pangan#")
DCT = Namespace("http://purl.org/dc/terms/")


def _load() -> Graph:
    if not KNOWLEDGE_TTL.exists():
        raise FileNotFoundError(f"Katalog RDF tidak ditemukan: {KNOWLEDGE_TTL}")
    graph = Graph()
    graph.parse(KNOWLEDGE_TTL, format="turtle")
    return graph


_GRAPH = _load()


def _local(node) -> str:
    return str(node).split("#")[-1]


def _kind(node) -> str:
    value = _GRAPH.value(node, KBR["knowledgeType"])
    return str(value) if value is not None else ""


def _definition(node) -> str:
    value = _GRAPH.value(node, SKOS.definition)
    return str(value) if value is not None else ""


def _synonyms(node) -> list[str]:
    return [str(value) for value in _GRAPH.objects(node, SKOS.altLabel)]


def _english(node) -> str:
    for value in _GRAPH.objects(node, SKOS.prefLabel):
        if isinstance(value, Literal) and value.language == "en":
            return str(value)
    return ""


def _source(node) -> str:
    value = _GRAPH.value(node, DCT.source)
    return str(value) if value is not None else ""


def _label(node) -> str:
    value = _GRAPH.value(node, RDFS.label)
    return str(value) if value is not None else ""


SYMPTOM_DEFINITIONS: dict[str, dict] = {}
CATEGORY_CONCEPTS: dict[str, dict] = {}
PHASE_DEFINITIONS: dict[str, dict] = {}
PART_DEFINITIONS: dict[str, dict] = {}
PLANT_DEFINITIONS: dict[str, dict] = {}
CONTROL_DEFINITIONS: dict[str, str] = {}
ENV_DEFINITIONS: dict[str, str] = {}
CLASS_DEFINITIONS: dict[str, str] = {}
PROPERTY_DEFINITIONS: dict[str, str] = {}
DISEASE_ENGLISH_NAMES: dict[str, str] = {}
DISEASE_DEFINITIONS: dict[str, str] = {}

for node in set(_GRAPH.subjects(KBR["knowledgeType"], None)):
    local = _local(node)
    kind = _kind(node)
    if kind == "symptom":
        SYMPTOM_DEFINITIONS[local] = {
            "definition": _definition(node),
            "synonyms": _synonyms(node),
            "english": _english(node),
            "source": _source(node),
        }
    elif kind == "category":
        CATEGORY_CONCEPTS[local] = {
            "label": _label(node) or local,
            "definition": _definition(node),
        }
    elif kind == "phase":
        PHASE_DEFINITIONS[local] = {
            "definition": _definition(node),
            "synonyms": _synonyms(node),
            "english": _english(node),
        }
    elif kind == "part":
        PART_DEFINITIONS[local] = {
            "definition": _definition(node),
            "synonyms": _synonyms(node),
            "english": _english(node),
        }
    elif kind == "plant":
        PLANT_DEFINITIONS[local] = {
            "definition": _definition(node),
            "synonyms": _synonyms(node),
        }
    elif kind == "control":
        CONTROL_DEFINITIONS[local] = _definition(node)
    elif kind == "environment":
        ENV_DEFINITIONS[local] = _definition(node)
    elif kind == "class":
        CLASS_DEFINITIONS[local] = _definition(node)
    elif kind == "property":
        PROPERTY_DEFINITIONS[local] = _definition(node)
    elif kind == "disease":
        DISEASE_ENGLISH_NAMES[local] = _english(node)
    elif kind == "disease_definition":
        DISEASE_DEFINITIONS[local] = _definition(node)

for node in set(_GRAPH.subjects(KBR["knowledgeType"], None)):
    kinds = {str(value) for value in _GRAPH.objects(node, KBR["knowledgeType"])}
    if "disease_definition" in kinds:
        DISEASE_DEFINITIONS[_local(node)] = _definition(node)

SYMPTOM_CATEGORIES: dict[str, str] = {}
for symptom in set(_GRAPH.subjects(KBR["knowledgeType"], None)):
    if _kind(symptom) != "symptom":
        continue
    broader = _GRAPH.value(symptom, SKOS.broader)
    if broader is not None:
        SYMPTOM_CATEGORIES[_local(symptom)] = _local(broader)

PHASE_CHAIN: list[tuple[str, str]] = []
for left, right in _GRAPH.subject_objects(KBR["phaseNext"]):
    PHASE_CHAIN.append((_local(left), _local(right)))

PHASE_STAGE_ORDER: dict[str, int] = {}
for node, value in _GRAPH.subject_objects(KBR["urutanFase"]):
    PHASE_STAGE_ORDER[_local(node)] = int(value)

PART_PARENTS: list[tuple[str, str]] = []
for child, parent in _GRAPH.subject_objects(KBR["partParent"]):
    PART_PARENTS.append((_local(child), _local(parent)))

SYMPTOM_CANONICAL_OVERRIDES: dict[str, list[str]] = {}
NON_SYMPTOM_OVERRIDES: set[str] = set()
for node in set(_GRAPH.subjects(KBR["knowledgeType"], None)):
    if _kind(node) != "override":
        continue
    source_id = _GRAPH.value(node, KBR["sourceId"])
    if source_id is None:
        continue
    source_text = str(source_id)
    canonicals = [_local(item) for item in _GRAPH.objects(node, KBR["canonicalGejala"])]
    if canonicals:
        SYMPTOM_CANONICAL_OVERRIDES[source_text] = canonicals
    if bool(_GRAPH.value(node, KBR["nonGejala"])):
        NON_SYMPTOM_OVERRIDES.add(source_text)
