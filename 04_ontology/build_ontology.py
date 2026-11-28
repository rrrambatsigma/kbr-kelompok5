"""Generator ABox ontologi "Penyakit Tanaman Pangan Indonesia".

Membaca knowledge tables terkurasi DOC002 dan DOC005 untuk tujuh tanaman
pangan, lalu membangun ABox di atas TBox ``tbox.py``. Prinsip utama:

- hanya fakta yang punya dukungan sumber yang di-assert;
- teks sumber disimpan verbatim pada node BuktiSumber;
- gejala dan pengendalian dinormalisasi ke konsep kanonik;
- observasi lingkungan kuantitatif dipisahkan dari kondisi kualitatif;
- class dan individual tidak dicampur;
- tidak ada hash, UUID, atau ID database di local name.

Pemakaian dari root repo::

    python 04_ontology/build_ontology.py
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

ONTO_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = ONTO_DIR.parent
TABLE_DIR = PROJECT_ROOT / "03_knowledge_tables"
CURATED2 = TABLE_DIR / "curated" / "DOC002"
CURATED5 = TABLE_DIR / "curated" / "DOC005"
METADATA_CSV = TABLE_DIR / "curated" / "metadata.csv"
AUTO_DIR = TABLE_DIR / "auto"
META_PATH = PROJECT_ROOT / "01_knowledge_sources" / "source_metadata" / "manual_metadata.json"
SOURCE_REGISTRY_CSV = PROJECT_ROOT / "01_knowledge_sources" / "external" / "source_registry.csv"
DEFAULT_TTL = ONTO_DIR / "ontology.ttl"
DEFAULT_OWL = ONTO_DIR / "ontology.owl"
REPORT_PATH = ONTO_DIR / "extraction_report.json"

sys.path.insert(0, str(ONTO_DIR))

import definitions as defs  # noqa: E402
import knowledge  # noqa: E402
import tbox  # noqa: E402
from tbox import DCTERMS, KBR, PROV, SKOS  # noqa: E402

PLANT_LOCAL = knowledge.PLANT_LOCAL
PLANT_CLASS = knowledge.PLANT_CLASS
PLANT_LABELS = knowledge.PLANT_LABELS
PLANT_ORDER = knowledge.PLANT_ORDER
PLANT_SCIENTIFIC_FALLBACK = knowledge.PLANT_SCIENTIFIC_FALLBACK
TAXON_CLASS = knowledge.TAXON_CLASS
TAXON_PRIORITY = knowledge.TAXON_PRIORITY
PART_WORDS = knowledge.PART_WORDS
PART_LABELS = knowledge.PART_LABELS
PART_OF = knowledge.PART_OF
PART_SUBCLASS = knowledge.PART_SUBCLASS
TABLE_PART = knowledge.TABLE_PART

CANONICAL_SYMPTOMS = knowledge.CANONICAL_SYMPTOMS

CONTROL_ACTIONS = knowledge.CONTROL_ACTIONS

PHASE_DEFS = knowledge.PHASE_DEFS

ENV_FACTORS = knowledge.ENV_FACTORS
QUALITATIVE_RULES = knowledge.QUALITATIVE_RULES
ENV_PATTERNS = knowledge.ENV_PATTERNS
ENV_CONTROL_CONTEXT_RE = knowledge.ENV_CONTROL_CONTEXT_RE
ENV_NEGATIVE_CONTEXT_RE = knowledge.ENV_NEGATIVE_CONTEXT_RE
VARIETY_STOPWORDS = knowledge.VARIETY_STOPWORDS
RESIST_MARKERS = knowledge.RESIST_MARKERS
VULN_MARKERS = knowledge.VULN_MARKERS
VARIETY_PRIMARY_RE = knowledge.VARIETY_PRIMARY_RE
VARIETY_FALLBACK_RE = knowledge.VARIETY_FALLBACK_RE
PLANT_WORDS = knowledge.PLANT_WORDS

def read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def norm(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def pascal(text: str) -> str:
    return "".join(w[:1].upper() + w[1:] for w in re.split(r"[^0-9A-Za-z]+", text or "") if w)


def significant_words(text: str, limit: int = 5) -> str:
    words = [w for w in re.findall(r"[A-Za-z0-9]+", text or "") if w.lower() not in VARIETY_STOPWORDS]
    return " ".join(words[:limit])


IMPACT_MARKERS = re.compile(
    r"\b(?:menyebabkan|mengakibatkan|berdampak|menurunkan|mengurangi|"
    r"kehilangan hasil|defoliasi|pengurangan)\b",
    re.I,
)


def compact_local(prefix: str, limit: int = 60) -> str:
    return (prefix or "Entitas")[:limit]


def unique_local(prefix: str, text: str, builder: "Builder") -> str:
    base = compact_local(prefix)
    local = base
    counter = 2
    while local in builder.used_locals:
        suffix = str(counter)
        local = base[: max(1, 60 - len(suffix))] + suffix
        counter += 1
    return local


def disease_part_hint(entry: dict) -> set[str]:
    name = (entry.get("local") or "").lower()
    return {part for word, part in PART_WORDS.items() if word in name}


def text_parts(text: str | None) -> list[str]:
    return knowledge.text_parts(text)


def disease_display(entry: dict) -> str:
    return entry.get("label") or entry.get("nama") or entry.get("local", "")


def plant_display(entry: dict) -> str:
    plant = entry.get("plant_local", "")
    return PLANT_LABELS.get(plant, plant)


def evidence_label(kind: str, entry: dict) -> str:
    return f"Bukti {kind} {disease_display(entry)} ({plant_display(entry)})"


def subsection_parts(subsection: str) -> list[str]:
    low = norm(subsection)
    found: list[str] = []
    for word, part in PART_WORDS.items():
        if word in low and part not in found:
            found.append(part)
    if "umbi" in low and "Akar" not in found:
        found.insert(0, "Akar")
    return found


def disease_qualifier(entry: dict[str, str]) -> str:
    parts = subsection_parts(entry.get("subsection") or "")
    if parts:
        return "".join(parts)
    en = pascal(entry.get("name_en") or "")
    if en:
        return en
    sec = pascal(entry.get("section") or "")
    return sec or "Umum"


DISEASE_LOCAL_ALIASES = {
    "ANTRAKNOSAKedelai": "PenyakitAntraknosaKedelai",
    "BERCAKDAUNKacangTanah": "PenyakitBercakDaunKacangTanah",
    "KARATKedelai": "PenyakitKaratDaunKedelai",
    "EMBUNBULUKedelai": "PenyakitEmbunPalsuDownyMildewKedelai",
    "BERCAKDAUNKacangHijau": "PenyakitBercakDaunKacangHijau",
    "EMBUNTEPUNGKacangHijau": "PenyakitEmbunTepungKacangHijau",
    "KARATKacangTanah": "PenyakitKaratDaunKacangTanah",
    "LAYUKacangHijau": "PenyakitLayuKacangHijau",
}

DISEASE_LABEL_ALIASES = {
    "ANTRAKNOSAKedelai": "Penyakit Antraknosa",
    "BERCAKDAUNKacangTanah": "Penyakit Bercak Daun",
    "KARATKedelai": "Penyakit Karat Daun",
    "EMBUNBULUKedelai": "Penyakit Embun Palsu (Downy mildew)",
    "BERCAKDAUNKacangHijau": "Penyakit Bercak Daun",
    "EMBUNTEPUNGKacangHijau": "Penyakit Embun Tepung",
    "KARATKacangTanah": "Penyakit Karat Daun",
    "LAYUKacangHijau": "Penyakit Layu",
}


def match_canonical_symptoms(text: str | None) -> list[str]:
    return knowledge.match_canonical_symptoms(text)


def match_control_actions(
    text: str | None,
    _category: str | None = None,
    _source: str | None = None,
) -> list[str]:
    return knowledge.match_control_actions(text)


def normalize_quote(text: str | None) -> str:
    value = (text or "").replace("\r", " ").replace("\n", " ")
    value = value.replace("\ufffdC", "°C").replace("\ufffd C", "°C")
    value = value.replace("\u2013", "-").replace("\u2014", "-").replace("\u00ad", "")
    return re.sub(r"\s+", " ", value).strip()


def short_label(text: str | None, limit: int = 72) -> str:
    value = normalize_quote(text).rstrip(" .")
    if len(value) > limit:
        value = value[:limit].rsplit(" ", 1)[0] + "..."
    return value


def safe_description(text: str | None) -> str:
    value = normalize_quote(text)
    if re.search(r"\b(et al\.|dkk\.)\s*$", value, re.I):
        value = value + " [kutipan sumber terpotong]"
    return value


def is_complete_sentence(text: str) -> bool:
    value = normalize_quote(text)
    if len(re.sub(r"[^0-9A-Za-z]", "", value)) < 35:
        return False
    if not re.match(r"^[\"“(]?[A-Z0-9]", value):
        return False
    if not re.search(r"[.!?]$", value):
        return False
    if re.search(r"\b(et al\.|dkk\.)\s*$", value, re.I):
        return False
    if value.count("(") != value.count(")"):
        return False
    if re.search(r"[,;:\-–—/]\s*$", value):
        return False
    return True


def decimal_value(text: str) -> Decimal | None:
    try:
        return Decimal(text.replace(",", "."))
    except (InvalidOperation, AttributeError):
        return None


def fmt_number(value: Decimal | None) -> str:
    if value is None:
        return ""
    value = value.normalize()
    rendered = format(value, "f")
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


def value_slug(obs: dict) -> str:
    unit = obs["unit"].replace("°C", "Celsius").replace("%", "Persen").replace("mm", "Milimeter")
    if obs.get("min") is not None and obs.get("max") is not None:
        low = fmt_number(obs["min"]).replace(".", "Koma")
        high = fmt_number(obs["max"]).replace(".", "Koma")
        return f"{low}Sampai{high}{unit}"
    op = pascal(obs.get("operator") or "")
    return f"{op}{fmt_number(obs.get('single')).replace('.', 'Koma')}{unit}"


def _env_unit_compatible(factor: str, unit: str) -> bool:
    if not unit:
        return factor == "Suhu"
    if factor == "Suhu":
        return unit in ("°C", "C")
    if factor == "Kelembapan":
        return unit == "%"
    if factor == "CurahHujan":
        return unit == "mm"
    return False


def _env_control_context(source: str, start: int, end: int) -> bool:
    context = source[max(0, start - 140) : min(len(source), end + 160)]
    return bool(ENV_CONTROL_CONTEXT_RE.search(context))


def _env_window(source: str, start: int, factor: str) -> str:
    window = source[start : start + 110]
    lower = window.lower()
    for other, cfg in ENV_FACTORS.items():
        if other == factor:
            continue
        indexes = [lower.find(term) for term in cfg["terms"]]
        indexes = [index for index in indexes if index > 0]
        if indexes:
            window = window[: min(indexes)]
    return re.split(r";|\.\s+(?=[A-Z])", window)[0]


def parse_env_observations(text: str) -> list[dict]:
    source = normalize_quote(text)
    lower = source.lower()
    results: list[dict] = []
    seen: set[tuple] = set()
    for factor, cfg in ENV_FACTORS.items():
        for term in cfg["terms"]:
            for match in re.finditer(r"\b" + re.escape(term) + r"\b", lower):
                if _env_control_context(source, match.start(), match.end()):
                    continue
                window = _env_window(source, match.end(), factor)
                low_window = window.lower()
                actual_class = cfg["class"]
                if factor == "Kelembapan" and ("tanah" in low_window or "lahan" in low_window):
                    actual_class = "KelembapanTanah"
                range_match = re.search(
                    r"(\d+(?:[.,]\d+)?)\s*(°\s*C|%|mm)?\s*(?:-|sampai|hingga|s/d)\s*(\d+(?:[.,]\d+)?)\s*(°\s*C|%|mm)?",
                    window,
                    re.I,
                )
                if range_match:
                    min_value = decimal_value(range_match.group(1))
                    max_value = decimal_value(range_match.group(3))
                    unit = (range_match.group(4) or range_match.group(2) or cfg["unit"]).replace(" ", "")
                    if unit.upper() in ("°C", "C"):
                        unit = "°C"
                    if not _env_unit_compatible(factor, unit):
                        continue
                    if min_value is not None and max_value is not None and min_value <= max_value:
                        key = (factor, actual_class, min_value, max_value, unit)
                        if key not in seen:
                            seen.add(key)
                            results.append(
                                {
                                    "factor": factor,
                                    "class": actual_class,
                                    "min": min_value,
                                    "max": max_value,
                                    "single": None,
                                    "operator": "range",
                                    "unit": unit,
                                    "condition": "Optimum" if re.search(r"optimum|optimal", low_window) else "",
                                    "window": window,
                                }
                            )
                    continue
                single_match = re.search(
                    r"(di\s*bawah|kurang\s*dari|<|lebih\s*dari|di\s*atas|>|sekitar|optimum|optimal|mencapai)?\s*(\d+(?:[.,]\d+)?)\s*(°\s*C|%|mm)?",
                    window,
                    re.I,
                )
                if not single_match:
                    continue
                comparator = (single_match.group(1) or "").strip().lower()
                value = decimal_value(single_match.group(2))
                unit = (single_match.group(3) or cfg["unit"]).replace(" ", "")
                if unit.upper() in ("°C", "C"):
                    unit = "°C"
                if value is None or not _env_unit_compatible(factor, unit):
                    continue
                if factor != "Suhu" and not single_match.group(3) and not comparator:
                    continue
                operator = "sama dengan"
                if comparator in ("di bawah", "kurang dari", "<"):
                    operator = "<"
                elif comparator in ("lebih dari", "di atas", ">"):
                    operator = ">"
                elif comparator == "sekitar":
                    operator = "sekitar"
                elif comparator in ("optimum", "optimal"):
                    operator = "optimum"
                key = (factor, actual_class, None, None, value, operator, unit)
                if key in seen:
                    continue
                seen.add(key)
                results.append(
                    {
                        "factor": factor,
                        "class": actual_class,
                        "min": None,
                        "max": None,
                        "single": value,
                        "operator": operator,
                        "unit": unit,
                        "condition": "Optimum" if operator == "optimum" else "",
                        "window": window,
                    }
                )
    return results


def qualitative_matches(text: str | None) -> list[tuple[str, str, str]]:
    return knowledge.qualitative_matches(text)


def extract_phases(text: str | None) -> list[str]:
    return knowledge.extract_phases(text)


def _strip_variety_tail(part: str) -> str:
    part = re.split(r"\s*\(", part)[0]
    part = re.sub(r"\s+\d+(?:\.\d+)?\s*%.*$", "", part)
    return part.strip().strip(",;:()\"'")


def _valid_variety(name: str) -> bool:
    if not name or len(name) < 2:
        return False
    for tok in name.split():
        if tok.isdigit():
            continue
        if len(tok) < 2:
            return False
        if tok.isupper():
            return False
        if re.search(r"[A-Z].*[A-Z]", tok):
            return False
    return True


def _strip_plant_prefix(name: str) -> str:
    tokens = name.split()
    plant_words = PLANT_WORDS
    while tokens and tokens[0].lower() in plant_words and len(tokens) > 1:
        tokens = tokens[1:]
    return " ".join(tokens)


def _proper_run(part: str) -> str:
    part = _strip_variety_tail(part)
    tokens: list[str] = []
    started = False
    for raw in part.split():
        tok = raw.strip(",;:()\"'")
        if not tok:
            continue
        if not started:
            if not re.match(r"^[A-Z]", tok):
                continue
            low = tok.lower()
            if low in VARIETY_STOPWORDS and low not in PLANT_WORDS:
                continue
            started = True
            tokens.append(tok)
            continue
        if re.match(r"^\d+$", tok):
            tokens.append(tok)
        elif re.match(r"^[A-Z][A-Za-z0-9\-']*$", tok):
            if tok.lower() in {"yang", "dan", "atau", "adalah", "dengan", "untuk", "pada"}:
                break
            tokens.append(tok)
        else:
            break
        if len(tokens) >= 6:
            break
    return " ".join(tokens)


def extract_varieties(text: str) -> list[str]:
    found: list[str] = []

    def push(name: str) -> None:
        name = _strip_plant_prefix(name)
        if not _valid_variety(name) or name in found or len(found) >= 6:
            return
        found.append(name)

    for match in VARIETY_PRIMARY_RE.finditer(text):
        rest = text[match.end():]
        window = re.split(r"[.\n]", rest)[0][:200]
        for part in re.split(r",\s*|\s+dan\s+|\s+atau\s+|\s+sedangkan\s+", window):
            push(_proper_run(part))
    if not found:
        for match in VARIETY_FALLBACK_RE.finditer(text):
            push(_proper_run(match.group(1)))
    return found


class Builder:
    def __init__(self) -> None:
        self.graph = Graph()
        self.errors: list[str] = []
        self.used_locals: set[str] = set()

    def individual(self, local: str, *classes: str) -> URIRef:
        if local in self.used_locals:
            self.errors.append(f"local name individu duplikat: {local}")
        self.used_locals.add(local)
        uri = KBR[local]
        self.graph.add((uri, RDF.type, OWL.NamedIndividual))
        for cls in classes:
            self.graph.add((uri, RDF.type, KBR[cls]))
        return uri

    def ensure_individual(self, local: str, *classes: str) -> URIRef:
        uri = KBR[local]
        if local not in self.used_locals:
            self.used_locals.add(local)
            self.graph.add((uri, RDF.type, OWL.NamedIndividual))
        for cls in classes:
            self.graph.add((uri, RDF.type, KBR[cls]))
        return uri

    def label(self, uri: URIRef, text: str | None) -> None:
        if text and text.strip():
            self.graph.add((uri, RDFS.label, Literal(text.strip(), lang="id")))
            self.graph.add((uri, SKOS.prefLabel, Literal(text.strip(), lang="id")))

    def alt(self, uri: URIRef, text: str | None, lang: str = "id") -> None:
        if text and text.strip():
            self.graph.add((uri, SKOS.altLabel, Literal(text.strip(), lang=lang)))

    def pref_label(self, uri: URIRef, text: str | None, lang: str = "id") -> None:
        if text and text.strip():
            self.graph.add((uri, SKOS.prefLabel, Literal(text.strip(), lang=lang)))

    def definition(self, uri: URIRef, text: str | None, source: str | None = None) -> None:
        if text and text.strip():
            self.graph.add((uri, SKOS.definition, Literal(text.strip(), lang="id")))
        if source and source.strip():
            self.graph.add((uri, DCTERMS.source, Literal(source.strip(), lang="id")))
        if source and source.strip().lower().startswith("glosarium doc006"):
            self.graph.add((uri, PROV.wasDerivedFrom, KBR["BukuDOC006"]))

    def comment(self, uri: URIRef, text: str | None) -> None:
        if text and text.strip():
            self.graph.add((uri, RDFS.comment, Literal(text.strip(), lang="id")))

    def lang(self, uri: URIRef, prop: str, value: str | None) -> None:
        if value and value.strip():
            self.graph.add((uri, KBR[prop], Literal(value.strip(), lang="id")))

    def plain(self, uri: URIRef, prop: str, value: str | None) -> None:
        if value and str(value).strip():
            self.graph.add((uri, KBR[prop], Literal(str(value).strip())))

    def decimal(self, uri: URIRef, prop: str, value: Decimal | None) -> None:
        if value is not None:
            self.graph.add((uri, KBR[prop], Literal(value, datatype=XSD.decimal)))

    def integer(self, uri: URIRef, prop: str, value: int | str | None) -> None:
        if value is None or str(value).strip() == "":
            return
        try:
            self.graph.add((uri, KBR[prop], Literal(int(value), datatype=XSD.integer)))
        except (TypeError, ValueError):
            self.errors.append(f"nilai bukan integer untuk {prop}: {value!r}")

    def link(self, uri: URIRef, prop: str, target: URIRef) -> None:
        self.graph.add((uri, KBR[prop], target))
        spec = tbox.OBJECT_PROPERTIES.get(prop, {})
        inverse = spec.get("inverse")
        if inverse:
            self.graph.add((target, KBR[inverse], uri))
        if prop in ("dikendalikanDengan", "pengendalianUmum", "merekomendasikanPengendalian"):
            self.graph.add((uri, KBR["berkaitanPengendalian"], target))

    def ext_link(self, uri: URIRef, prop: URIRef, target: URIRef) -> None:
        self.graph.add((uri, prop, target))


NON_SYMPTOM_MARKERS = re.compile(
    r"\b(kelembaban|kelembapan|suhu|angin|curah hujan|iklim|intensitas cahaya|naungan|ph)\b"
    r"|\b(kejadian penyakit|insidensi|kehilangan hasil|fase (vegetatif|generatif|pembibitan|anakan|matang))\b"
    r"|\b(hari setelah (infeksi|tanam|inokulasi)|musim|tingkat keparahan|bervariasi antara)\b"
    r"|\d+\s*%",
    re.I,
)


def is_non_symptom_text(text: str) -> bool:
    """Baris sumber yang menjelaskan lingkungan/epidemiologi, bukan gejala visual."""
    return bool(NON_SYMPTOM_MARKERS.search(text or ""))


def symptom_display(text: str | None) -> str:
    """Label gejala yang bersih: tanpa prefix dan tanpa pemotongan."""
    return normalize_quote(text)


def apply_class_property_definitions(builder: Builder) -> None:
    for name, (_label, _parent, comment) in tbox.CLASSES.items():
        text = defs.CLASS_DEFINITIONS.get(name, comment)
        builder.definition(KBR[name], text, "Dokumentasi TBox")
    for name, spec in tbox.OBJECT_PROPERTIES.items():
        text = defs.PROPERTY_DEFINITIONS.get(name, spec.get("comment"))
        builder.definition(KBR[name], text, "Dokumentasi TBox")
    for name, spec in tbox.DATA_PROPERTIES.items():
        text = defs.PROPERTY_DEFINITIONS.get(name, spec.get("comment"))
        builder.definition(KBR[name], text, "Dokumentasi TBox")


def build_category_concepts(builder: Builder) -> None:
    for local, spec in defs.CATEGORY_CONCEPTS.items():
        uri = builder.individual(local)
        builder.graph.add((uri, RDF.type, SKOS.Concept))
        builder.label(uri, spec["label"])
        builder.comment(uri, spec["definition"])
        builder.definition(uri, spec["definition"], "Kurasi pakar")
        builder.alt(uri, spec["label"].lower())


def apply_phase_class_definitions(builder: Builder) -> None:
    for name in (
        "FasePembibitan",
        "FaseVegetatif",
        "FaseGeneratif",
        "FaseAnakan",
        "FasePemasakan",
        "FasePanen",
    ):
        spec = defs.PHASE_DEFINITIONS[name]
        builder.definition(KBR[name], spec["definition"], "Kurasi pakar")
        builder.pref_label(KBR[name], spec.get("english"), "en")
        for synonym in spec.get("synonyms", []):
            builder.alt(KBR[name], synonym)


def ensure_phase_individual(builder: Builder, phase: str) -> URIRef:
    spec = PHASE_DEFS[phase]
    uri = builder.ensure_individual(phase, spec["class"])
    builder.label(uri, spec["label"])
    builder.comment(uri, "Fase pertumbuhan yang disebut pada sumber.")
    definition = defs.PHASE_DEFINITIONS.get(phase) or defs.PHASE_DEFINITIONS.get(spec["class"])
    if definition:
        builder.definition(uri, definition.get("definition"), "Kurasi pakar")
        builder.pref_label(uri, definition.get("english"), "en")
        for synonym in definition.get("synonyms", []):
            builder.alt(uri, synonym)
    rank = defs.PHASE_STAGE_ORDER.get(spec["class"])
    if rank is not None:
        builder.integer(uri, "urutanFase", rank)
    return uri


def plant_rows_merged() -> list[dict[str, str]]:
    merged: dict[str, dict[str, str]] = {}
    for rows in (read_csv(AUTO_DIR / "plants.csv"), read_csv(CURATED5 / "plants.csv")):
        for row in rows:
            pid = row["plant_id"].strip()
            if pid not in PLANT_LOCAL:
                continue
            local = PLANT_LOCAL[pid]
            if local not in merged:
                merged[local] = {
                    "local": local,
                    "label": (row.get("plant_name_id") or PLANT_LABELS[local]).strip(),
                    "scientific_name": (row.get("scientific_name") or "").strip(),
                    "plant_ids": [pid],
                }
            else:
                if not merged[local]["scientific_name"] and (row.get("scientific_name") or "").strip():
                    merged[local]["scientific_name"] = row["scientific_name"].strip()
                merged[local]["plant_ids"].append(pid)
    return [merged[k] for k in PLANT_ORDER if k in merged]


def penyakit_entries() -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []

    def add(row: dict[str, str], source: str) -> None:
        pid = row["plant_id"].strip()
        if pid not in PLANT_LOCAL:
            return
        nama = (row.get("disease_name_verbatim") or "").strip()
        if not nama:
            return
        plant_local = PLANT_LOCAL[pid]
        entries.append(
            {
                "disease_id": row["disease_id"].strip(),
                "plant_local": plant_local,
                "plant_id": pid,
                "nama": nama,
                "name_en": (row.get("disease_name_en_verbatim") or row.get("name_en_verbatim") or "").strip(),
                "base": pascal(nama + plant_local),
                "section": (row.get("section") or row.get("chapter_title") or "").strip(),
                "subsection": (row.get("subsection") or "").strip(),
                "page_start": (row.get("page_start") or "").strip(),
                "page_end": (row.get("page_end") or "").strip(),
                "chunk_id": (row.get("chunk_id") or "").strip(),
                "evidence_chunk_ids": (row.get("evidence_chunk_ids") or "").strip(),
                "source_block_id": (row.get("source_block_id") or "").strip(),
                "source_block_ids": (row.get("source_block_ids") or "").strip(),
                "reference_verbatim": (row.get("reference_verbatim") or "").strip(),
                "source": source,
            }
        )

    for row in read_csv(CURATED2 / "diseases.csv"):
        add(row, "DOC002")
    for row in read_csv(CURATED5 / "diseases.csv"):
        add(row, "DOC005")

    counts = Counter(entry["base"] for entry in entries)
    for entry in entries:
        if counts[entry["base"]] == 1:
            entry["local"] = entry["base"]
        else:
            entry["local"] = entry["base"] + disease_qualifier(entry)

    for entry in entries:
        canonical = DISEASE_LOCAL_ALIASES.get(entry["local"])
        if canonical:
            entry["legacy_local"] = entry["local"]
            entry["local"] = canonical
            entry["label"] = DISEASE_LABEL_ALIASES.get(
                entry["legacy_local"], entry["nama"]
            )
        else:
            entry["label"] = entry["nama"]
    return entries


def unique_diseases(entries: list[dict[str, str]]) -> list[dict[str, str]]:
    unique: dict[str, dict[str, str]] = {}
    for entry in entries:
        current = unique.get(entry["local"])
        if current is None or (
            current.get("legacy_local") and not entry.get("legacy_local")
        ):
            unique[entry["local"]] = entry
    return list(unique.values())


def symptom_records(entries: list[dict[str, str]]) -> tuple[list[dict], list[str]]:
    by_norm: dict[str, list[dict[str, str]]] = {}
    for entry in entries:
        by_norm.setdefault(norm(entry["nama"]), []).append(entry)
    ids = {e["disease_id"] for e in entries}
    records: list[dict] = []
    errors: list[str] = []
    seen: set[tuple[str, str, str]] = set()

    def add(record: dict) -> None:
        key = (record["disease_id"], record["text"], record.get("chunk_id", ""))
        if key not in seen:
            seen.add(key)
            record["kind"] = "gejala"
            records.append(record)

    for row in read_csv(CURATED2 / "symptoms.csv"):
        did = row["disease_id"].strip()
        text = (row.get("verbatim_text") or "").strip()
        if did in ids and text:
            add(
                {
                    "disease_id": did,
                    "text": text,
                    "source": "DOC002",
                    "source_id": (row.get("symptom_id") or "").strip(),
                    "chunk_id": (row.get("chunk_id") or "").strip(),
                    "page": (row.get("page_start") or "").strip(),
                    "char_start": (row.get("char_start") or "").strip(),
                    "char_end": (row.get("char_end") or "").strip(),
                }
            )
    for row in read_csv(CURATED5 / "symptoms.csv"):
        did = row["disease_id"].strip()
        text = (row.get("verbatim_text") or "").strip()
        if did in ids and text:
            add(
                {
                    "disease_id": did,
                    "text": text,
                    "source": "DOC005",
                    "source_id": (row.get("symptom_id") or "").strip(),
                    "chunk_id": (row.get("chunk_id") or "").strip(),
                    "page": (row.get("page_start") or "").strip(),
                    "char_start": (row.get("char_start") or "").strip(),
                    "char_end": (row.get("char_end") or "").strip(),
                }
            )
    for row in read_csv(CURATED2 / "ubi_kayu_tabel_5.csv"):
        nama = (row.get("disease_name") or "").strip()
        text = (row.get("symptom_text") or "").strip()
        if not nama or not text:
            continue
        candidates = by_norm.get(norm(nama), [])
        disease_id = ""
        if len(candidates) == 1:
            disease_id = candidates[0]["disease_id"]
        elif len(candidates) > 1:
            want = TABLE_PART.get(row["table_id"].strip(), "")
            hits = [c for c in candidates if want in norm(c["subsection"])]
            if len(hits) == 1:
                disease_id = hits[0]["disease_id"]
            else:
                errors.append(f"nama penyakit tabel ambigu: {nama!r}")
                continue
        else:
            errors.append(f"nama penyakit tabel tidak dikenal: {nama!r}")
            continue
        add(
            {
                "disease_id": disease_id,
                "text": text,
                "source": "DOC002",
                "source_id": f"{row.get('table_id', '').strip()}#{row.get('row_no', '').strip()}",
                "chunk_id": "",
                "source_block_id": (row.get("source_block_id") or "").strip(),
                "page": (row.get("page") or "").strip(),
            }
        )
    return records, errors


def pathogen_records(entries: list[dict[str, str]]) -> list[dict]:
    scope = {e["disease_id"] for e in entries}
    rows2 = {r["pathogen_id"].strip(): r for r in read_csv(CURATED2 / "pathogens.csv")}
    rows5 = {r["pathogen_id"].strip(): r for r in read_csv(CURATED5 / "pathogens.csv")}
    records: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for path, table, source in (
        (CURATED2 / "disease_pathogen.csv", rows2, "DOC002"),
        (CURATED5 / "disease_pathogen.csv", rows5, "DOC005"),
    ):
        for row in read_csv(path):
            did = row["disease_id"].strip()
            pid = row["pathogen_id"].strip()
            if did not in scope or (did, pid) in seen:
                continue
            seen.add((did, pid))
            records.append(
                {
                    "disease_id": did,
                    "pathogen_id": pid,
                    "row": table[pid],
                    "source": source,
                    "relation_note": (row.get("relation_note") or "").strip(),
                    "evidence_chunk_id": (row.get("evidence_chunk_id") or "").strip(),
                    "kind": "patogen",
                }
            )
    return records


def control_records(entries: list[dict[str, str]]) -> list[dict]:
    scope = {e["disease_id"] for e in entries}
    records: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for path, source in ((CURATED2 / "controls.csv", "DOC002"), (CURATED5 / "controls.csv", "DOC005")):
        for row in read_csv(path):
            did = row["disease_id"].strip()
            text = (row.get("verbatim_text") or "").strip()
            if did not in scope or row.get("scope", "").strip() != "disease" or not text:
                continue
            if (did, text) in seen:
                continue
            seen.add((did, text))
            records.append(
                {
                    "disease_id": did,
                    "text": text,
                    "source": source,
                    "source_id": (row.get("control_id") or "").strip(),
                    "chunk_id": (row.get("chunk_id") or "").strip(),
                    "page": (row.get("page_start") or "").strip(),
                    "char_start": (row.get("char_start") or "").strip(),
                    "char_end": (row.get("char_end") or "").strip(),
                    "category": (row.get("control_category") or "").strip(),
                    "kind": "pengendalian",
                }
            )
    return records


def chapter_control_records() -> list[dict]:
    records: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for row in read_csv(CURATED2 / "controls.csv"):
        pid = row["plant_id"].strip()
        text = (row.get("verbatim_text") or "").strip()
        if pid not in PLANT_LOCAL or row.get("scope", "").strip() != "chapter" or not text:
            continue
        plant_local = PLANT_LOCAL[pid]
        if (plant_local, text) in seen:
            continue
        seen.add((plant_local, text))
        records.append(
            {
                "plant_local": plant_local,
                "text": text,
                "source": "DOC002",
                "source_id": (row.get("control_id") or "").strip(),
                "chunk_id": (row.get("chunk_id") or "").strip(),
                "page": (row.get("page_start") or "").strip(),
                "char_start": (row.get("char_start") or "").strip(),
                "char_end": (row.get("char_end") or "").strip(),
                "category": (row.get("control_category") or "").strip(),
                "kind": "pengendalian",
            }
        )
    return records


def all_context_records(symptom_rows: list[dict], control_rows: list[dict]) -> list[dict]:
    return symptom_rows + control_rows


def make_evidence(
    builder: Builder,
    prefix: str,
    record: dict,
    evidence_class: str,
    reference_local: str,
    label: str,
    cache: dict[tuple, URIRef],
    report: dict,
) -> URIRef:
    key = (
        prefix,
        record.get("source"),
        record.get("source_id"),
        record.get("chunk_id"),
        record.get("text"),
        evidence_class,
    )
    if key in cache:
        return cache[key]
    local = unique_local(prefix, record.get("text", ""), builder)
    uri = builder.individual(local, evidence_class)
    builder.label(uri, label)
    builder.comment(uri, "Node bukti yang menyimpan kutipan dan lokasi sumber.")
    original = (record.get("text") or "").strip()
    normalized = normalize_quote(original)
    builder.lang(uri, "kutipanSumber", original)
    builder.lang(uri, "kutipanNormalisasi", normalized)
    builder.plain(uri, "dokumenSumber", record.get("source"))
    builder.plain(uri, "identifierSumber", record.get("source_id"))
    builder.plain(uri, "idChunkSumber", record.get("chunk_id") or record.get("evidence_chunk_id"))
    builder.plain(uri, "idBlokSumber", record.get("source_block_id"))
    builder.plain(uri, "halamanSumber", record.get("page"))
    if not is_complete_sentence(original):
        builder.lang(uri, "catatanKualitas", "Kutipan sumber berupa fragmen atau kalimat terpotong.")
        report["data_quality"]["fragment_quotes"] += 1
    builder.ext_link(uri, PROV.wasDerivedFrom, KBR[reference_local])
    cache[key] = uri
    return uri


def build_referensi(builder: Builder) -> None:
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    for doc_id in ("DOC002", "DOC005"):
        info = meta["documents"][doc_id]
        local = f"Buku{doc_id}"
        uri = builder.individual(local, "Buku")
        builder.label(uri, info.get("title"))
        builder.comment(uri, "Referensi buku yang menjadi sumber data.")
        builder.lang(uri, "judulReferensi", info.get("title"))
        builder.integer(uri, "tahunTerbit", info.get("publication_year"))
        builder.plain(uri, "namaPenulis", ", ".join(info.get("authors") or []))
        builder.plain(uri, "identifierSumber", doc_id)

    doc006 = builder.individual("BukuDOC006", "Buku")
    builder.label(doc006, "Penyakit-Penyakit Tanaman Hortikultura di Indonesia")
    builder.comment(doc006, "Referensi glosarium istilah penyakit tanaman (DOC006).")
    builder.lang(doc006, "judulReferensi", "Penyakit-Penyakit Tanaman Hortikultura di Indonesia")
    builder.integer(doc006, "tahunTerbit", 1994)
    builder.plain(doc006, "namaPenulis", "Haryono Semangun")
    builder.plain(doc006, "identifierSumber", "DOC006")

    if not SOURCE_REGISTRY_CSV.exists():
        return
    for row in read_csv(SOURCE_REGISTRY_CSV):
        source_type = (row.get("source_type") or "").strip()
        if source_type == "journal_article":
            cls_name, prefix = "JurnalIlmiah", "Jurnal"
        elif source_type in {"extension_publication", "extension_factsheet", "extension_article"}:
            cls_name, prefix = "PublikasiInstansi", "Publikasi"
        else:
            continue
        source_id = (row.get("source_id") or "").strip()
        if not source_id:
            continue
        local = prefix + pascal(source_id)
        uri = builder.ensure_individual(local, cls_name)
        title = (row.get("title") or "").strip()
        if not title:
            continue
        builder.label(uri, title)
        builder.comment(uri, f"Referensi eksternal {cls_name.lower()} dari registry sumber.")
        builder.lang(uri, "judulReferensi", title)
        builder.integer(uri, "tahunTerbit", (row.get("year") or "").strip())
        builder.plain(uri, "namaPenulis", (row.get("authors") or "").strip())
        builder.plain(uri, "identifierSumber", source_id)
        url = (row.get("url") or "").strip()
        if url:
            builder.graph.add((uri, KBR["urlReferensi"], Literal(url, datatype=XSD.anyURI)))


def add_equivalences(builder: Builder) -> None:
    pairs = [
        ("PhakopsoraPachyrhizi", "PhakopsporaPachyrhizi"),
        ("XanthomonasCampestrisPvManihotis", "XanthomonasCampestrispvManihotis"),
        ("CercosporaHenningsii", "CercosporidiumHenningsii"),
    ]
    for left, right in pairs:
        if left in builder.used_locals and right in builder.used_locals:
            builder.graph.add((KBR[left], OWL.sameAs, KBR[right]))
            builder.graph.add((KBR[right], OWL.sameAs, KBR[left]))


def build_tanaman(builder: Builder) -> None:
    for row in plant_rows_merged():
        uri = builder.individual(row["local"], PLANT_CLASS[row["local"]])
        builder.label(uri, row["label"])
        builder.comment(uri, "Tanaman pangan dalam ruang lingkup knowledge base.")
        scientific = row["scientific_name"]
        if not scientific:
            fallback = PLANT_SCIENTIFIC_FALLBACK.get(row["local"])
            if fallback:
                scientific, source_url = fallback
                builder.graph.add((uri, RDFS.seeAlso, URIRef(source_url)))
                builder.comment(
                    uri,
                    "Nama ilmiah dilengkapi dari Plants of the World Online (Kew) "
                    "karena tidak tercantum pada sumber utama.",
                )
        builder.plain(uri, "namaIlmiah", scientific or None)
        builder.plain(uri, "identifierSumber", ";".join(row["plant_ids"]))
        spec = defs.PLANT_DEFINITIONS.get(row["local"], {})
        builder.definition(uri, spec.get("definition"), "Kurasi pakar")
        for synonym in spec.get("synonyms", []):
            builder.alt(uri, synonym)


def build_bagi_tanaman(builder: Builder) -> None:
    for part, label in PART_LABELS.items():
        uri = builder.individual(part, "BagianTanaman")
        builder.label(uri, label)
        builder.comment(uri, "Bagian tanaman yang dapat menjadi lokasi gejala.")
        spec = defs.PART_DEFINITIONS.get(part, {})
        builder.definition(uri, spec.get("definition"), "Kurasi pakar")
        builder.pref_label(uri, spec.get("english"), "en")
        for synonym in spec.get("synonyms", []):
            builder.alt(uri, synonym)

    for child, parent in defs.PART_PARENTS:
        builder.link(KBR[child], "bagianDari", KBR[parent])


def build_canonical_symptoms(builder: Builder) -> None:
    for local, spec in CANONICAL_SYMPTOMS.items():
        uri = builder.individual(local, "GejalaKanonik")
        builder.graph.add((uri, RDF.type, SKOS.Concept))
        builder.label(uri, spec["label"])
        builder.comment(uri, spec["comment"])
        builder.alt(uri, spec["label"].lower())
        builder.plain(uri, "kodeGejala", local)

        definition = defs.SYMPTOM_DEFINITIONS.get(local, {})
        builder.definition(uri, definition.get("definition"), definition.get("source"))
        builder.pref_label(uri, definition.get("english"), "en")
        for synonym in definition.get("synonyms", []):
            builder.alt(uri, synonym)

        category = defs.SYMPTOM_CATEGORIES.get(local)
        if category:
            category_uri = KBR[category]
            builder.graph.add((uri, SKOS.broader, category_uri))
            builder.graph.add((category_uri, SKOS.narrower, uri))


def build_canonical_controls(builder: Builder) -> None:
    for local, spec in CONTROL_ACTIONS.items():
        uri = builder.individual(local, spec["category"])
        builder.label(uri, spec["label"])
        builder.comment(uri, spec["comment"])
        builder.lang(uri, "namaPengendalian", spec["label"])
        builder.definition(uri, defs.CONTROL_DEFINITIONS.get(local, spec["comment"]), "Kurasi pakar")
        builder.alt(uri, spec["label"].lower())


def build_kondisi_katalog(builder: Builder) -> None:
    for local, cls, label, _pattern in QUALITATIVE_RULES:
        uri = builder.individual(local, cls)
        builder.label(uri, label)
        builder.comment(uri, "Kondisi lingkungan kualitatif terkait penyakit tanaman.")
        builder.definition(
            uri,
            defs.ENV_DEFINITIONS.get(local),
            "Kurasi pakar",
        )


def build_penyakit(builder: Builder, entries: list[dict[str, str]], report: dict) -> None:
    cache: dict[tuple, URIRef] = {}
    groups: dict[str, list[dict[str, str]]] = {}
    for entry in entries:
        groups.setdefault(entry["local"], []).append(entry)

    for local, group in groups.items():
        canonical = next(
            (entry for entry in group if not entry.get("legacy_local")),
            group[0],
        )
        uri = builder.individual(local, "Penyakit")
        builder.label(uri, canonical.get("label") or canonical["nama"])
        builder.comment(uri, "Data penyakit dari sumber; rincian bukti tersedia pada node BuktiSumber.")
        builder.alt(uri, canonical["name_en"] or None)
        builder.plain(uri, "namaInggrisPenyakit", canonical["name_en"] or None)
        english = canonical.get("name_en") or defs.DISEASE_ENGLISH_NAMES.get(local)
        if english:
            builder.pref_label(uri, english, "en")
            builder.alt(uri, english, "en")
        plant_names = sorted({PLANT_LABELS.get(e["plant_local"], e["plant_local"]) for e in group})
        disease_label = canonical.get("label") or canonical["nama"]
        disease_definition = defs.DISEASE_DEFINITIONS.get(local)
        if disease_definition:
            builder.definition(uri, disease_definition, "Kurasi pakar")
        else:
            builder.definition(
                uri,
                f"Penyakit {disease_label} yang menyerang tanaman {', '.join(plant_names)}.",
                "Turunan relasi ontology",
            )

        for entry in group:
            if entry is not canonical or entry.get("legacy_local") or entry["nama"] != canonical.get("label"):
                builder.alt(uri, entry["nama"])
            builder.plain(uri, "identifierSumber", entry["disease_id"])
            builder.link(uri, "menyerangTanaman", KBR[entry["plant_local"]])
            reference = "BukuDOC005" if entry["source"] == "DOC005" else "BukuDOC002"
            builder.link(uri, "memilikiReferensi", KBR[reference])
            record = {
                "text": entry["nama"] + (f". {entry['reference_verbatim']}" if entry["reference_verbatim"] else ""),
                "source": entry["source"],
                "source_id": entry["disease_id"],
                "chunk_id": entry["chunk_id"] or entry["evidence_chunk_ids"].split(";")[0] if entry["evidence_chunk_ids"] else entry["chunk_id"],
                "source_block_id": entry["source_block_id"] or entry["source_block_ids"].split(";")[0] if entry["source_block_ids"] else entry["source_block_id"],
                "page": entry["page_start"],
                "kind": "penyakit",
            }
            evidence = make_evidence(
                builder,
                "BuktiPenyakit" + local,
                record,
                "BuktiPenyakit",
                reference,
                evidence_label("penyakit", entry),
                cache,
                report,
            )
            builder.link(uri, "didukungOleh", evidence)


def build_patogen(builder: Builder, entries: list[dict[str, str]], records: list[dict], report: dict) -> None:
    entries_by_id = {e["disease_id"]: e for e in entries}
    groups: dict[str, list[dict]] = {}
    for record in records:
        row = record["row"]
        key = norm(row.get("scientific_name")) or "unknown"
        groups.setdefault(key, []).append(record)
    local_by_key: dict[str, str] = {}
    used_bases: dict[str, list[str]] = {}
    representative: dict[str, dict] = {}
    taxon_by_key: dict[str, str] = {}
    for key, group in groups.items():
        representative[key] = max(group, key=lambda r: TAXON_PRIORITY.get((r["row"].get("taxon_group") or "").strip().lower(), 0))
        taxon_by_key[key] = (representative[key]["row"].get("taxon_group") or "").strip().lower()
        base = pascal(representative[key]["row"].get("scientific_name") or "") or "PatogenTidakDiketahui"
        used_bases.setdefault(base, []).append(key)
    for key, group in groups.items():
        row = representative[key]["row"]
        base = pascal(row.get("scientific_name") or "") or "PatogenTidakDiketahui"
        local = base if len(used_bases[base]) == 1 else base + str(used_bases[base].index(key) + 1)
        if local in tbox.CLASSES:
            local = "Patogen" + local
        local_by_key[key] = local
        taxon = taxon_by_key[key]
        classes = ["Patogen"]
        if taxon in TAXON_CLASS:
            classes = [TAXON_CLASS[taxon]]
        uri = builder.individual(local, *classes)
        builder.label(uri, row.get("scientific_name") or row.get("verbatim_text") or "Patogen tidak diketahui")
        builder.comment(uri, "Patogen yang tercatat pada sumber.")
        builder.plain(uri, "namaIlmiahPatogen", row.get("scientific_name") or None)
        builder.plain(uri, "identifierSumber", row.get("pathogen_id") or None)
        if taxon not in TAXON_CLASS:
            report["data_quality"]["unknown_pathogens"] += 1
    cache: dict[tuple, URIRef] = {}
    pathogen_diseases: dict[str, set[str]] = {}
    pathogen_plants: dict[str, set[str]] = {}
    for record in records:
        entry = entries_by_id[record["disease_id"]]
        row = record["row"]
        key = norm(row.get("scientific_name")) or "unknown"
        disease_uri = KBR[entry["local"]]
        pathogen_uri = KBR[local_by_key[key]]
        disease_label = entry.get("label") or entry.get("nama") or entry["local"]
        plant_label = PLANT_LABELS.get(entry.get("plant_local", ""), entry.get("plant_local", ""))
        pathogen_diseases.setdefault(local_by_key[key], set()).add(disease_label)
        if plant_label:
            pathogen_plants.setdefault(local_by_key[key], set()).add(plant_label)
        builder.link(disease_uri, "disebabkanOleh", pathogen_uri)
        reference = "BukuDOC005" if record["source"] == "DOC005" else "BukuDOC002"
        text = record["relation_note"] or row.get("verbatim_text") or row.get("scientific_name") or ""
        evidence_record = {
            "text": text,
            "source": record["source"],
            "source_id": row.get("pathogen_id"),
            "chunk_id": record["evidence_chunk_id"] or row.get("chunk_id"),
            "page": row.get("page"),
            "kind": "patogen",
        }
        evidence = make_evidence(
            builder,
            "BuktiPatogen" + entry["local"],
            evidence_record,
            "BuktiPatogen",
            reference,
            evidence_label("patogen", entry),
            cache,
            report,
        )
        builder.link(disease_uri, "didukungOleh", evidence)
        builder.link(pathogen_uri, "didukungOleh", evidence)
        report["pathogen_links"].append(
            {"disease": entry["local"], "pathogen": local_by_key[key], "taxon": taxon_by_key[key]}
        )

    for key, local in local_by_key.items():
        row = representative[key]["row"]
        scientific = row.get("scientific_name") or local
        taxon = TAXON_CLASS.get(taxon_by_key.get(key, ""), "Patogen")
        diseases = sorted(pathogen_diseases.get(local, set()))
        plants = sorted(pathogen_plants.get(local, set()))
        if diseases and plants:
            definition = (
                f"{taxon} {scientific} yang menyebabkan penyakit "
                f"{', '.join(diseases)} pada tanaman {', '.join(plants)}."
            )
        elif diseases:
            definition = f"{taxon} {scientific} yang menyebabkan penyakit {', '.join(diseases)}."
        else:
            definition = f"{taxon} {scientific} yang tercatat pada sumber."
        builder.definition(KBR[local], definition, "Turunan relasi ontology")


def build_gejala(
    builder: Builder,
    entries: list[dict[str, str]],
    records: list[dict],
    report: dict,
) -> None:
    entries_by_id = {e["disease_id"]: e for e in entries}
    groups: dict[tuple[str, str], dict] = {}
    unmapped: list[dict] = []
    evidence_cache: dict[tuple, URIRef] = {}
    def record_canonicals(record: dict) -> list[str]:
        source_id = (record.get("source_id") or "").strip()
        found = match_canonical_symptoms(record["text"])
        if not found:
            found = list(defs.SYMPTOM_CANONICAL_OVERRIDES.get(source_id, []))
        return found

    disease_has_canonical: dict[str, bool] = {}
    for record in records:
        if record_canonicals(record):
            disease_has_canonical[record["disease_id"]] = True
    for record in records:
        entry = entries_by_id[record["disease_id"]]
        canonicals = record_canonicals(record)
        if canonicals:
            for canonical in canonicals:
                key = (entry["local"], canonical)
                group = groups.setdefault(key, {"records": [], "parts": set(), "entry": entry})
                if not entry.get("legacy_local"):
                    group["entry"] = entry
                group["records"].append(record)
                hint = disease_part_hint(entry)
                if hint:
                    group["parts"].update(hint)
                else:
                    canonical_part = CANONICAL_SYMPTOMS[canonical]["part"]
                    if canonical_part:
                        group["parts"].add(canonical_part)
                        if canonical in {"BusukAkar", "BusukBatang"}:
                            group["parts"].update(text_parts(record["text"]))
                    else:
                        group["parts"].update(text_parts(record["text"]))
        else:
            source_id = (record.get("source_id") or "").strip()
            if (source_id in defs.NON_SYMPTOM_OVERRIDES or is_non_symptom_text(record["text"])) and disease_has_canonical.get(record["disease_id"]):
                report["canonical_symptoms"]["skipped_non_symptom"] += 1
                continue
            unmapped.append(record)
    for (_disease_local, canonical), group in groups.items():
        entry = group["entry"]
        if not group["parts"] and knowledge.DEFAULT_PART:
            group["parts"].add(knowledge.DEFAULT_PART)
        local = unique_local("Gejala" + entry["local"] + canonical, "", builder)
        uri = builder.individual(local, *(_part_classes(group["parts"]) or ["Gejala"]))
        symptom_label = CANONICAL_SYMPTOMS[canonical]["label"]
        builder.label(uri, symptom_label)
        builder.link(uri, "memilikiGejalaKanonik", KBR[canonical])
        for part in sorted(group["parts"]):
            if part in PART_LABELS:
                builder.link(uri, "terdapatPada", KBR[part])
        description = ""
        for record in group["records"]:
            text = record["text"]
            if not description:
                description = safe_description(text)
            elif is_complete_sentence(text) and not is_complete_sentence(description):
                description = safe_description(text)
            reference = "BukuDOC005" if record["source"] == "DOC005" else "BukuDOC002"
            evidence = make_evidence(
                builder,
                "BuktiGejala" + entry["local"],
                record,
                "BuktiGejala",
                reference,
                evidence_label("gejala", entry),
                evidence_cache,
                report,
            )
            builder.link(uri, "didukungOleh", evidence)
        if description:
            builder.lang(uri, "deskripsiGejala", description)
            builder.comment(
                uri,
                f"Gejala {symptom_label.lower()} pada tanaman {plant_display(entry)}: {normalize_quote(description)}",
            )
        else:
            builder.comment(uri, f"Gejala {symptom_label.lower()} pada tanaman {plant_display(entry)}.")
        builder.link(KBR[entry["local"]], "memilikiGejala", uri)
        report["canonical_symptoms"]["used"][canonical] = report["canonical_symptoms"]["used"].get(canonical, 0) + 1

    for record in unmapped:
        entry = entries_by_id[record["disease_id"]]
        parts = text_parts(record["text"])
        if not parts and knowledge.DEFAULT_PART:
            parts = [knowledge.DEFAULT_PART]
        local = unique_local("Gejala" + entry["local"], "", builder)
        uri = builder.individual(local, *(_part_classes(parts) or ["Gejala"]))
        builder.label(uri, symptom_display(record["text"]))
        for part in parts:
            builder.link(uri, "terdapatPada", KBR[part])
        description = safe_description(record["text"])
        if description:
            builder.lang(uri, "deskripsiGejala", description)
            builder.comment(uri, f"Gejala pada tanaman {plant_display(entry)}: {normalize_quote(description)}")
        else:
            builder.comment(uri, f"Gejala pada tanaman {plant_display(entry)}.")
        reference = "BukuDOC005" if record["source"] == "DOC005" else "BukuDOC002"
        evidence = make_evidence(
            builder,
            "BuktiGejala" + entry["local"],
            record,
            "BuktiGejala",
            reference,
            evidence_label("gejala", entry),
            evidence_cache,
            report,
        )
        builder.link(uri, "didukungOleh", evidence)
        builder.link(KBR[entry["local"]], "memilikiGejala", uri)
        report["data_quality"]["unmapped_symptoms"] += 1
    report["canonical_symptoms"]["total"] = len(groups) + len(unmapped)
    report["canonical_symptoms"]["canonical_groups"] = len(groups)
    report["canonical_symptoms"]["unmapped"] = len(unmapped)


def _part_classes(parts: set[str] | list[str]) -> list[str]:
    return [PART_SUBCLASS[part] for part in parts if part in PART_SUBCLASS]


def build_menyerang_bagian(
    builder: Builder,
    entries: list[dict[str, str]],
    symptom_rows: list[dict],
    report: dict,
) -> None:
    entries_by_id = {e["disease_id"]: e for e in entries}
    symptom_parts_by_disease: dict[str, set[str]] = {}
    canonical_parts_by_disease: dict[str, set[str]] = {}
    for record in symptom_rows:
        entry = entries_by_id.get(record["disease_id"])
        if entry is None:
            continue
        text = record.get("text") or ""
        symptom_parts_by_disease.setdefault(entry["local"], set()).update(text_parts(text))
        hint = disease_part_hint(entry)
        if hint:
            canonical_parts_by_disease.setdefault(entry["local"], set()).update(hint)
            continue
        for canonical in match_canonical_symptoms(text):
            part = CANONICAL_SYMPTOMS[canonical]["part"]
            if part:
                canonical_parts_by_disease.setdefault(entry["local"], set()).add(part)
                if canonical in {"BusukAkar", "BusukBatang"}:
                    canonical_parts_by_disease.setdefault(entry["local"], set()).update(text_parts(text))
            else:
                canonical_parts_by_disease.setdefault(entry["local"], set()).update(text_parts(text))

    seen: set[str] = set()
    for entry in entries:
        if entry["local"] in seen:
            continue
        seen.add(entry["local"])
        parts = sorted(disease_part_hint(entry) or canonical_parts_by_disease.get(entry["local"], set()))
        if not parts:
            parts = subsection_parts(entry["subsection"])
        if not parts:
            raw = sorted(symptom_parts_by_disease.get(entry["local"], set()))
            if len(raw) == 1:
                parts = raw
        if not parts:
            report["data_quality"]["diseases_without_explicit_part"] += 1
            continue
        for part in sorted(set(parts)):
            builder.link(KBR[entry["local"]], "menyerangBagian", KBR[part])
            report["part_links"].append({"disease": entry["local"], "part": part})


def build_pengendalian(
    builder: Builder,
    entries: list[dict[str, str]],
    records: list[dict],
    chapter_records: list[dict],
    report: dict,
) -> None:
    entries_by_id = {e["disease_id"]: e for e in entries}
    cache: dict[tuple, URIRef] = {}
    action_description: dict[str, str] = {}
    for record in records:
        entry = entries_by_id[record["disease_id"]]
        actions = match_control_actions(record["text"], record["category"], record["source"])
        reference = "BukuDOC005" if record["source"] == "DOC005" else "BukuDOC002"
        evidence = make_evidence(
            builder,
            "BuktiPengendalian" + entry["local"],
            record,
            "BuktiPengendalian",
            reference,
            evidence_label("pengendalian", entry),
            cache,
            report,
        )
        builder.link(KBR[entry["local"]], "didukungOleh", evidence)
        if not actions:
            report["data_quality"]["unmapped_controls"] += 1
            continue
        for action in actions:
            builder.link(KBR[entry["local"]], "dikendalikanDengan", KBR[action])
            builder.link(KBR[action], "didukungOleh", evidence)
            if action not in action_description and is_complete_sentence(record["text"]):
                action_description[action] = normalize_quote(record["text"])
        report["controls"]["disease"].append(
            {"disease": entry["local"], "actions": actions, "category": record["category"], "source": record["source"]}
        )
    for record in chapter_records:
        plant_local = record["plant_local"]
        actions = match_control_actions(record["text"], record["category"], record["source"])
        evidence = make_evidence(
            builder,
            "BuktiPengendalianUmum" + plant_local,
            record,
            "BuktiPengendalian",
            "BukuDOC002",
            f"Bukti pengendalian umum {PLANT_LABELS[plant_local]}",
            cache,
            report,
        )
        builder.link(KBR[plant_local], "didukungOleh", evidence)
        if not actions:
            report["data_quality"]["unmapped_controls"] += 1
            continue
        for action in actions:
            builder.link(KBR[plant_local], "pengendalianUmum", KBR[action])
            builder.link(KBR[action], "didukungOleh", evidence)
            if action not in action_description and is_complete_sentence(record["text"]):
                action_description[action] = normalize_quote(record["text"])
        report["controls"]["chapter"].append(
            {"plant": plant_local, "actions": actions, "source": record["source"]}
        )
    for action, description in action_description.items():
        builder.lang(KBR[action], "deskripsiPengendalian", description)


def build_varietas(
    builder: Builder,
    entries: list[dict[str, str]],
    records: list[dict],
    report: dict,
) -> None:
    entries_by_id = {e["disease_id"]: e for e in entries}
    disease_labels = {e["local"]: (e.get("label") or e.get("nama") or e["local"]) for e in entries}
    name_local: dict[str, str] = {}
    cache: dict[tuple, URIRef] = {}
    seen_links: set[tuple[str, str, str]] = set()
    variety_plants: dict[str, str] = {}
    variety_resistant: dict[str, set[str]] = {}
    variety_susceptible: dict[str, set[str]] = {}
    for record in records:
        entry = entries_by_id[record["disease_id"]]
        names = extract_varieties(record["text"])
        if not names:
            continue
        reference = "BukuDOC005" if record["source"] == "DOC005" else "BukuDOC002"
        evidence = make_evidence(
            builder,
            "BuktiVarietas" + entry["plant_local"],
            record,
            "BuktiSumber",
            reference,
            evidence_label("varietas", entry),
            cache,
            report,
        )
        resist = bool(RESIST_MARKERS.search(record["text"]))
        vuln = bool(VULN_MARKERS.search(record["text"]))
        for name in names:
            if name not in name_local:
                name_local[name] = unique_local("Varietas" + pascal(name), "", builder)
            local = name_local[name]
            classes = ["Varietas"]
            if "varietas unggul" in record["text"].lower():
                classes.append("VarietasUnggul")
            uri = builder.ensure_individual(local, *classes)
            builder.label(uri, name)
            builder.comment(uri, "Varietas tanaman yang disebut sumber.")
            builder.link(KBR[entry["plant_local"]], "memilikiVarietas", uri)
            builder.link(uri, "didukungOleh", evidence)
            plant_label = PLANT_LABELS.get(entry["plant_local"], entry["plant_local"])
            variety_plants[local] = plant_label
            if resist and not vuln:
                builder.link(uri, "tahanTerhadap", KBR[entry["local"]])
                variety_resistant.setdefault(local, set()).add(disease_labels.get(entry["local"], entry["local"]))
                report["varieties"]["resistant_links"].append({"variety": local, "disease": entry["local"]})
            elif vuln and not resist:
                builder.link(uri, "rentanTerhadap", KBR[entry["local"]])
                variety_susceptible.setdefault(local, set()).add(disease_labels.get(entry["local"], entry["local"]))
                report["varieties"]["susceptible_links"].append({"variety": local, "disease": entry["local"]})
            key = (local, entry["disease_id"], record.get("source_id", ""))
            if key not in seen_links:
                seen_links.add(key)
                report["varieties"]["items"].append(
                    {"local": local, "name": name, "plant": entry["plant_local"], "disease": entry["local"]}
                )

    local_name = {local: name for name, local in name_local.items()}
    for local, plant_label in variety_plants.items():
        name = local_name.get(local, local)
        text = f"Varietas {name} dari tanaman {plant_label}"
        resistant = sorted(variety_resistant.get(local, set()))
        susceptible = sorted(variety_susceptible.get(local, set()))
        if resistant:
            text += f"; diketahui tahan terhadap penyakit {', '.join(resistant)}"
        if susceptible:
            text += f"; diketahui rentan terhadap penyakit {', '.join(susceptible)}"
        builder.definition(KBR[local], text + ".", "Turunan relasi ontology")


def build_fase(
    builder: Builder,
    entries: list[dict[str, str]],
    records: list[dict],
    report: dict,
) -> None:
    entries_by_id = {e["disease_id"]: e for e in entries}
    cache: dict[tuple, URIRef] = {}

    for record in records:
        entry = entries_by_id[record["disease_id"]]
        phases = extract_phases(record["text"])
        if not phases:
            continue
        reference = "BukuDOC005" if record["source"] == "DOC005" else "BukuDOC002"
        evidence = make_evidence(
            builder,
            "BuktiFase" + entry["local"],
            record,
            "BuktiSumber",
            reference,
            evidence_label("fase", entry),
            cache,
            report,
        )
        for phase in phases:
            uri = ensure_phase_individual(builder, phase)
            builder.link(KBR[entry["local"]], "menyerangFase", uri)
            builder.link(uri, "didukungOleh", evidence)
            report["phases"]["links"].append({"disease": entry["local"], "phase": phase})

    for phase in (
        "FasePembibitanTanaman",
        "FaseVegetatifUmum",
        "FaseGeneratifUmum",
        "FaseMatangSusu",
        "FasePanenTanaman",
    ):
        ensure_phase_individual(builder, phase)
    for left, right in defs.PHASE_CHAIN:
        builder.link(KBR[left], "diikutiOleh", KBR[right])


def build_metadata(builder: Builder, entries: list[dict[str, str]], report: dict) -> None:
    by_local: dict[str, dict[str, str]] = {}
    for entry in entries:
        current = by_local.get(entry["local"])
        if current is None or (current.get("legacy_local") and not entry.get("legacy_local")):
            by_local[entry["local"]] = entry

    cache: dict[tuple, URIRef] = {}
    metadata_varieties: dict[str, str] = {}
    metadata_variety_plants: dict[str, str] = {}
    metadata_variety_resistant: dict[str, set[str]] = {}
    metadata_variety_susceptible: dict[str, set[str]] = {}
    for row in read_csv(METADATA_CSV):
        disease = (row.get("disease") or "").strip()
        gap = (row.get("gap") or "").strip().lower()
        value = (row.get("value") or "").strip()
        relation = (row.get("relation") or "").strip().lower()
        source = (row.get("source") or "").strip()
        source_id = (row.get("source_id") or "").strip()
        page = (row.get("page") or "").strip()
        quote = (row.get("quote") or "").strip()
        status = (row.get("review_status") or "").strip()

        if disease not in by_local:
            builder.errors.append(f"metadata penyakit tidak dikenal: {disease!r}")
            continue
        if gap not in {"severity", "phase", "variety", "english"}:
            builder.errors.append(f"metadata gap tidak dikenal: {gap!r} pada {disease}")
            continue
        if not value or not source_id or not quote:
            builder.errors.append(f"metadata {gap} {disease} tanpa value/source_id/quote")
            continue
        if source not in {"DOC002", "DOC005"}:
            builder.errors.append(f"metadata {gap} {disease} punya dokumen tidak dikenal: {source!r}")
            continue
        if status not in {"verified", "needs_review"}:
            builder.errors.append(f"metadata {gap} {disease} punya status tidak dikenal: {status!r}")
            continue

        entry = by_local[disease]
        record = {
            "text": quote,
            "source": source,
            "source_id": source_id,
            "page": page,
            "kind": "metadata",
        }
        reference = "BukuDOC005" if source == "DOC005" else "BukuDOC002"
        evidence = make_evidence(
            builder,
            "BuktiMetadata" + pascal(gap) + disease,
            record,
            "BuktiSumber",
            reference,
            evidence_label("metadata " + gap, entry),
            cache,
            report,
        )

        if re.search(r"fase\s+(?:[a-z]+\s+){0,3}hingga\s+panen|\bfase\s+panen\b", quote, re.I):
            phase_local = "FasePanenTanaman"
            phase_uri = ensure_phase_individual(builder, phase_local)
            builder.link(KBR[disease], "menyerangFase", phase_uri)
            builder.link(phase_uri, "didukungOleh", evidence)
            if not any(
                item["disease"] == disease and item["phase"] == phase_local
                for item in report["phases"]["links"]
            ):
                report["phases"]["links"].append({"disease": disease, "phase": phase_local})

        if gap == "severity":
            builder.lang(KBR[disease], "tingkatKeparahan", value)
            builder.link(KBR[disease], "didukungOleh", evidence)
        elif gap == "english":
            builder.plain(KBR[disease], "namaInggrisPenyakit", value)
            builder.link(KBR[disease], "didukungOleh", evidence)
        elif gap == "phase":
            if value not in PHASE_DEFS:
                builder.errors.append(f"metadata fase tidak dikenal: {value!r} pada {disease}")
                continue
            uri = ensure_phase_individual(builder, value)
            builder.link(KBR[disease], "menyerangFase", uri)
            builder.link(uri, "didukungOleh", evidence)
            builder.link(KBR[disease], "didukungOleh", evidence)
            if not any(
                item["disease"] == disease and item["phase"] == value
                for item in report["phases"]["links"]
            ):
                report["phases"]["links"].append({"disease": disease, "phase": value})
        else:
            if relation not in {"tahan", "rentan"}:
                builder.errors.append(
                    f"metadata varietas tanpa relasi tahan/rentan: {disease} {value!r}"
                )
                continue
            local = "Varietas" + pascal(value)
            uri = builder.ensure_individual(local, "Varietas")
            builder.label(uri, value)
            builder.comment(uri, "Varietas tanaman yang disebut pada sumber.")
            builder.link(KBR[entry["plant_local"]], "memilikiVarietas", uri)
            builder.link(uri, f"{relation}Terhadap", KBR[disease])
            builder.link(uri, "didukungOleh", evidence)
            metadata_varieties[local] = value
            metadata_variety_plants[local] = PLANT_LABELS.get(entry["plant_local"], entry["plant_local"])
            disease_label = entry.get("label") or entry.get("nama") or disease
            if relation == "tahan":
                metadata_variety_resistant.setdefault(local, set()).add(disease_label)
            else:
                metadata_variety_susceptible.setdefault(local, set()).add(disease_label)
            key = {"local": local, "name": value, "plant": entry["plant_local"], "disease": disease}
            if not any(
                item.get("local") == local and item.get("disease") == disease
                for item in report["varieties"]["items"]
            ):
                report["varieties"]["items"].append(key)
            link_key = "resistant_links" if relation == "tahan" else "susceptible_links"
            report["varieties"][link_key].append({"variety": local, "disease": disease})

        report["metadata"].append(
            {
                "disease": disease,
                "gap": gap,
                "value": value,
                "evidence": str(evidence).split("#")[-1],
            }
        )

    for local, name in metadata_varieties.items():
        plant_label = metadata_variety_plants.get(local, "")
        text = f"Varietas {name}"
        if plant_label:
            text += f" dari tanaman {plant_label}"
        resistant = sorted(metadata_variety_resistant.get(local, set()))
        susceptible = sorted(metadata_variety_susceptible.get(local, set()))
        if resistant:
            text += f"; diketahui tahan terhadap penyakit {', '.join(resistant)}"
        if susceptible:
            text += f"; diketahui rentan terhadap penyakit {', '.join(susceptible)}"
        builder.definition(KBR[local], text + ".", "Turunan relasi ontology")


def build_lingkungan(
    builder: Builder,
    entries: list[dict[str, str]],
    records: list[dict],
    report: dict,
) -> None:
    entries_by_id = {e["disease_id"]: e for e in entries}
    cache: dict[tuple, URIRef] = {}
    observation_cache: dict[tuple, URIRef] = {}
    condition_cache: dict[str, URIRef] = {}
    for record in records:
        entry = entries_by_id[record["disease_id"]]
        reference = "BukuDOC005" if record["source"] == "DOC005" else "BukuDOC002"
        observations = parse_env_observations(record["text"])
        qualities = qualitative_matches(record["text"])
        if not observations and not qualities:
            continue
        evidence = make_evidence(
            builder,
            "BuktiLingkungan" + entry["local"],
            record,
            "BuktiSumber",
            reference,
            evidence_label("faktor lingkungan", entry),
            cache,
            report,
        )
        for obs in observations:
            key = (
                record["disease_id"],
                obs["factor"],
                obs["class"],
                obs["min"],
                obs["max"],
                obs["single"],
                obs["operator"],
                obs["unit"],
            )
            if key in observation_cache:
                uri = observation_cache[key]
            else:
                local = "Observasi" + entry["local"] + obs["factor"] + value_slug(obs)
                uri = builder.individual(local, "ObservasiLingkungan", obs["class"])
                builder.label(uri, f"{obs['factor']} {value_slug(obs)} pada {entry['nama']}")
                builder.comment(uri, "Observasi faktor lingkungan yang diekstrak dari sumber.")
                if obs.get("min") is not None:
                    builder.decimal(uri, "nilaiMin", obs["min"])
                if obs.get("max") is not None:
                    builder.decimal(uri, "nilaiMaks", obs["max"])
                if obs.get("single") is not None:
                    builder.decimal(uri, "nilaiTunggal", obs["single"])
                builder.plain(uri, "operatorNilai", obs["operator"])
                builder.plain(uri, "satuan", obs["unit"])
                if obs.get("condition"):
                    builder.lang(uri, "kondisi", obs["condition"])
                    builder.lang(uri, "klasifikasiTurunan", obs["condition"])
                disease_label = entry.get("label") or entry.get("nama") or entry["local"]
                builder.definition(
                    uri,
                    f"Observasi {obs['factor']} {value_slug(obs)} yang memengaruhi penyakit {disease_label}.",
                    "Turunan relasi ontology",
                )
                observation_cache[key] = uri
                report["environment"]["numeric"].append(
                    {
                        "disease": entry["local"],
                        "factor": obs["factor"],
                        "min": fmt_number(obs.get("min")),
                        "max": fmt_number(obs.get("max")),
                        "value": fmt_number(obs.get("single")),
                        "operator": obs["operator"],
                        "unit": obs["unit"],
                    }
                )
            builder.link(KBR[entry["local"]], "dipengaruhiOleh", uri)
            builder.link(uri, "didukungOleh", evidence)
            builder.link(KBR[entry["local"]], "didukungOleh", evidence)
        for local, cls, label in qualities:
            if local not in condition_cache:
                uri = builder.ensure_individual(local, cls)
                builder.label(uri, label)
                builder.comment(uri, "Kondisi lingkungan kualitatif yang dinyatakan sumber.")
                if not any(builder.graph.objects(uri, SKOS.definition)):
                    builder.definition(
                        uri,
                        defs.ENV_DEFINITIONS.get(
                            local,
                            f"Kondisi lingkungan {label.lower()} yang memengaruhi penyakit tanaman.",
                        ),
                        "Kurasi pakar",
                    )
                condition_cache[local] = uri
            uri = condition_cache[local]
            builder.link(KBR[entry["local"]], "dipengaruhiOleh", uri)
            builder.link(uri, "didukungOleh", evidence)
            builder.link(KBR[entry["local"]], "didukungOleh", evidence)
            report["environment"]["qualitative"].append({"disease": entry["local"], "condition": local})


def build() -> tuple[Graph, dict, list[str], Builder]:
    report: dict = {
        "summary": {},
        "controls": {"disease": [], "chapter": []},
        "canonical_symptoms": {
            "used": {},
            "total": 0,
            "canonical_groups": 0,
            "unmapped": 0,
            "skipped_non_symptom": 0,
        },
        "definitions": {"filled": 0, "missing": 0, "by_type": {}},
        "environment": {"numeric": [], "qualitative": []},
        "varieties": {"items": [], "resistant_links": [], "susceptible_links": []},
        "phases": {"links": []},
        "metadata": [],
        "pathogen_links": [],
        "part_links": [],
        "data_quality": {
            "fragment_quotes": 0,
            "unmapped_symptoms": 0,
            "unmapped_controls": 0,
            "unknown_pathogens": 0,
            "diseases_without_explicit_part": 0,
        },
    }
    builder = Builder()
    tbox.build_tbox(builder.graph)
    apply_class_property_definitions(builder)
    builder.graph.bind("ptp", KBR)
    builder.graph.bind("prov", PROV)
    builder.graph.bind("skos", SKOS)
    builder.graph.bind("dcterms", DCTERMS)

    entries = penyakit_entries()
    unique_disease_entries = unique_diseases(entries)
    symptom_rows, symptom_errors = symptom_records(entries)
    builder.errors.extend(symptom_errors)
    pathogen_rows = pathogen_records(entries)
    control_rows = control_records(entries)
    chapter_rows = chapter_control_records()

    build_referensi(builder)
    build_tanaman(builder)
    build_bagi_tanaman(builder)
    build_canonical_symptoms(builder)
    build_canonical_controls(builder)
    build_kondisi_katalog(builder)
    build_category_concepts(builder)
    apply_phase_class_definitions(builder)
    build_penyakit(builder, entries, report)
    build_patogen(builder, entries, pathogen_rows, report)
    add_equivalences(builder)
    build_gejala(builder, entries, symptom_rows, report)
    build_menyerang_bagian(
        builder, entries, all_context_records(symptom_rows, control_rows), report
    )
    build_pengendalian(builder, entries, control_rows, chapter_rows, report)
    build_varietas(builder, entries, all_context_records(symptom_rows, control_rows), report)
    build_fase(builder, entries, all_context_records(symptom_rows, control_rows), report)
    build_metadata(builder, entries, report)
    build_lingkungan(builder, entries, all_context_records(symptom_rows, control_rows), report)

    definition_types = [
        "GejalaKanonik",
        "FasePembibitan",
        "FaseVegetatif",
        "FaseGeneratif",
        "FaseAnakan",
        "FasePemasakan",
        "FasePanen",
        "BagianTanaman",
        "Serealia",
        "Legum",
        "UmbiUmbian",
        "Jamur",
        "Bakteri",
        "Virus",
        "Oomycete",
        "Fitoplasma",
        "Nematoda",
        "PengendalianKulturTeknis",
        "PengendalianMekanis",
        "PengendalianBiologis",
        "PengendalianKimiawi",
        "PengendalianFisik",
        "PengendalianTerpadu",
        "Varietas",
        "Penyakit",
        "ObservasiLingkungan",
        "FaktorRisiko",
        "Suhu",
        "KelembapanUdara",
        "KelembapanTanah",
        "CurahHujan",
        "Musim",
        "Iklim",
        "KondisiTanah",
        "TeksturTanah",
        "IntensitasCahaya",
        "KetinggianTempat",
        "KondisiDrainase",
    ]
    for type_name in definition_types:
        nodes = set(builder.graph.subjects(RDF.type, KBR[type_name]))
        filled = sum(1 for node in nodes if any(builder.graph.objects(node, SKOS.definition)))
        report["definitions"]["by_type"][type_name] = {
            "total": len(nodes),
            "filled": filled,
            "missing": len(nodes) - filled,
        }
        report["definitions"]["filled"] += filled
        report["definitions"]["missing"] += len(nodes) - filled

    report["summary"] = {
        "plants": len(plant_rows_merged()),
        "diseases": len(unique_disease_entries),
        "symptom_records": len(symptom_rows),
        "pathogen_links": len(pathogen_rows),
        "control_records_disease": len(control_rows),
        "control_records_chapter": len(chapter_rows),
        "metadata_rows": len(report["metadata"]),
        "named_individuals": sum(1 for _ in builder.graph.subjects(RDF.type, OWL.NamedIndividual)),
        "triples": len(builder.graph),
    }
    report["coverage"] = {
        plant: {
            "diseases": sum(1 for e in unique_disease_entries if e["plant_local"] == plant),
            "symptoms": sum(1 for r in symptom_rows if e_plant(entries, r["disease_id"]) == plant),
            "controls": sum(1 for r in control_rows if e_plant(entries, r["disease_id"]) == plant),
        }
        for plant in PLANT_ORDER
    }
    report["data_quality"]["diseases_without_pathogen"] = sorted(
        e["local"] for e in unique_disease_entries if not any(builder.graph.objects(KBR[e["local"]], KBR["disebabkanOleh"]))
    )
    report["data_quality"]["diseases_without_control"] = sorted(
        e["local"] for e in unique_disease_entries if not any(builder.graph.objects(KBR[e["local"]], KBR["dikendalikanDengan"]))
    )
    report["data_quality"]["diseases_without_environment"] = sorted(
        e["local"] for e in unique_disease_entries if not any(builder.graph.objects(KBR[e["local"]], KBR["dipengaruhiOleh"]))
    )
    report["data_quality"]["diseases_without_scientific_name"] = sorted(
        e["local"] for e in unique_disease_entries if not any(builder.graph.objects(KBR[e["local"]], KBR["memilikiGejala"]))
    )
    errors = validate(builder.graph, builder, entries)
    return builder.graph, report, errors, builder


def e_plant(entries: list[dict[str, str]], disease_id: str) -> str:
    for entry in entries:
        if entry["disease_id"] == disease_id:
            return entry["plant_local"]
    return ""


def type_closure(graph: Graph, node: URIRef, cls: URIRef) -> bool:
    if (node, RDF.type, cls) in graph:
        return True
    for direct in graph.objects(node, RDF.type):
        if not isinstance(direct, URIRef):
            continue
        stack = [direct]
        seen: set[URIRef] = set()
        while stack:
            current = stack.pop()
            if current == cls:
                return True
            if current in seen:
                continue
            seen.add(current)
            for parent in graph.objects(current, RDFS.subClassOf):
                if isinstance(parent, URIRef):
                    stack.append(parent)
    return False


def validate(graph: Graph, builder: Builder, entries: list[dict[str, str]]) -> list[str]:
    errors = list(builder.errors)
    try:
        reparsed = Graph()
        reparsed.parse(data=graph.serialize(format="turtle"), format="turtle")
    except Exception as exc:  # noqa: BLE001
        return errors + [f"parse ulang gagal: {exc}"]

    for node in graph.subjects(RDF.type, OWL.NamedIndividual):
        local = str(node).split("#")[-1]
        if not re.match(r"^[A-Z][A-Za-z0-9]*$", local):
            errors.append(f"local name tidak PascalCase/ASCII: {local}")
        if "_" in local or "-" in local or re.search(r"[0-9a-f]{16,}", local):
            errors.append(f"local name mengandung hash/underscore: {local}")
        if not any(graph.objects(node, RDFS.label)):
            errors.append(f"individu tanpa label: {local}")
        if not any(graph.objects(node, SKOS.prefLabel)):
            errors.append(f"individu tanpa prefLabel: {local}")
        if not any(t for t in graph.objects(node, RDF.type) if t != OWL.NamedIndividual):
            errors.append(f"individu tanpa tipe domain: {local}")
        if KBR[local] in set(graph.subjects(RDF.type, OWL.Class)):
            errors.append(f"local name dipakai kelas dan individu: {local}")

    for cls in graph.subjects(RDF.type, OWL.Class):
        if not isinstance(cls, URIRef) or not str(cls).startswith(tbox.PTP):
            continue
        local = str(cls).split("#")[-1]
        if not any(graph.objects(cls, RDFS.label)):
            errors.append(f"kelas tanpa label: {local}")
        if not any(graph.objects(cls, SKOS.prefLabel)):
            errors.append(f"kelas tanpa prefLabel: {local}")
        if not any(graph.objects(cls, RDFS.comment)):
            errors.append(f"kelas tanpa komentar: {local}")
        if local not in tbox.TOP_DOMAINS and not any(graph.objects(cls, RDFS.subClassOf)):
            errors.append(f"kelas tanpa parent: {local}")

    for name, spec in tbox.OBJECT_PROPERTIES.items():
        prop = KBR[name]
        if not any(graph.objects(prop, RDFS.label)) or not any(graph.objects(prop, SKOS.prefLabel)):
            errors.append(f"properti objek tanpa label: {name}")
        if not any(graph.objects(prop, RDFS.comment)):
            errors.append(f"properti objek tanpa komentar: {name}")
        domain = spec.get("domain")
        if domain and not any(graph.objects(prop, RDFS.domain)):
            errors.append(f"properti objek tanpa domain: {name}")
        range_name = spec.get("range")
        if range_name and not any(graph.objects(prop, RDFS.range)):
            errors.append(f"properti objek tanpa range: {name}")
        inverse = spec.get("inverse")
        if inverse and (prop, OWL.inverseOf, KBR[inverse]) not in graph:
            errors.append(f"inverseOf hilang: {name} -> {inverse}")
        for subject, obj in graph.subject_objects(prop):
            if domain and not type_closure(graph, subject, KBR[domain]):
                errors.append(f"subjek {subject} tidak bertipe {domain} untuk {name}")
            if range_name and not type_closure(graph, obj, KBR[range_name]):
                errors.append(f"objek {obj} tidak bertipe {range_name} untuk {name}")

    for name, spec in tbox.DATA_PROPERTIES.items():
        prop = KBR[name]
        if not any(graph.objects(prop, RDFS.label)) or not any(graph.objects(prop, SKOS.prefLabel)):
            errors.append(f"properti data tanpa label: {name}")
        if not any(graph.objects(prop, RDFS.comment)):
            errors.append(f"properti data tanpa komentar: {name}")
        domain = spec.get("domain")
        for subject, obj in graph.subject_objects(prop):
            if domain and not type_closure(graph, subject, KBR[domain]):
                errors.append(f"subjek data {subject} tidak bertipe {domain} untuk {name}")
            if not isinstance(obj, Literal):
                errors.append(f"nilai data bukan literal untuk {name}: {obj}")
            elif spec["range"] == RDF.PlainLiteral and obj.language != "id":
                errors.append(f"literal {name} tidak berbahasa id: {obj}")
            elif spec["range"] == XSD.integer and obj.datatype != XSD.integer:
                errors.append(f"literal {name} bukan integer: {obj}")
            elif spec["range"] == XSD.decimal and obj.datatype != XSD.decimal:
                errors.append(f"literal {name} bukan decimal: {obj}")
            elif spec["range"] == XSD.string and obj.language:
                errors.append(f"literal {name} seharusnya string tanpa bahasa: {obj}")

    for local in tbox.TOP_DOMAINS:
        if not any(graph.objects(KBR[local], OWL.disjointWith)):
            errors.append(f"disjointWith hilang untuk domain: {local}")

    all_disjoint_nodes = list(graph.subjects(RDF.type, OWL.AllDisjointClasses))
    if len(all_disjoint_nodes) < len(tbox.ALL_DISJOINT_GROUPS):
        errors.append("jumlah AllDisjointClasses kurang")
    for group in tbox.ALL_DISJOINT_GROUPS:
        found = False
        for node in all_disjoint_nodes:
            for members in graph.objects(node, OWL.members):
                values = {str(item) for item in graph.items(members)}
                if {str(KBR[name]) for name in group} <= values:
                    found = True
        if not found:
            errors.append(f"AllDisjointClasses hilang untuk {group[0]}")

    for name, _patogen in tbox.EQUIVALENT_CLASSES:
        if not any(graph.objects(KBR[name], OWL.equivalentClass)):
            errors.append(f"equivalentClass hilang: {name}")
    if not any(graph.objects(KBR["Penyakit"], RDFS.subClassOf)):
        errors.append("restriksi Penyakit hilang")
    if not list(graph.objects(None, OWL.propertyChainAxiom)):
        errors.append("propertyChainAxiom hilang")
    for sub_prop, super_prop in tbox.SUBPROPERTY_OF:
        if (KBR[sub_prop], RDFS.subPropertyOf, KBR[super_prop]) not in graph:
            errors.append(f"subPropertyOf hilang: {sub_prop} -> {super_prop}")

    explicit_disease_categories = set(tbox.CLASSES) - {"Penyakit", "PenyakitPenyebabTidakDiketahui"}
    for category in explicit_disease_categories:
        if not category.startswith("Penyakit"):
            continue
        if any(graph.subjects(RDF.type, KBR[category])):
            errors.append(f"kategori penyakit di-assert eksplisit: {category}")

    for entry in entries:
        uri = KBR[entry["local"]]
        for prop in ("menyerangTanaman", "memilikiGejala", "memilikiReferensi", "didukungOleh"):
            if not any(graph.objects(uri, KBR[prop])):
                errors.append(f"penyakit {entry['local']} tanpa {prop}")
    for book in ("BukuDOC002", "BukuDOC005"):
        years = list(graph.objects(KBR[book], KBR["tahunTerbit"]))
        if len(years) != 1:
            errors.append(f"{book} harus punya tepat 1 tahunTerbit, ditemukan {len(years)}")

    for ev in graph.subjects(RDF.type, KBR["BuktiSumber"]):
        if not any(graph.objects(ev, KBR["kutipanSumber"])):
            errors.append(f"bukti tanpa kutipan: {ev}")
        if not any(graph.objects(ev, KBR["dokumenSumber"])):
            errors.append(f"bukti tanpa dokumen: {ev}")
        if not any(graph.objects(ev, PROV.wasDerivedFrom)):
            errors.append(f"bukti tanpa prov:wasDerivedFrom: {ev}")

    for subject, obj in graph.subject_objects(KBR["nilaiMin"]):
        max_values = list(graph.objects(subject, KBR["nilaiMaks"]))
        if max_values and Decimal(str(obj)) > Decimal(str(max_values[0])):
            errors.append(f"nilaiMin > nilaiMaks pada {subject}")
    for subject, unit in graph.subject_objects(KBR["satuan"]):
        if str(unit) not in ("°C", "%", "mm"):
            errors.append(f"satuan tidak dikenal pada {subject}: {unit}")

    for prop in ("deskripsiGejala", "deskripsiPengendalian", "deskripsiPenyakit", "deskripsiTanaman"):
        for subject, obj in graph.subject_objects(KBR[prop]):
            value = normalize_quote(str(obj))
            if re.search(r"\b(et al\.|dkk\.)\s*$", value, re.I):
                errors.append(f"{prop} berakhir et al.: {subject}")
            if value and prop != "deskripsiGejala" and not is_complete_sentence(value):
                errors.append(f"{prop} bukan kalimat lengkap: {subject}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bangun ontologi Penyakit Tanaman Pangan Indonesia.")
    parser.add_argument("--out", type=Path, default=DEFAULT_TTL, help="path keluaran TTL")
    args = parser.parse_args(argv)

    graph, report, errors, _builder = build()
    if errors:
        print("VALIDASI GAGAL:", file=sys.stderr)
        for error in errors[:80]:
            print(f"  - {error}", file=sys.stderr)
        if len(errors) > 80:
            print(f"  ... {len(errors) - 80} error lain", file=sys.stderr)
        return 2

    args.out.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=str(args.out), format="turtle")
    owl_path = args.out.with_suffix(".owl")
    graph.serialize(destination=str(owl_path), format="xml")
    report["summary"]["triples"] = len(graph)
    report["summary"]["named_individuals"] = sum(1 for _ in graph.subjects(RDF.type, OWL.NamedIndividual))
    report["summary"]["classes"] = sum(
        1 for cls in graph.subjects(RDF.type, OWL.Class) if isinstance(cls, URIRef) and str(cls).startswith(tbox.PTP)
    )
    report["summary"]["object_properties"] = sum(
        1 for prop in graph.subjects(RDF.type, OWL.ObjectProperty) if isinstance(prop, URIRef) and str(prop).startswith(tbox.PTP)
    )
    report["summary"]["data_properties"] = sum(
        1 for prop in graph.subjects(RDF.type, OWL.DatatypeProperty) if isinstance(prop, URIRef) and str(prop).startswith(tbox.PTP)
    )
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"ontologi ditulis: {args.out} dan {owl_path}")
    print(f"laporan ekstraksi: {REPORT_PATH}")
    print(
        f"triple: {len(graph)} | individu: {report['summary']['named_individuals']} | "
        f"penyakit: {report['summary']['diseases']} | gejala: {report['canonical_symptoms']['canonical_groups']} kanonik + "
        f"{report['canonical_symptoms']['unmapped']} tak dipetakan | pengendalian: {len(report['controls']['disease']) + len(report['controls']['chapter'])} | "
        f"varietas: {len(report['varieties']['items'])} | fase: {len(report['phases']['links'])} | metadata: {len(report['metadata'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
