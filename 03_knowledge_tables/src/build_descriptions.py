"""Ekstraksi deskripsi verbatim (rdfs:comment) untuk kelas dan individu ontologi.

Baris deskripsi dihasilkan lima jalur, semuanya bersumber dari pengetahuan yang
ada (tidak ada teks karangan):

1. ``mirror fakta``    -- literal ``deskripsi*`` pada baris fakta enrichment
                          (``deskripsiPenyakit``/``deskripsiTanaman``) disalin.
2. ``mirror kanonik``  -- literal ``deskripsiGejala``/``deskripsiPengendalian``
                          dari ``ontology.ttl`` disalin; jejak sumber dicocokkan
                          ke ``auto/symptoms.csv`` dan ``auto/controls.csv``.
3. ``paragraf dokumen``-- subjek referensi memakai paragraf Pendahuluan/Kata
                          Pengantar dokumen sumber.
4. ``ekstraksi``       -- kalimat dipilih verbatim; urutan: frasa utuh ->
                          kata kunci -> kata terakhir frasa, tiap tahap memakai
                          korpus terfilter 7 tanaman lebih dulu lalu korpus
                          dokumen penuh DOC002/DOC005.
5. ``bukti tautan``    -- kondisi tanpa frasa di sumber memakai
                          ``evidence_quote`` fakta yang menunjuknya.

Subjek tanpa sumber dibiarkan kosong dan dicatat di
``reports/DOC002_description_gaps.md``.

Output: ``auto/DOC002_md/DOC002_descriptions.csv``.
"""

from __future__ import annotations

import csv
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS

TABLE_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = TABLE_DIR.parent
sys.path.insert(0, str(TABLE_DIR / "src"))

import build_enrichment_facts as ef  # noqa: E402

ONTO_DIR = PROJECT_ROOT / "04_ontology"
ONTOLOGY_TTL = ONTO_DIR / "ontology.ttl"
FACTS_CSV = ef.FACTS_CSV
SYMPTOMS_CSV = TABLE_DIR / "auto" / "symptoms.csv"
CONTROLS_CSV = TABLE_DIR / "auto" / "controls.csv"
SOURCE_DIR = PROJECT_ROOT / "00_sumber_data"
OUTPUT_DIR = TABLE_DIR / "auto" / "DOC002_md"
OUTPUT_CSV = OUTPUT_DIR / "DOC002_descriptions.csv"
REPORT_MD = TABLE_DIR / "reports" / "DOC002_description_gaps.md"

KBR = "http://kbr.kelompok5.org/penyakit-tanaman-pangan#"

COLUMNS = [
    "subject_local",
    "subject_class",
    "predicate",
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

MIRROR_FACT_PREDICATES = {"deskripsiPenyakit", "deskripsiTanaman"}
MIRROR_CANONICAL = {
    "deskripsiGejala": ("Gejala", SYMPTOMS_CSV),
    "deskripsiPengendalian": ("Pengendalian", CONTROLS_CSV),
}
MIRROR_CLASSES = {"Penyakit", "TanamanPangan", "Gejala", "Pengendalian"}

EXTRACT_CLASSES = (
    "Patogen",
    "Varietas",
    "BagianTanaman",
    "FasePertumbuhan",
    "Referensi",
    "FaktorLingkungan",
    "FaktorRisiko",
)

CLASS_PRIORITY = [
    "Penyakit",
    "TanamanPangan",
    "Varietas",
    "Gejala",
    "Pengendalian",
    "Patogen",
    "FaktorLingkungan",
    "FaktorRisiko",
    "BagianTanaman",
    "FasePertumbuhan",
    "Referensi",
    "Buku",
]

DOC_FILES = [
    ("DOC002", SOURCE_DIR / "02_PenyakitTanamanPangan.md", "DOC002_MD_PENUH"),
    ("DOC005", SOURCE_DIR / "05_PenyakitUtamaKedelai.md", "DOC005_MD_KEDELAI"),
    ("DOC005", SOURCE_DIR / "07_PenyakitKacangHijau.md", "DOC005_MD_KACANG_HIJAU"),
]

INTRO_HEADINGS = ("Pendahuluan", "Kata Pengantar", "Prakata")

MIN_AUTO_LEN = 60
MIN_PARAGRAPH = 100
MIN_ALNUM = 25
DEFINITION_RE = re.compile(r"\b(?:adalah|merupakan|yakni|yaitu|dikenal sebagai)\b")
HEADING_RE = re.compile(r"^#{1,6}\s")
CAPTION_RE = re.compile(r"^\*{0,2}Gambar\s+\d", re.I)
INTRO_RE = re.compile(
    r"^#{1,6}\s+(?:\d+(?:\.\d+)*)?\s*(?:%s)\s*$" % "|".join(INTRO_HEADINGS),
    re.M | re.I,
)


@dataclass
class Target:
    local: str
    classes: tuple[str, ...]
    label: str
    phrase: str


@dataclass
class Candidate:
    unit: "ef.Unit"
    sentence: str
    normalized: str


def local_name(node: object) -> str:
    value = str(node)
    return value.rsplit("#", 1)[-1] if "#" in value else value.rsplit("/", 1)[-1]


def norm(text: object) -> str:
    return ef.norm(text)


def load_units() -> list[ef.Unit]:
    """Korpus primer: badan teks terfilter 7 tanaman."""
    units: list[ef.Unit] = []
    units.extend(ef.load_md_units())
    units.extend(ef.load_doc002_baseline())
    units.extend(ef.load_doc005_chunks())
    units.extend(ef.load_doc005_md_units())
    return units


def load_document_units() -> list[ef.Unit]:
    """Korpus dokumen: teks penuh DOC002 + DOC005 (tanpa filter bab/tanaman)."""
    units: list[ef.Unit] = []
    for document, path, source_id in DOC_FILES:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n").strip()
        if not text:
            continue
        units.append(
            ef.Unit(
                document=document,
                source_type="md_document",
                source_id=source_id,
                page="",
                chapter="",
                section="",
                subsection="",
                plant="",
                disease="",
                content_type="document",
                text=text,
            )
        )
    return units


def is_useful(sentence: str) -> bool:
    value = sentence.strip()
    if len(re.sub(r"[^0-9A-Za-z]", "", value)) < MIN_ALNUM:
        return False
    if HEADING_RE.match(value) or "|" in value or "<!--" in value or CAPTION_RE.match(value):
        return False
    return True


def build_index(units: list[ef.Unit]) -> list[Candidate]:
    """Indeks kalimat: dokumen dipotong per paragraf agar tidak lintas blok."""
    index: list[Candidate] = []
    for unit in units:
        chunks = (
            re.split(r"\n\s*\n", unit.text)
            if unit.source_type == "md_document"
            else [unit.text]
        )
        for chunk in chunks:
            for sentence in ef.sentences(chunk):
                if not is_useful(sentence):
                    continue
                index.append(Candidate(unit, sentence.strip(), norm(sentence)))
    return index


def load_targets() -> tuple[dict[str, Target], list[tuple[str, str]]]:
    graph = Graph()
    graph.parse(str(ONTOLOGY_TTL), format="turtle")

    classes: list[tuple[str, str]] = []
    for cls in graph.subjects(RDF.type, OWL.Class):
        if not str(cls).startswith(KBR):
            continue
        label = next(iter(graph.objects(cls, RDFS.label)), None)
        classes.append((local_name(cls), str(label) if label else local_name(cls)))
    classes.sort(key=lambda item: item[0])

    member_classes: dict[str, list[str]] = defaultdict(list)
    for individual in graph.subjects(RDF.type, OWL.NamedIndividual):
        if not str(individual).startswith(KBR):
            continue
        for cls in graph.objects(individual, RDF.type):
            if str(cls).startswith(KBR) and (cls, RDF.type, OWL.Class) in graph:
                member_classes[local_name(individual)].append(local_name(cls))

    labels: dict[str, str] = {}
    for individual, label in graph.subject_objects(RDFS.label):
        if str(individual).startswith(KBR):
            labels[local_name(individual)] = str(label)

    scientific: dict[str, str] = {}
    prop = URIRef(KBR + "namaIlmiahPatogen")
    for individual, name in graph.subject_objects(prop):
        if str(individual).startswith(KBR):
            scientific[local_name(individual)] = str(name)

    targets: dict[str, Target] = {}
    for local, cls_names in member_classes.items():
        ordered = sorted(
            cls_names,
            key=lambda name: CLASS_PRIORITY.index(name)
            if name in CLASS_PRIORITY
            else len(CLASS_PRIORITY),
        )
        label = labels.get(local, "")
        targets[local] = Target(local, tuple(ordered), label, scientific.get(local) or label)

    for local, label in ef.CONDITION_LABELS.items():
        if local not in targets:
            targets[local] = Target(local, ("FaktorLingkungan",), label, label)

    return targets, classes


def annotate_lines(record: dict[str, str], unit: ef.Unit) -> None:
    if unit.source_type != "md_document":
        return
    position = unit.text.find(record["literal_value"])
    if position < 0:
        return
    record["line_start"] = str(unit.text[:position].count("\n") + 1)
    record["line_end"] = str(unit.text[: position + len(record["literal_value"])].count("\n") + 1)


def make_record(candidate: Candidate, **fields: str) -> dict[str, str]:
    unit = candidate.unit
    record = {
        "literal_value": candidate.sentence,
        "source_document": unit.document,
        "source_type": unit.source_type,
        "source_id": unit.source_id,
        "evidence_quote": candidate.sentence,
        "page": unit.page,
        "line_start": unit.line_start,
        "line_end": unit.line_end,
    }
    record.update(fields)
    annotate_lines(record, unit)
    return record


def is_definitional(candidate: Candidate, needle: str) -> bool:
    return bool(
        DEFINITION_RE.search(candidate.normalized)
        and re.search(
            rf"{re.escape(needle)}\s+(?:adalah|merupakan|yakni|yaitu|dikenal sebagai)",
            candidate.normalized,
        )
    )


def pick_mode(
    index: list[Candidate],
    needle: str,
    tokens: list[str],
    mode: str,
    last_token: str,
) -> dict[str, str] | None:
    fallback: dict[str, str] | None = None
    for candidate in index:
        normalized = candidate.normalized
        if mode == "exact":
            if needle not in normalized:
                continue
            definitional = is_definitional(candidate, needle)
            record = make_record(
                candidate,
                confidence="high" if definitional else "medium",
                review_status=(
                    "auto_ok"
                    if definitional or len(candidate.sentence) >= MIN_AUTO_LEN
                    else "needs_review"
                ),
                notes="definisi sumber" if definitional else "frasa kunci pada kalimat sumber",
            )
            if definitional:
                return record
            if fallback is None:
                fallback = record
        elif mode == "relaxed":
            if needle in normalized or not tokens:
                continue
            if all(token in normalized for token in tokens):
                return make_record(
                    candidate,
                    confidence="low",
                    review_status="needs_review",
                    notes="kata kunci, bukan frasa utuh",
                )
        elif mode == "tail":
            if not last_token or needle in normalized or last_token not in normalized:
                continue
            if any(token in normalized for token in tokens[:-1]):
                continue
            return make_record(
                candidate,
                confidence="low",
                review_status="needs_review",
                notes=f"kata terakhir frasa ({last_token})",
            )
    return fallback


def find_match(
    phrase: str,
    primary_index: list[Candidate],
    document_index: list[Candidate],
    allow_last_token: bool = False,
) -> dict[str, str] | None:
    needle = norm(phrase)
    if len(needle) < 3:
        return None
    tokens = [token for token in needle.split() if len(token) >= 3]
    last_token = tokens[-1] if allow_last_token and len(tokens) >= 2 else ""
    modes = ["exact", "relaxed"] + (["tail"] if last_token else [])
    for mode in modes:
        for tier, index in (("primary", primary_index), ("document", document_index)):
            record = pick_mode(index, needle, tokens, mode, last_token)
            if record is None:
                continue
            if tier == "document":
                record["confidence"] = "low"
                record["review_status"] = "needs_review"
                record["notes"] = "fallback korpus dokumen penuh (di luar filter 7 tanaman)"
            return record
    return None


def read_indexed(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def mirror_fact_rows(
    targets: dict[str, Target], facts: list[dict[str, str]]
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for fact in facts:
        if (fact.get("predicate") or "") not in MIRROR_FACT_PREDICATES:
            continue
        local = (fact.get("subject_local") or "").strip()
        literal = (fact.get("literal_value") or "").strip()
        if not local or not literal:
            continue
        target = targets.get(local)
        rows.append(
            {
                "subject_local": local,
                "subject_class": target.classes[0] if target else (fact.get("subject_class") or ""),
                "predicate": "rdfs:comment",
                "literal_value": literal,
                "literal_lang": (fact.get("literal_lang") or "").strip() or "id",
                "source_document": fact.get("source_document", ""),
                "source_type": fact.get("source_type", ""),
                "source_id": fact.get("source_id", ""),
                "evidence_quote": fact.get("evidence_quote", ""),
                "page": fact.get("page", ""),
                "line_start": fact.get("line_start", ""),
                "line_end": fact.get("line_end", ""),
                "confidence": fact.get("confidence", "high"),
                "review_status": fact.get("review_status", "auto_ok"),
                "notes": "disalin dari fakta enrichment",
            }
        )
    return rows


def mirror_canonical_rows(targets: dict[str, Target], covered: set[str]) -> list[dict[str, str]]:
    graph = Graph()
    graph.parse(str(ONTOLOGY_TTL), format="turtle")

    joins: dict[str, dict[str, dict[str, str]]] = {}
    for predicate, (_, table) in MIRROR_CANONICAL.items():
        index: dict[str, dict[str, str]] = {}
        for row in read_indexed(table):
            index.setdefault(norm(row.get("verbatim_text")), row)
        joins[predicate] = index

    rows: list[dict[str, str]] = []
    for predicate, (class_name, _) in MIRROR_CANONICAL.items():
        for individual, literal in graph.subject_objects(URIRef(KBR + predicate)):
            if not str(individual).startswith(KBR):
                continue
            local = local_name(individual)
            if local in covered:
                continue
            value = str(literal).strip()
            if not value:
                continue
            joined = joins[predicate].get(norm(value))
            if joined:
                chunk_id = (joined.get("chunk_id") or "").strip()
                row_id = joined.get("symptom_id") or joined.get("control_id") or ""
                document = chunk_id.split("_", 1)[0] if chunk_id else ""
                status, confidence = "auto_ok", "high"
                notes = f"disalin dari deskripsi kanonik; tabel {row_id}"
                source_id = chunk_id or row_id
                page = (joined.get("page_start") or "").strip()
                source_type = "table_row"
            else:
                document = source_type = source_id = page = ""
                status, confidence = "needs_review", "medium"
                notes = "disalin dari deskripsi kanonik; jejak baris sumber tidak ditemukan"
            target = targets.get(local)
            rows.append(
                {
                    "subject_local": local,
                    "subject_class": target.classes[0] if target else class_name,
                    "predicate": "rdfs:comment",
                    "literal_value": value,
                    "literal_lang": "id",
                    "source_document": document,
                    "source_type": source_type,
                    "source_id": source_id,
                    "evidence_quote": value,
                    "page": page,
                    "line_start": "",
                    "line_end": "",
                    "confidence": confidence,
                    "review_status": status,
                    "notes": notes,
                }
            )
    return rows


def condition_evidence(facts: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    index: dict[str, dict[str, str]] = {}
    for fact in facts:
        local = (fact.get("object_local") or "").strip()
        if not local.startswith("Kondisi") or not (fact.get("evidence_quote") or "").strip():
            continue
        index.setdefault(local, fact)
    return index


def table_row_match(phrase: str, units: list[ef.Unit]) -> dict[str, str] | None:
    """Sel deskripsi pada baris tabel bila frasa hanya muncul di tabel."""
    needle = norm(phrase)
    if len(needle) < 3:
        return None
    for unit in units:
        if unit.source_type != "md_document":
            continue
        for number, line in enumerate(unit.text.splitlines(), start=1):
            if line.count("|") < 2 or needle not in norm(line):
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            usable = [
                cell
                for cell in cells
                if norm(cell) != needle
                and len(re.sub(r"[^0-9A-Za-z]", "", cell)) >= MIN_ALNUM
            ]
            if not usable:
                continue
            value = max(usable, key=len)
            return {
                "literal_value": value,
                "source_document": unit.document,
                "source_type": "table_row",
                "source_id": unit.source_id,
                "evidence_quote": line.strip(),
                "page": unit.page,
                "line_start": str(number),
                "line_end": str(number),
                "confidence": "low",
                "review_status": "needs_review",
                "notes": "sel deskripsi pada baris tabel sumber",
            }
    return None


def document_intro(local: str, document_units: list[ef.Unit]) -> dict[str, str] | None:
    wanted = "DOC005_MD_KEDELAI" if local.startswith("BukuDOC005") else "DOC002_MD_PENUH"
    for unit in document_units:
        if unit.source_id != wanted:
            continue
        match = INTRO_RE.search(unit.text)
        if not match:
            continue
        for paragraph in re.split(r"\n\s*\n", unit.text[match.end():]):
            value = re.sub(r"[*_]+", "", paragraph).strip()
            if len(value) < MIN_PARAGRAPH or HEADING_RE.match(value) or value.startswith("|"):
                continue
            if "<!--" in value:
                continue
            record = {
                "literal_value": value,
                "source_document": unit.document,
                "source_type": unit.source_type,
                "source_id": unit.source_id,
                "evidence_quote": value,
                "page": unit.page,
                "line_start": "",
                "line_end": "",
                "confidence": "medium",
                "review_status": "auto_ok",
                "notes": "paragraf pembuka dokumen sumber",
            }
            position = unit.text.find(paragraph.strip())
            if position >= 0:
                record["line_start"] = str(unit.text[:position].count("\n") + 1)
                record["line_end"] = str(
                    unit.text[: position + len(paragraph.strip())].count("\n") + 1
                )
            return record
    return None


def extract_rows(
    targets: dict[str, Target],
    primary_index: list[Candidate],
    document_index: list[Candidate],
    document_units: list[ef.Unit],
    facts: list[dict[str, str]],
) -> list[dict[str, str]]:
    evidence = condition_evidence(facts)
    rows: list[dict[str, str]] = []
    for target in targets.values():
        primary = target.classes[0]
        if primary not in EXTRACT_CLASSES:
            continue
        match: dict[str, str] | None = None
        if primary == "Referensi":
            match = document_intro(target.local, document_units)
        if match is None:
            match = find_match(
                target.phrase,
                primary_index,
                document_index,
                allow_last_token=primary == "Patogen",
            )
        if match is None and target.local in evidence:
            fact = evidence[target.local]
            match = {
                "literal_value": fact.get("evidence_quote", ""),
                "source_document": fact.get("source_document", ""),
                "source_type": fact.get("source_type", ""),
                "source_id": fact.get("source_id", ""),
                "evidence_quote": fact.get("evidence_quote", ""),
                "page": fact.get("page", ""),
                "line_start": fact.get("line_start", ""),
                "line_end": fact.get("line_end", ""),
                "confidence": "medium",
                "review_status": "needs_review",
                "notes": "bukti tautan kondisi; frasa label tidak ada di sumber",
            }
        if match is None:
            match = table_row_match(target.phrase, document_units)
        if match is None:
            continue
        rows.append(
            {
                "subject_local": target.local,
                "subject_class": primary,
                "predicate": "rdfs:comment",
                "literal_lang": "id",
                **match,
            }
        )
    return rows


def class_rows(
    classes: list[tuple[str, str]],
    primary_index: list[Candidate],
    document_index: list[Candidate],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for local, label in classes:
        match = find_match(label, primary_index, document_index)
        if match is None:
            continue
        if "definisi sumber" not in match["notes"]:
            match["review_status"] = "needs_review"
            match["notes"] = "kalimat terkait istilah kelas, bukan definisi"
            match["confidence"] = "low"
        rows.append(
            {
                "subject_local": local,
                "subject_class": "owl:Class",
                "predicate": "rdfs:comment",
                "literal_lang": "id",
                **match,
            }
        )
    return rows


def write_csv(rows: list[dict[str, str]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in COLUMNS})


def write_report(
    rows: list[dict[str, str]],
    targets: dict[str, Target],
    classes: list[tuple[str, str]],
) -> dict[str, object]:
    covered = {row["subject_local"] for row in rows if (row.get("literal_value") or "").strip()}
    by_class = Counter(row["subject_class"] for row in rows)
    by_status = Counter(row.get("review_status", "") for row in rows)
    by_notes = Counter(
        (row.get("notes") or "").split(";")[0] for row in rows if row.get("notes")
    )

    individual_targets = {
        local: target
        for local, target in targets.items()
        if any(name in EXTRACT_CLASSES or name in MIRROR_CLASSES for name in target.classes)
    }
    missing_individuals = sorted(local for local in individual_targets if local not in covered)
    missing_classes = sorted(local for local, _ in classes if local not in covered)

    lines: list[str] = []
    lines.append("# Laporan celah deskripsi (rdfs:comment)")
    lines.append("")
    lines.append("Sumber baris: `DOC002_descriptions.csv`; seluruh literal verbatim dari sumber.")
    lines.append("")
    lines.append("| Kelompok subjek | Jumlah |")
    lines.append("|---|---:|")
    for name, count in sorted(by_class.items()):
        lines.append(f"| {name} | {count} |")
    lines.append(f"| **Total baris** | **{len(rows)}** |")
    lines.append("")
    lines.append("| Status verifikasi | Jumlah |")
    lines.append("|---|---:|")
    for name, count in sorted(by_status.items()):
        lines.append(f"| {name} | {count} |")
    lines.append("")
    lines.append("| Asal baris | Jumlah |")
    lines.append("|---|---:|")
    for name, count in sorted(by_notes.items(), key=lambda item: -item[1]):
        lines.append(f"| {name} | {count} |")
    lines.append("")
    lines.append(
        f"Individu sasaran: {len(individual_targets)}, "
        f"terisi: {len(individual_targets) - len(missing_individuals)}, "
        f"kosong: {len(missing_individuals)}."
    )
    lines.append(
        f"Kelas: {len(classes)}, terisi: {len(classes) - len(missing_classes)}, "
        f"kosong: {len(missing_classes)}."
    )
    lines.append("")
    if missing_individuals:
        lines.append("## Individu tanpa deskripsi")
        lines.append("")
        lines.append("| Subjek | Kelas | Frasa pencarian |")
        lines.append("|---|---|---|")
        for local in missing_individuals:
            target = individual_targets[local]
            lines.append(
                f"| {local} | {', '.join(target.classes)} | {target.phrase or target.label} |"
            )
        lines.append("")
    if missing_classes:
        lines.append("## Kelas tanpa deskripsi")
        lines.append("")
        lines.append("| Kelas | Label |")
        lines.append("|---|---|")
        label_by_local = dict(classes)
        for local in missing_classes:
            lines.append(f"| {local} | {label_by_local.get(local, '')} |")
        lines.append("")
    lines.append(
        "Subjek kosong tidak diisi teks karangan: istilahnya memang tidak muncul di "
        "DOC002/DOC005 maupun di korpus terfilter."
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "rows": len(rows),
        "individuals_targeted": len(individual_targets),
        "individuals_missing": len(missing_individuals),
        "classes_total": len(classes),
        "classes_missing": len(missing_classes),
        "by_class": dict(by_class),
        "by_status": dict(by_status),
    }


def build() -> tuple[list[dict[str, str]], dict[str, object]]:
    document_units = load_document_units()
    primary_index = build_index(load_units())
    document_index = build_index(document_units)
    targets, classes = load_targets()
    facts = read_indexed(FACTS_CSV)

    rows: list[dict[str, str]] = []
    fact_rows = mirror_fact_rows(targets, facts)
    rows.extend(fact_rows)
    covered = {row["subject_local"] for row in fact_rows}
    rows.extend(mirror_canonical_rows(targets, covered))
    rows.extend(extract_rows(targets, primary_index, document_index, document_units, facts))
    rows.extend(class_rows(classes, primary_index, document_index))

    stats = write_report(rows, targets, classes)
    return rows, stats


def main() -> int:
    rows, stats = build()
    write_csv(rows)
    print(f"deskripsi: {stats['rows']} baris -> {OUTPUT_CSV.name}")
    print(
        f"individu {stats['individuals_targeted'] - stats['individuals_missing']}"
        f"/{stats['individuals_targeted']}, kelas "
        f"{stats['classes_total'] - stats['classes_missing']}/{stats['classes_total']}"
    )
    print(f"laporan -> {REPORT_MD.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
