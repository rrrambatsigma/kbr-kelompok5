"""Materialisasi ontology untuk backend (Pellet -> Turtle).

Membaca ``ontology_md.owl``, menjalankan Pellet, lalu menyimpan:

- ``ontology_md.ttl``: asserted + closure tipe + assertion kepala aturan SWRL.
  Artefak ini dibaca reasoning-api (Openllet) dan Protégé.
- ``ontology_md_inferred.ttl``: closure Pellet penuh, dibaca Fuseki/node-api.

Openllet 2.6.x menggelembungkan jaringan Rete bila aturan SWRL harus
menurunkan seluruh kepala aturan dari nol pada ontology ini. Karena itu
``ontology_md.ttl`` memuat hasil materialisasi SWRL dan closure tipe,
seperti artefak backend sebelum ontology baru.
"""

from __future__ import annotations

import sys
from pathlib import Path

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, OWL

ONTO_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ONTO_DIR))

from reasoner_utils import sync_reasoner_for_tests  # noqa: E402
from tbox import ONTOLOGY_IRI  # noqa: E402

INPUT_OWL = ONTO_DIR / "ontology_md.owl"
INPUT_TTL = ONTO_DIR / "ontology_md.ttl"
OUTPUT_TTL = ONTO_DIR / "ontology_md_inferred.ttl"
SWRL_IMP = URIRef("http://www.w3.org/2003/11/swrl#Imp")
KBR = Namespace("http://kbr.kelompok5.org/penyakit-tanaman-pangan#")

# Predikat kepala aturan di swrl_rules.ttl. Assertion-nya ikut disimpan ke
# ontology_md.ttl agar Openllet tidak perlu menurunkannya ulang dari nol.
RULE_HEAD_PREDICATES = (
    KBR.menghasilkanPenyakit,
    KBR.kandidatKuat,
    KBR.merekomendasikanPengendalian,
    KBR.merekomendasikanVarietas,
    KBR.menandaiRisikoLingkungan,
)


SKIP_TYPE_OBJECTS = {
    OWL.Class,
    OWL.ObjectProperty,
    OWL.DatatypeProperty,
    OWL.AnnotationProperty,
    OWL.Ontology,
    OWL.Restriction,
    OWL.NamedIndividual,
    OWL.AllDisjointClasses,
}


def _type_closure(graph: Graph) -> int:
    """Materialisasi tipe superclass untuk setiap individu.

    ``owlready2`` menuliskan nilai properti hasil inferensi, tetapi tidak
    menuliskan keanggotaan kelas turunan (mis. individu ``Jamur`` tidak
    otomatis bertipe ``Patogen``). Backend memakai tipe superclass pada
    query SPARQL, jadi closure ini ditambahkan sebelum artefak disimpan.
    """
    parents: dict[URIRef, set[URIRef]] = {}
    for child, parent in graph.subject_objects(RDFS.subClassOf):
        if isinstance(child, URIRef) and isinstance(parent, URIRef):
            parents.setdefault(child, set()).add(parent)

    cache: dict[URIRef, set[URIRef]] = {}

    def ancestors(cls: URIRef) -> set[URIRef]:
        if cls in cache:
            return cache[cls]
        seen: set[URIRef] = set()
        stack = list(parents.get(cls, ()))
        while stack:
            item = stack.pop()
            if item in seen:
                continue
            seen.add(item)
            stack.extend(parents.get(item, ()))
        cache[cls] = seen
        return seen

    added = 0
    for individual, cls in list(graph.subject_objects(RDF.type)):
        if not isinstance(individual, URIRef) or not isinstance(cls, URIRef):
            continue
        if cls in SKIP_TYPE_OBJECTS or str(cls).startswith(str(OWL)):
            continue
        for parent in ancestors(cls):
            if (individual, RDF.type, parent) not in graph:
                graph.add((individual, RDF.type, parent))
                added += 1
    return added


def _load_asserted() -> Graph:
    graph = Graph()
    graph.parse(INPUT_TTL, format="turtle")
    return graph


def _materialize_asserted(asserted: Graph, inferred: Graph) -> Graph:
    """Asserted + closure tipe + assertion kepala aturan SWRL.

    Closure tipe membuat semua keanggotaan kelas (termasuk tipe superclass
    seperti ``Jamur`` -> ``Patogen``) eksplisit, sehingga Openllet tidak
    menghitung ulang klasifikasi saat menjalankan Rete. Assertion kepala
    aturan mencegah Rete menurunkan ulang ratusan triple pada setiap start.
    """
    materialized = Graph()
    for triple in asserted:
        materialized.add(triple)
    for subject, cls in inferred.subject_objects(RDF.type):
        if isinstance(subject, URIRef) and isinstance(cls, URIRef):
            materialized.add((subject, RDF.type, cls))
    for predicate in RULE_HEAD_PREDICATES:
        for subject, obj in inferred.subject_objects(predicate):
            materialized.add((subject, predicate, obj))
    return materialized


def materialize() -> int:
    from owlready2 import World

    asserted = _load_asserted()
    world = World()
    onto = world.get_ontology(str(ONTOLOGY_IRI))
    with INPUT_OWL.open("rb") as handle:
        onto.load(fileobj=handle, format="rdfxml")

    sync_reasoner_for_tests(onto, infer_property_values=True)

    inferred = world.as_rdflib_graph()
    anonymous = URIRef("http://anonymous")
    for triple in list(inferred.triples((anonymous, None, None))):
        inferred.remove(triple)
    saved = Graph()
    saved.parse(data=inferred.serialize(format="turtle"), format="turtle")
    closure_added = _type_closure(saved)
    serialized = saved.serialize(format="turtle")
    OUTPUT_TTL.write_text(serialized, encoding="utf-8", newline="")
    inferred_count = len(saved)

    materialized = _materialize_asserted(asserted, saved)
    INPUT_TTL.write_text(
        materialized.serialize(format="turtle"), encoding="utf-8", newline=""
    )

    swrl_count = len(set(saved.subjects(RDF.type, SWRL_IMP)))
    added = inferred_count - len(asserted)
    print(f"output: {OUTPUT_TTL}")
    print(
        f"triples: {inferred_count} (asserted {len(asserted)}, "
        f"added {added}, closure +{closure_added})"
    )
    print(f"backend artifact: {INPUT_TTL} ({len(materialized)} triples)")
    print(f"swrl rules: {swrl_count}")
    return inferred_count


def main() -> int:
    if not INPUT_OWL.exists() or not INPUT_TTL.exists():
        print("artefak ontology_md.ttl/.owl belum ada; jalankan build_ontology_md.py")
        return 1
    return 0 if materialize() else 1


if __name__ == "__main__":
    raise SystemExit(main())
