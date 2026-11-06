package org.kbr.kelompok5.repository;

/**
 * Query SPARQL yang dipakai repository.
 */
public final class OntologyQueries {

    private OntologyQueries() {
    }

    private static final String PREFIXES = """
            PREFIX ptp: <http://kbr.kelompok5.org/penyakit-tanaman-pangan#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            """;

    public static final String FIND_ALL_PLANTS = PREFIXES + """
            SELECT ?plant ?label ?sci
                   (COUNT(DISTINCT ?d) AS ?diseaseCount)
                   (COUNT(DISTINCT ?v) AS ?varietyCount)
                   (COUNT(DISTINCT ?gc) AS ?generalControlCount)
            WHERE {
              ?plant a ptp:TanamanPangan .
              OPTIONAL { ?plant rdfs:label ?label }
              OPTIONAL { ?plant ptp:namaIlmiah ?sci }
              OPTIONAL { ?plant ptp:diserangPenyakit ?d }
              OPTIONAL { ?plant ptp:memilikiVarietas ?v }
              OPTIONAL { ?plant ptp:pengendalianUmum ?gc }
            }
            GROUP BY ?plant ?label ?sci
            ORDER BY LCASE(?label)
            """;

    public static final String FIND_ALL_DISEASES = PREFIXES + """
            SELECT ?disease ?label ?plant ?plantLabel
                   (COUNT(DISTINCT ?symptom) AS ?symptomCount)
                   (COUNT(DISTINCT ?control) AS ?controlCount)
            WHERE {
              ?disease a ptp:Penyakit .
              OPTIONAL { ?disease rdfs:label ?label }
              OPTIONAL {
                ?disease ptp:menyerangTanaman ?plant .
                OPTIONAL { ?plant rdfs:label ?plantLabel }
              }
              OPTIONAL { ?disease ptp:memilikiGejala ?symptom }
              OPTIONAL { ?disease ptp:dikendalikanDengan ?control }
            }
            GROUP BY ?disease ?label ?plant ?plantLabel
            ORDER BY LCASE(?label)
            """;

    public static final String FIND_DISEASES_BY_PLANT = PREFIXES + """
            SELECT ?disease ?label ?plant ?plantLabel
                   (COUNT(DISTINCT ?symptom) AS ?symptomCount)
                   (COUNT(DISTINCT ?control) AS ?controlCount)
            WHERE {
              ?disease a ptp:Penyakit .
              OPTIONAL { ?disease rdfs:label ?label }
              OPTIONAL {
                ?disease ptp:menyerangTanaman ?plant .
                OPTIONAL { ?plant rdfs:label ?plantLabel }
              }
              OPTIONAL { ?disease ptp:memilikiGejala ?symptom }
              OPTIONAL { ?disease ptp:dikendalikanDengan ?control }
              FILTER(?plant = ?plantParam)
            }
            GROUP BY ?disease ?label ?plant ?plantLabel
            ORDER BY LCASE(?label)
            """;

    public static final String FIND_ALL_SYMPTOMS = PREFIXES + """
            SELECT ?symptom ?label ?disease ?diseaseLabel
            WHERE {
              ?symptom a ptp:Gejala .
              OPTIONAL { ?symptom rdfs:label ?label }
              OPTIONAL {
                ?symptom ptp:merupakanGejalaDari ?disease .
                OPTIONAL { ?disease rdfs:label ?diseaseLabel }
              }
            }
            ORDER BY LCASE(?label)
            """;

    public static final String FIND_SYMPTOMS_BY_DISEASE = PREFIXES + """
            SELECT ?symptom ?label ?disease ?diseaseLabel
            WHERE {
              ?symptom a ptp:Gejala .
              OPTIONAL { ?symptom rdfs:label ?label }
              OPTIONAL {
                ?symptom ptp:merupakanGejalaDari ?disease .
                OPTIONAL { ?disease rdfs:label ?diseaseLabel }
              }
              FILTER(?disease = ?diseaseParam)
            }
            ORDER BY LCASE(?label)
            """;

    public static final String FIND_SYMPTOMS_BY_PLANT = PREFIXES + """
            SELECT DISTINCT ?symptom ?label ?disease ?diseaseLabel
            WHERE {
              ?plant ptp:diserangPenyakit ?disease .
              ?disease ptp:memilikiGejala ?symptom .
              OPTIONAL { ?symptom rdfs:label ?label }
              OPTIONAL { ?disease rdfs:label ?diseaseLabel }
              FILTER(?plant = ?plantParam)
            }
            ORDER BY LCASE(?label)
            """;
}
