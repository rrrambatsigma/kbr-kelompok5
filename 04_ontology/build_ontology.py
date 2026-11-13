"""Generator ontologi OWL 2 "Penyakit Tanaman Pangan Indonesia".

Membaca knowledge tables hasil kurasi (``03_knowledge_tables``) dan teks sumber
hasil ekstraksi (``02_extraction``) untuk tujuh tanaman pangan — padi, kedelai,
jagung, ubi jalar, ubi kayu, kacang tanah, kacang hijau — lalu membangun ABox di
atas TBox ``tbox.py``.

Prinsip:
- Verbatim: deskripsi, gejala, pengendalian, dan faktor lingkungan dikutip dari
  sumber. Tidak ada parafrase dan tidak ada tebakan.
- Setiap individu diberi provenance (kutipan, halaman, id blok) bila tersedia.
- Nama individu berupa slug deskriptif; tanpa hash md5, tanpa DIS/SYM, dan tanpa
  tahun di awal local name.
- Faktor lingkungan terstruktur: nilaiMin/nilaiMaks/nilaiTunggal, satuan,
  tingkat, dan kondisi.

Pemakaian (dari root repo)::

    python 04_ontology/build_ontology.py

Keluaran: ``04_ontology/ontology.ttl``, ``ontology.owl``, dan
``extraction_report.json``; kode keluar ``2`` bila validasi gagal.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

from rdflib import Graph, Literal, URIRef
from rdflib.collection import Collection
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, SKOS, XSD

ONTO_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = ONTO_DIR.parent
TABLE_DIR = PROJECT_ROOT / "03_knowledge_tables"
CURATED_DIR = TABLE_DIR / "curated"
CURATED2 = CURATED_DIR / "DOC002"
CURATED5 = CURATED_DIR / "DOC005"
AUTO_DIR = TABLE_DIR / "auto"
META_PATH = PROJECT_ROOT / "01_knowledge_sources" / "source_metadata" / "manual_metadata.json"
DOC002_BLOCKS = PROJECT_ROOT / "02_extraction" / "llamaparse" / "baseline" / "DOC002.blocks.jsonl"
DOC005_MD = PROJECT_ROOT / "02_extraction" / "extracted_text" / "DOC005.md"
DEFAULT_TTL = ONTO_DIR / "ontology.ttl"
DEFAULT_OWL = ONTO_DIR / "ontology.owl"
REPORT_PATH = ONTO_DIR / "extraction_report.json"

sys.path.insert(0, str(ONTO_DIR))

import tbox  # noqa: E402
from tbox import KBR, PROV  # noqa: E402

# plant_id -> local individu tanaman (digabung per nama tanaman lintas dokumen).
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

PLANT_CLASS: dict[str, str] = {
    "Padi": "Serealia",
    "Jagung": "Serealia",
    "Kedelai": "Legum",
    "KacangTanah": "Legum",
    "KacangHijau": "Legum",
    "UbiJalar": "UmbiUmbian",
    "UbiKayu": "UmbiUmbian",
}

TAXON_CLASS = {
    "jamur": "Jamur",
    "bakteri": "Bakteri",
    "virus": "Virus",
    "fitoplasma": "Fitoplasma",
    "oomycete": "Oomycete",
    "nematoda": "Nematoda",
}
PART_WORDS = {
    "daun": "Daun",
    "batang": "Batang",
    "akar": "Akar",
    "umbi": "Umbi",
    "buah": "Buah",
    "biji": "Biji",
    "bunga": "Bunga",
    "malai": "Malai",
    "pelepah": "Pelepah",
    "polong": "Polong",
    "pucuk": "Pucuk",
    "tongkol": "Tongkol",
    "leher": "LeherMalai",
}
PART_SUBCLASS = {
    "Daun": "GejalaDaun",
    "Batang": "GejalaBatang",
    "Akar": "GejalaAkar",
    "Umbi": "GejalaUmbi",
    "Buah": "GejalaBuah",
    "Biji": "GejalaBiji",
    "Bunga": "GejalaBunga",
    "Malai": "GejalaMalai",
    "Pelepah": "GejalaPelepah",
    "Polong": "GejalaPolong",
    "Pucuk": "GejalaPucuk",
    "Tongkol": "GejalaTongkol",
    "LeherMalai": "GejalaLeherMalai",
}
TABLE_PART = {"T5.1_DAUN": "Daun", "T5.2_BATANG": "Batang", "T5.3_AKAR": "Umbi"}

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
        "pestisida nabati", "ekstrak", "jamur antagonis",
    )),
    ("PengendalianFisik", (
        "solarisasi", "perlakuan panas", "air panas", "pemanasan", "elektroterapi",
        "radiasi", "pengeringan", "penyimpanan dingin",
    )),
    ("PengendalianKulturTeknis", (
        "kultur teknis", "benih sehat", "rotasi", "sanitasi", "jarak tanam",
        "drainase", "varietas tahan", "varietas", "pemupukan", "penanaman serempak",
        "perbaikan cara", "teknik budidaya", "waktu panen", "pupuk", "mulsa",
        "pengolahan tanah", "tumpang sari", "pengairan",
    )),
    ("PengendalianMekanis", (
        "pencabutan", "perangkap", "pengumpulan", "pemangkasan", "pemusnahan",
        "penyulingan", "pengendalian mekanis", "pembakaran",
    )),
    ("PengendalianTerpadu", ("terpadu", "integrated", "pengelolaan terpadu")),
]

CONTROL_NAMES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\brotasi\s+tanaman\b", re.I), "Rotasi tanaman"),
    (re.compile(r"\bsanitasi(?:\s+lahan)?\b", re.I), "Sanitasi lahan"),
    (re.compile(r"\bbenih\s+sehat\b", re.I), "Benih sehat"),
    (re.compile(r"\bperlakuan\s+benih\b", re.I), "Perlakuan benih"),
    (re.compile(r"\bvarietas\s+(?:tahan|unggul)\b", re.I), "Varietas tahan"),
    (re.compile(r"\bfungisida\s+nabati\b", re.I), "Fungisida nabati"),
    (re.compile(r"\bfungisida\s+sintetik\b", re.I), "Fungisida sintetik"),
    (re.compile(r"\bfungisida\b", re.I), "Fungisida"),
    (re.compile(r"\bbakterisida\b", re.I), "Bakterisida"),
    (re.compile(r"\bpestisida\s+nabati\b", re.I), "Pestisida nabati"),
    (re.compile(r"\bpestisida\b", re.I), "Pestisida"),
    (re.compile(r"\bagens(?:ia)?\s+hayati\b", re.I), "Agens hayati"),
    (re.compile(r"\btrichoderma\b", re.I), "Trichoderma"),
    (re.compile(r"\bsolarisasi\b", re.I), "Solarisasi tanah"),
    (re.compile(r"\bperlakuan\s+air\s+panas\b", re.I), "Perlakuan air panas"),
    (re.compile(r"\bperlakuan\s+panas\b", re.I), "Perlakuan panas"),
    (re.compile(r"\bpencabutan\b", re.I), "Pencabutan"),
    (re.compile(r"\bpemangkasan\b", re.I), "Pemangkasan"),
    (re.compile(r"\bpemusnahan\b", re.I), "Pemusnahan"),
    (re.compile(r"\bperangkap\b", re.I), "Perangkap"),
    (re.compile(r"\bdrainase\b", re.I), "Drainase"),
    (re.compile(r"\bpemupukan\b", re.I), "Pemupukan"),
    (re.compile(r"\bjarak\s+tanam\b", re.I), "Jarak tanam"),
    (re.compile(r"\bmulsa\b", re.I), "Mulsa"),
    (re.compile(r"\bpengolahan\s+tanah\b", re.I), "Pengolahan tanah"),
]

PHASE_RE = re.compile(
    r"\bfase\s+(matang\s+susu|vegetatif|generatif|pembibitan|anakan|matang|"
    r"pembungaan|pengisian\s+polong|panen)\b",
    re.I,
)
PHASE_LOCAL = {
    "matang susu": "FaseMatangSusu",
    "vegetatif": "FaseVegetatif",
    "generatif": "FaseGeneratif",
    "pembibitan": "FasePembibitan",
    "anakan": "FaseAnakan",
    "matang": "FaseMatang",
    "pembungaan": "FasePembungaan",
    "pengisian polong": "FasePengisianPolong",
    "panen": "FasePanen",
}
PHASE_LABEL = {
    "FaseMatangSusu": "Fase matang susu",
    "FaseVegetatif": "Fase vegetatif",
    "FaseGeneratif": "Fase generatif",
    "FasePembibitan": "Fase pembibitan",
    "FaseAnakan": "Fase anakan",
    "FaseMatang": "Fase matang",
    "FasePembungaan": "Fase pembungaan",
    "FasePengisianPolong": "Fase pengisian polong",
    "FasePanen": "Fase panen",
}

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
    "satu", "dua", "tiga", "diketahui", "dilaporkan", "dianjurkan",
    "diperoleh", "ditemukan", "diberikan", "diberi", "boleh",
    "sekitar", "sebelum", "sesudah", "saat", "ketika", "apabila", "bila",
    "jika", "karena", "sehingga", "namun", "tetapi", "sedangkan", "telah",
    "sudah", "masih", "belum", "tanpa", "oleh", "kepada", "bagi", "buat",
}

SYMPTOM_KEYWORDS: list[tuple[str, str]] = [
    ("bercak", "Bercak"), ("menguning", "Menguning"), ("kekuningan", "Kekuningan"),
    ("kuning", "Kuning"), ("layu", "Layu"), ("busuk", "Busuk"), ("kerdil", "Kerdil"),
    ("mosaik", "Mosaik"), ("hawar", "Hawar"), ("karat", "Karat"), ("embun", "Embun"),
    ("rebah", "Rebah"), ("rontok", "Rontok"), ("kering", "Kering"),
    ("mengerut", "Mengerut"), ("keriput", "Keriput"), ("nekrosis", "Nekrosis"),
    ("nekrotik", "Nekrotik"), ("klorosis", "Klorosis"), ("klorotik", "Klorotik"),
    ("belang", "Belang"), ("pucat", "Pucat"), ("putih", "Putih"),
    ("coklat", "Coklat"), ("cokelat", "Coklat"), ("hitam", "Hitam"),
    ("kehitaman", "Kehitaman"), ("ungu", "Ungu"), ("berlubang", "Berlubang"),
    ("menggulung", "Menggulung"), ("terpuntir", "Terpuntir"), ("patah", "Patah"),
    ("hampa", "Hampa"), ("kosong", "Kosong"), ("mengapur", "Mengapur"),
    ("berlendir", "Berlendir"), ("berair", "Berair"), ("kaku", "Kaku"),
    ("keriting", "Keriting"), ("mengering", "Mengering"), ("gugur", "Gugur"),
    ("mati", "Mati"), ("kecil", "Kecil"), ("besar", "Besar"), ("tebal", "Tebal"),
]

RESIST_MARKERS = re.compile(r"\b(tahan|resistan|resisten|toleran)\b", re.I)
VULN_MARKERS = re.compile(r"\b(rentan|peka)\b", re.I)
VARIETY_PRIMARY_RE = re.compile(r"\bvarietas\b", re.I)
VARIETY_FALLBACK_RE = re.compile(
    r"\badalah\s+([A-Z][A-Za-z0-9\-']*(?:\s+[A-Z0-9][A-Za-z0-9\-']*){0,5})",
    re.UNICODE,
)

STOP_SLUG = {
    "dan", "atau", "yang", "pada", "untuk", "dengan", "dari", "ini", "itu",
    "dalam", "sebagai", "adalah", "akan", "dapat", "juga", "serta", "oleh",
    "karena", "sehingga", "namun", "tetapi", "sedangkan", "telah", "sudah",
    "masih", "belum", "tanpa", "antara", "secara", "lebih", "sangat", "cukup",
    "paling", "saat", "ketika", "apabila", "bila", "jika", "tersebut", "yaitu",
    "yakni", "misalnya", "seperti", "contoh", "menurut", "terhadap", "bagi",
    "buat", "kepada", "ke", "di", "para", "suatu", "setiap", "semua", "dll",
}

PROCESS_STOP = {
    "bahwa", "menurut", "menjelaskan", "dilakukan", "hasil", "penelitian",
    "penulis", "dalam", "buku", "sumber", "gambar", "tabel", "and", "the",
    "of", "et", "al", "uji", "perlakuan", "sedangkan", "yaitu", "adalah",
    "merupakan", "terdapat", "dapat", "akan", "juga", "serta", "oleh",
    "gejala", "penyakit", "tanaman", "serangan", "tersebut", "melaporkan",
    "menunjukkan", "demikian", "disebabkan", "dipengaruhi", "sementara",
    "hasilnya", "dilaporkan", "diketahui", "mengatakan", "terutama",
    "sebesar", "hingga", "mampu", "mengurangi", "meningkatkan", "menekan",
    "upaya", "cara", "hal", "agar", "setelah", "sebelum", "berbagai",
    "berupa", "termasuk", "berdasarkan", "terhadap", "dalam", "pada",
}

CITATION_RE = re.compile(
    r"\((?:[^()]*?\b(?:19|20)\d{2}\b[^()]*?)\)"
    r"|\b(?:19|20)\d{2}\b"
)
CAPTION_RE = re.compile(
    r"^(?:(?:gambar|tabel|no\.?|nomor)\b|sumber\s*:)", re.I
)
PAGE_HEADER_RE = re.compile(
    r"^(?:\d+\s+)?(?:penyakit tanaman dan pengendaliannya|"
    r"penyakit utama pada tanaman|daftar isi)\b", re.I
)
BAD_LOCAL_RE = re.compile(
    r"(?:Var\d+|DOC\d+|Koma|Persen|DerajatCelsius|Bahwa|Menurut|"
    r"Dilakukan|Menjelaskan|HasilPenelitian|PengendalianPengendalian|"
    r"^BukuDOC|^GejalaGejala|^PengendalianPengendalian)"
)
REFERENCE_LOCAL = {
    "DOC002": "BukuPenyakitTanamanDanPengendaliannya",
    "DOC005": "BukuPenyakitUtamaPadaTanamanKedelaiKacangTanahDanKacangHijau",
}

# ---------------------------------------------------------------- utilitas umum


def read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def norm(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def pascal(text: str) -> str:
    words: list[str] = []
    for word in re.split(r"[^0-9A-Za-z]+", text or ""):
        if not word:
            continue
        if len(word) > 1 and word.isupper():
            word = word.capitalize()
        else:
            word = word[:1].upper() + word[1:]
        words.append(word)
    return "".join(words)


def slugify(text: str, max_words: int = 4) -> str:
    words = re.findall(r"[A-Za-z]+", text or "")
    picked = [w for w in words if w.lower() not in STOP_SLUG and len(w) > 2][:max_words]
    return pascal(" ".join(picked))


def split_sentences(text: str) -> list[str]:
    clean = re.sub(r"\s+", " ", (text or "")).strip()
    if not clean:
        return []
    parts = re.split(r"(?<=[.!?])\s+", clean)
    return [p.strip() for p in parts if p.strip()]


def first_sentences(text: str, count: int = 2) -> str:
    return " ".join(split_sentences(text)[:count]).strip()


def disease_key(name: str) -> str:
    text = (name or "").lower()
    text = re.sub(r"\(.*?\)", " ", text)
    text = re.sub(r"^penyakit\s+", "", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if text in {"karat", "karat daun"}:
        return "karat"
    return text


def canonical_disease_key(entry: dict) -> tuple[str, str, str]:
    return (
        entry["plant_local"],
        disease_key(entry["nama"]),
        TABLE_PART.get(entry["section"], ""),
    )


def disease_ids(entries: list[dict]) -> list[str]:
    result: list[str] = []
    for entry in entries:
        for did in entry.get("disease_ids") or [entry["disease_id"]]:
            if did not in result:
                result.append(did)
    return result


def disease_by_id(entries: list[dict]) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for entry in entries:
        for did in entry.get("disease_ids") or [entry["disease_id"]]:
            result[did] = entry
    return result


def clean_text(text: str | None) -> str:
    text = (text or "").replace("\u00a0", " ").replace("\ufffd", " ")
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"\|", " ", text)
    text = re.sub(
        r"^\s*(?:(?:gambar|tabel|no\.?|nomor)\b|sumber\s*:).*$",
        " ",
        text,
        flags=re.M | re.I,
    )
    return re.sub(r"\s+", " ", text).strip()


def bad_prose(raw: str | None, min_len: int = 80) -> bool:
    raw = (raw or "").strip()
    if not raw:
        return True
    if "|" in raw or "\ufffd" in raw:
        return True
    low = norm(raw)
    if CAPTION_RE.match(low) or PAGE_HEADER_RE.match(low):
        return True
    if len(clean_text(raw)) < min_len:
        return True
    return False


def local_words(value: str) -> set[str]:
    return {word.lower() for word in re.findall(r"[A-Z]?[a-z]+", value or "")}


def semantic_slug(
    text: str,
    max_words: int = 8,
    avoid: set[str] | None = None,
) -> str:
    text = CITATION_RE.sub(" ", text or "")
    avoid = avoid or set()
    words = re.findall(r"[A-Za-z]+", text)
    picked = [
        word for word in words
        if word.lower() not in STOP_SLUG
        and word.lower() not in PROCESS_STOP
        and word.lower() not in avoid
        and len(word) > 2
    ]
    return pascal(" ".join(picked[:max_words]))


def plant_label(plant_local: str) -> str:
    return {
        "Padi": "Padi",
        "Kedelai": "Kedelai",
        "Jagung": "Jagung",
        "UbiJalar": "Ubi jalar",
        "UbiKayu": "Ubi kayu",
        "KacangTanah": "Kacang tanah",
        "KacangHijau": "Kacang hijau",
    }[plant_local]


def text_parts(text: str) -> list[str]:
    low = (text or "").lower()
    parts: list[str] = []
    for word, name in PART_WORDS.items():
        if re.search(r"\b" + word, low) and name not in parts:
            parts.append(name)
    return parts


def subsection_parts(subsection: str) -> list[str]:
    low = norm(subsection)
    if "akar" in low or "umbi" in low:
        return ["Akar", "Umbi"]
    if "batang" in low:
        return ["Batang"]
    if "daun" in low:
        return ["Daun"]
    return []


def fmt_num(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return str(value).replace(".", ",")


def fmt_local_num(value: float) -> str:
    return fmt_num(value).replace(",", "Desimal")


def to_decimal(value: str) -> float:
    return float(value.replace(",", "."))


# ---------------------------------------------------------------- sumber teks


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_doc002_blocks() -> list[dict]:
    return load_jsonl(DOC002_BLOCKS)


def parse_md_sections(path: Path) -> list[dict]:
    """Pecah markdown DOC005 menjadi bagian berheading + nomor halaman."""
    sections: list[dict] = []
    current = {"title": "", "level": 0, "page": 0, "lines": []}
    page = 0
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            page_match = re.match(r"<!--\s*page:\s*(\d+)\s*-->", stripped)
            if page_match:
                page = int(page_match.group(1))
                continue
            heading = re.match(r"^(#{1,6})\s+(.*)$", stripped)
            if heading:
                sections.append(current)
                current = {
                    "title": heading.group(2).strip(),
                    "level": len(heading.group(1)),
                    "page": page,
                    "lines": [],
                }
            else:
                current["lines"].append(stripped)
    sections.append(current)
    return sections


# ---------------------------------------------------------------- entri penyakit


def penyakit_entries() -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []

    def add_row(row: dict[str, str], source: str) -> None:
        pid = row["plant_id"].strip()
        if pid not in PLANT_LOCAL:
            return
        nama = (row.get("disease_name_verbatim") or "").strip()
        if not nama:
            return
        plant_local = PLANT_LOCAL[pid]
        clean = re.sub(r"^penyakit\s+", "", nama, flags=re.I).strip()
        base = pascal(clean + " " + plant_local)
        entries.append(
            {
                "disease_id": row["disease_id"].strip(),
                "plant_local": plant_local,
                "plant_id": pid,
                "nama": nama,
                "base": base,
                "section": (row.get("section") or "").strip(),
                "subsection": (row.get("subsection") or "").strip(),
                "page_start": (row.get("page_start") or "").strip(),
                "page_end": (row.get("page_end") or "").strip(),
                "name_en": (row.get("name_en_verbatim") or "").strip(),
                "source": source,
            }
        )

    for row in read_csv(CURATED2 / "diseases.csv"):
        add_row(row, "DOC002")
    for row in read_csv(CURATED5 / "diseases.csv"):
        add_row(row, "DOC005")

    groups: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for entry in entries:
        groups.setdefault(canonical_disease_key(entry), []).append(entry)

    merged: list[dict[str, str]] = []
    for key, group in groups.items():
        primary = sorted(
            group,
            key=lambda item: (
                item["source"] != "DOC002",
                -len(item["nama"]),
                item["disease_id"],
            ),
        )[0]
        primary["variants"] = group
        primary["disease_ids"] = [item["disease_id"] for item in group]
        primary["sources"] = list(dict.fromkeys(item["source"] for item in group))
        primary["aliases"] = list(dict.fromkeys(item["nama"] for item in group))
        if len(group) > 1:
            primary["base"] = pascal(f"{key[1]} {key[0]}")
        primary["name_en"] = next(
            (item["name_en"] for item in group if item["name_en"]),
            "",
        )
        pages = [
            int(item["page_start"]) for item in group
            if item["page_start"].isdigit()
        ]
        ends = [
            int(item["page_end"]) for item in group
            if item["page_end"].isdigit()
        ]
        if pages:
            primary["page_start"] = str(min(pages))
            primary["page_end"] = str(max(ends or pages))
        merged.append(primary)

    base_counts: dict[str, int] = {}
    for entry in merged:
        base_counts[entry["base"]] = base_counts.get(entry["base"], 0) + 1

    used: set[str] = set()
    for entry in merged:
        local = entry["base"]
        if base_counts[entry["base"]] > 1:
            part = TABLE_PART.get(entry["section"], "")
            if not part:
                parts = subsection_parts(entry["subsection"])
                part = parts[0] if parts else ""
            if part:
                local += part
        if local in used:
            raise ValueError(
                f"local name tabrakan tanpa penanda aman: {local} "
                f"({entry['disease_id']})"
            )
        entry["local"] = local
        used.add(local)
    return merged


def plant_descriptions() -> dict[str, dict[str, str]]:
    path = CURATED_DIR / "plant_descriptions.csv"
    if not path.exists():
        return {}
    return {
        row["plant_id"].strip(): {
            "deskripsi": (row.get("deskripsi") or "").strip(),
            "source_page": (row.get("source_page") or "").strip(),
            "source_block_id": (row.get("source_block_id") or "").strip(),
            "notes": (row.get("notes") or "").strip(),
        }
        for row in read_csv(path)
        if row.get("plant_id")
    }


def plant_rows_merged() -> list[dict[str, str]]:
    merged: dict[str, dict[str, str]] = {}
    descriptions = plant_descriptions()
    sources = [
        read_csv(CURATED2 / "plants.csv"),
        read_csv(CURATED5 / "plants.csv"),
        read_csv(AUTO_DIR / "plants.csv"),
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
                    "deskripsi": descriptions.get(pid, {}).get("deskripsi", ""),
                    "source_page": descriptions.get(pid, {}).get("source_page", ""),
                    "source_block_id": descriptions.get(pid, {}).get("source_block_id", ""),
                    "notes": descriptions.get(pid, {}).get("notes", ""),
                    "plant_ids": [pid],
                }
            else:
                if not merged[local]["scientific_name"] and (row.get("scientific_name") or "").strip():
                    merged[local]["scientific_name"] = row["scientific_name"].strip()
                if not merged[local]["deskripsi"]:
                    merged[local]["deskripsi"] = descriptions.get(pid, {}).get("deskripsi", "")
                if not merged[local]["source_page"]:
                    merged[local]["source_page"] = descriptions.get(pid, {}).get("source_page", "")
                if not merged[local]["source_block_id"]:
                    merged[local]["source_block_id"] = descriptions.get(pid, {}).get("source_block_id", "")
                if pid not in merged[local]["plant_ids"]:
                    merged[local]["plant_ids"].append(pid)
    order = ["Padi", "Kedelai", "Jagung", "UbiJalar", "UbiKayu", "KacangTanah", "KacangHijau"]
    return [merged[k] for k in order if k in merged]


# ---------------------------------------------------------------- pasangan data


def gejala_rows(entries: list[dict[str, str]]) -> tuple[list[tuple[str, str, str, str, str]], list[str]]:
    """(disease_id, teks, symptom_id, page, chunk_id) dan daftar error."""
    by_norm: dict[str, list[dict[str, str]]] = {}
    for entry in entries:
        for alias in entry.get("aliases") or [entry["nama"]]:
            bucket = by_norm.setdefault(norm(alias), [])
            if entry not in bucket:
                bucket.append(entry)
    ids = set(disease_ids(entries))
    pairs: list[tuple[str, str, str, str, str]] = []
    errors: list[str] = []

    for row in read_csv(CURATED2 / "symptoms.csv"):
        did = row["disease_id"].strip()
        if did in ids:
            text = (row.get("verbatim_text") or "").strip()
            if text:
                pairs.append((did, text, row.get("symptom_id", "").strip(),
                              row.get("page_start", "").strip(), row.get("chunk_id", "").strip()))
    for row in read_csv(CURATED5 / "symptoms.csv"):
        did = row["disease_id"].strip()
        if did in ids:
            text = (row.get("verbatim_text") or "").strip()
            if text:
                pairs.append((did, text, row.get("symptom_id", "").strip(),
                              row.get("page_start", "").strip(), row.get("chunk_id", "").strip()))

    for row in read_csv(CURATED2 / "ubi_kayu_tabel_5.csv"):
        nama = (row.get("disease_name") or "").strip()
        if not nama:
            continue
        text = (row.get("symptom_text") or "").strip()
        cands = by_norm.get(norm(nama), [])
        if len(cands) == 1:
            did = cands[0]["disease_id"]
        elif len(cands) > 1:
            want = TABLE_PART.get(row["table_id"].strip(), "")
            hit = [c for c in cands if TABLE_PART.get(c["section"], "") == want]
            if len(hit) == 1:
                did = hit[0]["disease_id"]
            else:
                errors.append(f"nama penyakit tabel ambigu pada baris {row['table_id']}#{row['row_no']}: {nama!r}")
                continue
        else:
            errors.append(f"nama penyakit tabel tidak dikenal pada baris {row['table_id']}#{row['row_no']}: {nama!r}")
            continue
        if not text:
            errors.append(f"baris tabel {row['table_id']}#{row['row_no']} tanpa teks gejala")
            continue
        pairs.append((did, text, row.get("source_block_id", "").strip(),
                      row.get("page", "").strip(), row.get("source_block_id", "").strip()))
    return pairs, errors


def patogen_pairs(entries: list[dict[str, str]]) -> list[tuple[str, dict[str, str]]]:
    scope_ids = set(disease_ids(entries))
    pairs: list[tuple[str, dict[str, str]]] = []
    seen: set[tuple[str, str]] = set()

    pathogens2 = {r["pathogen_id"].strip(): r for r in read_csv(CURATED2 / "pathogens.csv")}
    for row in read_csv(CURATED2 / "disease_pathogen.csv"):
        did = row["disease_id"].strip()
        pid = row["pathogen_id"].strip()
        if did in scope_ids and (did, pid) not in seen and pid in pathogens2:
            seen.add((did, pid))
            pairs.append((did, pathogens2[pid]))

    pathogens5 = {r["pathogen_id"].strip(): r for r in read_csv(CURATED5 / "pathogens.csv")}
    for row in read_csv(CURATED5 / "disease_pathogen.csv"):
        did = row["disease_id"].strip()
        pid = row["pathogen_id"].strip()
        if did in scope_ids and (did, pid) not in seen and pid in pathogens5:
            seen.add((did, pid))
            pairs.append((did, pathogens5[pid]))
    return pairs


def pathogen_key(row: dict[str, str]) -> str:
    return norm(row.get("scientific_name")) or row["pathogen_id"].strip().lower()


def _taxon_rank(taxon: str) -> int:
    return 0 if (taxon or "").strip().lower() in ("", "unknown") else 1


def merge_pathogen_rows(pairs: list[tuple[str, dict[str, str]]]) -> dict[str, dict[str, str]]:
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


def control_pairs(entries: list[dict[str, str]]) -> list[tuple[str, str, str, str, str, str]]:
    """(disease_id, text, category, source, page, chunk_id) scope=disease."""
    scope_ids = set(disease_ids(entries))
    pairs: list[tuple[str, str, str, str, str, str]] = []
    seen: set[tuple[str, str]] = set()
    for path, source in ((CURATED2 / "controls.csv", "DOC002"), (CURATED5 / "controls.csv", "DOC005")):
        for row in read_csv(path):
            did = row["disease_id"].strip()
            text = (row.get("verbatim_text") or "").strip()
            if did in scope_ids and row["scope"].strip() == "disease" and text:
                if (did, text) not in seen:
                    seen.add((did, text))
                    pairs.append((did, text, (row.get("control_category") or "").strip(),
                                  source, row.get("page_start", "").strip(),
                                  row.get("chunk_id", "").strip()))
    return pairs


def chapter_control_pairs() -> list[tuple[str, str, str, str, str]]:
    """(plant_local, text, source, page, chunk_id) scope=chapter dari DOC002."""
    pairs: list[tuple[str, str, str, str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in read_csv(CURATED2 / "controls.csv"):
        pid = row["plant_id"].strip()
        text = (row.get("verbatim_text") or "").strip()
        if pid in PLANT_LOCAL and row["scope"].strip() == "chapter" and text:
            plant_local = PLANT_LOCAL[pid]
            if (plant_local, text) not in seen:
                seen.add((plant_local, text))
                pairs.append((plant_local, text, "DOC002",
                              row.get("page_start", "").strip(),
                              row.get("chunk_id", "").strip()))
    return pairs


# ---------------------------------------------------------------- ekstraksi teks


def doc002_blocks_for(entry: dict[str, str]) -> list[dict]:
    blocks = load_doc002_blocks()
    try:
        start = int(entry.get("page_start") or 0)
        end = int(entry.get("page_end") or start)
    except ValueError:
        start, end = 0, 0
    key = disease_key(entry["nama"])
    in_range = [
        b for b in blocks
        if isinstance(b.get("page_number"), int) and start <= b["page_number"] <= end
    ]
    matched = [
        b for b in in_range
        if key and (
            key in norm(b.get("section"))
            or key in norm(b.get("subsection"))
            or key in norm(b.get("text"))
        )
    ]
    return matched or in_range


def doc002_description(entry: dict[str, str]) -> tuple[str, str, str]:
    blocks = doc002_blocks_for(entry)
    key = disease_key(entry["nama"])

    def heading_match(block: dict) -> bool:
        heading = norm(block.get("section")) + " " + norm(block.get("subsection"))
        return bool(key) and key in heading

    def score(block: dict) -> tuple[int, int, int, int]:
        heading = norm(block.get("section")) + " " + norm(block.get("subsection"))
        penyebab = 1 if "penyebab" in heading else 0
        heading_hit = 1 if heading_match(block) else 0
        text_hit = 1 if key and key in norm(block.get("text")) else 0
        paragraph = 1 if block.get("content_type") == "paragraph" else 0
        return (penyebab, heading_hit, paragraph + text_hit, len(block.get("text") or ""))

    candidates = [b for b in blocks if (b.get("text") or "").strip()]
    candidates.sort(key=score, reverse=True)
    for block in candidates:
        raw = (block.get("text") or "").strip()
        if bad_prose(raw):
            continue
        quote = clean_text(first_sentences(raw, 3))
        if len(quote) < 80:
            quote = clean_text(raw)
        if len(quote) >= 80:
            return quote, str(block.get("page_number") or ""), str(block.get("block_id") or "")
    return "", "", ""


def doc005_sections() -> list[dict]:
    return parse_md_sections(DOC005_MD)


def doc005_sections_for(entry: dict[str, str], sections: list[dict]) -> list[dict]:
    key = disease_key(entry["nama"])
    try:
        start = int(entry.get("page_start") or 0)
        end = int(entry.get("page_end") or start)
    except ValueError:
        start, end = 0, 0
    for index, section in enumerate(sections):
        title = norm(section.get("title"))
        page = section.get("page") or 0
        if key and key in title and (not start or start - 2 <= page <= end + 2):
            collected: list[dict] = [section]
            level = section.get("level") or 0
            for nxt in sections[index + 1:]:
                if (nxt.get("level") or 0) <= level and (nxt.get("title") or "").strip():
                    break
                collected.append(nxt)
            return collected
    return []


def doc005_description(entry: dict[str, str], sections: list[dict]) -> tuple[str, str, str]:
    collected = doc005_sections_for(entry, sections)
    if not collected:
        return "", "", ""

    def clean_lines(section: dict) -> str:
        lines: list[str] = []
        for raw in section.get("lines", []):
            raw = (raw or "").strip()
            if not raw or "|" in raw or "\ufffd" in raw:
                continue
            low = norm(raw)
            if CAPTION_RE.match(low) or PAGE_HEADER_RE.match(low):
                continue
            cleaned = clean_text(raw)
            if cleaned:
                lines.append(cleaned)
        return " ".join(lines)

    ordered = [
        section for section in collected
        if "penyebab" in norm(section.get("title"))
    ] + [section for section in collected if "penyebab" not in norm(section.get("title"))]
    for section in ordered:
        text = clean_lines(section)
        if len(text) < 80:
            continue
        quote = first_sentences(text, 3)
        if len(quote) < 80:
            quote = text
        return quote, str(section.get("page") or ""), ""
    return "", "", ""


def disease_source_text(
    entry: dict[str, str],
    sections: list[dict] | None = None,
    symptom_texts: list[str] | None = None,
    control_texts: list[str] | None = None,
    relevant_only: bool = False,
) -> tuple[list[str], str, str]:
    """Kumpulkan teks sumber milik satu penyakit beserta halaman/id blok."""
    chunks: list[str] = []
    page = ""
    block_id = ""
    if entry["source"] == "DOC002":
        for block in doc002_blocks_for(entry):
            if relevant_only and block.get("content_type") == "table":
                continue
            text = (block.get("text") or "").strip()
            if text:
                chunks.append(text)
                if not page:
                    page = str(block.get("page_number") or "")
                    block_id = str(block.get("block_id") or "")
    else:
        collected = doc005_sections_for(entry, sections or doc005_sections())
        if relevant_only:
            filtered = [
                section for section in collected
                if re.search(
                    r"faktor|lingkungan|suhu|kelembap|penyebab|siklus",
                    norm(section.get("title")),
                )
            ]
            if filtered:
                collected = filtered
        for section in collected:
            lines = [
                line for line in section.get("lines", [])
                if line and (not relevant_only or "|" not in line)
            ]
            text = " ".join(lines)
            if text.strip():
                chunks.append(text.strip())
                if not page:
                    page = str(section.get("page") or "")
    for text in symptom_texts or []:
        chunks.append(text)
    for text in control_texts or []:
        chunks.append(text)
    return chunks, page, block_id


# ---------------------------------------------------------------- faktor lingkungan

NUM = r"(\d+(?:[.,]\d+)?)"
DASH = r"(?:\s*[-–—]\s*|\s+sampai\s+|\s+hingga\s+)"
DEG = r"(?:[°ºo0]\s*|\s+)"
TEMP_RANGE_RE = re.compile(
    rf"{NUM}{DASH}{NUM}\s*{DEG}C\b", re.I
)
TEMP_SINGLE_RE = re.compile(
    rf"{NUM}\s*{DEG}C\b", re.I
)
HUMIDITY_RE = re.compile(
    rf"(?:kelembapan|kelembaban)\s*(?:relatif|tanah)?\s*"
    rf"(?:mencapai|optimal|optimum|berkisar|sekitar|antara|>|≥|lebih\s+dari)?\s*"
    rf"{NUM}(?:{DASH}{NUM})?\s*%",
    re.I,
)
HUMIDITY_SINGLE_RE = re.compile(
    rf"(?:kelembapan|kelembaban)\s*(?:relatif|tanah)?\s*"
    rf"(?:mencapai|optimal|optimum|berkisar|sekitar|>|≥|lebih\s+dari)?\s*"
    rf"{NUM}\s*%",
    re.I,
)
HUMIDITY_QUAL_RE = re.compile(
    r"(?:kelembapan|kelembaban)\s+(?:tanah\s+)?(?:yang\s+)?(tinggi|rendah|sedang)", re.I
)
PH_RE = re.compile(
    rf"\bpH\s*(?:tanah)?\s*"
    rf"(?:optimal|optimum|berkisar|sekitar|antara|pada|"
    rf"di\s+bawah|di\s+atas|kurang\s+dari|lebih\s+dari|[<>≤≥])?\s*"
    rf"{NUM}(?:{DASH}{NUM})?",
    re.I,
)
RAIN_QUAL_RE = re.compile(r"curah\s+hujan\s+(?:yang\s+)?(tinggi|rendah|sedang)", re.I)
SEASON_RE = re.compile(r"musim\s+(hujan|kemarau|penghujan)", re.I)
LIGHT_RE = re.compile(rf"({NUM})\s*lux", re.I)
LIGHT_QUAL_RE = re.compile(r"(naungan|cahaya\s+matahari|intensitas\s+cahaya)", re.I)
WIND_RE = re.compile(r"\b(angin|kecepatan\s+angin)\b", re.I)


def normalize_temp(value: float) -> float:
    # OCR sumber menulis 220C/250C/300C untuk 22/25/30 derajat Celsius.
    if value > 100 and value % 10 == 0:
        return value / 10
    return value


def sentence_with(text: str, match: re.Match[str]) -> str:
    start = max(0, text.rfind(".", 0, match.start()) + 1)
    end = text.find(".", match.end())
    if end == -1:
        end = len(text)
    return text[start:end + 1].strip() or text[max(0, match.start() - 80):match.end() + 80].strip()


def condition_near(text: str, match: re.Match[str]) -> str:
    window = text[max(0, match.start() - 80):match.start()].lower()
    cut = max(window.rfind(ch) for ch in ".!?;,")
    for conj in (" sedangkan ", " tetapi ", " namun ", " dan ", " serta "):
        cut = max(cut, window.rfind(conj))
    if cut != -1:
        window = window[cut + 1:]
    for word, value in (
        ("suhu kamar", "kamar"),
        ("di bawah", "rendah"), ("di atas", "tinggi"),
        ("optimum", "optimal"), ("optimal", "optimal"), ("mendukung", "mendukung"),
        ("maksimum", "maksimum"), ("maksimal", "maksimum"),
        ("minimum", "minimum"), ("minimal", "minimum"),
        ("tinggi", "tinggi"), ("rendah", "rendah"), ("hangat", "hangat"),
        ("dingin", "dingin"), ("sejuk", "sejuk"),
    ):
        if word in window:
            return value
    return "tercatat"


def temp_level(value_min: float | None, value_max: float | None, value: float | None) -> str:
    v = value if value is not None else (
        (value_min + value_max) / 2 if value_min is not None and value_max is not None
        else (value_max if value_max is not None else value_min)
    )
    if v is None:
        return ""
    if v < 20:
        return "rendah"
    if v <= 30:
        return "sedang"
    return "tinggi"


def humidity_level(value_min: float | None, value_max: float | None, value: float | None) -> str:
    v = value if value is not None else (
        (value_min + value_max) / 2 if value_min is not None and value_max is not None
        else (value_max if value_max is not None else value_min)
    )
    if v is None:
        return ""
    if v < 60:
        return "rendah"
    if v < 80:
        return "sedang"
    return "tinggi"


def env_local(
    prefix: str,
    condition: str,
    value_min: float | None = None,
    value_max: float | None = None,
    value: float | None = None,
    unit: str = "",
) -> str:
    prefix = {
        "KelembapanRelatif": "KelembapanUdara",
        "PhTanah": "DerajatKeasamanTanah",
    }.get(prefix, prefix)
    tokens = [prefix]
    if condition:
        cond = pascal(condition)
        if condition.lower() not in prefix.lower():
            tokens.append(cond)
    if value_min is not None and value_max is not None:
        if float(value_min) == float(value_max):
            tokens.append(fmt_local_num(value_min))
        else:
            tokens.extend([fmt_local_num(value_min), "Sampai", fmt_local_num(value_max)])
    elif value is not None:
        tokens.append(fmt_local_num(value))
    return "".join(tokens)


def extract_environment(
    text: str,
    quote: str,
    page: str,
    block_id: str,
) -> list[dict]:
    found: list[dict] = []
    seen: set[str] = set()

    def add(
        local: str,
        cls: str,
        *,
        condition: str = "",
        level: str = "",
        unit: str = "",
        vmin: float | None = None,
        vmax: float | None = None,
        value: float | None = None,
        snippet: str = "",
    ) -> None:
        if local in seen:
            return
        seen.add(local)
        found.append(
            {
                "local": local,
                "classes": ["FaktorRisiko", "FaktorLingkungan", cls],
                "condition": condition,
                "level": level,
                "unit": unit,
                "value_min": vmin,
                "value_max": vmax,
                "value": value,
                "quote": snippet or quote,
                "page": page,
                "block_id": block_id,
            }
        )

    temp_range_spans: list[tuple[int, int]] = []
    for match in TEMP_RANGE_RE.finditer(text):
        temp_range_spans.append(match.span())
        raw_min, raw_max = to_decimal(match.group(1)), to_decimal(match.group(2))
        vmin, vmax = normalize_temp(raw_min), normalize_temp(raw_max)
        if vmin > vmax:
            vmin, vmax = vmax, vmin
        if vmin < 0 or vmax > 45:
            continue
        condition = condition_near(text, match)
        local = env_local("Suhu", condition, vmin, vmax, unit="°C")
        add(local, "Suhu", condition=condition, level=temp_level(vmin, vmax, None),
            unit="°C", vmin=vmin, vmax=vmax, snippet=sentence_with(text, match))
    for match in TEMP_SINGLE_RE.finditer(text):
        if any(start <= match.start() < end for start, end in temp_range_spans):
            continue
        value = normalize_temp(to_decimal(match.group(1)))
        if value <= 0 or value > 45:
            continue
        condition = condition_near(text, match)
        local = env_local("Suhu", condition, value=value, unit="°C")
        add(local, "Suhu", condition=condition, level=temp_level(None, None, value),
            unit="°C", value=value, snippet=sentence_with(text, match))
    humidity_range_spans: list[tuple[int, int]] = []
    for match in HUMIDITY_RE.finditer(text):
        humidity_range_spans.append(match.span())
        raw_min = to_decimal(match.group(1))
        raw_max = to_decimal(match.group(2)) if match.group(2) else raw_min
        vmin, vmax = (raw_min, raw_max) if raw_min <= raw_max else (raw_max, raw_min)
        if vmin < 0 or vmax > 100:
            continue
        soil = "tanah" in text[
            max(0, match.start() - 60):min(len(text), match.end() + 60)
        ].lower()
        cls = "KelembapanTanah" if soil else "KelembapanUdara"
        condition = condition_near(text, match)
        prefix = "KelembapanTanah" if soil else "KelembapanRelatif"
        local = env_local(prefix, condition, vmin, vmax, unit="%")
        add(local, cls, condition=condition, level=humidity_level(vmin, vmax, None),
            unit="%", vmin=vmin, vmax=vmax, snippet=sentence_with(text, match))
    for match in HUMIDITY_SINGLE_RE.finditer(text):
        if any(start <= match.start() < end for start, end in humidity_range_spans):
            continue
        value = to_decimal(match.group(1))
        if value < 0 or value > 100:
            continue
        soil = "tanah" in text[
            max(0, match.start() - 60):min(len(text), match.end() + 60)
        ].lower()
        cls = "KelembapanTanah" if soil else "KelembapanUdara"
        condition = condition_near(text, match)
        prefix = "KelembapanTanah" if soil else "KelembapanRelatif"
        local = env_local(prefix, condition, value=value, unit="%")
        add(local, cls, condition=condition, level=humidity_level(None, None, value),
            unit="%", value=value, snippet=sentence_with(text, match))
    for match in HUMIDITY_QUAL_RE.finditer(text):
        level = match.group(1).lower()
        soil = "tanah" in norm(text[match.start():match.end()])
        prefix = "KelembapanTanah" if soil else "KelembapanRelatif"
        local = env_local(prefix, level)
        add(local, "KelembapanTanah" if soil else "KelembapanUdara",
            condition=level, level=level, snippet=sentence_with(text, match))
    for match in PH_RE.finditer(text):
        raw_min = to_decimal(match.group(1))
        raw_max = to_decimal(match.group(2)) if match.group(2) else None
        token = text[match.start():match.end()].lower()
        if "<" in token or "di bawah" in token or "kurang dari" in token:
            condition = "rendah"
        elif ">" in token or "di atas" in token or "lebih dari" in token:
            condition = "tinggi"
        else:
            condition = condition_near(text, match)
        if raw_max is not None:
            vmin, vmax = (raw_min, raw_max) if raw_min <= raw_max else (raw_max, raw_min)
            local = env_local("PhTanah", condition, vmin, vmax)
            add(local, "DerajatKeasamanTanah", condition=condition,
                unit="pH", vmin=vmin, vmax=vmax, snippet=sentence_with(text, match))
        else:
            local = env_local("PhTanah", condition, value=raw_min)
            add(local, "DerajatKeasamanTanah", condition=condition,
                unit="pH", value=raw_min, snippet=sentence_with(text, match))
    for match in RAIN_QUAL_RE.finditer(text):
        level = match.group(1).lower()
        local = env_local("CurahHujan", level)
        add(local, "CurahHujan", condition=level, level=level,
            snippet=sentence_with(text, match))
    for match in SEASON_RE.finditer(text):
        season = match.group(1).lower()
        if season in ("hujan", "penghujan"):
            add("KondisiMusimHujan", "MusimHujan", condition="hujan", level="hujan",
                snippet=sentence_with(text, match))
        else:
            add("KondisiMusimKemarau", "MusimKemarau", condition="kemarau", level="kemarau",
                snippet=sentence_with(text, match))
    for match in LIGHT_RE.finditer(text):
        value = to_decimal(match.group(1))
        local = env_local("IntensitasCahaya", "rendah", value=value, unit="lux")
        add(local, "Cahaya", condition="rendah", unit="lux", value=value,
            snippet=sentence_with(text, match))
    if not any(item["classes"][-1] == "Cahaya" for item in found):
        match = LIGHT_QUAL_RE.search(text)
        if match:
            add("CahayaMatahari", "Cahaya", condition="tercatat",
                snippet=sentence_with(text, match))
    if not any(item["classes"][-1] == "Angin" for item in found):
        match = WIND_RE.search(text)
        if match:
            add("KondisiAngin", "Angin", condition="tercatat", snippet=sentence_with(text, match))
    return found


# ---------------------------------------------------------------- ekstraksi varietas


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
            if tok.lower() in VARIETY_STOPWORDS and tokens and tok.lower() in {
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

    for match in VARIETY_PRIMARY_RE.finditer(text):
        rest = text[match.end():]
        window = re.split(r"[.\n]", rest)[0][:200]
        parts = re.split(r",\s*|\s+dan\s+|\s+atau\s+|\s+sedangkan\s+", window)
        for part in parts:
            push(_proper_run(part))
    if not found:
        for match in VARIETY_FALLBACK_RE.finditer(text):
            push(_proper_run(match.group(1)))
    return found


def extract_phases(text: str) -> list[str]:
    found: list[str] = []
    for match in PHASE_RE.finditer(text):
        key = re.sub(r"\s+", " ", match.group(1).lower())
        local = PHASE_LOCAL.get(key)
        if local and local not in found:
            found.append(local)
    return found


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


def control_names(text: str) -> list[str]:
    names: list[str] = []
    for pattern, label in CONTROL_NAMES:
        if pattern.search(text or "") and label not in names:
            names.append(label)
    return names


# ---------------------------------------------------------------- penamaan lokal


class NameRegistry:
    def __init__(self) -> None:
        self.used: set[str] = set()

    def unique(self, base: str, alternatives: list[str] | tuple[str, ...] = ()) -> str:
        for candidate in [base, *alternatives]:
            candidate = (candidate or "").strip()
            if candidate and candidate not in self.used:
                self.used.add(candidate)
                return candidate
        raise ValueError(f"tidak ada local name unik untuk {base!r}")


def symptom_local(text: str, parts: list[str], disease_local: str = "") -> str:
    low = (text or "").lower()
    keywords: list[str] = []
    for word, label in SYMPTOM_KEYWORDS:
        if re.search(r"\b" + re.escape(word), low) and label not in keywords:
            keywords.append(label)
    part = parts[0] if parts else ""
    base = "Gejala" + (part or "") + "".join(keywords[:3])
    if base == "Gejala" or base == ("Gejala" + part):
        base += semantic_slug(text, 4) or disease_local or "TanpaTeks"
    return base or "GejalaTanpaTeks"


def control_local(
    text: str,
    subclasses: list[str],
    disease_local: str = "",
    plant_local: str = "",
) -> str:
    names = control_names(text)
    if names:
        base = "Pengendalian" + "".join(pascal(n) for n in names[:2])
    elif subclasses:
        base = subclasses[0]
        if not base.startswith("Pengendalian"):
            base = "Pengendalian" + base
        if base in tbox.CLASS_LABELS:
            base += disease_local or plant_local or "Umum"
    else:
        base = "Pengendalian" + (disease_local or plant_local or "Umum")
    return base


def pathogen_local(row: dict[str, str]) -> str:
    name = (row.get("scientific_name") or "").strip()
    name = re.sub(r"\(.*?\)", " ", name)
    name = re.sub(r"\b(?:sp|spp|pv|var|f)\b\.?", " ", name, flags=re.I)
    base = pascal(name)
    if not base:
        base = "PatogenTanpaNama"
    return base


# ---------------------------------------------------------------- builder ABox


class Builder:
    def __init__(self) -> None:
        self.graph = Graph()
        self.errors: list[str] = []
        self.names = NameRegistry()
        self.created: set[str] = set()

    def individual(self, local: str, *classes: str) -> URIRef:
        uri = KBR[local]
        self.created.add(local)
        self.graph.add((uri, RDF.type, OWL.NamedIndividual))
        for cls in classes:
            self.graph.add((uri, RDF.type, KBR[cls]))
        return uri

    def ensure_individual(self, local: str, *classes: str) -> URIRef:
        uri = KBR[local]
        self.created.add(local)
        if (uri, RDF.type, OWL.NamedIndividual) not in self.graph:
            self.graph.add((uri, RDF.type, OWL.NamedIndividual))
        for cls in classes:
            self.graph.add((uri, RDF.type, KBR[cls]))
        return uri

    def label(self, uri: URIRef, text: str | None) -> None:
        text = clean_text(text)
        if text:
            self.graph.add((uri, RDFS.label, Literal(text, lang="id")))
            self.graph.add((uri, SKOS.prefLabel, Literal(text, lang="id")))

    def alt_label(self, uri: URIRef, text: str | None) -> None:
        text = clean_text(text)
        if text:
            self.graph.add((uri, SKOS.altLabel, Literal(text, lang="id")))

    def definition(self, uri: URIRef, text: str | None) -> None:
        text = clean_text(text)
        if text:
            self.graph.add((uri, SKOS.definition, Literal(text, lang="id")))

    def comment(self, uri: URIRef, text: str | None) -> None:
        text = clean_text(text)
        if text:
            self.graph.add((uri, RDFS.comment, Literal(text, lang="id")))

    def identifier(self, uri: URIRef, value: str | None) -> None:
        if value and value.strip():
            self.graph.add((uri, DCTERMS.identifier, Literal(value.strip())))

    def source(self, uri: URIRef, value: str | None) -> None:
        if value and value.strip():
            self.graph.add((uri, DCTERMS.source, Literal(value.strip())))

    def derived(self, uri: URIRef, value: str | None) -> None:
        if value and value.strip():
            self.graph.add((uri, PROV.wasDerivedFrom, Literal(value.strip())))

    def s(self, uri: URIRef, prop: str, value: str | None) -> None:
        text = clean_text(value)
        if text:
            self.graph.add((uri, KBR[prop], Literal(text, lang="id")))

    def plain(self, uri: URIRef, prop: str, value: str | None) -> None:
        if value is not None and str(value).strip():
            self.graph.add((uri, KBR[prop], Literal(str(value).strip())))

    def i(self, uri: URIRef, prop: str, value: str | int | None) -> None:
        if value is None or str(value).strip() == "":
            return
        try:
            self.graph.add((uri, KBR[prop], Literal(int(str(value).strip()), datatype=XSD.integer)))
        except ValueError:
            self.errors.append(f"nilai bukan integer untuk {prop}: {value!r}")

    def d(self, uri: URIRef, prop: str, value: float | None) -> None:
        if value is None:
            return
        self.graph.add((uri, KBR[prop], Literal(float(value), datatype=XSD.decimal)))

    def link(self, uri: URIRef, prop: str, target: URIRef) -> None:
        self.graph.add((uri, KBR[prop], target))
        inverse = tbox.OBJECT_PROPERTIES.get(prop, {}).get("inverse")
        if inverse:
            self.graph.add((target, KBR[inverse], uri))
        if prop in ("dikendalikanDengan", "pengendalianUmum"):
            self.graph.add((uri, KBR["berkaitanPengendalian"], target))

    def provenance(self, uri: URIRef, quote: str, page: str, block_id: str) -> None:
        self.s(uri, "kutipanSumber", quote)
        self.i(uri, "halamanSumber", page)
        self.plain(uri, "idBlokSumber", block_id)
        self.derived(uri, block_id)


def build_referensi(builder: Builder) -> None:
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    for doc_id in ("DOC002", "DOC005"):
        info = meta["documents"][doc_id]
        local = REFERENCE_LOCAL[doc_id]
        uri = builder.individual(local, "Referensi", "Buku")
        builder.label(uri, info.get("title"))
        builder.s(uri, "judulReferensi", info.get("title"))
        year = info.get("publication_year")
        if year is not None:
            builder.graph.add((uri, KBR.tahunTerbit, Literal(int(year), datatype=XSD.integer)))
        authors = ", ".join(info.get("authors") or [])
        builder.s(uri, "namaPenulis", authors or None)
        builder.identifier(uri, doc_id)
        builder.source(uri, doc_id)
        builder.definition(uri, info.get("title"))
        builder.provenance(uri, info.get("title"), "", doc_id)


def build_tanaman(builder: Builder) -> None:
    for row in plant_rows_merged():
        classes = ["TanamanPangan"]
        plant_cls = PLANT_CLASS.get(row["local"])
        if plant_cls:
            classes.append(plant_cls)
        uri = builder.individual(row["local"], *classes)
        builder.label(uri, row["label"])
        builder.alt_label(uri, row["scientific_name"] or None)
        builder.s(uri, "namaIlmiah", row["scientific_name"] or None)
        builder.s(uri, "deskripsiTanaman", row["deskripsi"] or None)
        builder.definition(uri, row["deskripsi"] or None)
        if row.get("notes"):
            builder.comment(uri, row["notes"])
        builder.provenance(
            uri,
            row["deskripsi"],
            row.get("source_page", ""),
            row.get("source_block_id", ""),
        )
        for pid in row.get("plant_ids", []):
            builder.identifier(uri, pid)


def build_bagian_tanaman(builder: Builder) -> None:
    labels = {
        "Daun": "Daun",
        "Batang": "Batang",
        "Akar": "Akar",
        "Umbi": "Umbi",
        "Buah": "Buah",
        "Biji": "Biji",
        "Bunga": "Bunga",
        "Malai": "Malai",
        "Pelepah": "Pelepah",
        "Polong": "Polong",
        "Pucuk": "Pucuk",
        "Tongkol": "Tongkol",
        "LeherMalai": "Leher malai",
    }
    for local, label in labels.items():
        uri = builder.individual(local, "BagianTanaman")
        builder.label(uri, label)
        builder.comment(uri, f"Bagian tanaman: {label}.")


def doc002_table_description(entry: dict[str, str]) -> tuple[str, str, str]:
    key = disease_key(entry["nama"])
    part = TABLE_PART.get(entry["section"], "")
    for row in read_csv(CURATED2 / "ubi_kayu_tabel_5.csv"):
        if disease_key(row.get("disease_name", "")) != key:
            continue
        row_part = TABLE_PART.get(row.get("table_id", "").strip(), "")
        if part and row_part != part:
            continue
        text = clean_text(row.get("symptom_text"))
        if len(text) >= 20:
            return (
                text,
                (row.get("page") or "").strip(),
                (row.get("source_block_id") or "").strip(),
            )
    return "", "", ""


def build_penyakit(builder: Builder, entries: list[dict[str, str]]) -> None:
    sections5 = doc005_sections()
    for entry in entries:
        uri = builder.individual(entry["local"], "Penyakit")
        builder.label(uri, entry["nama"])
        for disease_id in entry.get("disease_ids") or [entry["disease_id"]]:
            builder.identifier(uri, disease_id)
        for source in entry.get("sources") or [entry["source"]]:
            builder.source(uri, source)
            builder.link(uri, "memilikiReferensi", KBR[REFERENCE_LOCAL[source]])
        builder.link(uri, "menyerangTanaman", KBR[entry["plant_local"]])
        for alias in entry.get("aliases") or [entry["nama"]]:
            if alias != entry["nama"]:
                builder.alt_label(uri, alias)
        if entry.get("name_en"):
            builder.alt_label(uri, entry["name_en"])
            builder.s(uri, "namaInggrisPenyakit", entry["name_en"])

        best: tuple[str, str, str] | None = None
        for variant in entry.get("variants") or [entry]:
            if variant["source"] == "DOC002":
                quote, page, block_id = doc002_description(variant)
                if not quote:
                    quote, page, block_id = doc002_table_description(variant)
            else:
                quote, page, block_id = doc005_description(variant, sections5)
            if quote and (best is None or len(quote) > len(best[0])):
                best = (quote, page, block_id)
        if best is None:
            quote, page, block_id = "", "", ""
        else:
            quote, page, block_id = best
        builder.s(uri, "deskripsiPenyakit", quote or None)
        builder.definition(uri, quote or entry["nama"])
        builder.provenance(uri, quote, page, block_id)


def build_patogen(builder: Builder, pairs: list[tuple[str, dict[str, str]]],
                  entries: list[dict[str, str]]) -> dict[str, str]:
    by_id = disease_by_id(entries)
    uniq = merge_pathogen_rows(pairs)

    local_by_key: dict[str, str] = {}
    for key, row in sorted(uniq.items()):
        base = pathogen_local(row)
        if base in tbox.CLASS_LABELS:
            base = "Patogen" + base
        local = builder.names.unique(base)
        local_by_key[key] = local
        taxon = (row.get("taxon_group") or "").strip().lower()
        classes = ["Patogen"]
        if taxon in TAXON_CLASS:
            classes.append(TAXON_CLASS[taxon])
        elif taxon not in ("", "unknown"):
            builder.errors.append(f"takson tidak dikenal: {taxon!r} pada {row.get('pathogen_id')}")
        uri = builder.individual(local, *classes)
        scientific = (row.get("scientific_name") or row.get("pathogen_id") or "").strip()
        builder.label(uri, scientific)
        builder.alt_label(uri, row.get("verbatim_text") or None)
        builder.s(uri, "namaIlmiahPatogen", scientific or None)
        builder.definition(uri, row.get("verbatim_text") or scientific)
        if row.get("note"):
            builder.s(uri, "catatanTakson", row["note"])
            builder.comment(uri, row["note"])
        builder.identifier(uri, row.get("pathogen_id"))
        builder.source(uri, "DOC005" if row.get("document_id") == "DOC005" else "DOC002")
        builder.provenance(
            uri,
            (row.get("verbatim_text") or scientific),
            row.get("page", ""),
            row.get("chunk_id", ""),
        )

    for disease_id, row in pairs:
        entry = by_id.get(disease_id)
        if not entry:
            continue
        builder.link(KBR[entry["local"]], "disebabkanOleh", KBR[local_by_key[pathogen_key(row)]])
    return local_by_key


def build_gejala(builder: Builder,
                 pairs: list[tuple[str, str, str, str, str]],
                 entries: list[dict[str, str]]) -> dict[str, URIRef]:
    by_id = disease_by_id(entries)
    cache: dict[str, URIRef] = {}
    for disease_id, text, symptom_id, page, chunk in pairs:
        entry = by_id.get(disease_id)
        if not entry or not clean_text(text):
            continue
        if text not in cache:
            parts = text_parts(text)
            part = parts[0] if parts else ""
            base = symptom_local(text, parts, entry["local"])
            avoid = local_words(entry["local"]) | local_words(entry["plant_local"])
            alternatives = list(dict.fromkeys([
                f"Gejala{part}{entry['local']}",
                f"Gejala{part}{entry['local']}{semantic_slug(text, 5, avoid)}",
                f"Gejala{part}{semantic_slug(text, 8, avoid)}",
            ]))
            local = builder.names.unique(base, alternatives)
            classes = ["Gejala"] + [PART_SUBCLASS[p] for p in parts if p in PART_SUBCLASS]
            uri = builder.individual(local, *classes)
            builder.label(uri, text)
            builder.definition(uri, text)
            builder.s(uri, "deskripsiGejala", text)
            builder.identifier(uri, symptom_id)
            builder.provenance(uri, text, page, chunk)
            for part in parts:
                builder.link(uri, "terdapatPada", KBR[part])
            cache[text] = uri
        builder.link(KBR[entry["local"]], "memilikiGejala", cache[text])
    return cache


def menyerang_bagian_pairs(
    entries: list[dict[str, str]],
    pairs: list[tuple[str, str, str, str, str]],
) -> list[tuple[str, str]]:
    by_disease: dict[str, list[str]] = {}
    for disease_id, text, _sid, _page, _chunk in pairs:
        by_disease.setdefault(disease_id, []).append(text)
    out: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for entry in entries:
        parts = subsection_parts(entry["subsection"])
        if not parts:
            parts = []
            for disease_id in entry.get("disease_ids") or [entry["disease_id"]]:
                for text in by_disease.get(disease_id, []):
                    for part in text_parts(text):
                        if part not in parts:
                            parts.append(part)
        for part in parts:
            key = (entry["disease_id"], part)
            if key not in seen:
                seen.add(key)
                out.append(key)
    return out


def build_menyerang_bagian(builder: Builder, bagian_pairs: list[tuple[str, str]],
                           entries: list[dict[str, str]]) -> None:
    by_id = disease_by_id(entries)
    for disease_id, part in bagian_pairs:
        entry = by_id.get(disease_id)
        if entry:
            builder.link(KBR[entry["local"]], "menyerangBagian", KBR[part])


def build_pengendalian(
    builder: Builder,
    pairs: list[tuple[str, str, str, str, str, str]],
    chapter_pairs: list[tuple[str, str, str, str, str]],
    entries: list[dict[str, str]],
    report: dict,
) -> None:
    by_id = disease_by_id(entries)
    cache: dict[str, URIRef] = {}
    report["controls"] = {"disease": [], "chapter": [], "unclassified": 0}

    for disease_id, text, cat, source, page, chunk in pairs:
        entry = by_id.get(disease_id)
        if not entry:
            continue
        subclasses = classify_control(text, cat, source)
        if not subclasses:
            report["controls"]["unclassified"] += 1
        if text not in cache:
            base = control_local(text, subclasses, entry["local"], entry["plant_local"])
            avoid = local_words(entry["local"]) | local_words(entry["plant_local"])
            first = base if base.endswith(entry["local"]) else f"{base}{entry['local']}"
            alternatives = list(dict.fromkeys([
                first,
                f"Pengendalian{entry['local']}{semantic_slug(text, 5, avoid)}",
                f"Pengendalian{entry['plant_local']}{semantic_slug(text, 7, avoid)}",
            ]))
            local = builder.names.unique(base, alternatives)
            uri = builder.individual(local, "Pengendalian", *subclasses)
            builder.label(uri, text)
            builder.definition(uri, text)
            builder.s(uri, "deskripsiPengendalian", text)
            names = control_names(text)
            if names:
                builder.s(uri, "namaPengendalian", "; ".join(names))
            builder.provenance(uri, text, page, chunk)
            builder.source(uri, source)
            cache[text] = uri
        builder.link(KBR[entry["local"]], "dikendalikanDengan", cache[text])
        report["controls"]["disease"].append(
            {"disease_id": disease_id, "classes": subclasses, "category": cat, "source": source}
        )

    for plant_local, text, source, page, chunk in chapter_pairs:
        subclasses = classify_control(text, "", source)
        if text not in cache:
            base = control_local(text, subclasses, "", plant_local)
            avoid = local_words(plant_local)
            first = base if base.endswith(plant_local) else f"{base}{plant_local}"
            alternatives = list(dict.fromkeys([
                first,
                f"Pengendalian{plant_local}{semantic_slug(text, 5, avoid)}",
                f"Pengendalian{plant_local}{semantic_slug(text, 7, avoid)}",
            ]))
            local = builder.names.unique(base, alternatives)
            uri = builder.individual(local, "Pengendalian", *subclasses)
            builder.label(uri, text)
            builder.definition(uri, text)
            builder.s(uri, "deskripsiPengendalian", text)
            names = control_names(text)
            if names:
                builder.s(uri, "namaPengendalian", "; ".join(names))
            builder.provenance(uri, text, page, chunk)
            builder.source(uri, source)
            cache[text] = uri
        builder.link(KBR[plant_local], "pengendalianUmum", cache[text])
        report["controls"]["chapter"].append(
            {"plant": plant_local, "classes": subclasses, "source": source}
        )


def build_varietas(
    builder: Builder,
    entries: list[dict[str, str]],
    control_list: list[tuple[str, str, str, str, str, str]],
    gejala_pairs: list[tuple[str, str, str, str, str]],
    report: dict,
) -> None:
    by_disease_texts: dict[str, list[tuple[str, str, str]]] = {}
    for disease_id, text, _cat, _src, page, chunk in control_list:
        by_disease_texts.setdefault(disease_id, []).append((text, page, chunk))
    for disease_id, text, _sid, page, chunk in gejala_pairs:
        by_disease_texts.setdefault(disease_id, []).append((text, page, chunk))

    by_id = disease_by_id(entries)
    report["varieties"] = []
    found: dict[tuple[str, str], dict] = {}
    for disease_id, texts in by_disease_texts.items():
        entry = by_id.get(disease_id)
        if not entry:
            continue
        joined = " \n ".join(text for text, _page, _chunk in texts)
        names = extract_varieties(joined)
        if not names:
            continue
        for name in names:
            key = (entry["plant_local"], name)
            evidence = next(
                ((text, page, chunk) for text, page, chunk in texts if name in text),
                (joined, "", ""),
            )
            if key not in found:
                found[key] = {
                    "plant": entry["plant_local"],
                    "name": name,
                    "disease_ids": [],
                    "evidence": evidence[0][:400],
                    "page": evidence[1],
                    "chunk": evidence[2],
                }
            found[key]["disease_ids"].append(disease_id)

    name_local: dict[str, str] = {}
    for (_plant, name), _info in sorted(found.items(), key=lambda kv: kv[0]):
        if name not in name_local:
            base = "Varietas" + pascal(name)
            name_local[name] = builder.names.unique(base)

    for (_plant, name), info in sorted(found.items(), key=lambda kv: kv[0]):
        local = name_local[name]
        uri = builder.ensure_individual(local, "Varietas")
        if not list(builder.graph.objects(uri, RDFS.label)):
            builder.label(uri, name)
            builder.definition(uri, f"Varietas {name}.")
            builder.provenance(uri, info["evidence"], info.get("page", ""), info.get("chunk", ""))
        builder.link(KBR[_plant], "memilikiVarietas", uri)
        lower = name.lower()
        if "unggul" in info["evidence"].lower():
            builder.graph.add((uri, RDF.type, KBR["VarietasUnggul"]))
        if "lokal" in info["evidence"].lower():
            builder.graph.add((uri, RDF.type, KBR["VarietasLokal"]))
        report["varieties"].append(
            {
                "local": local,
                "name": name,
                "plant": _plant,
                "disease_ids": info["disease_ids"],
                "evidence": info["evidence"],
                "page": info.get("page", ""),
                "chunk": info.get("chunk", ""),
            }
        )

    tahan_links: list[tuple[str, str]] = []
    rentan_links: list[tuple[str, str]] = []
    for (_plant, name), info in found.items():
        joined = " \n ".join(
            text
            for did in info["disease_ids"]
            for text, _page, _chunk in by_disease_texts.get(did, [])
        )
        resistant = bool(RESIST_MARKERS.search(joined))
        vulnerable = bool(VULN_MARKERS.search(joined))
        if resistant and not vulnerable:
            for did in info["disease_ids"]:
                entry = by_id.get(did)
                if entry:
                    link = (name_local[name], entry["local"])
                    if link not in tahan_links:
                        tahan_links.append(link)
                        builder.link(KBR[link[0]], "tahanTerhadap", KBR[link[1]])
        if vulnerable and not resistant:
            for did in info["disease_ids"]:
                entry = by_id.get(did)
                if entry:
                    link = (name_local[name], entry["local"])
                    if link not in rentan_links:
                        rentan_links.append(link)
                        builder.link(KBR[link[0]], "rentanTerhadap", KBR[link[1]])
    report["variety_links"] = {"tahan": tahan_links, "rentan": rentan_links}


def build_fase(
    builder: Builder,
    entries: list[dict[str, str]],
    gejala_pairs: list[tuple[str, str, str, str, str]],
    control_list: list[tuple[str, str, str, str, str, str]],
    report: dict,
) -> None:
    by_disease: dict[str, list[str]] = {}
    for disease_id, text, _sid, _page, _chunk in gejala_pairs:
        by_disease.setdefault(disease_id, []).append(text)
    for disease_id, text, _cat, _src, _page, _chunk in control_list:
        by_disease.setdefault(disease_id, []).append(text)

    by_id = disease_by_id(entries)
    report["phases"] = []
    used: set[str] = set()
    for disease_id, texts in sorted(by_disease.items()):
        entry = by_id.get(disease_id)
        if not entry:
            continue
        for text in texts:
            for local in extract_phases(text):
                if local not in used:
                    used.add(local)
                    uri = builder.individual(local, "FasePertumbuhan")
                    builder.label(uri, PHASE_LABEL[local])
                    builder.definition(uri, f"Fase pertumbuhan: {PHASE_LABEL[local]}.")
                    builder.provenance(uri, text, "", "")
                    report["phases"].append({"local": local, "label": PHASE_LABEL[local]})
                builder.link(KBR[entry["local"]], "menyerangFase", KBR[local])


def build_kondisi(
    builder: Builder,
    entries: list[dict[str, str]],
    gejala_pairs: list[tuple[str, str, str, str, str]],
    control_list: list[tuple[str, str, str, str, str, str]],
    report: dict,
) -> None:
    by_disease: dict[str, list[str]] = {}
    for disease_id, text, _sid, _page, _chunk in gejala_pairs:
        by_disease.setdefault(disease_id, []).append(text)
    for disease_id, text, _cat, _src, _page, _chunk in control_list:
        by_disease.setdefault(disease_id, []).append(text)

    by_id = disease_by_id(entries)
    sections5 = doc005_sections()
    report["environment"] = []
    report["environment_links"] = []
    env_seen: dict[str, dict] = {}

    for disease_id, texts in sorted(by_disease.items()):
        entry = by_id.get(disease_id)
        if not entry:
            continue
        source_chunks: list[str] = []
        page, block_id = "", ""
        for variant in entry.get("variants") or [entry]:
            chunks, vpage, vblock = disease_source_text(
                variant, sections5, texts, [], relevant_only=True
            )
            for chunk in chunks:
                if chunk not in source_chunks:
                    source_chunks.append(chunk)
            if not page and vpage:
                page, block_id = vpage, vblock
        text = " \n ".join(source_chunks)
        for item in extract_environment(text, "", page, block_id):
            local = item["local"]
            if local not in env_seen:
                env_seen[local] = item
                uri = builder.individual(local, *item["classes"])
                builder.label(uri, human_env_label(item))
                builder.definition(uri, item.get("quote") or human_env_label(item))
                builder.d(uri, "nilaiMin", item.get("value_min"))
                builder.d(uri, "nilaiMaks", item.get("value_max"))
                builder.d(uri, "nilaiTunggal", item.get("value"))
                if item.get("unit"):
                    builder.s(uri, "satuan", item["unit"])
                if item.get("level"):
                    builder.s(uri, "tingkat", item["level"])
                if item.get("condition"):
                    builder.s(uri, "kondisi", item["condition"])
                builder.provenance(uri, item.get("quote", ""), item.get("page", ""), item.get("block_id", ""))
                report["environment"].append(
                    {
                        "local": local,
                        "classes": item["classes"],
                        "condition": item.get("condition", ""),
                        "level": item.get("level", ""),
                        "unit": item.get("unit", ""),
                        "value_min": item.get("value_min"),
                        "value_max": item.get("value_max"),
                        "value": item.get("value"),
                        "quote": item.get("quote", ""),
                        "page": item.get("page", ""),
                    }
                )
            builder.link(KBR[entry["local"]], "dipengaruhiOleh", KBR[local])
            report["environment_links"].append({"disease_id": disease_id, "env": local})


def human_env_label(item: dict) -> str:
    cls = item["classes"][-1]
    names = {
        "Suhu": "Suhu",
        "KelembapanUdara": "Kelembapan udara",
        "KelembapanTanah": "Kelembapan tanah",
        "CurahHujan": "Curah hujan",
        "MusimHujan": "Musim hujan",
        "MusimKemarau": "Musim kemarau",
        "Cahaya": "Cahaya",
        "Angin": "Angin",
        "DerajatKeasamanTanah": "pH tanah",
    }
    base = names.get(cls, cls)
    bits: list[str] = [base]
    joined = base.lower()
    tokens = [item["condition"]] if item.get("condition") else [item.get("level", "")]
    for token in tokens:
        if token and token.lower() not in joined:
            bits.append(token)
            joined += " " + token.lower()
    unit = item.get("unit", "")
    unit_suffix = "" if unit in ("", "pH") else f" {unit}"
    if item.get("value_min") is not None and item.get("value_max") is not None:
        vmin, vmax = item["value_min"], item["value_max"]
        if float(vmin) == float(vmax):
            value_text = fmt_num(vmin)
        else:
            value_text = f"{fmt_num(vmin)}-{fmt_num(vmax)}"
        bits.append(value_text + unit_suffix)
    elif item.get("value") is not None:
        bits.append(fmt_num(item["value"]) + unit_suffix)
    return " ".join(bits)


# ---------------------------------------------------------------- validasi


def counts(graph: Graph) -> dict:
    classes = {
        name: len(list(graph.subjects(RDF.type, KBR[name])))
        for name in tbox.CLASS_LABELS
    }
    properties = {
        name: len(list(graph.triples((None, KBR[name], None))))
        for name in tbox.OBJECT_PROPERTIES
    }
    data_properties = {
        name: len(list(graph.triples((None, KBR[name], None))))
        for name in tbox.DATA_PROPERTIES
    }
    classes["NamedIndividual"] = len(list(graph.subjects(RDF.type, OWL.NamedIndividual)))
    return {"classes": classes, "properties": properties, "data_properties": data_properties}


def validate(graph: Graph, builder: Builder) -> list[str]:
    errors = list(builder.errors)

    try:
        serialized = graph.serialize(format="turtle")
        reparsed = Graph()
        reparsed.parse(data=serialized, format="turtle")
    except Exception as exc:  # noqa: BLE001
        return errors + [f"parse ulang gagal: {exc}"]

    # Nama lokal bersih.
    bad_local = re.compile(r"(_[0-9a-f]{8}$)|(DIS\d+)|(^20\d\d)")
    for subject in graph.subjects(RDF.type, OWL.NamedIndividual):
        local = str(subject).rsplit("#", 1)[-1]
        if bad_local.search(local) or BAD_LOCAL_RE.search(local):
            errors.append(f"local name tidak bersih: {local}")

    # Literal kosong dan sisa tabel/kapten.
    for literal_obj in graph.objects():
        if not isinstance(literal_obj, Literal):
            continue
        text = str(literal_obj)
        if text == "":
            errors.append("literal kosong ditemukan")
        if "|" in text or "\ufffd" in text:
            errors.append(f"literal mengandung sisa tabel/encoding: {text[:80]!r}")

    for subject, prop, literal_obj in graph.triples((None, None, None)):
        if prop not in (
            KBR["deskripsiPenyakit"],
            KBR["deskripsiGejala"],
            KBR["deskripsiPengendalian"],
        ):
            continue
        text = str(literal_obj)
        if CAPTION_RE.match(norm(text)) or PAGE_HEADER_RE.match(norm(text)):
            errors.append(f"deskripsi mengandung kaption/header: {text[:80]!r}")

    # Label dan komentar kelas/properti.
    for name in tbox.CLASS_LABELS:
        if not list(graph.objects(KBR[name], RDFS.label)):
            errors.append(f"kelas {name} tanpa rdfs:label")
        if not list(graph.objects(KBR[name], RDFS.comment)):
            errors.append(f"kelas {name} tanpa rdfs:comment")
    for name, spec in tbox.OBJECT_PROPERTIES.items():
        if not list(graph.objects(KBR[name], RDFS.label)):
            errors.append(f"object property {name} tanpa rdfs:label")
        if not list(graph.objects(KBR[name], RDFS.comment)):
            errors.append(f"object property {name} tanpa rdfs:comment")
    for name, spec in tbox.DATA_PROPERTIES.items():
        if not list(graph.objects(KBR[name], RDFS.label)):
            errors.append(f"data property {name} tanpa rdfs:label")
        if not list(graph.objects(KBR[name], RDFS.comment)):
            errors.append(f"data property {name} tanpa rdfs:comment")

    # Setiap individu berlabel.
    for subject in graph.subjects(RDF.type, OWL.NamedIndividual):
        if not list(graph.objects(subject, RDFS.label)):
            errors.append(f"individu tanpa label: {str(subject).rsplit('#', 1)[-1]}")

    # Domain/range object property.
    for name, spec in tbox.OBJECT_PROPERTIES.items():
        rng = KBR[spec["range"]]
        domain = KBR[spec["domain"]] if spec.get("domain") else None
        for subj, obj in graph.subject_objects(KBR[name]):
            if domain is not None and (subj, RDF.type, domain) not in graph:
                errors.append(f"subjek {subj} dari kbr:{name} tidak bertipe {spec['domain']}")
            if (obj, RDF.type, rng) not in graph:
                errors.append(f"objek {obj} dari kbr:{name} tidak bertipe {spec['range']}")

    # Domain data property.
    for name, spec in tbox.DATA_PROPERTIES.items():
        if not spec.get("domain"):
            continue
        domain = KBR[spec["domain"]]
        for subj, _obj in graph.subject_objects(KBR[name]):
            if (subj, RDF.type, domain) not in graph:
                errors.append(f"subjek {subj} dari kbr:{name} tidak bertipe {spec['domain']}")

    # Inverse lengkap.
    for name, spec in tbox.OBJECT_PROPERTIES.items():
        inverse = spec.get("inverse")
        if not inverse:
            continue
        if (KBR[name], OWL.inverseOf, KBR[inverse]) not in graph:
            errors.append(f"inverseOf hilang: {name} -> {inverse}")
        if (KBR[inverse], OWL.inverseOf, KBR[name]) not in graph:
            errors.append(f"inverseOf hilang: {inverse} -> {name}")

    # Disjoint class.
    for left, right in tbox.DISJOINT_PAIRS:
        if (KBR[left], OWL.disjointWith, KBR[right]) not in graph:
            errors.append(f"disjointWith hilang: {left} / {right}")

    # Disjoint property.
    for left, right in tbox.PROPERTY_DISJOINT:
        if (KBR[left], OWL.propertyDisjointWith, KBR[right]) not in graph:
            errors.append(f"propertyDisjointWith hilang: {left} / {right}")
    for left, right in tbox.DATA_PROPERTY_DISJOINT:
        if (KBR[left], OWL.propertyDisjointWith, KBR[right]) not in graph:
            errors.append(f"propertyDisjointWith hilang: {left} / {right}")

    # Equivalent class.
    for name in tbox.EQUIVALENT_CLASSES:
        if not list(graph.objects(KBR[name[0]], OWL.equivalentClass)):
            errors.append(f"equivalentClass hilang: {name[0]}")
    for name in tbox.NOMINAL_CLASSES:
        if not list(graph.objects(KBR[name], OWL.equivalentClass)):
            errors.append(f"equivalentClass nominal hilang: {name}")
    for name in tbox.DISJOINT_UNIONS:
        if not list(graph.objects(KBR[name], OWL.equivalentClass)):
            errors.append(f"disjointUnionOf hilang: {name}")

    # Restriksi.
    for sub_cls, prop, target, quant in tbox.RESTRICTIONS:
        found = False
        for node in graph.objects(KBR[sub_cls], RDFS.subClassOf):
            if (node, OWL.onProperty, KBR[prop]) not in graph:
                continue
            if quant == "some" and (node, OWL.someValuesFrom, KBR[target]) in graph:
                found = True
            elif quant == "only" and (node, OWL.allValuesFrom, KBR[target]) in graph:
                found = True
            elif quant == "min1":
                for lit in graph.objects(node, OWL.minCardinality):
                    if (node, OWL.onClass, KBR[target]) in graph and int(lit) == 1:
                        found = True
        if not found:
            errors.append(f"restriction hilang: {sub_cls} {quant} {prop}")

    # Tidak ada punning.
    class_iris = set(graph.subjects(RDF.type, OWL.Class))
    individual_iris = set(graph.subjects(RDF.type, OWL.NamedIndividual))
    for iri in class_iris & individual_iris:
        errors.append(f"punning kelas/individu: {str(iri).rsplit('#', 1)[-1]}")

    # Tidak boleh assert eksplisit kelas penyakit hasil inferensi.
    for forbidden in (
        "PenyakitJamur", "PenyakitBakteri", "PenyakitVirus",
        "PenyakitNematoda", "PenyakitOomycete", "PenyakitFitoplasma",
        "PenyakitLainnya", "PenyakitRisiko",
        "PenyakitRisikoSuhuTinggi", "PenyakitRisikoKelembapanTinggi",
        "PenyakitRisikoMusimHujan",
    ):
        if list(graph.subjects(RDF.type, KBR[forbidden])):
            errors.append(f"{forbidden} tidak boleh di-assert eksplisit")

    if len(list(graph.subjects(RDF.type, tbox.SWRL.Imp))) != len(tbox.SWRL_RULES):
        errors.append("jumlah aturan SWRL tidak sesuai")

    # Tanaman harus tepat satu subkelas.
    plant_iris = set(graph.subjects(RDF.type, KBR["TanamanPangan"]))
    for plant in plant_iris:
        valid = [cls for cls in ("Serealia", "Legum", "UmbiUmbian") if (plant, RDF.type, KBR[cls]) in graph]
        if len(valid) != 1:
            errors.append(f"tanaman {str(plant).rsplit('#', 1)[-1]} tidak tepat satu subkelas")

    # Setiap penyakit punya tanaman, gejala, referensi.
    for disease in graph.subjects(RDF.type, KBR["Penyakit"]):
        local = str(disease).rsplit("#", 1)[-1]
        for prop in ("menyerangTanaman", "memilikiGejala", "memilikiReferensi"):
            if not list(graph.objects(disease, KBR[prop])):
                errors.append(f"penyakit {local} tanpa {prop}")

    # Faktor lingkungan harus punya nilai/tingkat/kondisi.
    for env in graph.subjects(RDF.type, KBR["FaktorLingkungan"]):
        local = str(env).rsplit("#", 1)[-1]
        has_value = any(
            list(graph.objects(env, KBR[prop]))
            for prop in ("nilaiMin", "nilaiMaks", "nilaiTunggal", "tingkat", "kondisi")
        )
        if not has_value:
            errors.append(f"faktor lingkungan {local} tanpa nilai/tingkat/kondisi")

    # Functional data property: maksimal satu nilai per subjek.
    for name, spec in tbox.DATA_PROPERTIES.items():
        if not spec.get("functional"):
            continue
        for subj in set(graph.subjects(KBR[name], None)):
            values = list(graph.objects(subj, KBR[name]))
            if len(values) > 1:
                errors.append(f"functional property {name} punya {len(values)} nilai pada {str(subj).rsplit('#', 1)[-1]}")

    return errors


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
    build_bagian_tanaman(builder)
    build_penyakit(builder, entries)
    build_patogen(builder, p_pairs, entries)
    build_gejala(builder, g_pairs, entries)
    build_menyerang_bagian(builder, bagian_pairs, entries)
    build_pengendalian(builder, c_pairs, ch_pairs, entries, report)
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
        "environment_individuals": len(report.get("environment", [])),
    }

    expected = counts(builder.graph)
    errors = validate(builder.graph, builder)
    report["counts"] = expected
    report["coverage"] = coverage(builder.graph, entries)
    report["schema_only_classes"] = sorted(
        name for name, count in expected["classes"].items() if count == 0
    )
    return builder.graph, expected, errors, builder, report


def coverage(graph: Graph, entries: list[dict[str, str]]) -> dict:
    diseases = list(graph.subjects(RDF.type, KBR["Penyakit"]))
    total = len(diseases) or 1

    def missing(prop: str) -> list[str]:
        return sorted(
            str(d).rsplit("#", 1)[-1]
            for d in diseases
            if not list(graph.objects(d, KBR[prop]))
        )

    def has_control(disease) -> bool:
        if list(graph.objects(disease, KBR["dikendalikanDengan"])):
            return True
        plant = next(graph.objects(disease, KBR["menyerangTanaman"]), None)
        return bool(plant is not None and list(graph.objects(plant, KBR["pengendalianUmum"])))

    return {
        "penyakit_total": len(diseases),
        "berDeskripsi": sum(1 for d in diseases if list(graph.objects(d, KBR["deskripsiPenyakit"]))),
        "berPatogen": sum(1 for d in diseases if list(graph.objects(d, KBR["disebabkanOleh"]))),
        "berGejala": sum(1 for d in diseases if list(graph.objects(d, KBR["memilikiGejala"]))),
        "berPengendalian": sum(1 for d in diseases if has_control(d)),
        "berFaktorLingkungan": sum(1 for d in diseases if list(graph.objects(d, KBR["dipengaruhiOleh"]))),
        "persenDeskripsi": round(100 * sum(1 for d in diseases if list(graph.objects(d, KBR["deskripsiPenyakit"]))) / total, 1),
        "persenPatogen": round(100 * sum(1 for d in diseases if list(graph.objects(d, KBR["disebabkanOleh"]))) / total, 1),
        "persenFaktorLingkungan": round(100 * sum(1 for d in diseases if list(graph.objects(d, KBR["dipengaruhiOleh"]))) / total, 1),
        "tanpaDeskripsi": missing("deskripsiPenyakit"),
        "tanpaPatogen": missing("disebabkanOleh"),
        "tanpaPengendalian": sorted(
            str(d).rsplit("#", 1)[-1] for d in diseases if not has_control(d)
        ),
        "tanpaFaktorLingkungan": missing("dipengaruhiOleh"),
    }


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
    individuals = expected["classes"]["NamedIndividual"]
    cls = expected["classes"]
    print(f"ontologi ditulis: {args.out} dan {owl_path}")
    print(f"laporan ekstraksi: {REPORT_PATH}")
    print(
        f"triple: {len(graph)} | individu: {individuals} | penyakit: {cls['Penyakit']} | "
        f"gejala: {cls['Gejala']} | patogen: {cls['Patogen']} | pengendalian: {cls['Pengendalian']} | "
        f"varietas: {cls['Varietas']} | fase: {cls['FasePertumbuhan']} | "
        f"faktor lingkungan: {cls['FaktorLingkungan']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
