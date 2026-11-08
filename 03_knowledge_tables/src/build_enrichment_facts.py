"""Ekstrak fakta enrichment untuk 7 tanaman utama dari semua sumber relevan.

Sumber: curated DOC002/DOC005, baseline DOC002, chunks DOC005, dan chunk MD
DOC002. Output berupa CSV long-format siap dipakai generator TTL, entities CSV,
dan laporan gap. Semua fakta wajib membawa kutipan bukti dan ID sumber.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF

TABLE_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = TABLE_DIR.parent
ONTO_DIR = PROJECT_ROOT / "04_ontology"

sys.path.insert(0, str(ONTO_DIR))
sys.path.insert(0, str(TABLE_DIR / "src"))

import build_ontology as bo  # noqa: E402
from tbox import KBR  # noqa: E402

CURATED2 = TABLE_DIR / "curated" / "DOC002"
CURATED5 = TABLE_DIR / "curated" / "DOC005"
UBI_KAYU_TABLE_CSV = CURATED2 / "ubi_kayu_tabel_5.csv"
AUTO_DIR = TABLE_DIR / "auto"
DOC002_MD_CHUNKS = AUTO_DIR / "DOC002_md" / "DOC002_md_chunks.csv"
DOC002_BASELINE = PROJECT_ROOT / "02_extraction" / "llamaparse" / "baseline" / "DOC002.blocks.jsonl"
DOC005_CHUNKS = PROJECT_ROOT / "02_extraction" / "extracted_text" / "DOC005.chunks.jsonl"
DOC005_MD = PROJECT_ROOT / "00_sumber_data" / "07_PenyakitKacangHijau.md"
ONTOLOGY_TTL = ONTO_DIR / "ontology.ttl"

OUTPUT_DIR = AUTO_DIR / "DOC002_md"
FACTS_CSV = OUTPUT_DIR / "DOC002_enrichment_facts.csv"
ENTITIES_CSV = OUTPUT_DIR / "DOC002_enrichment_entities.csv"
REPORT_MD = TABLE_DIR / "reports" / "DOC002_enrichment_gaps.md"

SCOPE_PLANTS = ["Padi", "Kedelai", "Jagung", "UbiJalar", "UbiKayu", "KacangTanah", "KacangHijau"]
TABLE_PART = {"T5.1_DAUN": "daun", "T5.2_BATANG": "batang", "T5.3_AKAR": "akar"}
PLANT_LABELS = {
    "Padi": "Padi",
    "Kedelai": "Kedelai",
    "Jagung": "Jagung",
    "UbiJalar": "Ubi jalar",
    "UbiKayu": "Ubi kayu",
    "KacangTanah": "Kacang tanah",
    "KacangHijau": "Kacang hijau",
}
PLANT_LOCAL_BY_LABEL = {label: local for local, label in PLANT_LABELS.items()}
DOC002_CHAPTER_PLANT = {
    1: "Padi",
    2: "Kedelai",
    3: "KacangTanah",
    4: "UbiJalar",
    5: "UbiKayu",
    6: "Jagung",
}
DOC005_PLANT_MAP = {
    "kedelai": "Kedelai",
    "kacang tanah": "KacangTanah",
    "kacang hijau": "KacangHijau",
}

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
ENTITY_COLUMNS = ["entity_local", "entity_class", "label", "source_document", "source_id", "notes"]

CONDITION_LABELS = {
    "KondisiDataranRendah": "Dataran rendah",
    "KondisiDataranTinggi": "Dataran tinggi",
    "KondisiSuhuDingin": "Suhu dingin",
    "KondisiSuhuSedang": "Suhu sedang",
    "KondisiSuhuHangat": "Suhu hangat",
    "KondisiCurahHujanRendah": "Curah hujan rendah",
    "KondisiCurahHujanSedang": "Curah hujan sedang",
    "KondisiCurahHujanTinggi": "Curah hujan tinggi",
    "KondisiKelembapanUdaraRendah": "Kelembapan udara rendah",
    "KondisiKelembapanUdaraSedang": "Kelembapan udara sedang",
    "KondisiKelembapanUdaraTinggi": "Kelembapan udara tinggi",
    "KondisiCahayaRendah": "Cahaya rendah",
    "KondisiCahayaSedang": "Cahaya sedang",
    "KondisiCahayaTinggi": "Cahaya tinggi",
    "KondisiTanahSubur": "Tanah subur",
    "KondisiTanahGembur": "Tanah gembur",
    "KondisiTanahBerpasir": "Tanah berpasir",
    "KondisiTanahLiat": "Tanah liat",
    "KondisiTanahAsam": "Tanah asam",
    "KondisiTanahNetral": "Tanah netral",
    "KondisiTanahBasa": "Tanah basa",
    "KondisiDrainaseBaik": "Drainase baik",
    "KondisiDrainaseBuruk": "Drainase buruk",
    "KondisiIklimKering": "Iklim kering",
    "KondisiIklimBasah": "Iklim basah",
}
EXISTING_FACTOR_LABELS = {
    "KondisiKelembapanTinggi": "Kelembapan tinggi",
    "KondisiSuhu": "Suhu",
    "KondisiCurahHujan": "Curah hujan",
    "KondisiMusimHujan": "Musim hujan",
    "KondisiMusimKemarau": "Musim kemarau",
}

NUMBERING_RE = re.compile(r"^\d+(?:\.\d+)*\s*")
RISK_POSITIVE_RE = re.compile(
    r"mendukung|berkembang|meningkat|optimum|kondisi|faktor|infeksi|serangan|berkecambah|"
    r"sporulasi|menguntungkan|memengaruhi|menyebar|ditemukan|ekstrim",
    re.I,
)
RISK_NEGATIVE_RE = re.compile(
    r"pengendalian|perlakuan|aplikasi|fungisida|bakterisida|disemprot|direndam|pemanasan|"
    r"panas kering|mengeliminasi|membunuh|dikendalikan|insektisida",
    re.I,
)
ABBREVIATION_END_RE = re.compile(r"(?:\bet al\.|\b[A-Z]\.|\b(?:sp|spp|No|Gambar|Tabel)\.)$")
SCI_NAME_RE = re.compile(r"\b[A-Z][a-z]{2,}\s+[a-z]{2,}(?:\s+(?:pv\.|spp\.|sp\.))?")


@dataclass
class Unit:
    document: str
    source_type: str
    source_id: str
    page: str
    chapter: str
    section: str
    subsection: str
    plant: str
    disease: str
    content_type: str
    text: str
    disease_name: str = ""
    line_start: str = ""
    line_end: str = ""


@dataclass
class Fact:
    subject_local: str
    subject_class: str
    predicate: str
    object_local: str = ""
    object_class: str = ""
    literal_value: str = ""
    literal_lang: str = ""
    sources: list[tuple[str, str, str, str, str, str, str]] = field(default_factory=list)
    confidence: str = "medium"
    review_status: str = "auto_ok"
    notes: list[str] = field(default_factory=list)


def read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def norm(text: object) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()


def norm_section(text: object) -> str:
    return NUMBERING_RE.sub("", norm(text))


def norm_disease(text: object) -> str:
    value = norm(text)
    value = re.sub(r"^penyakit\s+", "", value)
    return re.sub(r"[^0-9a-z]+", " ", value).strip()


def sentences(text: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text or "") if part.strip()]
    merged: list[str] = []
    for part in parts:
        if merged and (part[:1].islower() or ABBREVIATION_END_RE.search(merged[-1])):
            merged[-1] = merged[-1] + " " + part
        else:
            merged.append(part)
    found: list[str] = []
    for sentence in merged:
        if len(sentence) >= 20:
            found.append(sentence)
    return found


def is_heading_line(line: str) -> bool:
    value = line.strip()
    if not value:
        return True
    if value.startswith("|") or value.startswith("#"):
        return True
    if re.match(r"^(?:Gambar|Tabel|Foto|Sumber)\b", value, re.I):
        return True
    if len(value) <= 90 and (
        value.isupper()
        or re.match(r"^(?:\d+|[a-z])[.)]?\s+[A-Z]", value)
        or re.match(r"^[a-z]\)\s+", value)
    ):
        return True
    return False


def first_body_paragraph(text: str) -> str:
    for chunk in re.split(r"\n\s*\n", text or ""):
        lines = [line.strip() for line in chunk.splitlines() if line.strip()]
        while lines and is_heading_line(lines[0]):
            lines.pop(0)
        body = " ".join(lines).strip()
        if len(body) < 80:
            continue
        if body.startswith("|"):
            continue
        return body
    return ""


def truncate_sentence(text: str, limit: int = 2000) -> tuple[str, bool]:
    value = (text or "").strip()
    if len(value) <= limit:
        return value, False
    cut = value[:limit]
    pos = max(cut.rfind(". "), cut.rfind("; "), cut.rfind(", "))
    if pos >= limit // 2:
        cut = cut[: pos + 1]
    return cut.strip(), True


def plant_from_doc002(chapter: str, section: str) -> str:
    match = re.search(r"Bab\s+(\d+)", chapter or "", re.I)
    if match:
        return DOC002_CHAPTER_PLANT.get(int(match.group(1)), "")
    match = re.match(r"^(\d+)(?:\.|$)", section or "")
    if match:
        return DOC002_CHAPTER_PLANT.get(int(match.group(1)), "")
    return ""


def plant_from_doc005(plant_name: str, chapter: str) -> str:
    for key, local in DOC005_PLANT_MAP.items():
        if key in norm(plant_name) or key in norm(chapter):
            return local
    return ""


def load_doc002_baseline() -> list[Unit]:
    units: list[Unit] = []
    for block in read_jsonl(DOC002_BASELINE):
        text = (block.get("text") or "").strip()
        content_type = (block.get("content_type") or "").strip()
        if not text or content_type not in {"paragraph", "list_item"}:
            continue
        chapter = (block.get("chapter") or "").strip()
        section = (block.get("section") or "").strip()
        plant = plant_from_doc002(chapter, section)
        if plant not in SCOPE_PLANTS:
            continue
        units.append(
            Unit(
                document="DOC002",
                source_type="baseline_block",
                source_id=(block.get("block_id") or "").strip(),
                page=str(block.get("page_number") or ""),
                chapter=chapter,
                section=section,
                subsection=(block.get("subsection") or "").strip(),
                plant=plant,
                disease="",
                content_type=content_type,
                text=text,
            )
        )
    return units


def load_doc005_chunks() -> list[Unit]:
    units: list[Unit] = []
    for chunk in read_jsonl(DOC005_CHUNKS):
        text = (chunk.get("text_markdown") or chunk.get("plain_text") or "").strip()
        if not text:
            continue
        plant = plant_from_doc005(
            (chunk.get("plant_name") or "").strip(),
            (chunk.get("chapter") or "").strip(),
        )
        if plant not in SCOPE_PLANTS:
            continue
        units.append(
            Unit(
                document="DOC005",
                source_type="doc005_chunk",
                source_id=(chunk.get("chunk_id") or "").strip(),
                page=str(chunk.get("page_start") or ""),
                chapter=(chunk.get("chapter") or "").strip(),
                section=(chunk.get("section") or "").strip(),
                subsection=(chunk.get("subsection") or "").strip(),
                plant=plant,
                disease="",
                content_type=(chunk.get("content_type") or "").strip(),
                text=text,
                disease_name=(chunk.get("disease_name") or "").strip(),
            )
        )
    return units


def load_md_units() -> list[Unit]:
    units: list[Unit] = []
    for row in read_csv(DOC002_MD_CHUNKS):
        if (row.get("doc_part") or "") != "body":
            continue
        plant = PLANT_LOCAL_BY_LABEL.get((row.get("plant_name") or "").strip(), "")
        if plant not in SCOPE_PLANTS:
            continue
        units.append(
            Unit(
                document="DOC002",
                source_type="md_chunk",
                source_id=(row.get("chunk_id") or "").strip(),
                page="",
                chapter=(row.get("chapter") or "").strip(),
                section=(row.get("section") or "").strip(),
                subsection=(row.get("subsection") or "").strip(),
                plant=plant,
                disease="",
                content_type=(row.get("content_type") or "").strip(),
                text=(row.get("text_markdown") or "").strip(),
                line_start=(row.get("line_start") or "").strip(),
                line_end=(row.get("line_end") or "").strip(),
            )
        )
    return units


def load_doc005_md_units() -> list[Unit]:
    if not DOC005_MD.exists():
        return []
    text = DOC005_MD.read_text(encoding="utf-8").replace("\r\n", "\n")
    match = re.search(r"^##\s+Pendahuluan\s*$", text, re.M | re.I)
    if not match:
        return []
    for paragraph in re.split(r"\n\s*\n", text[match.end():]):
        raw = paragraph.strip()
        value = re.sub(r"[*_]+", "", raw)
        if len(value) < 80 or value.startswith("#") or value.startswith("---"):
            continue
        position = text.find(raw, match.end())
        start = text[:position].count("\n") + 1 if position >= 0 else 0
        return [
            Unit(
                document="DOC005",
                source_type="md_chunk",
                source_id="DOC005_MD_PENDAHULUAN",
                page="",
                chapter="KACANG HIJAU",
                section="Pendahuluan",
                subsection="",
                plant="KacangHijau",
                disease="",
                content_type="paragraph",
                text=value,
                line_start=str(start),
            )
        ]
    return []


def disease_maps(entries: list[dict[str, str]]) -> tuple[dict, dict, dict]:
    by_id = {entry["disease_id"]: entry for entry in entries}
    by_name: dict[tuple[str, str], list[dict[str, str]]] = {}
    by_section: dict[tuple[str, str], list[dict[str, str]]] = {}
    by_subsection: dict[tuple[str, str], list[dict[str, str]]] = {}
    seen: dict[tuple, set[str]] = {}

    def add(target: dict, key: tuple, entry: dict[str, str]) -> None:
        if not key[1]:
            return
        ids = seen.setdefault((id(target), key), set())
        if entry["disease_id"] in ids:
            return
        ids.add(entry["disease_id"])
        target.setdefault(key, []).append(entry)

    for path in (CURATED2 / "diseases.csv", CURATED5 / "diseases.csv"):
        for row in read_csv(path):
            entry = by_id.get((row.get("disease_id") or "").strip())
            if not entry:
                continue
            plant = entry["plant_local"]
            add(by_name, (plant, norm_disease(row.get("disease_name_verbatim"))), entry)
            add(by_section, (plant, norm_section(row.get("section"))), entry)
            add(by_subsection, (plant, norm_section(row.get("subsection"))), entry)
    return by_name, by_section, by_subsection


def assign_diseases(units: list[Unit], entries: list[dict[str, str]]) -> None:
    by_name, by_section, by_subsection = disease_maps(entries)

    def unique(items: list[dict[str, str]], source: str) -> Optional[dict[str, str]]:
        filtered = [item for item in items if item.get("source") == source]
        locals_ = {item["local"] for item in filtered}
        return filtered[0] if len(locals_) == 1 else None

    for unit in units:
        source = "DOC005" if unit.document == "DOC005" else "DOC002"
        candidates: list[dict[str, str]] = []
        if unit.document == "DOC005":
            candidates = by_name.get((unit.plant, norm_disease(unit.disease_name)), [])
            if not candidates and unit.section:
                candidates = by_name.get((unit.plant, norm_disease(unit.section)), [])
        else:
            sub_key = (unit.plant, norm_section(unit.subsection))
            sec_key = (unit.plant, norm_section(unit.section))
            if sub_key in by_subsection:
                candidates = by_subsection[sub_key]
            elif sec_key in by_section:
                candidates = by_section[sec_key]
            if not candidates:
                haystack = norm_section(unit.section) + " " + norm_section(unit.subsection)
                haystack_name = norm_disease(haystack)
                for (plant, name), items in by_name.items():
                    if plant != unit.plant or len(name) < 8:
                        continue
                    if name in haystack_name or haystack_name in name:
                        candidates.extend(items)
        chosen = unique(candidates, source)
        if chosen:
            unit.disease = chosen["local"]


def add_fact(
    facts: dict[tuple, Fact],
    subject: str,
    subject_class: str,
    predicate: str,
    unit: Unit,
    quote: str,
    object_local: str = "",
    object_class: str = "",
    literal_value: str = "",
    literal_lang: str = "",
    confidence: str = "medium",
    review_status: str = "auto_ok",
    notes: str = "",
) -> None:
    key = (subject, predicate, object_local, literal_value)
    fact = facts.get(key)
    if fact is None:
        fact = Fact(
            subject_local=subject,
            subject_class=subject_class,
            predicate=predicate,
            object_local=object_local,
            object_class=object_class,
            literal_value=literal_value,
            literal_lang=literal_lang,
            confidence=confidence,
            review_status=review_status,
        )
        facts[key] = fact
    source = (
        unit.document,
        unit.source_type,
        unit.source_id,
        quote,
        unit.page,
        unit.line_start,
        unit.line_end,
    )
    if source not in fact.sources:
        fact.sources.append(source)
    if confidence == "high":
        fact.confidence = "high"
    if review_status == "needs_review":
        fact.review_status = "needs_review"
    if notes and notes not in fact.notes:
        fact.notes.append(notes)


def temperature_bucket(low: float, high: float) -> str:
    average = (low + high) / 2
    if average < 20:
        return "KondisiSuhuDingin"
    if average <= 27:
        return "KondisiSuhuSedang"
    return "KondisiSuhuHangat"


def rainfall_bucket(low: float, high: float) -> str:
    average = (low + high) / 2
    if average < 1000:
        return "KondisiCurahHujanRendah"
    if average <= 2500:
        return "KondisiCurahHujanSedang"
    return "KondisiCurahHujanTinggi"


def humidity_bucket(low: float, high: float) -> str:
    average = (low + high) / 2
    if average < 60:
        return "KondisiKelembapanUdaraRendah"
    if average <= 80:
        return "KondisiKelembapanUdaraSedang"
    return "KondisiKelembapanUdaraTinggi"


def light_bucket(low: float, high: float) -> str:
    average = (low + high) / 2
    if average < 8:
        return "KondisiCahayaRendah"
    if average <= 12:
        return "KondisiCahayaSedang"
    return "KondisiCahayaTinggi"


def percent_light_bucket(low: float, high: float) -> str:
    average = (low + high) / 2
    if average < 50:
        return "KondisiCahayaRendah"
    if average <= 70:
        return "KondisiCahayaSedang"
    return "KondisiCahayaTinggi"


def ph_bucket(low: float, high: float) -> str:
    average = (low + high) / 2
    if average < 6.5:
        return "KondisiTanahAsam"
    if average <= 7.5:
        return "KondisiTanahNetral"
    return "KondisiTanahBasa"


def parse_range(match: re.Match[str], group_a: int = 1, group_b: int = 2) -> tuple[float, float]:
    low = float(match.group(group_a).replace(".", ""))
    high = float(match.group(group_b).replace(".", ""))
    if high > 60 and high % 10 == 0:
        high = high / 10
    if low > high:
        low, high = high, low
    return low, high


def condition_locals(text: str) -> list[str]:
    value = norm(text)
    found: list[str] = []

    def add(local: str) -> None:
        if local not in found:
            found.append(local)

    if "dataran rendah" in value:
        add("KondisiDataranRendah")
    if "dataran tinggi" in value:
        add("KondisiDataranTinggi")

    temp_matches = list(
        re.finditer(r"suhu[^.]{0,100}?(\d{1,2})\s*[-–—]\s*(\d{1,3})\s*(?:°?\s*c|0c)", value)
    )
    if temp_matches:
        for match in temp_matches:
            low, high = parse_range(match)
            add(temperature_bucket(low, high))
    else:
        match = re.search(r"suhu[^.]{0,60}?(\d{1,2})\s*(?:°?\s*c|0c)", value)
        if match:
            temp = float(match.group(1))
            add(temperature_bucket(temp, temp))

    for pattern, bucket in (
        (r"(?:penyinaran|cahaya)[^.]{0,100}?(\d{1,2})\s*[-–—]\s*(\d{1,3})\s*jam", light_bucket),
        (r"(?:penyinaran|cahaya)[^.]{0,100}?(\d{1,3})\s*[-–—]\s*(\d{1,3})\s*%", percent_light_bucket),
    ):
        match = re.search(pattern, value)
        if match:
            low, high = parse_range(match)
            add(bucket(low, high))

    match = re.search(r"kelembap\w*|kelembab\w*", value)
    if match:
        percent = re.search(r"(\d{1,3})\s*[-–—]\s*(\d{1,3})\s*%", value)
        if percent:
            low, high = parse_range(percent)
            add(humidity_bucket(low, high))

    match = re.search(r"curah hujan[^.]{0,100}?(\d[\d.]*)\s*[-–—]\s*(\d[\d.]*)\s*mm", value)
    if match:
        low, high = parse_range(match)
        add(rainfall_bucket(low, high))
    else:
        match = re.search(r"curah hujan[^.]{0,60}?(\d[\d.]*)\s*mm", value)
        if match:
            total = float(match.group(1).replace(".", ""))
            add(rainfall_bucket(total, total))

    for word, local in (
        ("subur", "KondisiTanahSubur"),
        ("gembur", "KondisiTanahGembur"),
        ("berpasir", "KondisiTanahBerpasir"),
        ("tanah liat", "KondisiTanahLiat"),
        ("liat", "KondisiTanahLiat"),
        ("asam", "KondisiTanahAsam"),
        ("netral", "KondisiTanahNetral"),
        ("basa", "KondisiTanahBasa"),
    ):
        if "tanah" in value and word in value:
            add(local)

    match = re.search(r"ph[^.]{0,40}?(\d{1,2}(?:[.,]\d+)?)\s*[-–—]\s*(\d{1,2}(?:[.,]\d+)?)", value)
    if match:
        low = float(match.group(1).replace(",", "."))
        high = float(match.group(2).replace(",", "."))
        add(ph_bucket(low, high))
    else:
        match = re.search(r"ph[^.]{0,40}?(\d{1,2}(?:[.,]\d+)?)", value)
        if match:
            value_ph = float(match.group(1).replace(",", "."))
            add(ph_bucket(value_ph, value_ph))

    if "drainase" in value:
        if re.search(r"drainase[^.]{0,40}(?:baik|lancar)", value):
            add("KondisiDrainaseBaik")
        if re.search(r"drainase[^.]{0,40}(?:buruk|jelek|terganggu)", value):
            add("KondisiDrainaseBuruk")

    if "iklim" in value:
        if "kering" in value:
            add("KondisiIklimKering")
        if "basah" in value or "hujan" in value:
            add("KondisiIklimBasah")

    return found


def extract_conditions(units: list[Unit], facts: dict[tuple, Fact]) -> None:
    for unit in units:
        if unit.document != "DOC002" or "pendahuluan" not in norm(unit.section):
            continue
        if unit.plant not in SCOPE_PLANTS:
            continue
        for sentence in sentences(unit.text):
            for local in condition_locals(sentence):
                add_fact(
                    facts,
                    unit.plant,
                    "TanamanPangan",
                    "memilikiKondisiTumbuh",
                    unit,
                    sentence,
                    object_local=local,
                    object_class="FaktorLingkungan",
                    confidence="high" if re.search(r"\d", sentence) else "medium",
                )


def extract_plant_descriptions(units: list[Unit], facts: dict[tuple, Fact]) -> None:
    seen: set[str] = set()
    for unit in units:
        if unit.plant in seen:
            continue
        if "pendahuluan" not in norm(unit.section):
            continue
        body = first_body_paragraph(unit.text)
        if not body:
            continue
        literal, truncated = truncate_sentence(body)
        add_fact(
            facts,
            unit.plant,
            "TanamanPangan",
            "deskripsiTanaman",
            unit,
            body,
            literal_value=literal,
            literal_lang="id",
            confidence="high",
            notes="truncated" if truncated else "",
        )
        seen.add(unit.plant)


def extract_disease_descriptions(units: list[Unit], facts: dict[tuple, Fact]) -> None:
    seen: set[str] = set()
    for unit in units:
        if not unit.disease or unit.disease in seen:
            continue
        body = first_body_paragraph(unit.text)
        if not body:
            continue
        literal, truncated = truncate_sentence(body)
        add_fact(
            facts,
            unit.disease,
            "Penyakit",
            "deskripsiPenyakit",
            unit,
            body,
            literal_value=literal,
            literal_lang="id",
            confidence="medium",
            notes="truncated" if truncated else "",
        )
        seen.add(unit.disease)


def extract_table_descriptions(
    facts: dict[tuple, Fact],
    entries: list[dict[str, str]],
    md_units: list[Unit],
) -> None:
    by_name: dict[str, list[dict[str, str]]] = {}
    for entry in entries:
        by_name.setdefault(norm(entry["nama"]), []).append(entry)

    md_index = [
        (unit.source_id, norm(unit.text), unit)
        for unit in md_units
        if unit.document == "DOC002"
    ]
    block_index = [
        ((block.get("block_id") or "").strip(), norm(block.get("text")))
        for block in read_jsonl(DOC002_BASELINE)
    ]

    seen: set[str] = set()
    for row in read_csv(UBI_KAYU_TABLE_CSV):
        name = (row.get("disease_name") or "").strip()
        symptom = (row.get("symptom_text") or "").strip()
        if not name or not symptom:
            continue
        candidates = by_name.get(norm(name), [])
        if len(candidates) > 1:
            part = TABLE_PART.get((row.get("table_id") or "").strip(), "")
            candidates = [c for c in candidates if part in norm(c.get("subsection"))]
        if len(candidates) != 1:
            continue
        entry = candidates[0]
        local = entry["local"]
        if local in seen:
            continue
        if any(key[0] == local and key[1] == "deskripsiPenyakit" for key in facts):
            seen.add(local)
            continue

        needle = norm(symptom)
        source_type = "table_row"
        source_id = (row.get("source_block_id") or "").strip()
        line_start = ""
        line_end = ""
        review_status = "needs_review"
        if needle:
            for chunk_id, chunk_text, unit in md_index:
                if needle in chunk_text:
                    source_type = "md_chunk"
                    source_id = chunk_id
                    line_start, line_end = unit.line_start, unit.line_end
                    review_status = "auto_ok"
                    break
            else:
                for block_id, block_text in block_index:
                    if needle in block_text:
                        source_type = "baseline_block"
                        source_id = block_id
                        review_status = "auto_ok"
                        break

        notes = ["baris tabel gejala ubi kayu"]
        if source_type == "md_chunk":
            notes.append("verbatim di chunk tabel MD")
        elif source_type == "table_row":
            notes.append("sel tabel terkurasi; belum ditemukan verbatim di MD/baseline")

        unit = Unit(
            document="DOC002",
            source_type=source_type,
            source_id=source_id,
            page=(row.get("page") or "").strip(),
            chapter="Bab 5",
            section="5.2 Patogen Pada Tanaman Ubi Kayu",
            subsection=(row.get("table_title") or "").strip(),
            plant="UbiKayu",
            disease=local,
            content_type="table",
            text=symptom,
            line_start=line_start,
            line_end=line_end,
        )
        add_fact(
            facts,
            local,
            "Penyakit",
            "deskripsiPenyakit",
            unit,
            symptom,
            literal_value=symptom,
            literal_lang="id",
            confidence="medium",
            review_status=review_status,
            notes=";".join(notes),
        )
        seen.add(local)


def extract_risk_factors(units: list[Unit], facts: dict[tuple, Fact]) -> None:
    for unit in units:
        if not unit.disease:
            continue
        for sentence in sentences(unit.text):
            low = norm(sentence)
            if not sentence[:1].isupper() or RISK_NEGATIVE_RE.search(sentence):
                continue
            if not RISK_POSITIVE_RE.search(sentence):
                continue
            for local, _cls, pattern in bo.ENV_PATTERNS:
                if local == "KondisiSuhu":
                    if not re.search(r"suhu[^.]{0,80}(?:\d|optimum|tinggi|rendah|dingin|hangat)", low):
                        continue
                if pattern.search(sentence):
                    add_fact(
                        facts,
                        unit.disease,
                        "Penyakit",
                        "dipengaruhiOleh",
                        unit,
                        sentence,
                        object_local=local,
                        object_class="FaktorRisiko",
                        confidence="medium",
                    )


def extract_severity(units: list[Unit], facts: dict[tuple, Fact]) -> None:
    seen: set[str] = set()
    for unit in units:
        if not unit.disease or unit.disease in seen:
            continue
        for sentence in sentences(unit.text):
            if not re.search(r"(?:tingkat keparahan|kehilangan hasil|kerugian hasil|penurunan hasil)", norm(sentence)):
                continue
            if not re.search(r"\d", sentence):
                continue
            literal, truncated = truncate_sentence(sentence, 500)
            add_fact(
                facts,
                unit.disease,
                "Penyakit",
                "tingkatKeparahan",
                unit,
                sentence,
                literal_value=literal,
                literal_lang="id",
                confidence="medium",
                review_status="needs_review",
                notes="truncated" if truncated else "perlu verifikasi konteks",
            )
            seen.add(unit.disease)
            break


def annotate_md_crossrefs(facts: dict[tuple, Fact], md_units: list[Unit]) -> None:
    for fact in facts.values():
        if any(source[1] == "md_chunk" for source in fact.sources):
            continue
        primary = fact.sources[0]
        quote = primary[3]
        if not norm(quote):
            continue
        for unit in md_units:
            if norm(quote) and norm(quote) in norm(unit.text):
                source = (
                    unit.document,
                    unit.source_type,
                    unit.source_id,
                    quote,
                    unit.page,
                    unit.line_start,
                    unit.line_end,
                )
                if source not in fact.sources:
                    fact.sources.append(source)
                fact.notes.append("crossref_md")
                break


def load_existing_triples() -> set[tuple[str, str, str]]:
    graph = Graph()
    if ONTOLOGY_TTL.exists():
        graph.parse(data=ONTOLOGY_TTL.read_text(encoding="utf-8"), format="turtle")
    triples: set[tuple[str, str, str]] = set()
    for subject, predicate, obj in graph:
        triples.add((str(subject), str(predicate), str(obj)))
    return triples


def annotate_existing(facts: dict[tuple, Fact], existing: set[tuple[str, str, str]]) -> None:
    for fact in facts.values():
        subject = str(KBR[fact.subject_local])
        predicate = str(KBR[fact.predicate])
        if fact.object_local:
            obj = str(KBR[fact.object_local])
        else:
            obj = str(Literal(fact.literal_value, lang=fact.literal_lang or None))
        if (subject, predicate, obj) in existing:
            fact.notes.append("existing_in_base")


def fact_rows(facts: dict[tuple, Fact]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for index, fact in enumerate(facts.values(), start=1):
        sources = fact.sources
        primary = sources[0] if sources else ("", "", "", "", "", "", "")
        documents = sorted({source[0] for source in sources if source[0]})
        source_types = sorted({source[1] for source in sources if source[1]})
        source_ids = sorted({source[2] for source in sources if source[2]})
        pages = sorted({source[4] for source in sources if source[4]})
        line_starts = sorted({source[5] for source in sources if source[5]})
        line_ends = sorted({source[6] for source in sources if source[6]})
        notes = list(fact.notes)
        if len(sources) > 1:
            notes.append(f"evidence_count={len(sources)}")
        rows.append(
            {
                "fact_id": f"ENR_{index:04d}",
                "subject_local": fact.subject_local,
                "subject_class": fact.subject_class,
                "predicate": fact.predicate,
                "object_local": fact.object_local,
                "object_class": fact.object_class,
                "literal_value": fact.literal_value,
                "literal_lang": fact.literal_lang,
                "source_document": ";".join(documents),
                "source_type": ";".join(source_types),
                "source_id": ";".join(source_ids),
                "evidence_quote": primary[3],
                "page": ";".join(pages),
                "line_start": ";".join(line_starts),
                "line_end": ";".join(line_ends),
                "confidence": fact.confidence,
                "review_status": fact.review_status,
                "notes": ";".join(dict.fromkeys(notes)),
            }
        )
    return rows


def entity_rows(facts: dict[tuple, Fact], entries: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: dict[tuple[str, str], dict[str, str]] = {}
    for plant in SCOPE_PLANTS:
        rows[(plant, "TanamanPangan")] = {
            "entity_local": plant,
            "entity_class": "TanamanPangan",
            "label": PLANT_LABELS[plant],
            "source_document": "curated",
            "source_id": "",
            "notes": "",
        }
    for entry in entries:
        rows[(entry["local"], "Penyakit")] = {
            "entity_local": entry["local"],
            "entity_class": "Penyakit",
            "label": entry["nama"],
            "source_document": entry["source"],
            "source_id": entry["disease_id"],
            "notes": "",
        }
    for local, label in CONDITION_LABELS.items():
        rows[(local, "FaktorLingkungan")] = {
            "entity_local": local,
            "entity_class": "FaktorLingkungan",
            "label": label,
            "source_document": "derived",
            "source_id": "",
            "notes": "kondisi tumbuh terkontrol",
        }
    for fact in facts.values():
        if fact.predicate == "memilikiKondisiTumbuh":
            rows[(fact.object_local, "FaktorLingkungan")] = {
                "entity_local": fact.object_local,
                "entity_class": "FaktorLingkungan",
                "label": CONDITION_LABELS.get(fact.object_local, fact.object_local),
                "source_document": "derived",
                "source_id": "",
                "notes": "kondisi tumbuh terkontrol",
            }
        if fact.predicate == "dipengaruhiOleh":
            rows[(fact.object_local, "FaktorRisiko")] = {
                "entity_local": fact.object_local,
                "entity_class": "FaktorRisiko",
                "label": EXISTING_FACTOR_LABELS.get(fact.object_local, fact.object_local),
                "source_document": "ontology",
                "source_id": "",
                "notes": "faktor risiko existing",
            }
    return [rows[key] for key in sorted(rows)]


def write_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def curated_scope_sets(entries: list[dict[str, str]]) -> tuple[set[str], set[str], set[str]]:
    scope_ids = {entry["disease_id"] for entry in entries}
    pathogen_ids = {
        row["disease_id"].strip()
        for row in read_csv(CURATED2 / "disease_pathogen.csv")
        if row["disease_id"].strip() in scope_ids
    }
    pathogen_ids |= {
        row["disease_id"].strip()
        for row in read_csv(CURATED5 / "disease_pathogen.csv")
        if row["disease_id"].strip() in scope_ids
    }
    control_ids = {
        row["disease_id"].strip()
        for path in (CURATED2 / "controls.csv", CURATED5 / "controls.csv")
        for row in read_csv(path)
        if row["disease_id"].strip() in scope_ids and (row.get("scope") or "").strip() == "disease"
    }
    chapter_control_plants = {
        row["plant_id"].strip()
        for path in (CURATED2 / "controls.csv", CURATED5 / "controls.csv")
        for row in read_csv(path)
        if (row.get("scope") or "").strip() == "chapter"
    }
    return pathogen_ids, control_ids, chapter_control_plants


def gap_evidence(units: list[Unit], disease: str, keywords: re.Pattern[str]) -> list[str]:
    quotes: list[str] = []
    for unit in units:
        if unit.disease != disease:
            continue
        for sentence in sentences(unit.text):
            if keywords.search(sentence) and sentence not in quotes:
                quotes.append(sentence)
    return quotes[:3]


def build_report(
    facts: dict[tuple, Fact],
    units: list[Unit],
    entries: list[dict[str, str]],
    rows: list[dict[str, str]],
) -> str:
    pathogen_ids, control_ids, chapter_plants = curated_scope_sets(entries)
    by_predicate: dict[str, int] = {}
    conditions_by_plant: dict[str, set[str]] = {}
    descriptions_by_plant: set[str] = set()
    descriptions_by_disease: set[str] = set()
    for row in rows:
        by_predicate[row["predicate"]] = by_predicate.get(row["predicate"], 0) + 1
        if row["subject_class"] == "TanamanPangan":
            plant = row["subject_local"]
            if row["predicate"] == "memilikiKondisiTumbuh":
                conditions_by_plant.setdefault(plant, set()).add(row["object_local"])
            if row["predicate"] == "deskripsiTanaman":
                descriptions_by_plant.add(plant)
        if row["predicate"] == "deskripsiPenyakit":
            descriptions_by_disease.add(row["subject_local"])

    lines: list[str] = [
        "# Gap dan cakupan enrichment DOC002/DOC005",
        "",
        f"Scope: 7 tanaman utama. Fakta: **{len(rows)}**.",
        "",
        "## Ringkasan predikat",
        "",
        "| Predikat | Jumlah |",
        "|---|---:|",
    ]
    for predicate, count in sorted(by_predicate.items()):
        lines.append(f"| `{predicate}` | {count} |")

    lines += ["", "## Kondisi tumbuh per tanaman", "", "| Tanaman | Kondisi |", "|---|---|"]
    for plant in SCOPE_PLANTS:
        values = sorted(conditions_by_plant.get(plant, set()))
        lines.append(f"| {PLANT_LABELS[plant]} | {', '.join(CONDITION_LABELS.get(v, v) for v in values) or '—'} |")

    lines += ["", "## Deskripsi", "", "| Tipe | Terisi |", "|---|---:|"]
    lines.append(f"| Tanaman | {len(descriptions_by_plant)}/7 |")
    lines.append(f"| Penyakit | {len(descriptions_by_disease)}/{len(entries)} |")

    missing_plant_desc = [plant for plant in SCOPE_PLANTS if plant not in descriptions_by_plant]
    missing_conditions = [plant for plant in SCOPE_PLANTS if not conditions_by_plant.get(plant)]
    missing_disease_desc = [entry for entry in entries if entry["local"] not in descriptions_by_disease]
    lines += [
        "",
        "## Tanaman tanpa kondisi tumbuh",
        "",
        f"Jumlah: **{len(missing_conditions)}**",
        "",
    ]
    for plant in missing_conditions:
        lines.append(f"- {PLANT_LABELS[plant]}")
    if missing_conditions:
        lines.append(
            "- Tidak ada kalimat syarat tumbuh eksplisit untuk tanaman ini pada "
            "sumber dalam scope (baseline/MD DOC002 dan DOC005)."
        )
    lines += [
        "",
        "## Tanaman tanpa deskripsi",
        "",
        f"Jumlah: **{len(missing_plant_desc)}**",
        "",
    ]
    for plant in missing_plant_desc:
        lines.append(f"- {PLANT_LABELS[plant]} (tidak ada pendahuluan tanaman pada sumber)")
    if not missing_plant_desc:
        lines.append("Tidak ada — terisi penuh.")

    lines += [
        "",
        "## Penyakit tanpa deskripsi",
        "",
        f"Jumlah: **{len(missing_disease_desc)}**",
        "",
    ]
    for entry in missing_disease_desc:
        lines.append(f"- `{entry['disease_id']}` {entry['nama']} ({PLANT_LABELS[entry['plant_local']]})")
    if not missing_disease_desc:
        lines.append("Tidak ada — terisi penuh.")

    no_pathogen = [entry for entry in entries if entry["disease_id"] not in pathogen_ids]
    no_control = [entry for entry in entries if entry["disease_id"] not in control_ids]
    lines += [
        "",
        "## Penyakit tanpa tautan patogen di curated",
        "",
        f"Jumlah: **{len(no_pathogen)}**",
        "",
        "Tautan belum ada di curated; kutipan di bawah adalah kandidat bukti, bukan tautan final.",
        "",
    ]
    for entry in no_pathogen:
        quotes = gap_evidence(units, entry["local"], re.compile(r"disebabkan|penyebab|patogen|jamur|bakteri|virus|spp\.", re.I))
        lines.append(f"- `{entry['disease_id']}` {entry['nama']} ({PLANT_LABELS[entry['plant_local']]})")
        for quote in quotes:
            lines.append(f"  - bukti: {quote[:300]}")

    lines += [
        "",
        "## Penyakit tanpa pengendalian tingkat penyakit",
        "",
        f"Jumlah: **{len(no_control)}**",
        "",
    ]
    for entry in no_control:
        chapter_note = " (ada kendali tingkat bab)" if entry["plant_id"] in chapter_plants else ""
        quotes = gap_evidence(units, entry["local"], re.compile(r"pengendalian|dikendalikan|pengobatan|pencegahan|sanitasi|fungisida|bakterisida|rotasi|varietas tahan", re.I))
        lines.append(f"- `{entry['disease_id']}` {entry['nama']} ({PLANT_LABELS[entry['plant_local']]}){chapter_note}")
        for quote in quotes:
            lines.append(f"  - bukti: {quote[:300]}")

    md_table = sum(
        1
        for row in rows
        if row["predicate"] == "deskripsiPenyakit"
        and "baris tabel gejala ubi kayu" in row["notes"]
        and row["source_type"] == "md_chunk"
    )
    curated_table = sum(
        1
        for row in rows
        if row["predicate"] == "deskripsiPenyakit"
        and "baris tabel gejala ubi kayu" in row["notes"]
        and row["source_type"] == "table_row"
    )
    needs_review = sum(1 for row in rows if row["review_status"] == "needs_review")
    lines += [
        "",
        "## Catatan cakupan",
        "",
        "- Baseline DOC002 mencakup 6 tanaman DOC002 (Padi, Kedelai, Jagung, Ubi jalar, Ubi kayu, Kacang tanah).",
        "- DOC005 mencakup Kedelai, Kacang tanah, Kacang hijau.",
        "- MD DOC002 hanya mencakup Padi, Kedelai, dan Ubi kayu.",
        "- Penyakit Ubi kayu di DOC002 berupa baris tabel; deskripsi per penyakit diambil dari baris tabel gejala.",
        f"- Dari baris tabel Ubi kayu: {md_table} verbatim di chunk MD, {curated_table} sel tabel terkurasi (`needs_review`).",
        f"- Total fakta berstatus `needs_review`: {needs_review}.",
        "- Fakta tanaman di luar 7 tanaman utama dibuang.",
        "",
    ]
    return "\n".join(lines)


def build() -> tuple[list[dict[str, str]], list[dict[str, str]], str]:
    entries = bo.penyakit_entries()
    units = load_doc002_baseline() + load_doc005_chunks() + load_doc005_md_units()
    md_units = load_md_units()
    assign_diseases(units, entries)

    facts: dict[tuple, Fact] = {}
    extract_conditions(units, facts)
    extract_plant_descriptions(units, facts)
    extract_disease_descriptions(units, facts)
    extract_table_descriptions(facts, entries, md_units)
    extract_risk_factors(units, facts)
    extract_severity(units, facts)
    annotate_md_crossrefs(facts, md_units)
    annotate_existing(facts, load_existing_triples())

    rows = fact_rows(facts)
    entities = entity_rows(facts, entries)
    report = build_report(facts, units, entries, rows)
    return rows, entities, report


def main() -> int:
    rows, entities, report = build()
    write_csv(FACTS_CSV, FACT_COLUMNS, rows)
    write_csv(ENTITIES_CSV, ENTITY_COLUMNS, entities)
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text(report + "\n", encoding="utf-8")
    by_predicate: dict[str, int] = {}
    for row in rows:
        by_predicate[row["predicate"]] = by_predicate.get(row["predicate"], 0) + 1
    print(f"facts: {len(rows)}")
    print(f"entities: {len(entities)}")
    print(f"by_predicate: {dict(sorted(by_predicate.items()))}")
    print(f"output: {FACTS_CSV}")
    print(f"report: {REPORT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
