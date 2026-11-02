"""Generator ontologi OWL 2 "Penyakit Tanaman Pangan Indonesia".

Membaca knowledge tables hasil kurasi (``03_knowledge_tables``) untuk tujuh
tanaman pangan — padi, kedelai, jagung, ubi jalar, ubi kayu, kacang tanah,
kacang hijau — lalu membangun ABox di atas TBox ``tbox.py`` (minimal
SROIQ(D)). Setiap teks diambil verbatim dari sumber; informasi yang tidak
tersedia dikosongkan, bukan ditebak.

Ekstraksi deterministik (tercatat di ``extraction_report.json``):
- varietas dari pola ``varietas <NamaProper>`` (+ fallback ``adalah``);
- fase pertumbuhan dari whitelist regex ``fase …``;
- kondisi lingkungan dari keyword → individu kanonik singleton;
- klasifikasi pengendalian multi-label (DOC005 ``control_category``,
  DOC002 keyword) ke sub-kelas ``Pengendalian*``.

Pemakaian (dari root repo)::

    python 04_ontology/build_ontology.py

Keluaran: ``04_ontology/ontology.ttl``, ``ontology.owl``, dan
``extraction_report.json``; kode keluar ``2`` bila validasi gagal.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

from rdflib import Graph, Literal, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS, XSD

ONTO_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = ONTO_DIR.parent
TABLE_DIR = PROJECT_ROOT / "03_knowledge_tables"
CURATED2 = TABLE_DIR / "curated" / "DOC002"
CURATED5 = TABLE_DIR / "curated" / "DOC005"
AUTO_DIR = TABLE_DIR / "auto"
META_PATH = PROJECT_ROOT / "01_knowledge_sources" / "source_metadata" / "manual_metadata.json"
DEFAULT_TTL = ONTO_DIR / "ontology.ttl"
DEFAULT_OWL = ONTO_DIR / "ontology.owl"
REPORT_PATH = ONTO_DIR / "extraction_report.json"

sys.path.insert(0, str(ONTO_DIR))

import tbox  # noqa: E402
from tbox import KBR  # noqa: E402

# plant_id → local individu tanaman (digabung per nama tanaman lintas dokumen).
PLANT_LOCAL: dict[str, str] = {
    "PLANT_001": "Padi",
    "PLANT_002": "Kedelai",
    "PLANT_018": "Kedelai",
    "PLANT_006": "Jagung",
    "PLANT_004": "UbiJalar",
    "PLANT_005": "UbiKayu",
    "PLANT_003": "KacangTanah",
    "PLANT_019": "KacangTanah",
    "PLANT_020": "KacangHijau",
}
SCOPE_PLANTS = set(PLANT_LOCAL)

TAXON_CLASS = {
    "jamur": "Jamur",
    "bakteri": "Bakteri",
    "virus": "Virus",
    "fitoplasma": "OrganismeLain",
    "oomycete": "OrganismeLain",
    "nematoda": "OrganismeLain",
}
PART_WORDS = {
    "daun": "Daun",
    "batang": "Batang",
    "akar": "Akar",
    "umbi": "Umbi",
    "buah": "Buah",
    "biji": "Biji",
}
PART_SUBCLASS = {"Daun": "GejalaDaun", "Batang": "GejalaBatang", "Akar": "GejalaAkar", "Umbi": "GejalaUmbi"}
TABLE_PART = {"T5.1_DAUN": "daun", "T5.2_BATANG": "batang", "T5.3_AKAR": "akar"}

CATEGORY_MAP_DOC005: dict[str, list[str]] = {
    "varietas tahan": ["PengendalianKulturTeknis"],
    "benih sehat": ["PengendalianKulturTeknis"],
    "perlakuan benih": ["PengendalianKulturTeknis"],
    "sanitasi": ["PengendalianKulturTeknis"],
    "rotasi tanaman": ["PengendalianKulturTeknis"],
    "sanitasi dan rotasi": ["PengendalianKulturTeknis"],
    "kultur teknis": ["PengendalianKulturTeknis"],
    "fungisida nabati": ["PengendalianKimiawi"],
    "fungisida sintetik": ["PengendalianKimiawi"],
    "pestisida nabati": ["PengendalianKimiawi"],
    "agens hayati": ["PengendalianBiologis"],
}

CONTROL_KEYWORD_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("PengendalianKimiawi", (
        "fungisida", "bakterisida", "pestisida", "nabati", "sintetik", "sintetis",
        "benomyl", "mankozeb", "heksakonazol", "streptomisin", "antibiotik",
        "insektisida", "herbisida", "aplikasi kimia", "bahan aktif",
    )),
    ("PengendalianBiologis", (
        "agens hayati", "agens pengendali hayati", "pengendalian hayati",
        "trichoderma", "pseudomonas", "beauveria", "bacillus", "metarhizium",
        "entomopatogen", "mikroorganisme antagonis", "pengendalian nabati",
        "pestisida nabati", "ekstrak",
    )),
    ("PengendalianKulturTeknis", (
        "kultur teknis", "benih sehat", "rotasi", "sanitasi", "jarak tanam",
        "drainase", "varietas tahan", "varietas", "pemupukan", "penanaman serempak",
        "perbaikan cara", "teknik budidaya", "waktu panen", "pupuk",
    )),
    ("PengendalianMekanis", (
        "pencabutan", "perangkap", "pengumpulan", "pemangkasan", "pemusnahan",
        "penyulingan", "pengendalian mekanis",
    )),
    ("PengendalianTerpadu", ("terpadu", "integrated", "pengelolaan terpadu")),
]

PHASE_RE = re.compile(
    r"\bfase\s+(matang\s+susu|vegetatif|generatif|pembibitan|anakan|matang)\b",
    re.I,
)
PHASE_LOCAL = {
    "matang susu": "FaseMatangSusu",
    "vegetatif": "FaseVegetatif",
    "generatif": "FaseGeneratif",
    "pembibitan": "FasePembibitan",
    "anakan": "FaseAnakan",
    "matang": "FaseMatang",
}

ENV_PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    (
        "KondisiKelembapanTinggi",
        "KelembapanTinggi",
        re.compile(r"kelembapan\s+tinggi|kelembaban\s+tinggi", re.I),
    ),
    ("KondisiSuhu", "Suhu", re.compile(r"\bsuhu\b", re.I)),
    ("KondisiCurahHujan", "CurahHujan", re.compile(r"curah\s+hujan", re.I)),
    ("KondisiMusimHujan", "MusimHujan", re.compile(r"musim\s+hujan", re.I)),
    ("KondisiMusimKemarau", "MusimKemarau", re.compile(r"musim\s+kemarau", re.I)),
]

VARIETY_STOPWORDS = {
    "yang", "dan", "atau", "pada", "untuk", "dengan", "adalah", "dapat", "akan",
    "lebih", "dari", "ini", "itu", "dalam", "sebagai", "tanaman", "kedelai",
    "padi", "jagung", "ubi", "kacang", "hijau", "tanah", "kayu", "jalar",
    "unggul", "lokal", "hanya", "setiap", "beberapa", "lainnya", "lain",
    "baru", "tersebut", "terkait", "mampu", "memiliki", "terhadap", "penyakit",
    "tahan", "rentan", "peka", "genjah", "serta", "yaitu", "yakni", "antara",
    "hasil", "penelitian", "jenis", "secara", "umum", "disebut", "termasuk",
    "dikenal", "bernama", "misalnya", "contoh", "seperti", "menggunakan",
    "dipakai", "menanam", "penanaman", "agak", "sangat", "cukup", "paling",
    "karat", "daun", "bulai", "hawar", "layu", "bakteri", "virus", "jamur",
    "busuk", "kerdil", "mosaik", "embun", "bercak", "antraknosa",
    "superelongasi", "sapu", "setan", "titik", "tunas", "pangkal", "pelepah",
    "blas", "tungro", "kudis", "patogen", "ras", "galur", "isolat", "vektor",
    "hama", "inang", "balitkabi", "puslitbangtan", "menurut", "juga", "bisa",
    "harus", "perlu", "banyak", "murah", "mudah", "aman", "cepat", "baik",
    "tinggi", "rendah", "sedang", "normal", "optimum", "ideal", "varietas",
    "variety", "toleran", "resistan", "resisten", "ketahanan", "keparahan",
    "infeksi", "serangan", "kejadian", "gejala", "sumber", "cara", "salah",
    "satu", "dua", "tiga", "paling", "diketahui", "dilaporkan", "dianjurkan",
    "diperoleh", "ditemukan", "diberikan", "diberi", "dapat", "boleh",
    "misalnya", "antara", "lain", "sekitar", "sebelum", "sesudah", "saat",
    "ketika", "apabila", "bila", "jika", "karena", "sehingga", "namun",
    "tetapi", "sedangkan", "akan", "telah", "sudah", "masih", "belum",
    "dengan", "tanpa", "oleh", "ke", "di", "kepada", "bagi", "buat",
}

RESIST_MARKERS = re.compile(r"\b(tahan|resistan|resisten|toleran)\b", re.I)
VULN_MARKERS = re.compile(r"\b(rentan|peka)\b", re.I)
VARIETY_PRIMARY_RE = re.compile(r"\bvarietas\b", re.I)
VARIETY_FALLBACK_RE = re.compile(r"\badalah\s+([A-Z][A-Za-z0-9\-']*(?:\s+[A-Z0-9][A-Za-z0-9\-']*){0,5})", re.UNICODE)


def read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def norm(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def pascal(text: str) -> str:
    return "".join(w[:1].upper() + w[1:] for w in re.split(r"[^0-9A-Za-z]+", text or "") if w)


def short_hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:8]


def text_parts(text: str) -> list[str]:
    low = (text or "").lower()
    return [name for word, name in PART_WORDS.items() if re.search(r"\b" + word, low)]


def subsection_parts(subsection: str) -> list[str]:
    low = norm(subsection)
    if "akar" in low or "umbi" in low:
        return ["Akar", "Umbi"]
    if "batang" in low:
        return ["Batang"]
    if "daun" in low:
        return ["Daun"]
    return []


def plant_label(plant_local: str) -> str:
    labels = {
        "Padi": "Padi",
        "Kedelai": "Kedelai",
        "Jagung": "Jagung",
        "UbiJalar": "Ubi jalar",
        "UbiKayu": "Ubi kayu",
        "KacangTanah": "Kacang tanah",
        "KacangHijau": "Kacang hijau",
    }
    return labels[plant_local]


# ---------------------------------------------------------------- koleksi data

def plant_rows_merged() -> list[dict[str, str]]:
    """Baris tanaman unik per local (label + scientific_name non-kosong pertama)."""
    merged: dict[str, dict[str, str]] = {}
    sources = [
        read_csv(AUTO_DIR / "plants.csv"),
        read_csv(CURATED5 / "plants.csv"),
    ]
    for rows in sources:
        for row in rows:
            pid = row["plant_id"].strip()
            if pid not in PLANT_LOCAL:
                continue
            local = PLANT_LOCAL[pid]
            if local not in merged:
                merged[local] = {
                    "local": local,
                    "label": (row.get("plant_name_id") or plant_label(local)).strip(),
                    "scientific_name": (row.get("scientific_name") or "").strip(),
                    "plant_ids": [pid],
                }
            else:
                if not merged[local]["scientific_name"] and (row.get("scientific_name") or "").strip():
                    merged[local]["scientific_name"] = row["scientific_name"].strip()
                merged[local]["plant_ids"].append(pid)
    order = ["Padi", "Kedelai", "Jagung", "UbiJalar", "UbiKayu", "KacangTanah", "KacangHijau"]
    return [merged[k] for k in order if k in merged]


def penyakit_entries() -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    seen_local: dict[str, list[str]] = {}

    def add_row(row: dict[str, str], source: str) -> None:
        pid = row["plant_id"].strip()
        if pid not in PLANT_LOCAL:
            return
        plant_local = PLANT_LOCAL[pid]
        nama = (row.get("disease_name_verbatim") or "").strip()
        if not nama:
            return
        base = pascal(nama + plant_local)
        disease_id = row["disease_id"].strip()
        seen_local.setdefault(base, []).append(disease_id)
        entries.append(
            {
                "disease_id": disease_id,
                "plant_local": plant_local,
                "plant_id": pid,
                "nama": nama,
                "base": base,
                "subsection": (row.get("subsection") or "").strip(),
                "source": source,
            }
        )

    for row in read_csv(CURATED2 / "diseases.csv"):
        add_row(row, "DOC002")
    for row in read_csv(CURATED5 / "diseases.csv"):
        add_row(row, "DOC005")

    for entry in entries:
        base = entry["base"]
        if len(seen_local[base]) == 1:
            entry["local"] = base
        else:
            entry["local"] = base + pascal(entry["disease_id"])
    return entries


def gejala_rows(entries: list[dict[str, str]]) -> tuple[list[tuple[str, str, str]], list[str]]:
    """Kembalikan (disease_id, teks, sumber) dan daftar error pencocokan."""
    by_norm: dict[str, list[dict[str, str]]] = {}
    for entry in entries:
        by_norm.setdefault(norm(entry["nama"]), []).append(entry)
    ids = {e["disease_id"] for e in entries}
    pairs: list[tuple[str, str, str]] = []
    errors: list[str] = []

    for row in read_csv(CURATED2 / "symptoms.csv"):
        if row["disease_id"].strip() in ids:
            text = (row.get("verbatim_text") or "").strip()
            if text:
                pairs.append((row["disease_id"].strip(), text, "DOC002"))
    for row in read_csv(CURATED5 / "symptoms.csv"):
        if row["disease_id"].strip() in ids:
            text = (row.get("verbatim_text") or "").strip()
            if text:
                pairs.append((row["disease_id"].strip(), text, "DOC005"))
    for row in read_csv(CURATED2 / "ubi_kayu_tabel_5.csv"):
        nama = (row.get("disease_name") or "").strip()
        if not nama:
            continue
        text = (row.get("symptom_text") or "").strip()
        cands = by_norm.get(norm(nama), [])
        if len(cands) == 1:
            disease_id = cands[0]["disease_id"]
        elif len(cands) > 1:
            want = TABLE_PART.get(row["table_id"].strip(), "")
            hit = [c for c in cands if want in norm(c["subsection"])]
            if len(hit) == 1:
                disease_id = hit[0]["disease_id"]
            else:
                errors.append(f"nama penyakit tabel ambigu pada baris {row['table_id']}#{row['row_no']}: {nama!r}")
                continue
        else:
            errors.append(f"nama penyakit tabel tidak dikenal pada baris {row['table_id']}#{row['row_no']}: {nama!r}")
            continue
        if not text:
            errors.append(f"baris tabel {row['table_id']}#{row['row_no']} tanpa teks gejala")
            continue
        pairs.append((disease_id, text, "DOC002"))
    return pairs, errors


def patogen_pairs(entries: list[dict[str, str]]) -> list[tuple[str, dict[str, str]]]:
    scope_ids = {e["disease_id"] for e in entries}
    pairs: list[tuple[str, dict[str, str]]] = []
    seen: set[tuple[str, str]] = set()

    pathogens2 = {r["pathogen_id"].strip(): r for r in read_csv(CURATED2 / "pathogens.csv")}
    for row in read_csv(CURATED2 / "disease_pathogen.csv"):
        disease_id = row["disease_id"].strip()
        pathogen_id = row["pathogen_id"].strip()
        if disease_id in scope_ids and (disease_id, pathogen_id) not in seen:
            seen.add((disease_id, pathogen_id))
            pairs.append((disease_id, pathogens2[pathogen_id]))

    pathogens5 = {r["pathogen_id"].strip(): r for r in read_csv(CURATED5 / "pathogens.csv")}
    for row in read_csv(CURATED5 / "disease_pathogen.csv"):
        disease_id = row["disease_id"].strip()
        pathogen_id = row["pathogen_id"].strip()
        if disease_id in scope_ids and (disease_id, pathogen_id) not in seen:
            seen.add((disease_id, pathogen_id))
            pairs.append((disease_id, pathogens5[pathogen_id]))
    return pairs


def pathogen_key(row: dict[str, str]) -> str:
    return norm(row.get("scientific_name")) or row["pathogen_id"].strip().lower()


def _taxon_rank(taxon: str) -> int:
    t = (taxon or "").strip().lower()
    return 0 if t in ("", "unknown") else 1


def merge_pathogen_rows(
    pairs: list[tuple[str, dict[str, str]]],
) -> dict[str, dict[str, str]]:
    """Unik per scientific_name; taxon diketahui mengalahkan unknown; terakhir menang."""
    rows: dict[str, list[dict[str, str]]] = {}
    for _did, row in pairs:
        rows.setdefault(pathogen_key(row), []).append(row)
    merged: dict[str, dict[str, str]] = {}
    for key, group in rows.items():
        best = group[0]
        for row in group[1:]:
            if _taxon_rank(row.get("taxon_group")) >= _taxon_rank(best.get("taxon_group")):
                best = row
        merged[key] = best
    return merged


def control_pairs(entries: list[dict[str, str]]) -> list[tuple[str, str, str, str]]:
    """(disease_id, text, control_category, source) scope=disease."""
    scope_ids = {e["disease_id"] for e in entries}
    pairs: list[tuple[str, str, str, str]] = []
    seen: set[tuple[str, str]] = set()
    for path, source in ((CURATED2 / "controls.csv", "DOC002"), (CURATED5 / "controls.csv", "DOC005")):
        for row in read_csv(path):
            disease_id = row["disease_id"].strip()
            text = (row.get("verbatim_text") or "").strip()
            if disease_id in scope_ids and row["scope"].strip() == "disease" and text:
                if (disease_id, text) not in seen:
                    seen.add((disease_id, text))
                    cat = (row.get("control_category") or "").strip()
                    pairs.append((disease_id, text, cat, source))
    return pairs


def chapter_control_pairs() -> list[tuple[str, str, str]]:
    """(plant_local, text, source) scope=chapter dari DOC002 (in-scope)."""
    pairs: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in read_csv(CURATED2 / "controls.csv"):
        pid = row["plant_id"].strip()
        text = (row.get("verbatim_text") or "").strip()
        if pid in PLANT_LOCAL and row["scope"].strip() == "chapter" and text:
            plant_local = PLANT_LOCAL[pid]
            if (plant_local, text) not in seen:
                seen.add((plant_local, text))
                pairs.append((plant_local, text, "DOC002"))
    return pairs


def gejala_texts_by_disease(pairs: list[tuple[str, str, str]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for disease_id, text, _src in pairs:
        out.setdefault(disease_id, []).append(text)
    return out


def control_texts_by_disease(pairs: list[tuple[str, str, str, str]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for disease_id, text, _cat, _src in pairs:
        out.setdefault(disease_id, []).append(text)
    return out


def menyerang_bagian_pairs(
    entries: list[dict[str, str]], pairs: list[tuple[str, str, str]]
) -> list[tuple[str, str]]:
    by_disease = gejala_texts_by_disease(pairs)
    out: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for entry in entries:
        if entry["subsection"]:
            parts = subsection_parts(entry["subsection"])
        else:
            parts = []
            for text in by_disease.get(entry["disease_id"], []):
                for part in text_parts(text):
                    if part not in parts:
                        parts.append(part)
        for part in parts:
            key = (entry["disease_id"], part)
            if key not in seen:
                seen.add(key)
                out.append(key)
    return out


# ------------------------------------------------------------------- ekstraksi

def _strip_variety_tail(part: str) -> str:
    part = re.split(r"\s*\(", part)[0]
    part = re.sub(r"\s+\d+(?:\.\d+)?\s*%.*$", "", part)
    part = part.strip().strip(",;:()\"'")
    return part


def _valid_variety(name: str) -> bool:
    """Tolak huruf tunggal, akronim patogen (CMMV/PStV), dan token kosong."""
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
    plant_words = {"jagung", "kedelai", "padi", "kacang", "hijau", "tanah", "ubi", "kayu", "jalar"}
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
            if low in VARIETY_STOPWORDS and low not in {
                "padi", "kedelai", "jagung", "ubi", "kacang", "hijau", "tanah", "kayu", "jalar",
            }:
                continue
            started = True
            tokens.append(tok)
            continue
        if re.match(r"^\d+$", tok):
            tokens.append(tok)
        elif re.match(r"^[A-Z][A-Za-z0-9\-']*$", tok):
            if tok.lower() in VARIETY_STOPWORDS and len(tokens) > 0 and tok.lower() in {
                "yang", "dan", "atau", "adalah", "dengan", "untuk", "pada",
            }:
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

    for m in VARIETY_PRIMARY_RE.finditer(text):
        rest = text[m.end():]
        window = re.split(r"[.\n]", rest)[0][:200]
        parts = re.split(r",\s*|\s+dan\s+|\s+atau\s+|\s+sedangkan\s+", window)
        for part in parts:
            push(_proper_run(part))
    if not found:
        for m in VARIETY_FALLBACK_RE.finditer(text):
            push(_proper_run(m.group(1)))
    return found


def extract_phases(text: str) -> list[str]:
    locals_found: list[str] = []
    for m in PHASE_RE.finditer(text):
        key = re.sub(r"\s+", " ", m.group(1).lower())
        local = PHASE_LOCAL.get(key)
        if local and local not in locals_found:
            locals_found.append(local)
    return locals_found


def extract_env_locals(text: str) -> list[str]:
    hits: list[str] = []
    for local, _cls, pattern in ENV_PATTERNS:
        if local not in hits and pattern.search(text or ""):
            hits.append(local)
    return hits


def classify_control(text: str, category: str, source: str) -> list[str]:
    classes: list[str] = []
    if source == "DOC005" and category:
        mapped = CATEGORY_MAP_DOC005.get(category.strip().lower())
        if mapped:
            for cls in mapped:
                if cls not in classes:
                    classes.append(cls)
    low = (text or "").lower()
    for cls, keywords in CONTROL_KEYWORD_RULES:
        if cls in classes:
            continue
        if any(kw in low for kw in keywords):
            classes.append(cls)
    return classes


# ---------------------------------------------------------------- builder ABox

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
        inverse = tbox.OBJECT_PROPERTIES.get(prop, {}).get("inverse")
        if inverse:
            self.graph.add((target, KBR[inverse], uri))
        if prop in ("dikendalikanDengan", "pengendalianUmum"):
            self.graph.add((uri, KBR["berkaitanPengendalian"], target))


def gejala_uri(text: str, cache: dict[str, URIRef], builder: Builder) -> URIRef:
    if text in cache:
        return cache[text]
    words = [w for w in text.split() if w][:5]
    local = "Gejala" + (pascal(" ".join(words)) or "TanpaTeks") + "_" + short_hash(text)
    classes = ["Gejala"] + [PART_SUBCLASS[p] for p in text_parts(text) if p in PART_SUBCLASS]
    uri = builder.individual(local, *classes)
    builder.label(uri, text)
    builder.s(uri, "deskripsiGejala", text)
    for part in text_parts(text):
        builder.link(uri, "terdapatPada", KBR[part])
    cache[text] = uri
    return uri


def pengendalian_uri(text: str, cache: dict[str, URIRef], builder: Builder, subclasses: list[str]) -> URIRef:
    if text in cache:
        uri = cache[text]
        for cls in subclasses:
            builder.graph.add((uri, RDF.type, KBR[cls]))
        return uri
    words = [w for w in text.split() if w][:5]
    local = "Pengendalian" + (pascal(" ".join(words)) or "TanpaTeks") + "_" + short_hash(text)
    uri = builder.individual(local, "Pengendalian", *subclasses)
    builder.label(uri, text)
    builder.s(uri, "deskripsiPengendalian", text)
    cache[text] = uri
    return uri


def build_referensi(builder: Builder) -> None:
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    for doc_id in ("DOC002", "DOC005"):
        info = meta["documents"][doc_id]
        local = f"Buku{doc_id}"
        uri = builder.individual(local, "Referensi", "Buku")
        builder.label(uri, info.get("title"))
        builder.s(uri, "judulReferensi", info.get("title"))
        year = info.get("publication_year")
        if year is not None:
            builder.graph.add((uri, KBR.tahunTerbit, Literal(int(year), datatype=XSD.integer)))
        authors = ", ".join(info.get("authors") or [])
        builder.s(uri, "namaPenulis", authors or None)


def build_tanaman(builder: Builder) -> None:
    for row in plant_rows_merged():
        uri = builder.individual(row["local"], "TanamanPangan")
        builder.label(uri, row["label"])
        builder.s(uri, "namaIlmiah", row["scientific_name"] or None)


def build_bagi_tanaman(builder: Builder) -> None:
    for name in PART_WORDS.values():
        uri = builder.individual(name, "BagianTanaman")
        builder.label(uri, name)


def build_penyakit(builder: Builder, entries: list[dict[str, str]]) -> None:
    for entry in entries:
        uri = builder.individual(entry["local"], "Penyakit")
        builder.label(uri, entry["nama"])
        builder.link(uri, "menyerangTanaman", KBR[entry["plant_local"]])
        ref = "BukuDOC005" if entry["source"] == "DOC005" else "BukuDOC002"
        builder.link(uri, "memilikiReferensi", KBR[ref])


def build_patogen(builder: Builder, pairs: list[tuple[str, dict[str, str]]]) -> dict[str, str]:
    entries = {e["disease_id"]: e for e in penyakit_entries()}
    uniq = merge_pathogen_rows(pairs)

    bases: dict[str, list[str]] = {}
    for key, row in uniq.items():
        base = pascal(row.get("scientific_name") or "") or pascal(row["pathogen_id"])
        bases.setdefault(base, []).append(key)

    local_by_key: dict[str, str] = {}
    for key, row in uniq.items():
        base = pascal(row.get("scientific_name") or "") or pascal(row["pathogen_id"])
        local = base if len(bases[base]) == 1 else base + pascal(row["pathogen_id"])
        local_by_key[key] = local
        taxon = (row.get("taxon_group") or "").strip().lower()
        classes = ["Patogen"]
        if taxon in TAXON_CLASS:
            classes.append(TAXON_CLASS[taxon])
        uri = builder.individual(local, *classes)
        builder.label(uri, row.get("scientific_name") or row["pathogen_id"])
        builder.s(uri, "namaIlmiahPatogen", row.get("scientific_name"))

    for disease_id, row in pairs:
        builder.link(
            KBR[entries[disease_id]["local"]],
            "disebabkanOleh",
            KBR[local_by_key[pathogen_key(row)]],
        )
    return local_by_key


def build_gejala(builder: Builder, pairs: list[tuple[str, str, str]]) -> dict[str, URIRef]:
    entries = {e["disease_id"]: e for e in penyakit_entries()}
    cache: dict[str, URIRef] = {}
    for disease_id, text, _src in pairs:
        uri = gejala_uri(text, cache, builder)
        builder.link(KBR[entries[disease_id]["local"]], "memilikiGejala", uri)
    return cache


def build_menyerang_bagian(builder: Builder, bagian_pairs: list[tuple[str, str]]) -> None:
    entries = {e["disease_id"]: e for e in penyakit_entries()}
    for disease_id, part in bagian_pairs:
        builder.link(KBR[entries[disease_id]["local"]], "menyerangBagian", KBR[part])


def build_pengendalian(
    builder: Builder,
    pairs: list[tuple[str, str, str, str]],
    chapter_pairs: list[tuple[str, str, str]],
    report: dict,
) -> None:
    entries = {e["disease_id"]: e for e in penyakit_entries()}
    cache: dict[str, URIRef] = {}
    report["controls"] = {"disease": [], "chapter": [], "unclassified": 0}

    for disease_id, text, cat, source in pairs:
        subclasses = classify_control(text, cat, source)
        if not subclasses:
            report["controls"]["unclassified"] += 1
        uri = pengendalian_uri(text, cache, builder, subclasses)
        builder.link(KBR[entries[disease_id]["local"]], "dikendalikanDengan", uri)
        report["controls"]["disease"].append(
            {"disease_id": disease_id, "classes": subclasses, "category": cat, "source": source}
        )

    for plant_local, text, source in chapter_pairs:
        subclasses = classify_control(text, "", source)
        uri = pengendalian_uri(text, cache, builder, subclasses)
        builder.link(KBR[plant_local], "pengendalianUmum", uri)
        report["controls"]["chapter"].append(
            {"plant": plant_local, "classes": subclasses, "source": source}
        )


def build_varietas(
    builder: Builder,
    entries: list[dict[str, str]],
    control_pairs_list: list[tuple[str, str, str, str]],
    gejala_pairs: list[tuple[str, str, str]],
    report: dict,
) -> list[tuple[str, str]]:
    """Ekstraksi varietas; kembalikan (variety_local, disease_local) utk tahanTerhadap."""
    by_disease_texts: dict[str, list[str]] = {}
    for disease_id, text, _cat, _src in control_pairs_list:
        by_disease_texts.setdefault(disease_id, []).append(text)
    for disease_id, text, _src in gejala_pairs:
        by_disease_texts.setdefault(disease_id, []).append(text)

    entries_by_id = {e["disease_id"]: e for e in entries}
    report["varieties"] = []
    resistance_links: list[tuple[str, str]] = []
    plant_of: dict[str, str] = {e["local"]: e["plant_local"] for e in entries}

    # Kumpulkan (plant_local, variety_name) + bukti dari teks per penyakit.
    found: dict[tuple[str, str], dict] = {}
    for disease_id, texts in by_disease_texts.items():
        entry = entries_by_id.get(disease_id)
        if not entry:
            continue
        joined = " \n ".join(texts)
        names = extract_varieties(joined)
        if not names:
            continue
        for name in names:
            key = (entry["plant_local"], name)
            if key not in found:
                found[key] = {
                    "plant": entry["plant_local"],
                    "name": name,
                    "disease_ids": [],
                    "evidence": joined[:400],
                }
            found[key]["disease_ids"].append(disease_id)

    # Nama varietas → local individual (unik per nama global).
    name_local: dict[str, str] = {}
    for (_plant, name), info in found.items():
        if name not in name_local:
            base = "Varietas" + pascal(name)
            local = base
            suffix = 2
            while local in builder.used_locals or local in name_local.values():
                local = f"{base}{suffix}"
                suffix += 1
            name_local[name] = local

    for (_plant, name), info in sorted(found.items(), key=lambda kv: kv[0]):
        local = name_local[name]
        uri = builder.ensure_individual(local, "Varietas")
        builder.label(uri, name)
        builder.link(KBR[_plant], "memilikiVarietas", uri)
        report["varieties"].append(
            {
                "local": local,
                "name": name,
                "plant": _plant,
                "disease_ids": info["disease_ids"],
                "evidence": info["evidence"],
            }
        )

    # tahanTerhadap: hanya bila teks penyebaran punya penanda resistensi
    # dan tidak ada penanda rentan/peka pada teks yang sama.
    for (_plant, name), info in found.items():
        joined = " \n ".join(
            t
            for did in info["disease_ids"]
            for t in by_disease_texts.get(did, [])
        )
        if not RESIST_MARKERS.search(joined):
            continue
        if VULN_MARKERS.search(joined):
            continue
        for did in info["disease_ids"]:
            entry = entries_by_id.get(did)
            if not entry:
                continue
            link = (name_local[name], entry["local"])
            if link not in resistance_links:
                resistance_links.append(link)
                builder.link(KBR[link[0]], "tahanTerhadap", KBR[link[1]])
    return resistance_links


def build_fase(
    builder: Builder,
    entries: list[dict[str, str]],
    gejala_pairs: list[tuple[str, str, str]],
    control_pairs_list: list[tuple[str, str, str, str]],
    report: dict,
) -> None:
    by_disease: dict[str, list[str]] = {}
    for disease_id, text, _src in gejala_pairs:
        by_disease.setdefault(disease_id, []).append(text)
    for disease_id, text, _cat, _src in control_pairs_list:
        by_disease.setdefault(disease_id, []).append(text)

    entries_by_id = {e["disease_id"]: e for e in entries}
    report["phases"] = []
    used: set[str] = set()
    for disease_id, texts in sorted(by_disease.items()):
        entry = entries_by_id.get(disease_id)
        if not entry:
            continue
        for text in texts:
            for local in extract_phases(text):
                if local not in used:
                    used.add(local)
                    label = {
                        "FaseMatangSusu": "Fase matang susu",
                        "FaseVegetatif": "Fase vegetatif",
                        "FaseGeneratif": "Fase generatif",
                        "FasePembibitan": "Fase pembibitan",
                        "FaseAnakan": "Fase anakan",
                        "FaseMatang": "Fase matang",
                    }[local]
                    uri = builder.individual(local, "FasePertumbuhan")
                    builder.label(uri, label)
                    report["phases"].append({"local": local, "label": label})
                builder.link(KBR[entry["local"]], "menyerangFase", KBR[local])


def build_kondisi(
    builder: Builder,
    entries: list[dict[str, str]],
    gejala_pairs: list[tuple[str, str, str]],
    control_pairs_list: list[tuple[str, str, str, str]],
    report: dict,
) -> None:
    by_disease: dict[str, list[str]] = {}
    for disease_id, text, _src in gejala_pairs:
        by_disease.setdefault(disease_id, []).append(text)
    for disease_id, text, _cat, _src in control_pairs_list:
        by_disease.setdefault(disease_id, []).append(text)

    entries_by_id = {e["disease_id"]: e for e in entries}
    report["environment"] = []
    created: set[str] = set()

    for local, cls, _pattern in ENV_PATTERNS:
        if local not in created:
            created.add(local)
            label = {
                "KondisiKelembapanTinggi": "Kelembapan tinggi",
                "KondisiSuhu": "Suhu",
                "KondisiCurahHujan": "Curah hujan",
                "KondisiMusimHujan": "Musim hujan",
                "KondisiMusimKemarau": "Musim kemarau",
            }[local]
            uri = builder.individual(local, "FaktorRisiko", "FaktorLingkungan", cls)
            builder.label(uri, label)
            report["environment"].append(
                {"local": local, "class": cls, "label": label}
            )

    links: list[dict] = []
    for disease_id, texts in sorted(by_disease.items()):
        entry = entries_by_id.get(disease_id)
        if not entry:
            continue
        joined = " \n ".join(texts)
        for local, _cls, _pattern in ENV_PATTERNS:
            if _pattern.search(joined):
                builder.link(KBR[entry["local"]], "dipengaruhiOleh", KBR[local])
                links.append({"disease_id": disease_id, "env": local})
    report["environment_links"] = links


# ------------------------------------------------------------------ ekspektasi

def expected_counts() -> dict:
    entries = penyakit_entries()
    g_pairs, _errors = gejala_rows(entries)
    p_pairs = patogen_pairs(entries)
    c_pairs = control_pairs(entries)
    ch_pairs = chapter_control_pairs()
    bagian_pairs = menyerang_bagian_pairs(entries, g_pairs)
    plants = plant_rows_merged()

    gejala_texts = {text for _d, text, _s in g_pairs}
    control_texts = {text for _d, text, _c, _s in c_pairs}
    chapter_texts = {text for _p, text, _s in ch_pairs}
    pathogen_rows: dict[str, dict[str, str]] = {}
    for _d, row in p_pairs:
        key = norm(row.get("scientific_name")) or row["pathogen_id"].strip().lower()
        pathogen_rows[key] = row

    pathogen_rows = merge_pathogen_rows(p_pairs)

    varietas_locals = _varietas_locals(entries, c_pairs, g_pairs)
    fase_locals, fase_links = _fase_counts(entries, g_pairs, c_pairs)
    env_links = _env_counts(entries, g_pairs, c_pairs)

    pengendalian_texts = control_texts | chapter_texts

    classes: dict[str, int] = {
        "TanamanPangan": len(plants),
        "Penyakit": len(entries),
        "Gejala": len(gejala_texts),
        "Patogen": len(pathogen_rows),
        "BagianTanaman": len(PART_WORDS),
        "Pengendalian": len(pengendalian_texts),
        "Referensi": 2,
        "Buku": 2,
        "Varietas": len(varietas_locals),
        "FasePertumbuhan": len(fase_locals),
        "PenyakitJamur": 0,
        "PenyakitBakteri": 0,
        "PenyakitVirus": 0,
        "PenyakitLainnya": 0,
    }
    for text in gejala_texts:
        for part in text_parts(text):
            if part in PART_SUBCLASS:
                classes[PART_SUBCLASS[part]] = classes.get(PART_SUBCLASS[part], 0) + 1
    for row in pathogen_rows.values():
        mapped = TAXON_CLASS.get((row.get("taxon_group") or "").strip().lower())
        if mapped:
            classes[mapped] = classes.get(mapped, 0) + 1

    # sub-kelas pengendalian (individu cache per teks, multi-label)
    text_class: dict[str, list[str]] = {}
    for _d, text, cat, src in c_pairs:
        if text not in text_class:
            text_class[text] = classify_control(text, cat, src)
    for _p, text, src in ch_pairs:
        if text not in text_class:
            text_class[text] = classify_control(text, "", src)
    for classes_list in text_class.values():
        for cls in classes_list:
            classes[cls] = classes.get(cls, 0) + 1

    # kondisi lingkungan: 5 singleton selalu dibuat + tipe eksplisit
    for local, cls, _p in ENV_PATTERNS:
        classes[cls] = classes.get(cls, 0) + 1
    classes["FaktorRisiko"] = len(ENV_PATTERNS)
    classes["FaktorLingkungan"] = len(ENV_PATTERNS)

    classes["NamedIndividual"] = (
        classes["TanamanPangan"]
        + classes["Penyakit"]
        + classes["Gejala"]
        + classes["Patogen"]
        + classes["BagianTanaman"]
        + classes["Pengendalian"]
        + classes["Referensi"]
        + classes["Varietas"]
        + classes["FasePertumbuhan"]
        + len(ENV_PATTERNS)
    )

    # pasangan (disease, control) unik untuk dikendalikanDengan
    disease_control_pairs = {(d, t) for d, t, _c, _s in c_pairs}
    chapter_plant_pairs = {(p, t) for p, t, _s in ch_pairs}

    # materialisasi berkaitanPengendalian = disease-control + plant-chapter
    berkaitan = len(disease_control_pairs) + len(chapter_plant_pairs)

    # gejala→part terdapatPada (unik per teks)
    terdapat = sum(len({p for p in text_parts(text)}) for text in gejala_texts)

    properties: dict[str, int] = {
        "menyerangTanaman": len(entries),
        "diserangPenyakit": len(entries),
        "memilikiGejala": len(g_pairs),
        "merupakanGejalaDari": len(g_pairs),
        "disebabkanOleh": len(p_pairs),
        "menyebabkanPenyakit": len(p_pairs),
        "menyerangBagian": len(bagian_pairs),
        "terdapatPada": terdapat,
        "dikendalikanDengan": len(disease_control_pairs),
        "mengendalikanPenyakit": len(disease_control_pairs),
        "pengendalianUmum": len(chapter_plant_pairs),
        "berkaitanPengendalian": berkaitan,
        "memilikiReferensi": len(entries),
        "dijelaskanDalam": len(entries),
        "memilikiVarietas": sum(1 for _ in _varietas_plant_links(entries, c_pairs, g_pairs)),
        "merupakanVarietasDari": sum(1 for _ in _varietas_plant_links(entries, c_pairs, g_pairs)),
        "tahanTerhadap": len(_resistance_links(entries, c_pairs, g_pairs)),
        "menyerangFase": fase_links,
        "dipengaruhiOleh": env_links,
    }

    data_properties: dict[str, int] = {
        "namaIlmiah": sum(1 for r in plants if r["scientific_name"]),
        "namaIlmiahPatogen": sum(
            1 for r in pathogen_rows.values() if (r.get("scientific_name") or "").strip()
        ),
        "deskripsiGejala": len(gejala_texts),
        "deskripsiPengendalian": len(pengendalian_texts),
        "judulReferensi": 2,
        "tahunTerbit": 2,
        "namaPenulis": 2,
    }
    return {"classes": classes, "properties": properties, "data_properties": data_properties}


def _varietas_plant_links(
    entries: list[dict[str, str]],
    c_pairs: list[tuple[str, str, str, str]],
    g_pairs: list[tuple[str, str, str]],
) -> list[tuple[str, str]]:
    report: dict = {}
    Builder_for_count = _DryBuilder()
    build_varietas(Builder_for_count, entries, c_pairs, g_pairs, report)
    return Builder_for_count.plant_varietas_links


class _DryBuilder(Builder):
    def __init__(self) -> None:
        super().__init__()
        self.plant_varietas_links: list[tuple[str, str]] = []

    def link(self, uri: URIRef, prop: str, target: URIRef) -> None:
        if prop == "memilikiVarietas":
            self.plant_varietas_links.append((str(uri), str(target)))
        super().link(uri, prop, target)


def _varietas_locals(
    entries: list[dict[str, str]],
    c_pairs: list[tuple[str, str, str, str]],
    g_pairs: list[tuple[str, str, str]],
) -> set[str]:
    report: dict = {}
    b = _DryBuilder()
    build_varietas(b, entries, c_pairs, g_pairs, report)
    return {local for _p, local in b.plant_varietas_links}


def _resistance_links(
    entries: list[dict[str, str]],
    c_pairs: list[tuple[str, str, str, str]],
    g_pairs: list[tuple[str, str, str]],
) -> list[tuple[str, str]]:
    report: dict = {}
    b = _DryBuilder()
    return build_varietas(b, entries, c_pairs, g_pairs, report)


def _fase_counts(
    entries: list[dict[str, str]],
    g_pairs: list[tuple[str, str, str]],
    c_pairs: list[tuple[str, str, str, str]],
) -> tuple[set[str], int]:
    by_disease: dict[str, list[str]] = {}
    for disease_id, text, _src in g_pairs:
        by_disease.setdefault(disease_id, []).append(text)
    for disease_id, text, _c, _s in c_pairs:
        by_disease.setdefault(disease_id, []).append(text)
    used: set[str] = set()
    links = 0
    for texts in by_disease.values():
        seen_here: set[str] = set()
        for text in texts:
            for local in extract_phases(text):
                used.add(local)
                if local not in seen_here:
                    seen_here.add(local)
                    links += 1
    return used, links


def _env_counts(
    entries: list[dict[str, str]],
    g_pairs: list[tuple[str, str, str]],
    c_pairs: list[tuple[str, str, str, str]],
) -> int:
    by_disease: dict[str, list[str]] = {}
    for disease_id, text, _src in g_pairs:
        by_disease.setdefault(disease_id, []).append(text)
    for disease_id, text, _c, _s in c_pairs:
        by_disease.setdefault(disease_id, []).append(text)
    links = 0
    for texts in by_disease.values():
        joined = " \n ".join(texts)
        for _local, _cls, pattern in ENV_PATTERNS:
            if pattern.search(joined):
                links += 1
    return links


def build() -> tuple[Graph, dict, list[str], Builder, dict]:
    report: dict = {}
    builder = Builder()
    tbox.build_tbox(builder.graph)
    builder.graph.bind("ptp", KBR)

    entries = penyakit_entries()
    g_pairs, g_errors = gejala_rows(entries)
    builder.errors.extend(g_errors)
    p_pairs = patogen_pairs(entries)
    c_pairs = control_pairs(entries)
    ch_pairs = chapter_control_pairs()
    bagian_pairs = menyerang_bagian_pairs(entries, g_pairs)

    build_referensi(builder)
    build_tanaman(builder)
    build_bagi_tanaman(builder)
    build_penyakit(builder, entries)
    build_patogen(builder, p_pairs)
    build_gejala(builder, g_pairs)
    build_menyerang_bagian(builder, bagian_pairs)
    build_pengendalian(builder, c_pairs, ch_pairs, report)
    build_varietas(builder, entries, c_pairs, g_pairs, report)
    build_fase(builder, entries, g_pairs, c_pairs, report)
    build_kondisi(builder, entries, g_pairs, c_pairs, report)

    report["summary"] = {
        "plants": len(plant_rows_merged()),
        "diseases": len(entries),
        "symptom_pairs": len(g_pairs),
        "pathogen_pairs": len(p_pairs),
        "control_pairs_disease": len(c_pairs),
        "control_pairs_chapter": len(ch_pairs),
        "bagian_pairs": len(bagian_pairs),
    }

    expected = expected_counts()
    errors = validate(builder.graph, builder, expected)
    return builder.graph, expected, errors, builder, report


# ------------------------------------------------------------------ validasi

def validate(graph: Graph, builder: Builder, expected: dict) -> list[str]:
    errors = list(builder.errors)

    try:
        serialized = graph.serialize(format="turtle")
        reparsed = Graph()
        reparsed.parse(data=serialized, format="turtle")
    except Exception as exc:  # noqa: BLE001
        return errors + [f"parse ulang gagal: {exc}"]

    for cls, count in sorted(expected["classes"].items()):
        target = OWL.NamedIndividual if cls == "NamedIndividual" else KBR[cls]
        actual = len(list(graph.subjects(RDF.type, target)))
        if actual != count:
            errors.append(f"jumlah individu {cls}: {actual} != {count}")

    for prop, count in sorted(expected["properties"].items()):
        actual = len(list(graph.triples((None, KBR[prop], None))))
        if actual != count:
            errors.append(f"jumlah triple {prop}: {actual} != {count}")

    for prop, count in sorted(expected["data_properties"].items()):
        actual = len(list(graph.triples((None, KBR[prop], None))))
        if actual != count:
            errors.append(f"jumlah triple data {prop}: {actual} != {count}")

    for name, spec in tbox.OBJECT_PROPERTIES.items():
        rng = KBR[spec["range"]]
        domain = KBR[spec["domain"]] if spec.get("domain") else None
        for subj, obj in graph.subject_objects(KBR[name]):
            if domain is not None and (subj, RDF.type, domain) not in graph:
                errors.append(f"subjek {subj} dari kbr:{name} tidak bertipe {spec['domain']}")
            if (obj, RDF.type, rng) not in graph:
                errors.append(f"objek {obj} dari kbr:{name} tidak bertipe {spec['range']}")

    for name in tbox.DATA_PROPERTIES:
        domain = KBR[tbox.DATA_PROPERTIES[name]["domain"]]
        for subj, _obj in graph.subject_objects(KBR[name]):
            if (subj, RDF.type, domain) not in graph:
                errors.append(f"subjek {subj} dari kbr:{name} tidak bertipe {domain}")

    for literal_obj in graph.objects():
        if isinstance(literal_obj, Literal) and str(literal_obj) == "":
            errors.append("literal kosong ditemukan")

    for penyakit_cls, _patogen_cls in tbox.EQUIVALENT_CLASSES:
        if not any(graph.objects(KBR[penyakit_cls], OWL.equivalentClass)):
            errors.append(f"axiom equivalentClass hilang: {penyakit_cls}")

    # SROIQ(D) guards
    if not list(graph.objects(None, OWL.propertyChainAxiom)):
        errors.append("propertyChainAxiom hilang (aksara R)")
    for sub_prop, super_prop in tbox.SUBPROPERTY_OF:
        if (KBR[sub_prop], RDFS.subPropertyOf, KBR[super_prop]) not in graph:
            errors.append(f"subPropertyOf hilang: {sub_prop}⊑{super_prop} (aksara S)")
    for cls_name, members in tbox.NOMINAL_CLASSES.items():
        eq = list(graph.objects(KBR[cls_name], OWL.equivalentClass))
        one_of = False
        for node in eq:
            for coll in graph.objects(node, OWL.oneOf):
                chain = list(Collection(graph, coll))
                if [KBR[m] for m in members] == chain:
                    one_of = True
        if not one_of:
            errors.append(f"oneOf hilang: {cls_name} (aksara O)")
    inverse_count = len(list(graph.subject_objects(OWL.inverseOf)))
    if inverse_count != 12:
        errors.append(f"jumlah inverseOf: {inverse_count} != 12 (aksara I)")

    min1_found = False
    for node in graph.objects(KBR["Penyakit"], RDFS.subClassOf):
        if (node, OWL.onProperty, KBR["memilikiReferensi"]) in graph:
            for lit in graph.objects(node, OWL.minCardinality):
                if (node, OWL.onClass, KBR["Referensi"]) in graph and int(lit) == 1:
                    min1_found = True
    if not min1_found:
        errors.append("min 1 Referensi hilang pada Penyakit (aksara Q)")
    ex1_found = False
    for node in graph.objects(KBR["Buku"], RDFS.subClassOf):
        if (node, OWL.onProperty, KBR["tahunTerbit"]) in graph:
            for lit in graph.objects(node, OWL.cardinality):
                if (node, OWL.onDatatype, XSD.integer) in graph and int(lit) == 1:
                    ex1_found = True
    if not ex1_found:
        errors.append("exactly 1 xsd:integer tahunTerbit hilang pada Buku (aksara Q/D)")

    restr_found = set()
    for sub_cls, prop, target, quant in tbox.RESTRICTIONS:
        for node in graph.objects(KBR[sub_cls], RDFS.subClassOf):
            if (node, OWL.onProperty, KBR[prop]) not in graph:
                continue
            if quant == "some" and (node, OWL.someValuesFrom, KBR[target]) in graph:
                restr_found.add((sub_cls, prop, quant))
            elif quant == "only" and (node, OWL.allValuesFrom, KBR[target]) in graph:
                restr_found.add((sub_cls, prop, quant))
            elif quant == "min1":
                for lit in graph.objects(node, OWL.minCardinality):
                    if (node, OWL.onClass, KBR[target]) in graph and int(lit) == 1:
                        restr_found.add((sub_cls, prop, quant))
    for sub_cls, prop, _target, quant in tbox.RESTRICTIONS:
        if (sub_cls, prop, quant) not in restr_found:
            errors.append(f"restriction hilang: {sub_cls} {quant} {prop}")

    if len(list(graph.subject_objects(OWL.disjointWith))) != len(tbox.DISJOINT_PAIRS):
        errors.append(
            f"jumlah disjointWith: {len(list(graph.subject_objects(OWL.disjointWith)))} "
            f"!= {len(tbox.DISJOINT_PAIRS)}"
        )

    for forbidden in ("PenyakitJamur", "PenyakitBakteri", "PenyakitVirus", "PenyakitLainnya"):
        explicit = list(graph.subjects(RDF.type, KBR[forbidden]))
        if explicit:
            errors.append(f"{forbidden} tidak boleh di-assert eksplisit (harus inferensi reasoner)")

    for local, _cls, _p in ENV_PATTERNS:
        uri = KBR[local]
        for required in ("FaktorRisiko", "FaktorLingkungan", _cls):
            if (uri, RDF.type, KBR[required]) not in graph:
                errors.append(f"individu kondisi {local} tidak bertipe eksplisit {required}")

    entries = penyakit_entries()
    for entry in entries:
        uri = KBR[entry["local"]]
        for prop in ("menyerangTanaman", "memilikiGejala", "memilikiReferensi"):
            if not any(graph.objects(uri, KBR[prop])):
                errors.append(f"penyakit {entry['local']} tanpa {prop}")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bangun ontologi Penyakit Tanaman Pangan Indonesia.")
    parser.add_argument("--out", type=Path, default=DEFAULT_TTL, help="path keluaran TTL")
    args = parser.parse_args(argv)

    graph, expected, errors, builder, report = build()
    if errors:
        print("VALIDASI GAGAL:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 2

    args.out.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=str(args.out), format="turtle")
    owl_path = args.out.with_suffix(".owl")
    graph.serialize(destination=str(owl_path), format="xml")
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    individuals = len(list(graph.subjects(RDF.type, OWL.NamedIndividual)))
    cls = expected["classes"]
    print(f"ontologi ditulis: {args.out} dan {owl_path}")
    print(f"laporan ekstraksi: {REPORT_PATH}")
    print(
        f"triple: {len(graph)} | individu: {individuals} | penyakit: {cls['Penyakit']} | "
        f"gejala: {cls['Gejala']} | patogen: {cls['Patogen']} | pengendalian: {cls['Pengendalian']} | "
        f"varietas: {cls['Varietas']} | fase: {cls['FasePertumbuhan']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
