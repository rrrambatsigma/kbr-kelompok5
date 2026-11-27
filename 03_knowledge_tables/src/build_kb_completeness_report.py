"""Audit kelengkapan KB pada ontology_md.ttl.

Laporan ini menjadi dashboard Phase 0: satu baris per penyakit, dengan status
untuk lingkungan, patogen, pengendalian, bagian tanaman, gejala, dan enrichment
lain. Sumber kebenaran adalah ontology_md.ttl, bukan ontology.ttl.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

from rdflib import Graph
from rdflib.namespace import RDF, RDFS

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TABLE_DIR = PROJECT_ROOT / "03_knowledge_tables"
ONTO_DIR = PROJECT_ROOT / "04_ontology"
sys.path.insert(0, str(ONTO_DIR))

from tbox import KBR  # noqa: E402

ONTOLOGY_TTL = ONTO_DIR / "ontology_md.ttl"
REPORT_JSON = ONTO_DIR / "extraction_report_md.json"
QUALITY_REPORT_JSON = ONTO_DIR / "extraction_report.json"
OUTPUT_MD = TABLE_DIR / "reports" / "KB_COMPLETENESS.md"
OUTPUT_JSON = TABLE_DIR / "reports" / "KB_COMPLETENESS.json"

PLANT_ORDER = {
    "Padi": 0,
    "Kedelai": 1,
    "Jagung": 2,
    "UbiJalar": 3,
    "UbiKayu": 4,
    "KacangTanah": 5,
    "KacangHijau": 6,
}

AUDIT_NOTES = [
    "`TanamanKerdilStuntUbiKayu` berbagi patogen Begomovirus dengan "
    "`CassavaMosaicBegomovirusCMBsUbiKayu`; perlu keputusan merge/alias "
    "sebelum dipaksa punya bukti lingkungan.",
    "`PenyakitRebahSemaiKedelai` (Sclerotium rolfsii) dan "
    "`PenyakitRebahKecambahKedelai` (Rhizoctonia solani) adalah dua penyakit "
    "berbeda; jangan digabung.",
    "Pengendalian UbiKayu tersedia sebagai `pengendalianUmum` level tanaman; "
    "fallback ini dihitung sebagai jalur rekomendasi yang sah.",
    "Spike SWRL/Pellet berhasil: Pellet 2.3.1 lewat owlready2 dapat "
    "menginfer object property dari SWRL dengan `infer_property_values=True`.",
    "Empat aturan SWRL sudah digabung ke ontology_md: kandidat gejala, "
    "kandidat lingkungan, rekomendasi spesifik, dan fallback pengendalian umum.",
    "Kondisi tumbuh 7/7 tanaman diisi dari sumber eksternal; 5 fakta baru "
    "ditambahkan ke ontology_md.",
    "Severity, fase, varietas, dan nama Inggris tetap best-effort; nilainya "
    "tidak dipaksakan bila sumber tidak menyatakan.",
    "`00_sumber_data/02_PenyakitTanamanPangan.md` hanya preview/truncated; "
    "teks lengkap DOC002 yang dipakai audit ada di "
    "`02_extraction/llamaparse/baseline/DOC002.blocks.jsonl`.",
    "Audit sumber per gap ada di `03_knowledge_tables/reports/SOURCE_GAP_AUDIT.md`; "
    "triage mapping ada di `03_knowledge_tables/reports/MAPPING_TRIAGE.md`.",
]

GAP_ROWS = [
    ("environment_missing", "Tanpa bukti lingkungan", "Inti", "DOC002/DOC005", "Isi dari kutipan sumber"),
    ("pathogen_missing", "Tanpa patogen", "Inti", "DOC002/DOC005", "Lengkapi tautan patogen"),
    ("pathogen_unknown_taxon", "Patogen tanpa takson", "Inti", "DOC002/DOC005", "Lengkapi takson"),
    ("control_missing", "Tanpa pengendalian sama sekali", "Inti", "DOC002/DOC005", "Isi aksi pengendalian"),
    ("part_missing", "Tanpa bagian tanaman", "Inti", "DOC002/DOC005", "Isi bagian tanaman"),
    ("growth_conditions_missing_plants", "Tanaman tanpa kondisi tumbuh", "Inti", "DOC002/DOC005/EXTERNAL_ENV", "Isi kondisi tumbuh"),
    ("unmapped_symptoms", "Gejala belum dipetakan", "Mapping", "DOC002/DOC005", "Triage lalu petakan/exception"),
    ("unmapped_controls", "Pengendalian belum dipetakan", "Mapping", "DOC002/DOC005", "Triage lalu petakan/exception"),
    ("severity_missing", "Tanpa severity", "Best-effort", "DOC002/DOC005", "Isi bila sumber eksplisit"),
    ("phase_missing", "Tanpa fase", "Best-effort", "DOC002/DOC005", "Isi bila sumber eksplisit"),
    ("plant_phase_missing", "Tanaman tanpa fase pertumbuhan", "Best-effort", "DOC002/DOC005/EXTERNAL_ENV", "Isi fase pertumbuhan tanaman"),
    ("resistant_variety_missing", "Tanpa varietas tahan", "Best-effort", "DOC002/DOC005", "Isi bila sumber eksplisit"),
    ("english_name_missing", "Tanpa nama Inggris", "Best-effort", "DOC002/DOC005/eksternal", "Isi bila sumber eksplisit"),
]


def local_name(uri: object) -> str:
    return str(uri).split("#")[-1]


def values(graph: Graph, subject: object, predicate: object) -> list[object]:
    return list(graph.objects(subject, predicate))


def has_comment(graph: Graph, subject: object) -> bool:
    return bool(graph.value(subject, RDFS.comment))


def pathogen_status(graph: Graph, disease: object) -> tuple[str, int]:
    pathogens = values(graph, disease, KBR.disebabkanOleh)
    if not pathogens:
        return "missing", 0
    generic = False
    for pathogen in pathogens:
        types = set(graph.objects(pathogen, RDF.type))
        if KBR.Patogen in types and not (
            types
            & {
                KBR.Jamur,
                KBR.Bakteri,
                KBR.Virus,
                KBR.Nematoda,
                KBR.Oomycete,
                KBR.Fitoplasma,
            }
        ):
            generic = True
    return ("unknown_taxon" if generic else "ok"), len(pathogens)


def control_status(graph: Graph, disease: object, plant: object) -> str:
    if values(graph, disease, KBR.dikendalikanDengan):
        return "specific"
    if plant is not None and values(graph, plant, KBR.pengendalianUmum):
        return "fallback"
    return "missing"


def build() -> dict:
    graph = Graph()
    graph.parse(ONTOLOGY_TTL, format="turtle")

    disease_uris = sorted(
        graph.subjects(RDF.type, KBR.Penyakit), key=lambda uri: local_name(uri)
    )
    rows: list[dict[str, object]] = []
    plants = sorted(
        graph.subjects(RDF.type, KBR.TanamanPangan),
        key=lambda uri: PLANT_ORDER.get(local_name(uri), 99),
    )

    for disease in disease_uris:
        plant_uris = values(graph, disease, KBR.menyerangTanaman)
        plant_uri = plant_uris[0] if plant_uris else None
        plant = local_name(plant_uri) if plant_uri else ""
        label = graph.value(disease, RDFS.label)
        pathogen, pathogen_count = pathogen_status(graph, disease)
        control = control_status(graph, disease, plant_uri)
        parts = values(graph, disease, KBR.menyerangBagian)
        symptoms = values(graph, disease, KBR.memilikiGejala)
        resistant = list(graph.subjects(KBR.tahanTerhadap, disease))

        rows.append(
            {
                "plant": plant,
                "disease_local": local_name(disease),
                "disease_label": str(label) if label else local_name(disease),
                "environment": len(values(graph, disease, KBR.dipengaruhiOleh)),
                "pathogen": pathogen,
                "pathogen_count": pathogen_count,
                "control": control,
                "part_count": len(parts),
                "severity": bool(values(graph, disease, KBR.tingkatKeparahan)),
                "phase": bool(values(graph, disease, KBR.menyerangFase)),
                "symptom_count": len(symptoms),
                "resistant_varieties": len(resistant),
                "description": bool(
                    graph.value(disease, KBR.deskripsiPenyakit)
                    or graph.value(disease, RDFS.comment)
                ),
                "english_name": bool(values(graph, disease, KBR.namaInggrisPenyakit)),
            }
        )

    plants_data: list[dict[str, object]] = []
    for plant_uri in plants:
        plant = local_name(plant_uri)
        conditions = values(graph, plant_uri, KBR.memilikiKondisiTumbuh)
        general_controls = values(graph, plant_uri, KBR.pengendalianUmum)
        phases = values(graph, plant_uri, KBR.memilikiFasePertumbuhan)
        plants_data.append(
            {
                "plant": plant,
                "diseases": sum(1 for row in rows if row["plant"] == plant),
                "growth_conditions": len(conditions),
                "general_controls": len(general_controls),
                "phases": len(phases),
            }
        )

    pathogen_uris = {
        pathogen
        for disease in disease_uris
        for pathogen in graph.objects(disease, KBR.disebabkanOleh)
    }
    unknown_taxon = []
    for pathogen in pathogen_uris:
        types = set(graph.objects(pathogen, RDF.type))
        if KBR.Patogen in types and not (
            types
            & {
                KBR.Jamur,
                KBR.Bakteri,
                KBR.Virus,
                KBR.Nematoda,
                KBR.Oomycete,
                KBR.Fitoplasma,
            }
        ):
            unknown_taxon.append(local_name(pathogen))

    shared_pathogens: dict[tuple[str, ...], list[str]] = defaultdict(list)
    for disease in disease_uris:
        names = tuple(
            sorted(
                local_name(pathogen)
                for pathogen in graph.objects(disease, KBR.disebabkanOleh)
            )
        )
        if names:
            shared_pathogens[names].append(local_name(disease))
    shared_pathogen_groups = [
        {"pathogens": list(names), "diseases": diseases}
        for names, diseases in sorted(shared_pathogens.items())
        if len(diseases) > 1
    ]

    label_groups: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        key = " ".join(
            str(row["disease_label"])
            .lower()
            .replace("penyakit", "")
            .replace("(", "")
            .replace(")", "")
            .replace("-", " ")
            .split()
        )
        label_groups[key].append(str(row["disease_local"]))
    label_duplicates = [
        {"normalized_label": label, "diseases": diseases}
        for label, diseases in sorted(label_groups.items())
        if len(diseases) > 1
    ]

    extraction = {}
    if REPORT_JSON.exists():
        extraction = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
    quality = {}
    if QUALITY_REPORT_JSON.exists():
        quality = json.loads(QUALITY_REPORT_JSON.read_text(encoding="utf-8"))

    summary = {
        "ontology": str(ONTOLOGY_TTL.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "diseases": len(rows),
        "plants": len(plants_data),
        "environment_missing": sum(1 for row in rows if row["environment"] == 0),
        "pathogen_missing": sum(1 for row in rows if row["pathogen"] == "missing"),
        "pathogen_unknown_taxon": sum(
            1 for row in rows if row["pathogen"] == "unknown_taxon"
        ),
        "pathogen_unknown_taxon_unique": len(unknown_taxon),
        "control_specific_missing": sum(
            1 for row in rows if row["control"] != "specific"
        ),
        "control_fallback": sum(1 for row in rows if row["control"] == "fallback"),
        "control_missing": sum(1 for row in rows if row["control"] == "missing"),
        "part_missing": sum(1 for row in rows if row["part_count"] == 0),
        "severity_missing": sum(1 for row in rows if not row["severity"]),
        "phase_missing": sum(1 for row in rows if not row["phase"]),
        "resistant_variety_missing": sum(
            1 for row in rows if row["resistant_varieties"] == 0
        ),
        "description_missing": sum(1 for row in rows if not row["description"]),
        "english_name_missing": sum(1 for row in rows if not row["english_name"]),
        "growth_conditions_missing_plants": sum(
            1 for plant in plants_data if plant["growth_conditions"] == 0
        ),
        "plant_phase_missing": sum(1 for plant in plants_data if plant["phases"] == 0),
        "unmapped_symptoms": quality.get("data_quality", {}).get(
            "unmapped_symptoms"
        ),
        "unmapped_controls": quality.get("data_quality", {}).get(
            "unmapped_controls"
        ),
        "unknown_pathogens_report": quality.get("data_quality", {}).get(
            "unknown_pathogens"
        ),
    }

    return {
        "summary": summary,
        "rows": rows,
        "plants": plants_data,
        "unknown_taxon": sorted(unknown_taxon),
        "shared_pathogen_groups": shared_pathogen_groups,
        "label_duplicates": label_duplicates,
        "audit_notes": AUDIT_NOTES,
    }


def markdown(report: dict) -> str:
    summary = report["summary"]
    lines = [
        "# Audit Kelengkapan KB",
        "",
        f"Sumber: `{summary['ontology']}`",
        "",
        "## Ringkasan",
        "",
        "| Dimensi | Gap |",
        "|---|---:|",
        f"| Penyakit | {summary['diseases']} |",
        f"| Tanaman | {summary['plants']} |",
        f"| Tanpa bukti lingkungan | {summary['environment_missing']} |",
        f"| Tanpa patogen | {summary['pathogen_missing']} |",
        f"| Patogen tanpa takson | {summary['pathogen_unknown_taxon_unique']} unik |",
        f"| Tanpa pengendalian spesifik | {summary['control_specific_missing']} |",
        f"| Memakai fallback pengendalian tanaman | {summary['control_fallback']} |",
        f"| Tanpa pengendalian sama sekali | {summary['control_missing']} |",
        f"| Tanpa bagian tanaman | {summary['part_missing']} |",
        f"| Tanpa severity | {summary['severity_missing']} |",
        f"| Tanpa fase | {summary['phase_missing']} |",
        f"| Tanaman tanpa fase pertumbuhan | {summary['plant_phase_missing']} |",
        f"| Tanpa varietas tahan | {summary['resistant_variety_missing']} |",
        f"| Tanpa deskripsi penyakit | {summary['description_missing']} |",
        f"| Tanpa nama Inggris | {summary['english_name_missing']} |",
        f"| Tanaman tanpa kondisi tumbuh | {summary['growth_conditions_missing_plants']} |",
        f"| Gejala belum dipetakan | {summary['unmapped_symptoms']} |",
        f"| Pengendalian belum dipetakan | {summary['unmapped_controls']} |",
        "",
        "## Klasifikasi gap",
        "",
        "| Jenis gap | Jumlah | Sifat | Sumber | Tindakan |",
        "|---|---:|---|---|---|",
    ]
    for key, label, nature, source, action in GAP_ROWS:
        lines.append(f"| {label} | {summary[key]} | {nature} | {source} | {action} |")

    lines.extend(
        [
            "",
            "## Status per tanaman",
            "",
            "| Tanaman | Penyakit | Kondisi tumbuh | Pengendalian umum | Fase |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for plant in report["plants"]:
        lines.append(
            f"| {plant['plant']} | {plant['diseases']} | "
            f"{plant['growth_conditions']} | {plant['general_controls']} | "
            f"{plant['phases']} |"
        )

    lines.extend(
        [
            "",
            "## Matriks per penyakit",
            "",
            "| Tanaman | Penyakit | Lingkungan | Patogen | Kendali | Bagian | "
            "Severity | Fase | Gejala | Varietas | Deskripsi |",
            "|---|---|---:|---|---|---:|---|---|---:|---:|---|",
        ]
    )
    for row in report["rows"]:
        lines.append(
            f"| {row['plant']} | {row['disease_label']} | "
            f"{row['environment']} | {row['pathogen']} | {row['control']} | "
            f"{row['part_count']} | {'ya' if row['severity'] else '-'} | "
            f"{'ya' if row['phase'] else '-'} | {row['symptom_count']} | "
            f"{row['resistant_varieties']} | "
            f"{'ya' if row['description'] else '-'} |"
        )

    lines.extend(["", "## Patogen tanpa takson", ""])
    if report["unknown_taxon"]:
        for name in report["unknown_taxon"]:
            lines.append(f"- `{name}`")
    else:
        lines.append("Tidak ada.")

    lines.extend(["", "## Penyakit berbagi patogen", ""])
    if report["shared_pathogen_groups"]:
        for group in report["shared_pathogen_groups"]:
            lines.append(
                f"- {', '.join(group['pathogens'])}: "
                f"{', '.join(group['diseases'])}"
            )
    else:
        lines.append("Tidak ada.")

    lines.extend(["", "## Label duplikat", ""])
    if report["label_duplicates"]:
        for group in report["label_duplicates"]:
            lines.append(
                f"- `{group['normalized_label']}`: "
                f"{', '.join(group['diseases'])}"
            )
    else:
        lines.append("Tidak ada.")

    lines.extend(["", "## Catatan audit", ""])
    for note in report["audit_notes"]:
        lines.append(f"- {note}")

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
    print(f"diseases: {report['summary']['diseases']}")
    print(f"environment_missing: {report['summary']['environment_missing']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
