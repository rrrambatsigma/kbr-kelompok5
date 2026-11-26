"""Materialisasi inferred ontology untuk backend (Pellet -> Turtle).

Membaca ``ontology_md.owl``, menjalankan Pellet, lalu menyimpan gabungan
triple asserted + inferred ke ``ontology_md_inferred.ttl`` (dibaca backend).
"""

from __future__ import annotations

import sys
from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.namespace import RDF, OWL

ONTO_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ONTO_DIR))

from reasoner_utils import sync_reasoner_for_tests  # noqa: E402
from tbox import ONTOLOGY_IRI  # noqa: E402

INPUT_OWL = ONTO_DIR / "ontology_md.owl"
INPUT_TTL = ONTO_DIR / "ontology_md.ttl"
OUTPUT_TTL = ONTO_DIR / "ontology_md_inferred.ttl"
SWRL_IMP = URIRef("http://www.w3.org/2003/11/swrl#Imp")


def _load_asserted() -> Graph:
    graph = Graph()
    graph.parse(INPUT_TTL, format="turtle")
    return graph


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
    serialized = inferred.serialize(format="turtle")
    OUTPUT_TTL.write_text(serialized, encoding="utf-8", newline="")
    saved = Graph()
    saved.parse(data=serialized, format="turtle")
    inferred_count = len(saved)
    swrl_count = len(set(saved.subjects(RDF.type, SWRL_IMP)))
    added = inferred_count - len(asserted)
    print(f"output: {OUTPUT_TTL}")
    print(f"triples: {inferred_count} (asserted {len(asserted)}, added {added})")
    print(f"swrl rules: {swrl_count}")
    return inferred_count


def main() -> int:
    if not INPUT_OWL.exists() or not INPUT_TTL.exists():
        print("artefak ontology_md.ttl/.owl belum ada; jalankan build_ontology_md.py")
        return 1
    return 0 if materialize() else 1


if __name__ == "__main__":
    raise SystemExit(main())
