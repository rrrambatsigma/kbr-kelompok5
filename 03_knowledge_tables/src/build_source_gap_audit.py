"""Audit ketersediaan bukti sumber untuk setiap gap KB.

Laporan ini menjawab pertanyaan: apakah gap yang terlihat di ontology benar-benar
tidak punya informasi di sumber, atau hanya belum diekstrak/dipetakan. Sumber
utama: curated DOC002/DOC005, baseline DOC002, chunks DOC005, dan MD Kacang
Hijau. Tidak ada sumber eksternal yang dipakai di sini.
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from rdflib import Graph
from rdflib.namespace import RDF, RDFS

TABLE_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = TABLE_DIR.parent
ONTO_DIR = PROJECT_ROOT / "04_ontology"
sys.path.insert(0, str(ONTO_DIR))
sys.path.insert(0, str(TABLE_DIR / "src"))

import build_enrichment_facts as ef  # noqa: E402
import build_ontology as bo  # noqa: E402
from tbox import KBR  # noqa: E402

ONTOLOGY_TTL = ONTO_DIR / "ontology_md.ttl"
OUTPUT_MD = TABLE_DIR / "reports" / "SOURCE_GAP_AUDIT.md"
OUTPUT_JSON = TABLE_DIR / "reports" / "SOURCE_GAP_AUDIT.json"

SEVERITY_RE = re.compile(
    r"tingkat\s+keparahan|keparahan\s+penyakit|kehilangan\s+hasil|"
    r"kerugian\s+hasil|penurunan\s+hasil|penurunan\s+produksi|"
    r"kejadian\s+penyakit|intensitas\s+serangan|serangan\s+berat|"
    r"serangan\s+ringan|kerusakan\s+parah",
    re.I,
)
PHASE_RE = re.compile(
    r"\b(?:fase|masa|saat|periode)\s+(?:tanaman\s+)?"
    r"(matang\s+susu|vegetatif|generatif|pembibitan|persemaian|anakan|"
    r"pembungaan|pemasakan|matang|panen|kecambah|bibit)\b",
    re.I,
)
VARIETY_RE = re.compile(
    r"\b(?:varietas|kultivar|galur)\s+"
    r"([A-Z][A-Za-z0-9\-']*(?:\s+[A-Z0-9][A-Za-z0-9\-']*){0,5})",
    re.UNICODE,
)
RESIST_RE = re.compile(r"\b(tahan|toleran|resisten|resistan|rentan|peka)\b", re.I)
ENGLISH_DISEASE_RE = re.compile(
    r"\b(?:[A-Z][a-z]+\s+){1,5}(?:disease|blight|spot|rot|mildew|mosaic|"
    r"virus|wilt|rust|smut|stunt|mottle|necrosis|streak|broom|elongation)\b",
)
DRAINAGE_RE = re.compile(r"\bdrainase\b|\bpengaturan\s+air\b|\bperbaikan\s+drainase\b", re.I)
ROTATION_RE = re.compile(r"\brotasi\s+tanaman\b|\bpergiliran\s+tanaman\b|\brotasi\b|\bpergiliran\b", re.I)


def local_name(uri: object) -> str:
    return str(uri).split("#")[-1]


def ontology_gaps() -> dict[str, dict[str, bool]]:
    graph = Graph()
    graph.parse(ONTOLOGY_TTL, format="turtle")
    gaps: dict[str, dict[str, bool]] = {}
    for disease in graph.subjects(RDF.type, KBR.Penyakit):
        local = local_name(disease)
        gaps[local] = {
            "severity": not bool(graph.value(disease, KBR.tingkatKeparahan)),
            "phase": not bool(graph.value(disease, KBR.menyerangFase)),
            "variety": not bool(list(graph.subjects(KBR.tahanTerhadap, disease))),
            "english": not bool(graph.value(disease, KBR.namaInggrisPenyakit)),
        }
    return gaps


def dedupe_units(units: list[ef.Unit]) -> list[ef.Unit]:
    seen: set[tuple[str, str, str]] = set()
    result: list[ef.Unit] = []
    for unit in units:
        key = (unit.document, unit.source_id, unit.text[:80])
        if key and key not in seen:
            seen.add(key)
            result.append(unit)
    return result


def _page_number(value: str) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _block_order(source_id: str) -> int:
    match = re.search(r"_B(\d+)$", source_id or "")
    return int(match.group(1)) if match else 0


def _context_units(
    units: list[ef.Unit], entry: dict[str, str], exact: list[ef.Unit]
) -> list[ef.Unit]:
    """Ambil blok lanjutan yang kehilangan heading karena pindah halaman."""
    if not exact or entry.get("source") != "DOC002":
        return []
    start = _page_number(entry.get("page_start", ""))
    end = _page_number(entry.get("page_end", "")) or start
    if start is None:
        return []
    first_page = min(_page_number(unit.page) or start for unit in exact)
    first_order = min(
        _block_order(unit.source_id)
        for unit in exact
        if (_page_number(unit.page) or start) == first_page
    )
    exact_ids = {unit.source_id for unit in exact}
    context: list[ef.Unit] = []
    for unit in units:
        if unit.document != "DOC002" or unit.source_id in exact_ids:
            continue
        page = _page_number(unit.page)
        if page is None or page < start or page > end:
            continue
        if page == first_page and _block_order(unit.source_id) < first_order:
            continue
        if unit.section and entry.get("section"):
            if ef.norm_section(unit.section) != ef.norm_section(entry.get("section")):
                continue
        if unit.subsection and entry.get("subsection"):
            if ef.norm_section(unit.subsection) != ef.norm_section(entry.get("subsection")):
                continue
        context.append(unit)
    return context


def candidate_rows(
    units: list[ef.Unit],
    entry: dict[str, str],
    pattern: re.Pattern[str],
    limit: int = 3,
) -> list[dict[str, str]]:
    disease = entry["local"]
    plant = entry["plant_local"]
    exact = [unit for unit in units if unit.disease == disease]
    scope = "disease"
    if not exact:
        exact = [unit for unit in units if unit.plant == plant]
        scope = "plant"
    ordered = [(unit, scope) for unit in exact]
    ordered += [(unit, "disease_context") for unit in _context_units(units, entry, exact)]
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for unit, unit_scope in ordered:
        for sentence in ef.sentences(unit.text):
            if not pattern.search(sentence):
                continue
            value = ef.norm(sentence)
            if value in seen:
                continue
            seen.add(value)
            rows.append(
                {
                    "text": sentence,
                    "document": unit.document,
                    "source_type": unit.source_type,
                    "source_id": unit.source_id,
                    "page": unit.page,
                    "section": unit.section,
                    "subsection": unit.subsection,
                    "scope": unit_scope,
                }
            )
            if len(rows) >= limit:
                return rows
    return rows


def severity_status(rows: list[dict[str, str]]) -> tuple[str, str]:
    if not rows:
        return "absent", "Tidak ada kalimat severity di unit penyakit/tanaman."
    strong = [
        row
        for row in rows
        if re.search(r"\d", row["text"])
        and re.search(r"kehilangan|penurunan|keparahan|intensitas|kejadian|%", row["text"], re.I)
    ]
    if strong:
        return "available", "Ada angka kehilangan hasil/keparahan/intensitas."
    return "partial", "Ada pernyataan kualitatif (berat/ringan/merugikan), tanpa angka."


def phase_status(rows: list[dict[str, str]]) -> tuple[str, str]:
    if not rows:
        return "absent", "Tidak ada penyebutan fase tanaman."
    if any(re.search(r"\bfase\b", row["text"], re.I) for row in rows):
        return "available", "Fase disebut eksplisit dengan kata 'fase'."
    return "partial", "Ada istilah masa/saat/periode, tetapi bukan label fase eksplisit."


def variety_status(rows: list[dict[str, str]]) -> tuple[str, str]:
    if not rows:
        return "absent", "Tidak ada varietas/kultivar yang disebut."
    named = [
        row
        for row in rows
        if VARIETY_RE.search(row["text"]) and RESIST_RE.search(row["text"])
    ]
    if named:
        return "available", "Ada nama varietas/kultivar dengan status tahan/toleran/rentan."
    if any(RESIST_RE.search(row["text"]) for row in rows):
        return "partial", "Ada pernyataan tahan/toleran/rentan, tetapi nama varietas tidak jelas."
    return "partial", "Ada penyebutan varietas, tetapi status ketahanan tidak eksplisit."


def english_status(
    entry: dict[str, str], units: list[ef.Unit], disease: str, plant: str
) -> tuple[str, str, list[dict[str, str]]]:
    name_en = (entry.get("name_en") or "").strip()
    if name_en:
        return (
            "available",
            "Nama Inggris tersedia di tabel curated.",
            [
                {
                    "text": name_en,
                    "document": entry.get("source", ""),
                    "source_type": "curated",
                    "source_id": entry.get("disease_id", ""),
                    "page": entry.get("page_start", ""),
                    "section": entry.get("section", ""),
                    "subsection": entry.get("subsection", ""),
                    "scope": "disease",
                }
            ],
        )
    label = entry.get("label") or entry.get("nama") or ""
    match = re.search(r"\(([^)]*[A-Za-z][^)]*)\)", label)
    if match and ENGLISH_DISEASE_RE.search(match.group(1)):
        return (
            "available",
            "Nama Inggris tercetak di label penyakit.",
            [
                {
                    "text": match.group(1),
                    "document": entry.get("source", ""),
                    "source_type": "curated_label",
                    "source_id": entry.get("disease_id", ""),
                    "page": entry.get("page_start", ""),
                    "section": entry.get("section", ""),
                    "subsection": entry.get("subsection", ""),
                    "scope": "disease",
                }
            ],
        )
    rows = candidate_rows(units, entry, ENGLISH_DISEASE_RE)
    if rows:
        return "partial", "Ada frasa Inggris di sumber; perlu verifikasi sebagai nama penyakit.", rows
    return "absent", "Tidak ada nama Inggris eksplisit di sumber dalam scope.", []


def unit_for_record(
    record: dict, units_by_source: dict[tuple[str, str], ef.Unit]
) -> ef.Unit | None:
    return units_by_source.get((record.get("source", ""), record.get("chunk_id", "")))


def preliminary_symptom_class(text: str) -> str:
    low = ef.norm(text)
    if re.search(
        r"patogen|jamur|bakteri|virus|suhu|kelembapan|kelembaban|inokulum|"
        r"pengendalian|dikendalikan|varietas|tanah|musim|fotosintesis|"
        r"gambar|tabel|sumber|penelitian|mikroskopis|koloni|media",
        low,
    ):
        return "bukan_gejala"
    if re.search(
        r"bercak|lesi|lesio|bintik|pustul|tepung|belang|kuning|nekrotik|"
        r"kering|rontok|gugur|patah|menggulung|keriput|abnormal|deformasi|"
        r"kanker|lekukan|halo|cincin|busuk|mati|membusuk|kerdil|malai|"
        r"daun|batang|akar|umbi|buah|biji|polong|pucuk|tunas",
        low,
    ):
        if re.search(r"bercak|lesi|lesio|bintik|pustul", low):
            return "duplikat_parafrase"
        return "butuh_konsep_baru"
    return "ambigu"


def preliminary_control_class(text: str) -> str:
    low = ef.norm(text)
    if re.search(
        r"pestisida|fungisida|bakterisida|insektisida|herbisida|mikroba|"
        r"antagonis|trichoderma|bacillus|pseudomonas|varietas|rotasi|"
        r"sanitasi|benih|mulsa|jarak tanam|pemupukan|pengairan|drainase|"
        r"panen|penyimpanan|suhu|kelembaban|kelembapan|aplikasi|disemprot|"
        r"perlakuan|pengendalian|dikendalikan|menekan|mengurangi|mencegah",
        low,
    ):
        if re.search(
            r"pestisida|fungisida|bakterisida|insektisida|herbisida|"
            r"mikroba|antagonis|trichoderma|bacillus|pseudomonas",
            low,
        ):
            return "duplikat_parafrase"
        return "butuh_konsep_baru"
    if len(re.sub(r"[^0-9A-Za-z]", "", text)) < 40:
        return "bukan_tindakan"
    if re.search(r"penelitian|hasil|menurut|dilaporkan|menunjukkan|gambar|tabel", low):
        return "bukan_tindakan"
    return "ambigu"


def source_record_row(
    record: dict,
    entry: dict[str, str] | None,
    unit: ef.Unit | None,
    kind: str,
) -> dict[str, str]:
    if entry is None:
        plant = record.get("plant_local", "")
        disease = f"{plant} (tingkat tanaman)"
        label = f"Pengendalian umum {plant}"
    else:
        plant = entry["plant_local"]
        disease = entry["local"]
        label = entry.get("label") or entry.get("nama") or disease
    text = record.get("text", "")
    category = (
        preliminary_symptom_class(text)
        if kind == "gejala"
        else preliminary_control_class(text)
    )
    return {
        "kind": kind,
        "plant": plant,
        "disease": disease,
        "label": label,
        "source": record.get("source", ""),
        "source_id": record.get("source_id", ""),
        "chunk_id": record.get("chunk_id", ""),
        "page": record.get("page", ""),
        "section": unit.section if unit else "",
        "subsection": unit.subsection if unit else "",
        "text": text,
        "triage": category,
        "status": "available",
        "note": "Teks sumber tersedia; status triage masih awal.",
    }


def build() -> dict:
    entries = bo.penyakit_entries()
    unique = bo.unique_diseases(entries)
    entry_by_local = {entry["local"]: entry for entry in unique}
    by_id = {entry["disease_id"]: entry for entry in entries}
    gaps = ontology_gaps()

    units = dedupe_units(
        ef.load_doc002_baseline()
        + ef.load_doc005_chunks()
        + ef.load_doc005_md_units()
        + ef.load_md_units()
    )
    ef.assign_diseases(units, entries)
    units_by_source = {
        (unit.document, unit.source_id): unit
        for unit in units
        if unit.source_id
    }

    metadata_rows: list[dict[str, str]] = []
    status_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for local in sorted(gaps, key=lambda value: (entry_by_local[value]["plant_local"], value)):
        entry = entry_by_local[local]
        plant = entry["plant_local"]
        for gap_type, pattern, status_fn in (
            ("severity", SEVERITY_RE, severity_status),
            ("phase", PHASE_RE, phase_status),
            ("variety", re.compile(r"\b(?:varietas|kultivar|galur)\b|\b(?:tahan|toleran|rentan|peka)\b", re.I), variety_status),
        ):
            if not gaps[local][gap_type]:
                continue
            candidates = candidate_rows(units, entry, pattern)
            status, reason = status_fn(candidates)
            status_counts[gap_type][status] += 1
            metadata_rows.append(
                {
                    "plant": plant,
                    "disease": local,
                    "label": entry.get("label") or entry.get("nama") or local,
                    "gap": gap_type,
                    "status": status,
                    "reason": reason,
                    "candidate": candidates[0] if candidates else {},
                    "candidate_count": str(len(candidates)),
                }
            )
        if gaps[local]["english"]:
            status, reason, candidates = english_status(entry, units, local, plant)
            status_counts["english"][status] += 1
            metadata_rows.append(
                {
                    "plant": plant,
                    "disease": local,
                    "label": entry.get("label") or entry.get("nama") or local,
                    "gap": "english",
                    "status": status,
                    "reason": reason,
                    "candidate": candidates[0] if candidates else {},
                    "candidate_count": str(len(candidates)),
                }
            )

    symptoms, errors = bo.symptom_records(entries)
    unmapped_symptoms = [
        record
        for record in symptoms
        if not bo.match_canonical_symptoms(record["text"])
    ]
    controls = bo.control_records(entries) + bo.chapter_control_records()
    unmapped_controls = [
        record
        for record in controls
        if not bo.match_control_actions(
            record["text"], record.get("category", ""), record.get("source", "")
        )
    ]

    mapping_rows = [
        source_record_row(
            record,
            by_id.get(record.get("disease_id", "")),
            unit_for_record(record, units_by_source),
            "gejala",
        )
        for record in unmapped_symptoms
    ] + [
        source_record_row(
            record,
            by_id.get(record.get("disease_id", "")),
            unit_for_record(record, units_by_source),
            "pengendalian",
        )
        for record in unmapped_controls
    ]

    drainage = [
        unit
        for unit in units
        if DRAINAGE_RE.search(unit.text)
    ]
    rotation = [
        unit
        for unit in units
        if ROTATION_RE.search(unit.text)
    ]

    return {
        "summary": {
            "diseases": len(gaps),
            "unmapped_symptoms": len(unmapped_symptoms),
            "unmapped_controls": len(unmapped_controls),
            "metadata_rows": len(metadata_rows),
            "status_counts": {
                gap: dict(counts) for gap, counts in sorted(status_counts.items())
            },
            "symptom_errors": errors,
            "drainage_units": len(drainage),
            "rotation_units": len(rotation),
        },
        "metadata": metadata_rows,
        "mapping": mapping_rows,
        "drainage": [
            {
                "disease": unit.disease,
                "plant": unit.plant,
                "source": unit.document,
                "source_id": unit.source_id,
                "page": unit.page,
                "section": unit.section,
                "text": ef.norm(unit.text)[:500],
            }
            for unit in drainage[:20]
        ],
        "rotation": [
            {
                "disease": unit.disease,
                "plant": unit.plant,
                "source": unit.document,
                "source_id": unit.source_id,
                "page": unit.page,
                "section": unit.section,
                "text": ef.norm(unit.text)[:500],
            }
            for unit in rotation[:20]
        ],
    }


GAP_LABELS = {
    "severity": "Severity",
    "phase": "Fase",
    "variety": "Varietas tahan",
    "english": "Nama Inggris",
}


def quote(row: dict[str, str], limit: int = 240) -> str:
    candidate = row.get("candidate") or {}
    text = candidate.get("text") or ""
    return ef.norm(text)[:limit].replace("|", "\\|")


def markdown(report: dict) -> str:
    summary = report["summary"]
    lines = [
        "# Audit Ketersediaan Sumber per Gap",
        "",
        "Sumber yang diaudit: `00_sumber_data/05_PenyakitUtamaKedelai.md`, "
        "`00_sumber_data/07_PenyakitKacangHijau.md`, baseline lengkap "
        "`02_extraction/llamaparse/baseline/DOC002.blocks.jsonl`, dan chunks "
        "DOC002/DOC005. Tidak ada sumber eksternal.",
        "",
        "> Catatan: `00_sumber_data/02_PenyakitTanamanPangan.md` hanya preview/"
        "truncated. Teks lengkap DOC002 ada di baseline blocks.",
        "",
        "## Ringkasan",
        "",
        "| Item | Jumlah |",
        "|---|---:|",
        f"| Penyakit | {summary['diseases']} |",
        f"| Gejala belum dipetakan | {summary['unmapped_symptoms']} |",
        f"| Pengendalian belum dipetakan | {summary['unmapped_controls']} |",
        f"| Baris audit metadata | {summary['metadata_rows']} |",
        f"| Unit sumber menyebut drainase | {summary['drainage_units']} |",
        f"| Unit sumber menyebut rotasi/pergiliran | {summary['rotation_units']} |",
        "",
        "## Status metadata",
        "",
        "| Gap | available | partial | absent |",
        "|---|---:|---:|---:|",
    ]
    for gap in ("severity", "phase", "variety", "english"):
        counts = summary["status_counts"].get(gap, {})
        lines.append(
            f"| {GAP_LABELS[gap]} | {counts.get('available', 0)} | "
            f"{counts.get('partial', 0)} | {counts.get('absent', 0)} |"
        )

    lines += [
        "",
        "## Detail gap metadata",
        "",
        "| Tanaman | Penyakit | Gap | Status | Alasan | Bukti/kutipan | Sumber |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in report["metadata"]:
        candidate = row.get("candidate") or {}
        source = " ".join(
            value
            for value in (
                candidate.get("document", ""),
                candidate.get("source_id", ""),
                f"hal. {candidate.get('page')}" if candidate.get("page") else "",
            )
            if value
        )
        lines.append(
            f"| {row['plant']} | {row['label']} | {GAP_LABELS[row['gap']]} | "
            f"{row['status']} | {row['reason']} | {quote(row)} | {source} |"
        )

    lines += [
        "",
        "## Gejala belum dipetakan",
        "",
        "Semua baris di bawah berasal dari sumber. Status `available` berarti teks "
        "bukti ada; kolom `triase awal` memisahkan kandidat gejala nyata dari noise.",
        "",
        "| # | Tanaman | Penyakit | Triase awal | Kutipan | Sumber | Chunk |",
        "|---:|---|---|---|---|---|---|",
    ]
    symptom_rows = [row for row in report["mapping"] if row["kind"] == "gejala"]
    for index, row in enumerate(symptom_rows, start=1):
        lines.append(
            f"| {index} | {row['plant']} | {row['label']} | {row['triage']} | "
            f"{ef.norm(row['text'])[:220].replace('|', '\\|')} | {row['source']} | "
            f"{row['chunk_id'] or row['source_id']} |"
        )

    lines += [
        "",
        "## Pengendalian belum dipetakan",
        "",
        "| # | Tanaman | Penyakit | Triase awal | Kutipan | Sumber | Chunk |",
        "|---:|---|---|---|---|---|---|",
    ]
    control_rows = [row for row in report["mapping"] if row["kind"] == "pengendalian"]
    for index, row in enumerate(control_rows, start=1):
        lines.append(
            f"| {index} | {row['plant']} | {row['label']} | {row['triage']} | "
            f"{ef.norm(row['text'])[:220].replace('|', '\\|')} | {row['source']} | "
            f"{row['chunk_id'] or row['source_id']} |"
        )

    lines += [
        "",
        "## Drainase dan rotasi",
        "",
        f"- Unit sumber yang menyebut drainase: **{summary['drainage_units']}**.",
        f"- Unit sumber yang menyebut rotasi/pergiliran: **{summary['rotation_units']}**.",
        "- Informasi ini sudah ada di sumber, tetapi saat ini lebih banyak "
        "direpresentasikan sebagai aksi pengendalian daripada kondisi lingkungan.",
        "",
        "Contoh bukti drainase:",
        "",
    ]
    for row in report["drainage"][:5]:
        lines.append(
            f"- {row['source']} `{row['source_id']}`: {ef.norm(row['text'])[:300]}"
        )
    lines += ["", "Contoh bukti rotasi:", ""]
    for row in report["rotation"][:5]:
        lines.append(
            f"- {row['source']} `{row['source_id']}`: {ef.norm(row['text'])[:300]}"
        )

    lines += [
        "",
        "## Kesimpulan",
        "",
        "- Gap gejala/pengendalian bukan berarti sumber kosong; teks bukti tersedia "
        "dan menunggu triase/mapping.",
        "- Severity, fase, varietas, dan nama Inggris bersifat best-effort: sebagian "
        "tersedia, sebagian hanya parsial, dan sisanya tidak tersedia.",
        "- Drainase dan rotasi tetap tersedia di sumber, tetapi tidak dimodelkan "
        "sebagai kelas faktor lingkungan; drainase/rotasi dipakai sebagai aksi "
        "pengendalian, sedangkan kondisi drainase diwakili `KondisiDrainaseBaik`/"
        "`KondisiDrainaseBuruk`.",
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
    print(f"metadata rows: {report['summary']['metadata_rows']}")
    print(f"unmapped symptoms: {report['summary']['unmapped_symptoms']}")
    print(f"unmapped controls: {report['summary']['unmapped_controls']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
