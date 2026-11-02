"""Generator ontologi OWL 2 "Penyakit Tanaman Pangan Indonesia".

Membaca knowledge tables hasil kurasi (``03_knowledge_tables``) untuk tiga
tanaman prototipe — Kacang Tanah, Ubi Jalar, Ubi Kayu — lalu membangun ABox
di atas TBox ``tbox.py``. Setiap teks diambil verbatim dari sumber; informasi
yang tidak tersedia dikosongkan, bukan ditebak.

Pemakaian (dari root repo)::

    python 04_ontology/build_ontology.py

Keluaran: ``04_ontology/ontology.ttl`` dan ``ontology.owl``; kode keluar ``2``
bila validasi gagal.
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
from rdflib.namespace import OWL, RDF, RDFS, XSD

ONTO_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = ONTO_DIR.parent
TABLE_DIR = PROJECT_ROOT / "03_knowledge_tables"
CURATED_DIR = TABLE_DIR / "curated"
AUTO_DIR = TABLE_DIR / "auto"
META_PATH = PROJECT_ROOT / "01_knowledge_sources" / "source_metadata" / "manual_metadata.json"
DEFAULT_TTL = ONTO_DIR / "ontology.ttl"
DEFAULT_OWL = ONTO_DIR / "ontology.owl"

sys.path.insert(0, str(ONTO_DIR))

import tbox  # noqa: E402
from tbox import KBR  # noqa: E402

SCOPE_PLANTS = ("PLANT_003", "PLANT_004", "PLANT_005")
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


# ---------------------------------------------------------------- koleksi data

def scope_plants_rows() -> list[dict[str, str]]:
    rows = read_csv(AUTO_DIR / "plants.csv")
    return [r for r in rows if r["plant_id"].strip() in SCOPE_PLANTS]


def penyakit_entries() -> list[dict[str, str]]:
    plants = {r["plant_id"].strip(): r for r in read_csv(AUTO_DIR / "plants.csv")}
    rows = [r for r in read_csv(CURATED_DIR / "diseases.csv") if r["plant_id"].strip() in SCOPE_PLANTS]
    bases: dict[str, list[str]] = {}
    for row in rows:
        plant = plants[row["plant_id"].strip()]
        base = pascal(row["disease_name_verbatim"].strip() + plant["plant_name_id"].strip())
        bases.setdefault(base, []).append(row["disease_id"].strip())
    entries = []
    for row in rows:
        disease_id = row["disease_id"].strip()
        plant = plants[row["plant_id"].strip()]
        nama = row["disease_name_verbatim"].strip()
        base = pascal(nama + plant["plant_name_id"].strip())
        local = base if len(bases[base]) == 1 else base + pascal(disease_id)
        entries.append(
            {
                "disease_id": disease_id,
                "plant_id": row["plant_id"].strip(),
                "plant_local": pascal(plant["plant_name_id"].strip()),
                "nama": nama,
                "local": local,
                "subsection": (row.get("subsection") or "").strip(),
            }
        )
    return entries


def gejala_rows(entries: list[dict[str, str]]) -> tuple[list[tuple[str, str]], list[str]]:
    """Kembalikan pasangan (disease_id, teks_gejala) dan daftar error pencocokan."""
    by_norm: dict[str, list[dict[str, str]]] = {}
    for entry in entries:
        by_norm.setdefault(norm(entry["nama"]), []).append(entry)
    pairs: list[tuple[str, str]] = []
    errors: list[str] = []
    for row in read_csv(CURATED_DIR / "symptoms.csv"):
        if row["disease_id"].strip() in {e["disease_id"] for e in entries}:
            text = (row.get("verbatim_text") or "").strip()
            if text:
                pairs.append((row["disease_id"].strip(), text))
    for row in read_csv(CURATED_DIR / "ubi_kayu_tabel_5.csv"):
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
        pairs.append((disease_id, text))
    return pairs, errors


def patogen_pairs(entries: list[dict[str, str]]) -> list[tuple[str, dict[str, str]]]:
    scope_ids = {e["disease_id"] for e in entries}
    pathogens = {r["pathogen_id"].strip(): r for r in read_csv(CURATED_DIR / "pathogens.csv")}
    pairs = []
    seen: set[tuple[str, str]] = set()
    for row in read_csv(CURATED_DIR / "disease_pathogen.csv"):
        disease_id = row["disease_id"].strip()
        pathogen_id = row["pathogen_id"].strip()
        if disease_id in scope_ids and (disease_id, pathogen_id) not in seen:
            seen.add((disease_id, pathogen_id))
            pairs.append((disease_id, pathogens[pathogen_id]))
    return pairs


def control_pairs(entries: list[dict[str, str]]) -> list[tuple[str, str]]:
    scope_ids = {e["disease_id"] for e in entries}
    pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in read_csv(CURATED_DIR / "controls.csv"):
        disease_id = row["disease_id"].strip()
        text = (row.get("verbatim_text") or "").strip()
        if disease_id in scope_ids and row["scope"].strip() == "disease" and text:
            if (disease_id, text) not in seen:
                seen.add((disease_id, text))
                pairs.append((disease_id, text))
    return pairs


def gejala_texts_by_disease(pairs: list[tuple[str, str]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for disease_id, text in pairs:
        out.setdefault(disease_id, []).append(text)
    return out


def menyerang_bagian_pairs(
    entries: list[dict[str, str]], pairs: list[tuple[str, str]]
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


def build_tanaman(builder: Builder) -> None:
    for row in scope_plants_rows():
        local = pascal(row["plant_name_id"].strip())
        uri = builder.individual(local, "TanamanPangan")
        builder.label(uri, row.get("plant_name_id"))
        builder.s(uri, "namaIlmiah", row.get("scientific_name"))


def build_referensi(builder: Builder) -> None:
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    info = meta["documents"]["DOC002"]
    uri = builder.individual("BukuDOC002", "Referensi", "Buku")
    builder.label(uri, info.get("title"))
    builder.s(uri, "judulReferensi", info.get("title"))
    year = info.get("publication_year")
    if year is not None:
        builder.graph.add((uri, KBR.tahunTerbit, Literal(int(year), datatype=XSD.integer)))
    authors = ", ".join(info.get("authors") or [])
    builder.s(uri, "namaPenulis", authors or None)


def build_bagi_tanaman(builder: Builder) -> None:
    for name in PART_WORDS.values():
        uri = builder.individual(name, "BagianTanaman")
        builder.label(uri, name)


def build_penyakit(builder: Builder, entries: list[dict[str, str]]) -> None:
    for entry in entries:
        uri = builder.individual(entry["local"], "Penyakit")
        builder.label(uri, entry["nama"])
        builder.link(uri, "menyerangTanaman", KBR[entry["plant_local"]])
        builder.link(uri, "memilikiReferensi", KBR["BukuDOC002"])


def build_patogen(builder: Builder, pairs: list[tuple[str, dict[str, str]]]) -> None:
    entries = {e["disease_id"]: e for e in penyakit_entries()}
    uniq: dict[str, dict[str, str]] = {}
    for _disease_id, row in pairs:
        uniq.setdefault(row["pathogen_id"].strip(), row)
    bases: dict[str, list[str]] = {}
    for pathogen_id, row in uniq.items():
        base = pascal(row["scientific_name"]) or pascal(pathogen_id)
        bases.setdefault(base, []).append(pathogen_id)
    local_by_id: dict[str, str] = {}
    for pathogen_id, row in uniq.items():
        base = pascal(row["scientific_name"]) or pascal(pathogen_id)
        local = base if len(bases[base]) == 1 else base + pascal(pathogen_id)
        local_by_id[pathogen_id] = local
        taxon = (row.get("taxon_group") or "").strip().lower()
        classes = ["Patogen"]
        if taxon in TAXON_CLASS:
            classes.append(TAXON_CLASS[taxon])
        uri = builder.individual(local, *classes)
        builder.label(uri, row.get("scientific_name") or pathogen_id)
        builder.s(uri, "namaIlmiahPatogen", row.get("scientific_name"))
    for disease_id, row in pairs:
        builder.link(
            KBR[entries[disease_id]["local"]],
            "disebabkanOleh",
            KBR[local_by_id[row["pathogen_id"].strip()]],
        )


def build_gejala(builder: Builder, pairs: list[tuple[str, str]]) -> None:
    entries = {e["disease_id"]: e for e in penyakit_entries()}
    cache: dict[str, URIRef] = {}
    for disease_id, text in pairs:
        uri = gejala_uri(text, cache, builder)
        builder.link(KBR[entries[disease_id]["local"]], "memilikiGejala", uri)


def build_menyerang_bagian(builder: Builder, bagian_pairs: list[tuple[str, str]]) -> None:
    entries = {e["disease_id"]: e for e in penyakit_entries()}
    for disease_id, part in bagian_pairs:
        builder.link(KBR[entries[disease_id]["local"]], "menyerangBagian", KBR[part])


def build_pengendalian(builder: Builder, pairs: list[tuple[str, str]]) -> None:
    entries = {e["disease_id"]: e for e in penyakit_entries()}
    cache: dict[str, URIRef] = {}
    for disease_id, text in pairs:
        if text not in cache:
            words = [w for w in text.split() if w][:5]
            local = "Pengendalian" + (pascal(" ".join(words)) or "TanpaTeks") + "_" + short_hash(text)
            uri = builder.individual(local, "Pengendalian")
            builder.label(uri, text)
            builder.s(uri, "deskripsiPengendalian", text)
            cache[text] = uri
        builder.link(KBR[entries[disease_id]["local"]], "dikendalikanDengan", cache[text])


# ------------------------------------------------------------------ ekspektasi

def expected_counts() -> dict:
    entries = penyakit_entries()
    g_pairs, _errors = gejala_rows(entries)
    p_pairs = patogen_pairs(entries)
    c_pairs = control_pairs(entries)
    bagian_pairs = menyerang_bagian_pairs(entries, g_pairs)
    plants = scope_plants_rows()

    gejala_texts = {text for _d, text in g_pairs}
    control_texts = {text for _d, text in c_pairs}
    pathogen_ids = {row["pathogen_id"].strip() for _d, row in p_pairs}
    pathogen_rows = {row["pathogen_id"].strip(): row for _d, row in p_pairs}

    classes: dict[str, int] = {
        "TanamanPangan": len(plants),
        "Penyakit": len(entries),
        "Gejala": len(gejala_texts),
        "Patogen": len(pathogen_ids),
        "BagianTanaman": len(PART_WORDS),
        "Pengendalian": len(control_texts),
        "Referensi": 1,
        "Buku": 1,
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
    classes["NamedIndividual"] = (
        classes["TanamanPangan"]
        + classes["Penyakit"]
        + classes["Gejala"]
        + classes["Patogen"]
        + classes["BagianTanaman"]
        + classes["Pengendalian"]
        + classes["Referensi"]
    )

    properties: dict[str, int] = {
        "menyerangTanaman": len(entries),
        "diserangPenyakit": len(entries),
        "memilikiGejala": len(g_pairs),
        "merupakanGejalaDari": len(g_pairs),
        "disebabkanOleh": len(p_pairs),
        "menyebabkanPenyakit": len(p_pairs),
        "menyerangBagian": len(bagian_pairs),
        "terdapatPada": sum(len({p for p in text_parts(text)}) for text in gejala_texts),
        "dikendalikanDengan": len(c_pairs),
        "mengendalikanPenyakit": len(c_pairs),
        "memilikiReferensi": len(entries),
        "dijelaskanDalam": len(entries),
    }
    data_properties: dict[str, int] = {
        "namaIlmiah": sum(1 for r in plants if (r.get("scientific_name") or "").strip()),
        "namaIlmiahPatogen": sum(
            1 for r in pathogen_rows.values() if (r.get("scientific_name") or "").strip()
        ),
        "deskripsiGejala": len(gejala_texts),
        "deskripsiPengendalian": len(control_texts),
        "judulReferensi": 1,
        "tahunTerbit": 1,
        "namaPenulis": 1,
    }
    return {"classes": classes, "properties": properties, "data_properties": data_properties}


def build() -> tuple[Graph, dict, list[str], Builder]:
    builder = Builder()
    tbox.build_tbox(builder.graph)
    builder.graph.bind("ptp", KBR)

    entries = penyakit_entries()
    g_pairs, g_errors = gejala_rows(entries)
    builder.errors.extend(g_errors)
    p_pairs = patogen_pairs(entries)
    c_pairs = control_pairs(entries)
    bagian_pairs = menyerang_bagian_pairs(entries, g_pairs)

    build_referensi(builder)
    build_tanaman(builder)
    build_bagi_tanaman(builder)
    build_penyakit(builder, entries)
    build_patogen(builder, p_pairs)
    build_gejala(builder, g_pairs)
    build_menyerang_bagian(builder, bagian_pairs)
    build_pengendalian(builder, c_pairs)

    expected = expected_counts()
    errors = validate(builder.graph, builder, expected)
    return builder.graph, expected, errors, builder


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
        domain, rng = KBR[spec["domain"]], KBR[spec["range"]]
        for subj, obj in graph.subject_objects(KBR[name]):
            if (subj, RDF.type, domain) not in graph:
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

    restr_found = set()
    for sub_cls, prop, target, quant in tbox.RESTRICTIONS:
        for node in graph.objects(KBR[sub_cls], RDFS.subClassOf):
            if (node, OWL.onProperty, KBR[prop]) in graph:
                quantifier = OWL.someValuesFrom if quant == "some" else OWL.allValuesFrom
                if (node, quantifier, KBR[target]) in graph:
                    restr_found.add((sub_cls, prop, quant))
    for sub_cls, prop, _target, quant in tbox.RESTRICTIONS:
        if (sub_cls, prop, quant) not in restr_found:
            errors.append(f"restriction hilang: {sub_cls} {quant} {prop}")

    if len(list(graph.subject_objects(OWL.disjointWith))) != len(tbox.DISJOINT_PAIRS):
        errors.append(
            f"jumlah disjointWith: {len(list(graph.subject_objects(OWL.disjointWith)))} "
            f"!= {len(tbox.DISJOINT_PAIRS)}"
        )

    if len(list(graph.subject_objects(OWL.inverseOf))) != 10:
        errors.append(f"jumlah inverseOf: {len(list(graph.subject_objects(OWL.inverseOf)))} != 10")

    for forbidden in ("PenyakitJamur", "PenyakitBakteri", "PenyakitVirus", "PenyakitLainnya"):
        explicit = list(graph.subjects(RDF.type, KBR[forbidden]))
        if explicit:
            errors.append(f"{forbidden} tidak boleh di-assert eksplisit (harus inferensi reasoner)")

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

    graph, expected, errors, builder = build()
    if errors:
        print("VALIDASI GAGAL:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 2

    args.out.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=str(args.out), format="turtle")
    owl_path = args.out.with_suffix(".owl")
    graph.serialize(destination=str(owl_path), format="xml")
    individuals = len(list(graph.subjects(RDF.type, OWL.NamedIndividual)))
    cls = expected["classes"]
    print(f"ontologi ditulis: {args.out} dan {owl_path}")
    print(
        f"triple: {len(graph)} | individu: {individuals} | penyakit: {cls['Penyakit']} | "
        f"gejala: {cls['Gejala']} | patogen: {cls['Patogen']} | pengendalian: {cls['Pengendalian']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
