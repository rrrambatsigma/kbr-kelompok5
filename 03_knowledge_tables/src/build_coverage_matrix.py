from __future__ import annotations

import csv
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
INTERNAL_FACTS = TABLE_DIR / "auto" / "DOC002_md" / "DOC002_enrichment_facts.csv"
EXTERNAL_FACTS = TABLE_DIR / "auto" / "EXTERNAL_ENV" / "EXTERNAL_ENV_facts.csv"
OUTPUT_CSV = TABLE_DIR / "reports" / "EXTERNAL_ENV" / "coverage_matrix.csv"

PLANT_ORDER = {
    "Padi": 0,
    "Kedelai": 1,
    "Jagung": 2,
    "UbiJalar": 3,
    "UbiKayu": 4,
    "KacangTanah": 5,
    "KacangHijau": 6,
}

COLUMNS = [
    "plant",
    "disease_local",
    "disease_label",
    "status",
    "observation_count",
    "external_observation_count",
    "internal_observation_count",
    "source_ids",
    "notes",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def local_name(uri: object) -> str:
    return str(uri).split("#")[-1]


def build() -> list[dict[str, str]]:
    graph = Graph()
    graph.parse(ONTOLOGY_TTL, format="turtle")

    diseases = sorted(
        {
            local_name(subject)
            for subject in graph.subjects(RDF.type, KBR.Penyakit)
        }
    )
    disease_uri = {disease: KBR[disease] for disease in diseases}

    observations: dict[str, list[dict[str, str]]] = defaultdict(list)
    for path in (INTERNAL_FACTS, EXTERNAL_FACTS):
        for row in read_csv(path):
            if (row.get("predicate") or "").strip() != "dipengaruhiOleh":
                continue
            disease = (row.get("subject_local") or "").strip()
            source_id = (row.get("source_id") or "").strip()
            if not disease or not source_id:
                continue
            observations[disease].append(
                {
                    "source_id": source_id,
                    "external": (
                        (row.get("source_type") or "").strip()
                        == "external_evidence"
                        or (row.get("source_document") or "").startswith(
                            "SRC_EXT_"
                        )
                    ),
                }
            )

    rows: list[dict[str, str]] = []
    for disease in diseases:
        uri = disease_uri[disease]
        plant_names = sorted(
            {
                local_name(plant)
                for plant in graph.objects(uri, KBR.menyerangTanaman)
            }
        )
        plant = plant_names[0] if plant_names else ""
        label = graph.value(uri, RDFS.label)
        graph_observations = list(graph.objects(uri, KBR.dipengaruhiOleh))
        disease_observations = observations.get(disease, [])
        external_count = sum(
            1 for item in disease_observations if item["external"]
        )
        internal_count = max(0, len(graph_observations) - external_count)
        source_ids = sorted(
            {item["source_id"] for item in disease_observations},
            key=lambda value: (not value.startswith("SRC_EXT_"), value),
        )
        if graph_observations and not source_ids:
            source_ids = ["ontology.ttl"]

        if graph_observations:
            status = "covered"
            if external_count and internal_count:
                notes = "terverifikasi eksternal; baseline internal"
            elif external_count:
                notes = "terverifikasi eksternal"
            elif disease_observations:
                notes = "baseline internal saja"
            else:
                notes = "baseline ontology"
        elif plant == "Kedelai":
            status = "pending_3c"
            notes = "belum diverifikasi"
        else:
            status = "no_verified_source"
            notes = "belum ada sumber spesifik"

        rows.append(
            {
                "plant": plant,
                "disease_local": disease,
                "disease_label": str(label) if label else disease,
                "status": status,
                "observation_count": str(len(graph_observations)),
                "external_observation_count": str(external_count),
                "internal_observation_count": str(internal_count),
                "source_ids": ";".join(source_ids),
                "notes": notes,
            }
        )

    rows.sort(
        key=lambda row: (
            PLANT_ORDER.get(row["plant"], 99),
            row["disease_local"],
        )
    )
    return rows


def main() -> int:
    rows = build()
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"output: {OUTPUT_CSV}")
    print(f"diseases: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
