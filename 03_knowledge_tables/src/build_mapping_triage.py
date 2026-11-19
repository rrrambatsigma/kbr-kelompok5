"""Triage record gejala/pengendalian yang belum dipetakan.

Laporan ini memisahkan gap nyata (butuh konsep baru) dari duplikat/parafrase,
noise non-gejala/non-tindakan, dan kasus ambigu yang perlu review manual.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

TABLE_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = TABLE_DIR.parent
ONTO_DIR = PROJECT_ROOT / "04_ontology"
sys.path.insert(0, str(ONTO_DIR))

import build_ontology as bo  # noqa: E402

OUTPUT_MD = TABLE_DIR / "reports" / "MAPPING_TRIAGE.md"
OUTPUT_JSON = TABLE_DIR / "reports" / "MAPPING_TRIAGE.json"

SYMPTOM_CORE_RE = re.compile(
    r"\b(bercak|noda|lesi|lesio|bintik|pustul|tepung|belang|mosaik|kuning|"
    r"klorosis|klorotik|nekrotik|nekrosis|kering|rontok|gugur|patah|"
    r"menggulung|keriput|abnormal|deformasi|kanker|lekukan|halo|cincin|"
    r"busuk|membusuk|mati|kematian|kerdil|malai|layu|hawar|kresek|"
    r"berlubang|pemanjangan|ruas|tipis|lemah|tidak\s+tumbuh\s+normal)\b",
    re.I,
)
SYMPTOM_NOISE_RE = re.compile(
    r"\b(patogen|jamur|bakteri|virus|cendawan|inokulum|konidia|spora|"
    r"miselium|hifa|uredia|suhu|kelembapan|kelembaban|tanah|musim|"
    r"lingkungan|cahaya|angin|hujan|pengendalian|dikendalikan|varietas|"
    r"benih|mulsa|fungisida|bakterisida|insektisida|sanitasi|rotasi|"
    r"panen|penyimpanan|gambar|tabel|penelitian|menurut|dilaporkan|"
    r"sumber|halaman|fotosintesis)\b",
    re.I,
)
SYMPTOM_META_RE = re.compile(
    r"\b(gambar|tabel|penelitian|menurut|dilaporkan|sumber|halaman|"
    r"sama dengan|tidak berbeda|dibandingkan|fotosintesis)\b",
    re.I,
)
CONTROL_CORE_RE = re.compile(
    r"\b(gunakan|menggunakan|aplikasi|aplikasikan|tanam|menanam|beri|memberi|"
    r"atur|mengatur|pilih|memilih|bersihkan|membersihkan|bakar|membakar|"
    r"kumpulkan|mengumpulkan|cabut|mencabut|semprot|menyemprot|rendam|"
    r"merendam|perlakukan|perlakuan|kendalikan|mengendalikan|cegah|mencegah|"
    r"kurangi|mengurangi|tekan|menekan|hindari|menghindari|lakukan|dilakukan|"
    r"terapkan|menerapkan|seleksi|karantina|panen|simpan|penyimpanan|"
    r"sanitasi|rotasi|pergiliran|mulsa|pemupukan|pengairan|drainase|"
    r"pemangkasan|penjarangan|pengelolaan|pengendalian)\b",
    re.I,
)
CONTROL_KNOWN_RE = re.compile(
    r"\b(varietas|kultivar|benih|sanitasi|rotasi|pergiliran|mulsa|"
    r"jarak\s+tanam|pemupukan|pengairan|drainase|fungisida|bakterisida|"
    r"insektisida|herbisida|pestisida|nabati|agens\s+hayati|antagonis|"
    r"trichoderma|harzianum|bacillus|subtilis|pseudomonas|fluorescens|"
    r"pgpr|rizobakteri|biopestisida|ekstrak|kultur\s+meristem|"
    r"penyimpanan|panen|karantina|pemangkasan)\b",
    re.I,
)
CONTROL_NOISE_RE = re.compile(
    r"\b(penelitian|hasil|menurut|dilaporkan|menunjukkan|gambar|tabel|"
    r"mikroskopis|koloni|media|isolat|uji|diuji|ketahanan|kerentanan)\b",
    re.I,
)
GENERIC_FRAGMENT_RE = re.compile(r"^(?:[a-z]\.|[a-z]\)|dan|atau|serta|yang|pada)\b", re.I)


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def symptom_class(text: str) -> tuple[str, str]:
    low = norm(text).lower()
    core = SYMPTOM_CORE_RE.search(low)
    noise = SYMPTOM_NOISE_RE.search(low)
    meta = SYMPTOM_META_RE.search(low)
    if core and not meta:
        if re.search(r"bercak|noda|lesi|lesio|bintik|pustul", low):
            return "duplikat_parafrase", "Sudah ada konsep BercakDaun; perlu relaksasi sinonim."
        if re.search(r"tepung|belang|mosaik", low):
            return "butuh_konsep_baru", "Pola tepung/belang berulang belum punya konsep kanonik."
        if re.search(r"kuning|klorosis|klorotik|nekrotik|nekrosis", low):
            return "butuh_konsep_baru", "Perlu konsep klorosis/nekrosis yang menampung variasi kalimat."
        if re.search(r"kering|rontok|gugur", low):
            return "butuh_konsep_baru", "Gejala daun kering/rontok berulang dan layak dinormalisasi."
        if re.search(r"busuk|membusuk", low):
            return "butuh_konsep_baru", "Busuk tanpa bagian tanaman perlu konsep generik."
        if re.search(r"patah|malai", low):
            return "butuh_konsep_baru", "Malai patah/empty perlu konsep terpisah dari malai kosong."
        if re.search(r"pemanjangan|ruas|tipis|lemah|tidak\s+tumbuh\s+normal|kematian", low):
            return "butuh_konsep_baru", "Gejala pertumbuhan/kematian perlu konsep generik."
        return "butuh_konsep_baru", "Gejala nyata belum masuk kosakata kanonik."
    if noise or meta:
        return "bukan_gejala", "Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala."
    if len(re.sub(r"[^0-9A-Za-z]", "", text)) < 35:
        return "ambigu", "Fragmen terlalu pendek; perlu konteks halaman."
    return "ambigu", "Tidak ada pola gejala yang cukup jelas."


def control_class(text: str) -> tuple[str, str]:
    low = norm(text).lower()
    core = CONTROL_CORE_RE.search(low)
    known = CONTROL_KNOWN_RE.search(low)
    noise = CONTROL_NOISE_RE.search(low)
    if core and known and not (noise and not re.search(r"gunakan|aplikasi|tanam|bersihkan|bakar|kendalikan|cegah|kurangi|tekan|hindari|terapkan", low)):
        return "duplikat_parafrase", "Tindakan sudah dikenal; tinggal perluas keyword/rule."
    if core:
        if re.search(r"varietas|kultivar|benih|sanitasi|rotasi|mulsa|jarak|pemupukan|pengairan|drainase", low):
            return "duplikat_parafrase", "Tindakan sudah dikenal; tinggal perluas keyword/rule."
        return "tindakan_nyata", "Tindakan nyata yang belum punya aksi kanonik."
    if known:
        return "duplikat_parafrase", "Sebutan tindakan ada, tetapi kalimatnya fragmen/parafrase."
    if noise or GENERIC_FRAGMENT_RE.search(low) or len(re.sub(r"[^0-9A-Za-z]", "", text)) < 40:
        return "bukan_tindakan", "Fragmen/konteks penelitian, bukan instruksi tindakan."
    return "ambigu", "Tidak ada verba tindakan yang jelas."


def build() -> dict:
    entries = bo.penyakit_entries()
    by_id = {entry["disease_id"]: entry for entry in entries}
    symptoms, errors = bo.symptom_records(entries)
    controls = bo.control_records(entries) + bo.chapter_control_records()

    rows: list[dict[str, str]] = []
    for kind, records, classifier in (
        ("gejala", symptoms, symptom_class),
        ("pengendalian", controls, control_class),
    ):
        for record in records:
            if kind == "gejala":
                if bo.match_canonical_symptoms(record["text"]):
                    continue
            elif bo.match_control_actions(
                record["text"], record.get("category", ""), record.get("source", "")
            ):
                continue
            category, reason = classifier(record["text"])
            entry = by_id.get(record.get("disease_id", ""))
            if entry:
                plant = entry["plant_local"]
                disease = entry["local"]
                label = entry.get("label") or entry.get("nama") or disease
            else:
                plant = record.get("plant_local", "")
                disease = f"{plant} (tingkat tanaman)"
                label = f"Pengendalian umum {plant}"
            rows.append(
                {
                    "kind": kind,
                    "plant": plant,
                    "disease": disease,
                    "label": label,
                    "source": record.get("source", ""),
                    "source_id": record.get("source_id", ""),
                    "chunk_id": record.get("chunk_id", ""),
                    "text": record["text"],
                    "category": category,
                    "reason": reason,
                }
            )

    counts = Counter((row["kind"], row["category"]) for row in rows)
    return {
        "summary": {
            "total": len(rows),
            "symptoms": sum(1 for row in rows if row["kind"] == "gejala"),
            "controls": sum(1 for row in rows if row["kind"] == "pengendalian"),
            "counts": {
                f"{kind}:{category}": count
                for (kind, category), count in sorted(counts.items())
            },
            "errors": errors,
        },
        "rows": rows,
    }


CATEGORY_LABELS = {
    "duplikat_parafrase": "Duplikat/parafrase",
    "butuh_konsep_baru": "Butuh konsep baru",
    "tindakan_nyata": "Tindakan nyata",
    "bukan_gejala": "Bukan gejala",
    "bukan_tindakan": "Bukan tindakan",
    "ambigu": "Ambigu",
}
ACTION_LABELS = {
    "duplikat_parafrase": "Perluas keyword/rule lalu petakan",
    "butuh_konsep_baru": "Tambah konsep/rule kanonik",
    "tindakan_nyata": "Tambah aksi kanonik",
    "bukan_gejala": "Exception: bukan gejala",
    "bukan_tindakan": "Exception: bukan tindakan",
    "ambigu": "Review manual",
}


def markdown(report: dict) -> str:
    summary = report["summary"]
    lines = [
        "# Triage Mapping Gejala dan Pengendalian",
        "",
        "Laporan ini memisahkan gap nyata dari noise. Sumber baris adalah "
        "`SOURCE_GAP_AUDIT.json`; klasifikasi di sini adalah keputusan awal "
        "sebelum perubahan aturan mapping.",
        "",
        "## Ringkasan",
        "",
        "| Item | Jumlah |",
        "|---|---:|",
        f"| Total record belum dipetakan | {summary['total']} |",
        f"| Gejala | {summary['symptoms']} |",
        f"| Pengendalian | {summary['controls']} |",
        "",
        "| Jenis | Kategori | Jumlah |",
        "|---|---|---:|",
    ]
    for key, count in summary["counts"].items():
        kind, category = key.split(":", 1)
        lines.append(f"| {kind.capitalize()} | {CATEGORY_LABELS[category]} | {count} |")

    for kind, title in (("gejala", "Gejala"), ("pengendalian", "Pengendalian")):
        lines += [
            "",
            f"## {title}",
            "",
            "| # | Tanaman | Penyakit | Kategori | Usulan | Alasan | Kutipan |",
            "|---:|---|---|---|---|---|---|",
        ]
        rows = [row for row in report["rows"] if row["kind"] == kind]
        for index, row in enumerate(rows, start=1):
            text = norm(row["text"])[:240].replace("|", "\\|")
            lines.append(
                f"| {index} | {row['plant']} | {row['label']} | "
                f"{CATEGORY_LABELS[row['category']]} | {ACTION_LABELS[row['category']]} | "
                f"{row['reason']} | {text} |"
            )

    lines += [
        "",
        "## Keputusan",
        "",
        "- `Duplikat/parafrase` diselesaikan dengan memperluas aturan yang sudah ada, "
        "bukan menambah kelas baru.",
        "- `Butuh konsep baru` hanya untuk pola yang berulang dan benar-benar gejala.",
        "- `Bukan gejala`/`Bukan tindakan` masuk exception list, bukan dipaksa menjadi 0.",
        "- `Ambigu` perlu review manual sebelum dipetakan.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    report = build()
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text(markdown(report), encoding="utf-8", newline="")
    OUTPUT_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="",
    )
    print(f"output: {OUTPUT_MD}")
    print(f"output: {OUTPUT_JSON}")
    print(json.dumps(report["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
