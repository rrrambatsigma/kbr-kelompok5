"""Bangun tabel patogen, gejala, dan pengendalian (Blok B & C, Tahap 2.3-2.4).

Input read-only:
- ``02_extraction/extracted_text/DOC002.chunks.jsonl``
- ``03_knowledge_tables/curated/diseases.csv``
- ``03_knowledge_tables/auto/ubi_kayu_table_rows.csv``

Output ke ``auto/``:
- ``pathogens.csv``, ``disease_pathogen.csv``
- ``symptoms.csv``, ``controls.csv``
- ``review/pathogen_candidates.csv`` untuk kurasi manual

Aturan:
- Kalimat disimpan utuh beserta offset pada teks chunk yang spasinya dinormalisasi.
- Kandidat patogen hanya diambil dari bagian "Penyebab/Patogen" atau kalimat
  yang menyebut hubungan sebab-akibat, tidak dari bagian pengendalian.
- Kandidat yang tidak dapat dipastikan diberi ``needs_review``, bukan dibuang
  diam-diam.

Jalankan: ``python 03_knowledge_tables/build_extended_tables.py``
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

TABLE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TABLE_DIR.parent
EXTRACTION_DIR = PROJECT_ROOT / "02_extraction" / "extracted_text"
CHUNKS_PATH = EXTRACTION_DIR / "DOC002.chunks.jsonl"

AUTO_DIR = TABLE_DIR / "auto"
CURATED_DIR = TABLE_DIR / "curated"
REVIEW_DIR = TABLE_DIR / "review"
REPORTS_DIR = TABLE_DIR / "reports"

NUMBERING_RE = re.compile(r"^\s*\d+(?:\.\d+)*\.?\s*")
WS_RE = re.compile(r"\s+")
SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+|(?<=;)\s+(?=[A-Z])")

# Kalimat yang menyatakan hubungan sebab-akibat secara tegas.
STRONG_PATHOGEN_RE = re.compile(
    r"disebabkan oleh|penyebab penyakit|patogen penyebab|menginfeksi|disebabkan|"
    r"menyebabkan penyakit|patogen yang menyebabkan",
    re.IGNORECASE,
)
# Nama genus yang muncul langsung setelah kata penanda takson.
GENUS_AFTER_CUE_RE = re.compile(
    r"(?:disebabkan oleh|patogen penyebab|penyebab penyakit|"
    r"patogen yang menyebabkan)\s+"
    r"(?:(?:patogen|jamur|cendawan|bakteri|nematoda|virus|fitoplasma)\s+)?"
    r"([A-Z][a-z]{3,})\b"
)
PATHOGEN_CUE_RE = re.compile(
    r"disebabkan oleh|penyebab penyakit|patogen penyebab|menginfeksi|"
    r"penyebab utama|disebabkan|patogen",
    re.IGNORECASE,
)
# Kalimat yang membicarakan agen pengendali hayati, bukan patogen.
BIOCONTROL_RE = re.compile(
    r"antagonis|agens hayati|pengendali hayati|biokontrol|musuh alami",
    re.IGNORECASE,
)
# Kalimat yang membicarakan vektor serangga, bukan patogen.
VECTOR_RE = re.compile(
    r"\bwereng\b|\bvektor\b|\bthrips\b|\baphid\b|\bkutu\b",
    re.IGNORECASE,
)
SYMPTOM_CUE_RE = re.compile(
    r"gejala|tanda|serangan|lesi|nekrosis|bercak|layu|menguning|klorosis|"
    r"mosaik|kerdil|pucat|mengering|membusuk|busuk|mati",
    re.IGNORECASE,
)
CONTROL_CUE_RE = re.compile(
    r"pengendalian|dikendalikan|mengendalikan|sanitasi|fungisida|bakterisida|"
    r"insektisida|varietas tahan|rotasi|eradikasi|pemangkasan|pergiliran|"
    r"benih sehat|pencegahan|karantina|menekan|aplikasi|penggunaan",
    re.IGNORECASE,
)

# Kata pertama yang bukan nama genus.
STOP_FIRST = {
    "Penyakit", "Penyebab", "Patogen", "Gejala", "Bakteri", "Jamur", "Cendawan",
    "Virus", "Nematoda", "Pengendalian", "Pada", "Selain", "Tanaman", "Beberapa",
    "Disebabkan", "Indonesia", "Infeksi", "Daun", "Layu", "Perkembangan", "Spora",
    "Serangan", "Akibat", "Penularan", "Serangga", "Upaya", "Kehilangan",
    "Kemudian", "Hasil", "Aplikasi", "Secara", "Kedelai", "Penanaman", "Belang",
    "Penyebaran", "Umumnya", "Vector", "Vektor", "Stadium", "Penggunaan",
    "Bercak", "Suhu", "Siklus", "Kecil", "Miselium", "Pemberian", "Ketika",
    "Konidia", "Akan", "Busuk", "Bagian", "Identifikasi", "Fenomena",
    "Aktivitas", "Koloni", "Kultur", "Perlakuan", "Rice", "Kedua", "Dalam",
    "Rumput", "Pemanfaatan", "Kondisi", "Downy", "Antraknosa", "Polong", "Benih",
    "Melengkung", "Memucat", "Malformasi", "Peanut", "Dengan", "Namun",
    "Spesies", "Informasi", "Jika", "Kejadian", "Salah", "Kutu", "Buah", "Bean",
    "Setelah", "Meskipun", "Arabika", "Berbagai", "Terdapat", "Untuk", "Tubuh",
    "Adanya", "Sklerotia", "Memiliki", "Kecambah", "Rizobakteri", "Hampir",
    "Image", "Spores", "Pathogen", "Cycle", "Menginfeksi", "Edamame", "Tahapan",
    "Secondary", "Ungu", "Menghilangkan", "Oleh", "Sporulasi", "Inang",
    "Kurangnya", "Mikroorganisme", "Pestisida", "Aphids", "Tetapi", "Kisaran",
    "Terdapatnya", "Kacang", "Gram", "Gulma", "Sering", "Sumber", "Adapun",
    "Sedangkan", "Keparahan", "Tingginya", "Corn", "Rizobakteria", "Isolat",
    "Faktor", "Populasi", "Cara", "Perlu", "Kentang", "Jenis", "Perakaran",
    "Umbi", "Sista", "Keberadaan", "Belum", "Jaringan", "Pengamatan", "Apabila",
    "Oomycetes", "Angin", "Hifa", "Karena", "Sehingga", "Berdasarkan", "Media",
    "Isolasi", "Cucumber", "Tobacco", "Pepper", "Aphid", "Thrips", "Merupakan",
    "Semua", "Mungkin", "Selanjutnya", "Tidak", "Akar", "Plants", "Closely",
    "Field", "Selama", "Settling", "Transmission", "Proses", "Kanidia", "Mildew",
    "Membersihkan", "Batang", "Kombinasi", "Mikroba", "Penampang", "Memanen",
    "Melaksanakan", "Ketersediaan", "Teknik", "Ketiganya", "Sebagai", "Luka",
    "Tanah", "Pencegahan", "Sistem", "Mekanisme", "Inokulasi", "Bahkan",
    "Oomycete", "Kerugian", "Banyak", "Strategi", "Agen", "Inayati", "Saleh",
    "Damayanti", "Hernandez", "Barahima", "Kumar", "Mizukami", "Budiman",
    "Muhsin", "Fitria", "Hidayah", "Oyetunde", "Anjasmoro", "Mahameru",
    "Nurdika", "Andayani", "Clark", "Suastika", "Mukasa", "Kennedy", "Cooper",
    "Mogoro", "Desi", "Tuhumury", "Rahayu", "Amadioha", "Mensah",
    "Roselina", "Murill", "Chairin", "Mubarik", "Nugini", "Sudharto", "Jepang",
    "Xoo", "Xoc", "Sweet", "Fungi", "Kemampuan", "Cruciferae", "Nilaparvata",
    "Glischrochilus", "Bemisia", "Myzus", "Aphis",
}

# Kata kedua yang bukan epithet spesies.
STOP_SECOND = {
    "and", "et", "al", "dan", "atau", "ini", "itu", "yang", "pada", "dari",
    "dapat", "tidak", "juga", "akan", "telah", "masih", "lebih", "sangat",
    "sering", "dengan", "untuk", "oleh", "dalam", "di", "ke", "sebagai",
    "merupakan", "menjadi", "tersebut", "adalah", "penyakit", "bercak", "busuk",
    "layu", "karat", "daun", "buah", "akar", "batang", "umbi", "benih",
    "tanaman", "jamur", "bakteri", "virus", "patogen", "gejala", "serangan",
    "infeksi", "tanah", "air", "suhu", "kelembaban", "varietas", "hasil",
    "produksi", "hama", "kutu", "wereng", "vektor", "inang", "bibit", "lahan",
    "pupuk", "pestisida", "fungisida", "terhadap", "seperti", "karena", "yaitu",
    "merupakan", "spp", "sp", "kau", "nya", "berupa", "mempunyai", "dikenal",
    "lainnya", "setiap", "lain", "ditemukan", "memiliki", "dilakukan",
    "digunakan", "menyebabkan", "menyerang", "masih", "hanya", "sudah", "telah",
    "belum", "paling", "serta", "hingga", "sampai", "sehingga", "tetapi",
    "namun", "sedangkan", "yakni", "pertama", "kedua", "ketiga",
}

BINOMIAL_RE = re.compile(r"\b([A-Z][a-z]{2,})\s+([a-z]{3,}|[Ss]p\.|[Ss]pp\.)")
VIRUS_RE = re.compile(
    r"\b(?:[A-Z][A-Za-z-]+\s+){1,4}Virus(?:\s+[A-Z0-9]{1,2})?\b"
    r"|\b[A-Z][a-z]+\s+(?:[a-z-]+\s+){0,3}virus\b"
)
VIRUS_STOP_FIRST = {
    "Penyakit", "Patogen", "Kedua", "Beberapa", "Jenis", "Infeksi", "Vektor",
    "Mosaik", "Tanaman", "Daun", "Gejala", "Serangan", "Virus", "Pada",
    "Hal", "Selain", "Identifikasi", "Penggunaan", "Penularan",
}
VIRUS_GENERIC = {"sweet potato virus", "potato virus"}
GENERIC_TABLE_PATHOGEN = {"jamur", "fungi", "fungi/jamur"}

TAXON_CUES = [
    ("fitoplasma", re.compile(r"fitoplasma", re.IGNORECASE)),
    ("virus", re.compile(r"\bvirus\b", re.IGNORECASE)),
    ("bakteri", re.compile(r"bakteri", re.IGNORECASE)),
    ("nematoda", re.compile(r"nematoda", re.IGNORECASE)),
    ("oomycete", re.compile(r"oomycete", re.IGNORECASE)),
    ("jamur", re.compile(r"\bjamur\b|cendawan", re.IGNORECASE)),
]

PATHOGEN_COLUMNS = [
    "pathogen_id",
    "scientific_name",
    "taxon_group",
    "verbatim_text",
    "page",
    "chunk_id",
    "review_status",
]

DISEASE_PATHOGEN_COLUMNS = [
    "disease_id",
    "pathogen_id",
    "evidence_chunk_id",
    "relation_note",
    "review_status",
]

SYMPTOM_COLUMNS = [
    "symptom_id",
    "disease_id",
    "plant_id",
    "verbatim_text",
    "chunk_id",
    "page_start",
    "page_end",
    "char_start",
    "char_end",
    "review_status",
]

CONTROL_COLUMNS = [
    "control_id",
    "disease_id",
    "plant_id",
    "verbatim_text",
    "chunk_id",
    "page_start",
    "page_end",
    "char_start",
    "char_end",
    "control_category",
    "scope",
    "review_status",
]


def norm(text: Any) -> str:
    return WS_RE.sub(" ", str(text or "")).strip()


def strip_numbering(text: str) -> str:
    return NUMBERING_RE.sub("", str(text or "")).strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column) for column in columns})


def component(chunk: dict[str, Any]) -> str:
    """Tentukan peran chunk di dalam satu penyakit."""

    sub = (chunk.get("subsection") or "").lower()
    kind = chunk.get("chunk_type") or ""
    if kind == "control" or "pengendalian" in sub:
        return "control"
    if kind == "symptoms" or "gejala" in sub:
        return "symptoms"
    if kind == "pathogen" or "penyebab" in sub or "patogen" in sub:
        return "pathogen"

    # Sebagian bab memakai heading generik di dalam teks, bukan di metadata.
    head = norm(chunk.get("plain_text"))[:70].lower()
    if re.match(r"^(pengendalian|pengelolaan)\b", head):
        return "control"
    if re.match(r"^(gejala|tanda)\b", head):
        return "symptoms"
    if re.match(r"^(penyebab|patogen)\b", head):
        return "pathogen"
    return "overview"


def strip_heading(text: str, chunk: dict[str, Any]) -> str:
    """Buang heading yang menempel di awal teks chunk."""

    for field in ("subsection", "section"):
        heading = chunk.get(field)
        if heading and text.startswith(heading):
            text = text[len(heading) :]
            break
    return text.strip()


def sentences(text: str) -> list[tuple[int, int]]:
    """Kembalikan rentang kalimat pada teks yang sudah dinormalisasi."""

    spans: list[tuple[int, int]] = []
    start = 0
    for match in SENTENCE_END_RE.finditer(text):
        end = match.start()
        if end > start:
            spans.append((start, end))
        start = match.end()
    if start < len(text):
        spans.append((start, len(text)))
    return spans


def scope_chunks(
    disease: dict[str, str], chunks: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Ambil chunk milik satu penyakit.

    Cakupan ditentukan dengan berjalan menurut urutan dokumen: mulai dari chunk
    heading penyakit, berhenti tepat sebelum heading penyakit berikutnya. Cara ini
    menangani bab yang memakai subbab generik ("Penyebab", "Gejala") di dalam
    sebuah penyakit.
    """

    chapter_items = [
        chunk for chunk in chunks if chunk.get("chapter") == disease["chapter_title"]
    ]
    target = strip_numbering(
        disease["subsection"]
        if disease["heading_level"] == "subsection"
        else disease["section"]
    )

    def key(chunk: dict[str, Any]) -> str:
        field = (
            "subsection"
            if disease["heading_level"] == "subsection"
            else "section"
        )
        return strip_numbering(chunk.get(field) or "")

    starts = [index for index, chunk in enumerate(chapter_items) if key(chunk) == target]
    if not starts:
        return []

    # Heading penyakit lain di bab yang sama menjadi batas akhir.
    other_starts = sorted(
        index
        for index, chunk in enumerate(chapter_items)
        if key(chunk)
        and key(chunk) != target
        and re.match(r"^\d+\.\d+", chunk.get(
            "subsection" if disease["heading_level"] == "subsection" else "section"
        ) or "")
    )
    begin = starts[0]
    ends = [index for index in other_starts if index > begin]
    end = ends[0] if ends else len(chapter_items)
    scoped = [
        chunk
        for chunk in chapter_items[begin:end]
        if chunk.get("chunk_type") not in {"figure_caption", "reference", "table"}
    ]
    return scoped


def classify_taxon(text: str) -> str:
    for name, pattern in TAXON_CUES:
        if pattern.search(text):
            return name
    return "unknown"


def is_candidate(first: str, second: str) -> bool:
    if first in STOP_FIRST:
        return False
    if second.lower() in {"sp", "spp"}:
        return True
    if second in STOP_SECOND:
        return False
    if second[:1].isupper():
        return False
    return True


def clean_table_pathogen(value: str) -> list[str]:
    """Pisahkan patogen pada satu sel tabel menjadi nama-nama terpisah."""

    value = value.replace("*", "")
    value = re.sub(r"\([^()]*\d{4}[^()]*\)", " ", value)
    parts = re.split(r"\s*(?:,|;|\batau\b|\bdan\b)\s*", value)
    names: list[str] = []
    for part in parts:
        part = norm(part)
        part = re.sub(r"\s*\.$", "", part)
        if len(part) < 4:
            continue
        if part.lower() in {"spp", "sp", "jamur", "fungi"}:
            continue
        names.append(part)
    return names


def build_pathogens(
    diseases: list[dict[str, str]],
    chunks: list[dict[str, Any]],
    table_rows: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    key_to_id: dict[str, str] = {}

    def pathogen_id(name: str, taxon: str, page: Any, chunk_id: str) -> str:
        key = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
        if key not in key_to_id:
            pid = f"PAT_{len(key_to_id) + 1:03d}"
            key_to_id[key] = pid
            rows.append(
                {
                    "pathogen_id": pid,
                    "scientific_name": name,
                    "taxon_group": taxon,
                    "verbatim_text": name,
                    "page": page,
                    "chunk_id": chunk_id,
                    "review_status": "auto_ok" if taxon != "unknown" else "needs_review",
                }
            )
        elif taxon != "unknown":
            for row in rows:
                if row["pathogen_id"] == key_to_id[key] and row["taxon_group"] == "unknown":
                    row["taxon_group"] = taxon
        return key_to_id[key]

    for disease in diseases:
        if disease["heading_level"] == "table":
            continue
        scoped = scope_chunks(disease, chunks)
        seen: set[str] = set()
        for chunk in scoped:
            comp = component(chunk)
            if comp == "control":
                continue
            text = strip_heading(norm(chunk["plain_text"]), chunk)
            for start, end in sentences(text):
                sentence = text[start:end]
                if len(sentence) < 30:
                    continue
                if comp != "pathogen" and not STRONG_PATHOGEN_RE.search(sentence):
                    continue
                reason = ""
                if BIOCONTROL_RE.search(sentence):
                    reason = "kalimat menyebut agens pengendali hayati"
                elif VECTOR_RE.search(sentence):
                    reason = "kalimat menyebut vektor serangga"

                names: list[str] = []
                strong = bool(STRONG_PATHOGEN_RE.search(sentence))
                control_sentence = bool(CONTROL_CUE_RE.search(sentence))
                binomial_ok = (
                    comp == "pathogen" and not (control_sentence and not strong)
                ) or (comp != "pathogen" and strong and not control_sentence)
                if binomial_ok:
                    for match in BINOMIAL_RE.finditer(sentence):
                        if is_candidate(
                            match.group(1), match.group(2).rstrip(".")
                        ):
                            names.append(match.group(0).rstrip("."))
                for match in GENUS_AFTER_CUE_RE.finditer(sentence):
                    # Kalau kalimat memuat nama virus lengkap, jangan ambil
                    # kata pertama nama virus sebagai genus.
                    if VIRUS_RE.search(sentence):
                        continue
                    genus = match.group(1)
                    if genus in STOP_FIRST:
                        continue
                    # Jangan duplikasi genus yang sudah tercakup binomial.
                    if any(name.lower().startswith(genus.lower() + " ") for name in names):
                        continue
                    names.append(genus)
                for match in VIRUS_RE.finditer(sentence):
                    name = norm(match.group(0)).rstrip(".,;")
                    head = name.split()[0]
                    if head in VIRUS_STOP_FIRST:
                        continue
                    if name.lower() in VIRUS_GENERIC:
                        continue
                    names.append(name)

                for name in names:
                    first = name.split()[0]
                    second = name.split()[1] if len(name.split()) > 1 else ""
                    if name.lower() in seen:
                        continue
                    seen.add(name.lower())
                    if reason:
                        candidates.append(
                            {
                                "disease_id": disease["disease_id"],
                                "disease_name": disease["disease_name_verbatim"],
                                "candidate": name,
                                "taxon_cue": classify_taxon(sentence),
                                "page": chunk["page_start"],
                                "chunk_id": chunk["chunk_id"],
                                "component": comp,
                                "sentence": sentence[:300],
                                "status": "rejected",
                                "reason": reason,
                            }
                        )
                        continue
                    taxon = classify_taxon(sentence)
                    if taxon == "unknown":
                        # Heading subbab/bab kadang menyebut kelompok patogen,
                        # mis. "Penyakit Kedelai Oleh Jamur".
                        taxon = classify_taxon(
                            norm(chunk.get("subsection") or "")
                        )
                    if taxon == "unknown":
                        taxon = classify_taxon(norm(chunk.get("section") or ""))
                    if taxon == "unknown":
                        taxon = classify_taxon(norm(chunk["plain_text"]))
                    pid = pathogen_id(
                        name, taxon, chunk["page_start"], chunk["chunk_id"]
                    )
                    link_status = "auto_ok" if taxon != "unknown" else "needs_review"
                    links.append(
                        {
                            "disease_id": disease["disease_id"],
                            "pathogen_id": pid,
                            "evidence_chunk_id": chunk["chunk_id"],
                            "relation_note": sentence[:240],
                            "review_status": link_status,
                        }
                    )
                    candidates.append(
                        {
                            "disease_id": disease["disease_id"],
                            "disease_name": disease["disease_name_verbatim"],
                            "candidate": name,
                            "taxon_cue": taxon,
                            "page": chunk["page_start"],
                            "chunk_id": chunk["chunk_id"],
                            "component": comp,
                            "sentence": sentence[:300],
                            "status": "accepted",
                            "reason": "",
                        }
                    )

        # Heading bab yang memang berisi nama patogen (Bab 4, 6, 7, 15).
        heading = (
            disease["section"]
            if disease["heading_level"] == "section"
            else disease["subsection"]
        )
        heading = strip_numbering(heading or "")
        heading_names: list[str] = []
        for match in BINOMIAL_RE.finditer(heading):
            if is_candidate(match.group(1), match.group(2).rstrip(".")):
                heading_names.append(match.group(0).rstrip("."))
        for match in VIRUS_RE.finditer(heading):
            name = norm(match.group(0)).rstrip(".,;")
            if name.split()[0] not in VIRUS_STOP_FIRST:
                heading_names.append(name)
        for name in heading_names:
            if name.lower() in seen:
                continue
            seen.add(name.lower())
            taxon = classify_taxon(heading)
            pid = pathogen_id(name, taxon, disease["page_start"], "")
            links.append(
                {
                    "disease_id": disease["disease_id"],
                    "pathogen_id": pid,
                    "evidence_chunk_id": "",
                    "relation_note": f"heading {disease['heading_level']}: {heading}",
                    "review_status": "needs_review",
                }
            )
            candidates.append(
                {
                    "disease_id": disease["disease_id"],
                    "disease_name": disease["disease_name_verbatim"],
                    "candidate": name,
                    "taxon_cue": taxon,
                    "page": disease["page_start"],
                    "chunk_id": "",
                    "component": "heading",
                    "sentence": heading[:300],
                    "status": "accepted",
                    "reason": "nama patogen pada heading",
                }
            )

    # Penyakit dari tabel ubi kayu: patogen sudah berupa sel terstruktur.
    # Kunci memakai (table_id, nama penyakit) karena nama penyakit bisa sama
    # di tabel berbeda (mis. "Antraknosa" pada daun dan batang).
    table_by_disease: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in table_rows:
        if row["status"] == "missing_row":
            continue
        table_by_disease.setdefault(
            (row["table_id"], row["disease_name"]), []
        ).append(row)

    for disease in diseases:
        if disease["heading_level"] != "table":
            continue
        key = (disease["section"], disease["disease_name_verbatim"])
        for table_row in table_by_disease.get(key, []):
            for name in clean_table_pathogen(table_row["pathogen_name"]):
                if name.lower() in GENERIC_TABLE_PATHOGEN:
                    continue
                taxon = classify_taxon(table_row["pathogen_name"])
                pid = pathogen_id(name, taxon, table_row["page"], "")
                links.append(
                    {
                        "disease_id": disease["disease_id"],
                        "pathogen_id": pid,
                        "evidence_chunk_id": "",
                        "relation_note": f"sel tabel {table_row['table_id']} baris {table_row['row_no']}",
                        "review_status": "needs_review",
                    }
                )
                candidates.append(
                    {
                        "disease_id": disease["disease_id"],
                        "disease_name": disease["disease_name_verbatim"],
                        "candidate": name,
                        "taxon_cue": taxon,
                        "page": table_row["page"],
                        "chunk_id": table_row["source_block_id"],
                        "component": "table",
                        "sentence": table_row["pathogen_name"][:300],
                        "status": "accepted",
                        "reason": "sel tabel",
                    }
                )

    # Buang nama genus jika penyakit yang sama sudah punya nama spesies
    # dengan genus tersebut (mis. "Ganoderma" vs "Ganoderma boninense").
    by_id = {row["pathogen_id"]: row for row in rows}
    binomial_genera: dict[str, set[str]] = {}
    for link in links:
        name = by_id[link["pathogen_id"]]["scientific_name"]
        if " " in name:
            binomial_genera.setdefault(link["disease_id"], set()).add(
                name.split()[0].lower()
            )
    links = [
        link
        for link in links
        if " " in by_id[link["pathogen_id"]]["scientific_name"]
        or by_id[link["pathogen_id"]]["scientific_name"].lower()
        not in binomial_genera.get(link["disease_id"], set())
    ]
    linked_ids = {link["pathogen_id"] for link in links}
    rows = [row for row in rows if row["pathogen_id"] in linked_ids]

    # Penomoran ulang agar tetap berurutan setelah penyaringan.
    renumber = {
        row["pathogen_id"]: f"PAT_{index:03d}"
        for index, row in enumerate(rows, start=1)
    }
    for row in rows:
        row["pathogen_id"] = renumber[row["pathogen_id"]]
    for link in links:
        link["pathogen_id"] = renumber[link["pathogen_id"]]

    return rows, links, candidates


def build_sentences(
    diseases: list[dict[str, str]],
    chunks: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    symptoms: list[dict[str, Any]] = []
    controls: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []

    scoped_by_disease: dict[str, list[dict[str, Any]]] = {}
    for disease in diseases:
        if disease["heading_level"] == "table":
            continue
        scoped_by_disease[disease["disease_id"]] = scope_chunks(disease, chunks)

    for disease in diseases:
        if disease["heading_level"] == "table":
            continue
        scoped = scoped_by_disease[disease["disease_id"]]
        has_symptom_block = any(component(c) == "symptoms" for c in scoped)
        has_control_block = any(component(c) == "control" for c in scoped)
        seen: set[str] = set()

        for chunk in scoped:
            comp = component(chunk)
            text = norm(chunk["plain_text"])
            body = strip_heading(text, chunk)
            base = text.find(body)
            for start, end in sentences(body):
                sentence = body[start:end]
                sentence_clean = norm(sentence)
                if len(sentence_clean) < 40:
                    continue
                if re.match(r"^\(?\w+[^()]{0,30}\d{4}\)?\.?$", sentence_clean):
                    continue
                if sentence_clean.lower() in seen:
                    continue
                if "---" in sentence_clean:
                    continue
                has_sym = bool(SYMPTOM_CUE_RE.search(sentence_clean))
                has_ctl = bool(CONTROL_CUE_RE.search(sentence_clean))
                is_symptom = False
                is_control = False
                if comp == "symptoms":
                    if has_ctl and not has_sym:
                        is_control = True
                    else:
                        is_symptom = True
                elif comp == "control":
                    is_control = True
                else:
                    if has_sym and has_ctl:
                        ambiguous.append(
                            {
                                "disease_id": disease["disease_id"],
                                "chunk_id": chunk["chunk_id"],
                                "sentence": sentence_clean,
                            }
                        )
                    elif not has_symptom_block and has_sym:
                        is_symptom = True
                    elif not has_control_block and has_ctl:
                        is_control = True
                if is_symptom and is_control:
                    ambiguous.append(
                        {
                            "disease_id": disease["disease_id"],
                            "chunk_id": chunk["chunk_id"],
                            "sentence": sentence_clean,
                        }
                    )
                    is_symptom = False
                if not is_symptom and not is_control:
                    continue
                seen.add(sentence_clean.lower())
                offset = base + start if base >= 0 else start
                row = {
                    "disease_id": disease["disease_id"],
                    "plant_id": disease["plant_id"],
                    "verbatim_text": sentence_clean,
                    "chunk_id": chunk["chunk_id"],
                    "page_start": chunk["page_start"],
                    "page_end": chunk["page_start"],
                    "char_start": offset,
                    "char_end": offset + len(sentence_clean),
                    "review_status": "auto_ok",
                }
                if is_symptom:
                    symptoms.append(row)
                else:
                    row = dict(row)
                    row["control_category"] = ""
                    row["scope"] = "disease"
                    controls.append(row)

    # Pengendalian tingkat bab: heading pengendalian yang tidak berada di bawah penyakit.
    for chunk in chunks:
        if chunk.get("chunk_type") != "control":
            continue
        section = strip_numbering(chunk.get("section") or "")
        if not re.search(r"pengendalian", section, re.IGNORECASE):
            continue
        chapter = chunk.get("chapter") or ""
        plant_id = next(
            (
                d["plant_id"]
                for d in diseases
                if d["chapter_title"] == chapter
            ),
            "",
        )
        text = norm(chunk["plain_text"])
        body = strip_heading(text, chunk)
        base = text.find(body)
        for start, end in sentences(body):
            sentence = norm(body[start:end])
            if len(sentence) < 40:
                continue
            offset = base + start if base >= 0 else start
            controls.append(
                {
                    "disease_id": "",
                    "plant_id": plant_id,
                    "verbatim_text": sentence,
                    "chunk_id": chunk["chunk_id"],
                    "page_start": chunk["page_start"],
                    "page_end": chunk["page_start"],
                    "char_start": offset,
                    "char_end": offset + len(sentence),
                    "control_category": "",
                    "scope": "chapter",
                    "review_status": "auto_ok",
                }
            )

    for index, row in enumerate(symptoms, start=1):
        row["symptom_id"] = f"SYM_{index:03d}"
    for index, row in enumerate(controls, start=1):
        row["control_id"] = f"CTL_{index:03d}"
    return symptoms, controls, ambiguous


def main() -> int:
    chunks = read_jsonl(CHUNKS_PATH)
    diseases = read_csv(CURATED_DIR / "diseases.csv")
    table_rows = read_csv(AUTO_DIR / "ubi_kayu_table_rows.csv")

    pathogens, links, candidates = build_pathogens(diseases, chunks, table_rows)
    symptoms, controls, ambiguous = build_sentences(diseases, chunks)

    write_csv(AUTO_DIR / "pathogens.csv", pathogens, PATHOGEN_COLUMNS)
    write_csv(AUTO_DIR / "disease_pathogen.csv", links, DISEASE_PATHOGEN_COLUMNS)
    write_csv(AUTO_DIR / "symptoms.csv", symptoms, SYMPTOM_COLUMNS)
    write_csv(AUTO_DIR / "controls.csv", controls, CONTROL_COLUMNS)
    write_csv(
        REVIEW_DIR / "pathogen_candidates.csv",
        candidates,
        [
            "disease_id",
            "disease_name",
            "candidate",
            "taxon_cue",
            "page",
            "chunk_id",
            "component",
            "sentence",
            "status",
            "reason",
        ],
    )
    write_csv(
        REVIEW_DIR / "ambiguous_sentences.csv",
        ambiguous,
        ["disease_id", "chunk_id", "sentence"],
    )

    diseases_with_pathogen = len({link["disease_id"] for link in links})
    with_symptom = len({row["disease_id"] for row in symptoms})
    with_control = len({row["disease_id"] for row in controls if row["disease_id"]})
    report = {
        "generated_by": "build_extended_tables.py",
        "pathogen_rows": len(pathogens),
        "disease_pathogen_rows": len(links),
        "pathogen_candidates": len(candidates),
        "diseases_with_pathogen": diseases_with_pathogen,
        "symptom_rows": len(symptoms),
        "diseases_with_symptom": with_symptom,
        "control_rows": len(controls),
        "control_rows_chapter_scope": sum(
            1 for row in controls if row["scope"] == "chapter"
        ),
        "diseases_with_control": with_control,
        "ambiguous_sentences": len(ambiguous),
        "taxon_groups": dict(Counter(row["taxon_group"] for row in pathogens)),
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "extended_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
