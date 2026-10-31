"""Generator ontologi OWL 2 project kbr-kelompok5.

Membaca knowledge tables hasil kurasi (``03_knowledge_tables/curated`` dan
``auto/``), metadata dokumen, serta ``chapter_map.json`` lalu membangun ABox
di atas TBox dari ``tbox.py`` menjadi ``ontology.tttl``.

Pemakaian (dari root repo)::

    python 04_ontology/build_ontology.py

Keluaran: ``04_ontology/ontology.ttl``, kode keluar ``2`` bila validasi gagal.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

ONTO_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = ONTO_DIR.parent
TABLE_DIR = PROJECT_ROOT / "03_knowledge_tables"
CURATED_DIR = TABLE_DIR / "curated"
AUTO_DIR = TABLE_DIR / "auto"
META_PATH = PROJECT_ROOT / "01_knowledge_sources" / "source_metadata" / "manual_metadata.json"
CHAPTER_MAP_PATH = TABLE_DIR / "config" / "chapter_map.json"
DEFAULT_OUT = ONTO_DIR / "ontology.ttl"

sys.path.insert(0, str(ONTO_DIR))

import tbox  # noqa: E402
from tbox import KBR, KBRD  # noqa: E402

TAXON_TO_CLASS = {
    "jamur": "Fungus",
    "bakteri": "Bacterium",
    "virus": "Virus",
    "nematoda": "Nematode",
    "fitoplasma": "Phytoplasma",
    "oomycete": "Oomycete",
}

NUTRITION_CATEGORY_CLASSES: dict[str, dict[str, list[str]]] = {
    "nutrients": {
        "makronutrien dan mikronutrien": ["Nutrient"],
        "mikronutrien": ["Micronutrient", "Nutrient"],
    },
    "fertilizers": {
        "pupuk nitrogen": ["NitrogenFertilizer", "Fertilizer"],
        "pupuk fosfor": ["PhosphateFertilizer", "Fertilizer"],
        "pupuk kalium": ["PotassiumFertilizer", "Fertilizer"],
        "pupuk majemuk": ["CompoundFertilizer", "Fertilizer"],
        "jenis pupuk": ["Fertilizer"],
    },
    "practices": {
        "strategi pengelolaan nutrisi": ["NutrientManagementStrategy", "FertilizationPractice"],
        "pemupukan berimbang": ["BalancedFertilization", "FertilizationPractice"],
    },
    "compost": {
        "kompos": ["Compost", "OrganicFertilizer", "Fertilizer"],
        "bioaktivator": ["Bioactivator", "OrganicFertilizer", "Fertilizer"],
        "pupuk organik cair": ["LiquidOrganicFertilizer", "OrganicFertilizer", "Fertilizer"],
        "manfaat pupuk organik": ["OrganicFertilizerBenefit"],
    },
}

EVIDENCE_COLUMNS: list[tuple[str, str, str]] = [
    ("auto/plants.csv", "evidence_chunk_id", "hasEvidence"),
    ("curated/diseases.csv", "evidence_chunk_ids", "hasEvidence"),
    ("curated/pathogens.csv", "chunk_id", "hasEvidence"),
    ("curated/pathogens.csv", "taxon_evidence_chunk_id", "hasTaxonEvidence"),
    ("curated/symptoms.csv", "chunk_id", "hasEvidence"),
    ("curated/controls.csv", "chunk_id", "hasEvidence"),
    ("curated/DOC003/plants.csv", "evidence_chunk_id", "hasEvidence"),
    ("curated/DOC003/amorphophallus_spp_diseases.csv", "chunk_id", "hasEvidence"),
    ("curated/DOC003/pathogens.csv", "chunk_id", "hasEvidence"),
    ("curated/DOC003/pathogens.csv", "taxon_evidence_chunk_id", "hasTaxonEvidence"),
    ("curated/DOC003/symptoms.csv", "chunk_id", "hasEvidence"),
    ("curated/DOC003/controls.csv", "chunk_id", "hasEvidence"),
    ("curated/DOC004/nutrients.csv", "chunk_id", "hasEvidence"),
    ("curated/DOC004/fertilizers.csv", "chunk_id", "hasEvidence"),
    ("curated/DOC004/practices.csv", "chunk_id", "hasEvidence"),
    ("curated/DOC004/compost.csv", "chunk_id", "hasEvidence"),
]

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def plain_local(raw: str) -> str:
    local = re.sub(r"[^A-Za-z0-9_-]", "_", raw)
    local = re.sub(r"_+", "_", local).strip("_")
    if not local:
        local = "x"
    if not re.match(r"[A-Za-z_]", local):
        local = "x_" + local
    return local


def text_local(prefix: str, text: str) -> str:
    slug = _SLUG_RE.sub("-", text.lower()).strip("-")[:48] or "x"
    digest = hashlib.md5(text.encode("utf-8")).hexdigest()[:8]
    return f"{prefix}_{slug}_{digest}"


def split_chunk_ids(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(";") if part.strip()]


def section_paths(chapter: str, section: str, subsection: str) -> list[tuple[str, ...]]:
    chapter = chapter.strip()
    section = section.strip()
    subsection = subsection.strip()
    paths: list[tuple[str, ...]] = [(chapter,)]
    section_path: tuple[str, ...] | None = None
    if section:
        section_path = (chapter, section)
        paths.append(section_path)
    if subsection:
        paths.append(section_path + (subsection,) if section_path else (chapter, subsection))
    return paths


def section_target(chapter: str, section: str, subsection: str) -> tuple[str, ...]:
    paths = section_paths(chapter, section, subsection)
    return paths[-1]


class Builder:
    def __init__(self) -> None:
        self.graph = Graph()
        self.chunks: set[str] = set()
        self.class_counts: Counter[str] = Counter()
        self.triple_property_counts: Counter[str] = Counter()
        self.errors: list[str] = []
        self.section_cache: dict[tuple[str, ...], URIRef] = {}
        self.chapter_number_by_title: dict[str, int] = {}
        self.plant_ids: set[str] = set()

    def declare(self, uri: URIRef, *classes: str) -> None:
        self.graph.add((uri, RDF.type, OWL.NamedIndividual))
        for cls in classes:
            self.graph.add((uri, RDF.type, KBR[cls]))
            self.class_counts[cls] += 1

    def label(self, uri: URIRef, text: str) -> None:
        if text and text.strip():
            self.graph.add((uri, RDFS.label, Literal(text.strip(), lang="id")))

    def s(self, uri: URIRef, prop: str, value: str | None) -> None:
        if value is not None and value.strip():
            self.graph.add((uri, KBR[prop], Literal(value.strip(), lang="id")))

    def i(self, uri: URIRef, prop: str, value: str | None) -> None:
        if value is not None and str(value).strip():
            try:
                self.graph.add((uri, KBR[prop], Literal(int(str(value).strip()), datatype=XSD.integer)))
            except ValueError:
                self.errors.append(f"nilai bukan integer untuk {prop}: {value!r}")

    def link(self, uri: URIRef, prop: str, target: URIRef) -> None:
        self.graph.add((uri, KBR[prop], target))
        self.triple_property_counts[prop] += 1
        inverse = tbox.OBJECT_PROPERTIES.get(prop, {}).get("inverse")
        if inverse:
            self.graph.add((target, KBR[inverse], uri))
            self.triple_property_counts[inverse] += 1

    def evidence_iri(self, chunk_id: str) -> URIRef:
        if chunk_id not in self.chunks:
            self.chunks.add(chunk_id)
            iri = KBRD[plain_local(chunk_id)]
            self.declare(iri, "EvidenceChunk")
            self.label(iri, chunk_id)
            self.s(iri, "chunkId", chunk_id)
        return KBRD[plain_local(chunk_id)]

    def link_evidence(self, uri: URIRef, raw: str, prop: str = "hasEvidence") -> None:
        for chunk_id in split_chunk_ids(raw):
            self.link(uri, prop, self.evidence_iri(chunk_id))

    def section(self, path: tuple[str, ...]) -> URIRef:
        if path in self.section_cache:
            return self.section_cache[path]
        local = text_local("SEC", "\x1f".join(path))
        uri = KBRD[local]
        level = "chapter" if len(path) == 1 else ("section" if len(path) == 2 else "subsection")
        self.declare(uri, "SourceSection")
        self.label(uri, path[-1])
        self.s(uri, "sectionLevel", level)
        self.s(uri, "sectionLabel", path[-1])
        self.s(uri, "chapterTitle", path[0])
        if path[0] in self.chapter_number_by_title:
            self.i(uri, "chapterNumber", str(self.chapter_number_by_title[path[0]]))
        if len(path) > 1:
            parent = self.section(path[:-1])
            self.link(parent, "containsSection", uri)
        self.section_cache[path] = uri
        return uri

    def source(self, doc_id: str) -> URIRef:
        return KBRD[doc_id]


def load_chapter_titles(builder: Builder, plants_rows: list[dict[str, str]]) -> None:
    for row in plants_rows:
        title = (row.get("chapter_title") or "").strip()
        number = (row.get("chapter_number") or "").strip()
        if title and number:
            builder.chapter_number_by_title.setdefault(title, number)


def build_sources(builder: Builder) -> None:
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    documents = meta.get("documents", {})
    for doc_id, info in documents.items():
        uri = builder.source(doc_id)
        builder.declare(uri, "KnowledgeSource")
        builder.label(uri, info.get("title") or doc_id)
        builder.s(uri, "documentId", doc_id)
        builder.s(uri, "title", info.get("title"))
        for author in info.get("authors") or []:
            builder.s(uri, "author", author)
        year = info.get("publication_year")
        if year is not None:
            builder.graph.add((uri, KBR.publicationYear, Literal(int(year), datatype=XSD.integer)))
        builder.s(uri, "publisher", info.get("publisher"))
        builder.s(uri, "languageCode", info.get("language"))
        for note in info.get("notes") or []:
            builder.s(uri, "sourceNote", note)


def build_plants(builder: Builder) -> None:
    specs = [
        (AUTO_DIR / "plants.csv", "DOC002"),
        (CURATED_DIR / "DOC003" / "plants.csv", "DOC003"),
    ]
    for path, doc_id in specs:
        for row in read_csv(path):
            plant_id = row["plant_id"].strip()
            uri = KBRD[plain_local(plant_id)]
            builder.declare(uri, "Plant")
            builder.label(uri, row.get("plant_name_id") or plant_id)
            builder.s(uri, "plantNameId", row.get("plant_name_id"))
            builder.s(uri, "plantNameEn", row.get("plant_name_en"))
            builder.s(uri, "scientificName", row.get("scientific_name"))
            builder.i(uri, "scientificNamePage", row.get("scientific_name_page"))
            builder.i(uri, "chapterNumber", row.get("chapter_number"))
            builder.s(uri, "chapterTitle", row.get("chapter_title"))
            builder.i(uri, "pageStart", row.get("page_start"))
            builder.i(uri, "pageEnd", row.get("page_end"))
            builder.s(uri, "notes", row.get("notes"))
            builder.link_evidence(uri, row.get("evidence_chunk_id") or "")
            builder.link(uri, "hasSourceDocument", builder.source(doc_id))
            builder.plant_ids.add(plant_id)


def build_diseases_doc002(builder: Builder) -> None:
    for row in read_csv(CURATED_DIR / "diseases.csv"):
        disease_id = row["disease_id"].strip()
        uri = KBRD[plain_local(disease_id)]
        name = (row.get("disease_name_verbatim") or "").strip()
        builder.declare(uri, "Disease")
        builder.label(uri, name or (row.get("disease_name_key") or disease_id))
        builder.s(uri, "diseaseName", row.get("disease_name_verbatim"))
        builder.s(uri, "diseaseNameKey", row.get("disease_name_key"))
        builder.s(uri, "diseaseNameEn", row.get("name_en_verbatim"))
        builder.s(uri, "chapterTitle", row.get("chapter_title"))
        builder.s(uri, "headingLevel", row.get("heading_level"))
        builder.s(uri, "section", row.get("section"))
        builder.s(uri, "subsection", row.get("subsection"))
        builder.i(uri, "pageStart", row.get("page_start"))
        builder.i(uri, "pageEnd", row.get("page_end"))
        builder.s(uri, "sourceBlockId", row.get("source_block_ids"))
        builder.s(uri, "reviewStatus", row.get("review_status"))
        builder.s(uri, "notes", row.get("notes"))
        builder.link_evidence(uri, row.get("evidence_chunk_ids") or "")
        builder.link(uri, "hasSourceDocument", builder.source("DOC002"))
        plant = KBRD[plain_local(row["plant_id"].strip())]
        builder.link(uri, "occursIn", plant)
        target = section_target(
            row.get("chapter_title") or "",
            row.get("section") or "",
            row.get("subsection") or "",
        )
        builder.link(uri, "locatedInSection", builder.section(target))


def build_diseases_doc003(builder: Builder) -> None:
    for row in read_csv(CURATED_DIR / "DOC003" / "amorphophallus_spp_diseases.csv"):
        disease_id = row["disease_id"].strip()
        uri = KBRD[plain_local(disease_id)]
        builder.declare(uri, "Disease")
        builder.label(uri, row.get("disease_name_verbatim") or disease_id)
        builder.s(uri, "diseaseName", row.get("disease_name_verbatim"))
        builder.s(uri, "diseaseNameEn", row.get("disease_name_en_verbatim"))
        builder.s(uri, "hostName", row.get("host_verbatim"))
        builder.s(uri, "reference", row.get("reference_verbatim"))
        builder.s(uri, "sourceType", row.get("source_type"))
        builder.i(uri, "pageStart", row.get("page_start"))
        builder.i(uri, "pageEnd", row.get("page_end"))
        builder.s(uri, "sourceBlockId", row.get("source_block_id"))
        builder.s(uri, "reviewStatus", row.get("review_status"))
        builder.s(uri, "notes", row.get("notes"))
        builder.link_evidence(uri, row.get("chunk_id") or "")
        builder.link(uri, "hasSourceDocument", builder.source("DOC003"))
        builder.link(uri, "occursIn", KBRD[plain_local(row["plant_id"].strip())])


def doc002_pathogen_ids() -> set[str]:
    return {row["pathogen_id"].strip() for row in read_csv(CURATED_DIR / "pathogens.csv")}


def pathogen_local(pathogen_id: str, doc_id: str, doc2_ids: set[str]) -> str:
    if doc_id == "DOC003" and pathogen_id in doc2_ids:
        return plain_local(f"{pathogen_id}_DOC003")
    return plain_local(pathogen_id)


def build_pathogens(builder: Builder) -> None:
    doc2_ids = doc002_pathogen_ids()
    specs = [
        (CURATED_DIR / "pathogens.csv", "DOC002"),
        (CURATED_DIR / "DOC003" / "pathogens.csv", "DOC003"),
    ]
    for path, doc_id in specs:
        for row in read_csv(path):
            pathogen_id = row["pathogen_id"].strip()
            uri = KBRD[pathogen_local(pathogen_id, doc_id, doc2_ids)]
            taxon = (row.get("taxon_group") or "").strip()
            classes = ["Pathogen"]
            if taxon in TAXON_TO_CLASS:
                classes.append(TAXON_TO_CLASS[taxon])
            builder.declare(uri, *classes)
            builder.label(uri, row.get("scientific_name") or pathogen_id)
            builder.s(uri, "scientificName", row.get("scientific_name"))
            builder.s(uri, "verbatimText", row.get("verbatim_text"))
            builder.s(uri, "taxonGroupLabel", row.get("taxon_group"))
            builder.s(uri, "taxonEvidenceQuote", row.get("taxon_evidence_quote"))
            builder.i(uri, "pageStart", row.get("page"))
            builder.s(uri, "reviewStatus", row.get("review_status"))
            builder.s(uri, "notes", row.get("note"))
            builder.link_evidence(uri, row.get("chunk_id") or "")
            taxon_chunk = (row.get("taxon_evidence_chunk_id") or "").strip()
            if taxon_chunk:
                builder.link_evidence(uri, taxon_chunk, "hasTaxonEvidence")
            builder.link(uri, "hasSourceDocument", builder.source(doc_id))


def build_disease_pathogen(builder: Builder) -> None:
    doc2_ids = doc002_pathogen_ids()
    specs = [
        ("disease_pathogen.csv", "DOC002"),
        ("DOC003/disease_pathogen.csv", "DOC003"),
    ]
    for rel_path, doc_id in specs:
        for row in read_csv(CURATED_DIR / rel_path):
            disease = KBRD[plain_local(row["disease_id"].strip())]
            pathogen = KBRD[
                pathogen_local(row["pathogen_id"].strip(), doc_id, doc2_ids)
            ]
            builder.link(disease, "causedBy", pathogen)


def build_symptoms(builder: Builder) -> None:
    specs = [
        (CURATED_DIR / "symptoms.csv", "DOC002"),
        (CURATED_DIR / "DOC003" / "symptoms.csv", "DOC003"),
    ]
    for path, doc_id in specs:
        for row in read_csv(path):
            symptom_id = row["symptom_id"].strip()
            uri = KBRD[plain_local(symptom_id)]
            builder.declare(uri, "Symptom")
            builder.label(uri, row.get("verbatim_text") or symptom_id)
            builder.s(uri, "verbatimText", row.get("verbatim_text"))
            builder.i(uri, "pageStart", row.get("page_start"))
            builder.i(uri, "pageEnd", row.get("page_end"))
            builder.i(uri, "charStart", row.get("char_start"))
            builder.i(uri, "charEnd", row.get("char_end"))
            builder.s(uri, "reviewStatus", row.get("review_status"))
            builder.link_evidence(uri, row.get("chunk_id") or "")
            builder.link(KBRD[plain_local(row["disease_id"].strip())], "hasSymptom", uri)
            builder.link(uri, "observedOn", KBRD[plain_local(row["plant_id"].strip())])
            builder.link(uri, "hasSourceDocument", builder.source(doc_id))


def build_controls(builder: Builder) -> None:
    specs = [
        (CURATED_DIR / "controls.csv", "DOC002"),
        (CURATED_DIR / "DOC003" / "controls.csv", "DOC003"),
    ]
    for path, doc_id in specs:
        for row in read_csv(path):
            control_id = row["control_id"].strip()
            uri = KBRD[plain_local(control_id)]
            scope = (row.get("scope") or "").strip()
            scope_class = "DiseaseControl" if scope == "disease" else "ChapterControl"
            builder.declare(uri, "ControlMeasure", scope_class)
            builder.label(uri, row.get("verbatim_text") or control_id)
            builder.s(uri, "verbatimText", row.get("verbatim_text"))
            builder.i(uri, "pageStart", row.get("page_start"))
            builder.i(uri, "pageEnd", row.get("page_end"))
            builder.i(uri, "charStart", row.get("char_start"))
            builder.i(uri, "charEnd", row.get("char_end"))
            builder.s(uri, "controlCategory", row.get("control_category"))
            builder.s(uri, "reviewStatus", row.get("review_status"))
            builder.link_evidence(uri, row.get("chunk_id") or "")
            disease_id = (row.get("disease_id") or "").strip()
            if disease_id and scope == "disease":
                builder.link(uri, "appliesTo", KBRD[plain_local(disease_id)])
            builder.link(uri, "appliesToPlant", KBRD[plain_local(row["plant_id"].strip())])
            builder.link(uri, "hasSourceDocument", builder.source(doc_id))


def build_ubi_tables(builder: Builder) -> None:
    chapters = json.loads(CHAPTER_MAP_PATH.read_text(encoding="utf-8"))["chapters"]
    plant_by_chapter = {int(c["chapter_number"]): c["plant_id"] for c in chapters}
    rows = read_csv(CURATED_DIR / "ubi_kayu_tabel_5.csv")
    table_titles: dict[str, str] = {}
    for row in rows:
        table_id = row["table_id"].strip()
        table_titles.setdefault(table_id, (row.get("table_title") or "").strip())

    table_by_id: dict[str, URIRef] = {}
    for table_id, title in table_titles.items():
        uri = KBRD[plain_local(table_id)]
        builder.declare(uri, "SourceTable", "CassavaSourceTable")
        builder.label(uri, title or table_id)
        builder.s(uri, "tableTitle", title)
        match = re.match(r"T(\d+)", table_id)
        if match:
            plant_id = plant_by_chapter.get(int(match.group(1)))
            if plant_id:
                builder.link(uri, "aboutPlant", KBRD[plain_local(plant_id)])
        builder.link(uri, "hasSourceDocument", builder.source("DOC002"))
        table_by_id[table_id] = uri

    unnumbered_count: dict[str, int] = {}
    for row in rows:
        table_id = row["table_id"].strip()
        row_no = row["row_no"].strip()
        if row_no:
            local = plain_local(f"{table_id}_R{row_no}")
        else:
            n = unnumbered_count.get(table_id, 0) + 1
            unnumbered_count[table_id] = n
            local = plain_local(f"{table_id}_R_unnumbered_{n}")
        uri = KBRD[local]
        builder.declare(uri, "SourceTableRow")
        disease_name = (row.get("disease_name") or "").strip()
        builder.label(uri, disease_name or f"Baris {row_no} {table_id}")
        builder.s(uri, "rowNumber", row_no)
        builder.s(uri, "diseaseName", row.get("disease_name"))
        builder.s(uri, "pathogenName", row.get("pathogen_name"))
        builder.s(uri, "symptomText", row.get("symptom_text"))
        builder.i(uri, "pageStart", row.get("page"))
        builder.s(uri, "sourceBlockId", row.get("source_block_id"))
        builder.s(uri, "rowStatus", row.get("status"))
        builder.s(uri, "notes", row.get("note"))
        builder.link(uri, "isTableRowOf", table_by_id[table_id])
        builder.link(uri, "hasSourceDocument", builder.source("DOC002"))


def build_nutrition(builder: Builder) -> None:
    for table, category_map in NUTRITION_CATEGORY_CLASSES.items():
        rel_path = CURATED_DIR / "DOC004" / f"{table}.csv"
        for row in read_csv(rel_path):
            record_id = row["record_id"].strip()
            uri = KBRD[plain_local(record_id)]
            category = (row.get("category") or "").strip()
            if category not in category_map:
                builder.errors.append(f"kategori tak dikenal di {table}.csv: {category!r}")
                classes = []
            else:
                classes = category_map[category]
            builder.declare(uri, *(classes or ["KnowledgeRecord"]))
            subject = (row.get("subject") or "").strip()
            attribute = (row.get("attribute") or "").strip()
            builder.label(uri, f"{subject} — {attribute}" if attribute else subject or record_id)
            builder.s(uri, "category", row.get("category"))
            builder.s(uri, "subject", row.get("subject"))
            builder.s(uri, "attribute", row.get("attribute"))
            builder.s(uri, "recordValue", row.get("value"))
            builder.s(uri, "unit", row.get("unit"))
            builder.s(uri, "verbatimText", row.get("verbatim_text"))
            builder.i(uri, "pageStart", row.get("page"))
            builder.s(uri, "sourceBlockId", row.get("source_block_id"))
            builder.s(uri, "reviewStatus", row.get("review_status"))
            builder.s(uri, "notes", row.get("notes"))
            builder.link_evidence(uri, row.get("chunk_id") or "")
            builder.link(uri, "hasSourceDocument", builder.source("DOC004"))


def expected_counts() -> dict:
    diseases1 = read_csv(CURATED_DIR / "diseases.csv")
    diseases3 = read_csv(CURATED_DIR / "DOC003" / "amorphophallus_spp_diseases.csv")
    pathogens1 = read_csv(CURATED_DIR / "pathogens.csv")
    pathogens3 = read_csv(CURATED_DIR / "DOC003" / "pathogens.csv")
    symptoms1 = read_csv(CURATED_DIR / "symptoms.csv")
    symptoms3 = read_csv(CURATED_DIR / "DOC003" / "symptoms.csv")
    controls1 = read_csv(CURATED_DIR / "controls.csv")
    controls3 = read_csv(CURATED_DIR / "DOC003" / "controls.csv")
    plants1 = read_csv(AUTO_DIR / "plants.csv")
    plants3 = read_csv(CURATED_DIR / "DOC003" / "plants.csv")
    table_rows = read_csv(CURATED_DIR / "ubi_kayu_tabel_5.csv")
    nutrition_rows = {
        table: read_csv(CURATED_DIR / "DOC004" / f"{table}.csv")
        for table in NUTRITION_CATEGORY_CLASSES
    }
    dp1 = read_csv(CURATED_DIR / "disease_pathogen.csv")
    dp3 = read_csv(CURATED_DIR / "DOC003" / "disease_pathogen.csv")
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))

    classes: Counter[str] = Counter()
    classes["KnowledgeSource"] = len(meta["documents"])
    classes["Plant"] = len(plants1) + len(plants3)
    classes["Disease"] = len(diseases1) + len(diseases3)
    classes["Symptom"] = len(symptoms1) + len(symptoms3)
    classes["ControlMeasure"] = len(controls1) + len(controls3)
    classes["Pathogen"] = len(pathogens1) + len(pathogens3)
    for row in pathogens1 + pathogens3:
        mapped = TAXON_TO_CLASS.get((row.get("taxon_group") or "").strip())
        if mapped:
            classes[mapped] += 1
    all_controls = controls1 + controls3
    for row in all_controls:
        scope = (row.get("scope") or "").strip()
        classes["DiseaseControl" if scope == "disease" else "ChapterControl"] += 1
    classes["SourceTable"] = len({r["table_id"].strip() for r in table_rows})
    classes["CassavaSourceTable"] = classes["SourceTable"]
    classes["SourceTableRow"] = len(table_rows)
    classes["EvidenceChunk"] = len(expected_chunk_ids())

    nutrition_classes: Counter[str] = Counter()
    for table, rows in nutrition_rows.items():
        category_map = NUTRITION_CATEGORY_CLASSES[table]
        for row in rows:
            for cls in category_map[(row.get("category") or "").strip()]:
                nutrition_classes[cls] += 1
    classes.update(nutrition_classes)

    section_paths_set: set[tuple[str, ...]] = set()
    for row in diseases1:
        section_paths_set.update(
            section_paths(
                row.get("chapter_title") or "",
                row.get("section") or "",
                row.get("subsection") or "",
            )
        )
    chapters = {p[0] for p in section_paths_set}
    contains = len(section_paths_set) - len(chapters)

    properties: Counter[str] = Counter()
    properties["occursIn"] = len(diseases1) + len(diseases3)
    properties["causedBy"] = len(dp1) + len(dp3)
    properties["hasSymptom"] = len(symptoms1) + len(symptoms3)
    properties["observedOn"] = len(symptoms1) + len(symptoms3)
    properties["appliesTo"] = sum(
        1 for r in all_controls if (r.get("scope") or "").strip() == "disease"
    )
    properties["appliesToPlant"] = sum(1 for r in all_controls if (r.get("plant_id") or "").strip())
    properties["hasDisease"] = properties["occursIn"]
    properties["causes"] = properties["causedBy"]
    properties["symptomOf"] = properties["hasSymptom"]
    properties["hasControlMeasure"] = properties["appliesTo"]
    properties["locatedInSection"] = len(diseases1)
    properties["isTableRowOf"] = len(table_rows)
    properties["hasTableRow"] = properties["isTableRowOf"]
    properties["aboutPlant"] = classes["SourceTable"]
    properties["containsSection"] = contains
    properties["sectionOf"] = contains
    properties["SourceSection_individuals"] = len(section_paths_set)

    evidence_total = 0
    for rel_path, column, prop in EVIDENCE_COLUMNS:
        rows = read_csv(TABLE_DIR / rel_path)
        for row in rows:
            raw = (row.get(column) or "").strip()
            if prop == "hasEvidence":
                evidence_total += len(split_chunk_ids(raw))
            else:
                evidence_total_taxon = 1 if raw else 0
                properties["hasTaxonEvidence"] += evidence_total_taxon
    properties["hasEvidence"] = evidence_total

    nutrition_individuals = sum(
        len({row["record_id"].strip() for row in rows}) for rows in nutrition_rows.values()
    )
    records_total = (
        classes["Plant"]
        + classes["Disease"]
        + classes["Pathogen"]
        + classes["Symptom"]
        + classes["ControlMeasure"]
        + classes["SourceTable"]
        + classes["SourceTableRow"]
        + nutrition_individuals
    )
    properties["hasSourceDocument"] = records_total

    return {
        "classes": {k: v for k, v in classes.items() if v},
        "properties": dict(properties),
    }


def expected_chunk_ids() -> set[str]:
    ids: set[str] = set()
    for rel_path, column, _prop in EVIDENCE_COLUMNS:
        for row in read_csv(TABLE_DIR / rel_path):
            ids.update(split_chunk_ids((row.get(column) or "").strip()))
    ids.discard("")
    return ids


def build() -> tuple[Graph, dict, list[str], Builder]:
    builder = Builder()
    tbox.build_tbox(builder.graph)
    builder.graph.bind("kbr", KBR)
    builder.graph.bind("kbrd", tbox.KBRD)

    load_chapter_titles(builder, read_csv(AUTO_DIR / "plants.csv"))
    build_sources(builder)
    build_plants(builder)
    build_diseases_doc002(builder)
    build_diseases_doc003(builder)
    build_pathogens(builder)
    build_disease_pathogen(builder)
    build_symptoms(builder)
    build_controls(builder)
    build_ubi_tables(builder)
    build_nutrition(builder)

    expected = expected_counts()
    errors = validate(builder.graph, builder, expected)
    return builder.graph, expected, errors, builder


def validate(graph: Graph, builder: Builder, expected: dict) -> list[str]:
    errors = list(builder.errors)

    try:
        serialized = graph.serialize(format="turtle")
        reparsed = Graph()
        reparsed.parse(data=serialized, format="turtle")
    except Exception as exc:  # noqa: BLE001
        return errors + [f"parse ulang gagal: {exc}"]

    for cls, count in sorted(expected["classes"].items()):
        actual = len(list(graph.subjects(RDF.type, KBR[cls])))
        if actual != count:
            errors.append(f"jumlah individu {cls}: {actual} != {count}")

    if builder.class_counts["SourceSection"] != expected["properties"]["SourceSection_individuals"]:
        errors.append(
            "jumlah individu SourceSection: "
            f"{builder.class_counts['SourceSection']} != "
            f"{expected['properties']['SourceSection_individuals']}"
        )

    for prop, count in sorted(expected["properties"].items()):
        if prop == "SourceSection_individuals":
            continue
        actual = len(list(graph.triples((None, KBR[prop], None))))
        if actual != count:
            errors.append(f"jumlah triple {prop}: {actual} != {count}")

    for prop, spec in tbox.OBJECT_PROPERTIES.items():
        rng = KBR[spec["range"]]
        for obj in graph.objects(None, KBR[prop]):
            if (obj, RDF.type, rng) not in graph:
                errors.append(f"objek {obj} dari kbr:{prop} tidak bertipe {rng}")

    for literal_obj in graph.objects():
        if isinstance(literal_obj, Literal) and str(literal_obj) == "":
            errors.append("literal kosong ditemukan")

    axiom_checks = [
        (KBR.containsSection, RDF.type, OWL.TransitiveProperty),
        (KBR.containsSection, RDF.type, OWL.AsymmetricProperty),
        (KBR.containsSection, RDF.type, OWL.IrreflexiveProperty),
        (KBR.hasTaxonEvidence, RDFS.subPropertyOf, KBR.hasEvidence),
        (KBR.occursIn, RDF.type, OWL.FunctionalProperty),
        (KBR.observedOn, RDF.type, OWL.FunctionalProperty),
        (KBR.isTableRowOf, RDF.type, OWL.FunctionalProperty),
        (KBR.CassavaSourceTable, OWL.equivalentClass, None),
    ]
    for subj, pred, obj in axiom_checks:
        if obj is None:
            if not any(graph.objects(subj, pred)):
                errors.append(f"axiom hilang: {subj} {pred} ?")
        elif (subj, pred, obj) not in graph:
            errors.append(f"axiom hilang: {subj} {pred} {obj}")

    chains = list(graph.objects(None, OWL.propertyChainAxiom))
    if len(chains) != len(tbox.PROPERTY_CHAINS):
        errors.append(f"jumlah propertyChainAxiom: {len(chains)} != {len(tbox.PROPERTY_CHAINS)}")

    for name, spec in tbox.OBJECT_PROPERTIES.items():
        inverse = spec.get("inverse")
        if not inverse:
            continue
        for subj, obj in graph.subject_objects(KBR[name]):
            if (obj, KBR[inverse], subj) not in graph:
                errors.append(f"inverse tak lengkap: {subj} kbr:{name} {obj}")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bangun ontology.ttl dari knowledge tables.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="path keluaran TTL")
    args = parser.parse_args(argv)

    graph, _expected, errors, builder = build()
    if errors:
        print("VALIDASI GAGAL:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 2

    args.out.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=str(args.out), format="turtle")
    individuals = len(list(graph.subjects(RDF.type, OWL.NamedIndividual)))
    print(f"ontology.ttl ditulis: {args.out}")
    print(
        f"triple: {len(graph)} | individu: {individuals} | "
        f"chunk bukti: {len(builder.chunks)} | bagian dokumen: {builder.class_counts['SourceSection']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
