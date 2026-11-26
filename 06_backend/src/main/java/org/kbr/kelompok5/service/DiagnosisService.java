package org.kbr.kelompok5.service;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.apache.jena.query.Query;
import org.apache.jena.query.QueryExecution;
import org.apache.jena.query.QueryExecutionFactory;
import org.apache.jena.query.QueryFactory;
import org.apache.jena.query.QuerySolution;
import org.apache.jena.query.ResultSet;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.RDFNode;
import org.springframework.stereotype.Service;

@Service
public class DiagnosisService {

    private final Model model;

    public DiagnosisService(Model model) {
        this.model = model;
    }

    public List<Map<String, String>> listDiagnoses() {
        String sparql = """
            PREFIX kbr: <http://kbr.kelompok5.org/penyakit-tanaman-pangan#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?diagnosis ?label ?plant ?plantLabel WHERE {
              ?diagnosis a kbr:Diagnosis .
              OPTIONAL { ?diagnosis rdfs:label ?label }
              OPTIONAL {
                ?diagnosis kbr:memilikiTanaman ?plant .
                OPTIONAL { ?plant rdfs:label ?plantLabel }
              }
            }
            ORDER BY ?diagnosis
            """;

        List<Map<String, String>> rows = new ArrayList<>();
        for (Map<String, String> row : select(sparql)) {
            Map<String, String> item = new LinkedHashMap<>();
            item.put("id", localName(row.get("diagnosis")));
            item.put("label", row.getOrDefault("label", ""));
            item.put("plant", localName(row.getOrDefault("plant", "")));
            item.put("plantLabel", row.getOrDefault("plantLabel", ""));
            rows.add(item);
        }
        return rows;
    }

    public Map<String, Object> getDiagnosis(String localName) {
        Map<String, String> header = first(select("""
            PREFIX kbr: <http://kbr.kelompok5.org/penyakit-tanaman-pangan#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?diagnosis ?label ?plant ?plantLabel WHERE {
              ?diagnosis a kbr:Diagnosis .
              FILTER(REPLACE(STR(?diagnosis), "^.*[/#]", "") = "%s")
              OPTIONAL { ?diagnosis rdfs:label ?label }
              OPTIONAL {
                ?diagnosis kbr:memilikiTanaman ?plant .
                OPTIONAL { ?plant rdfs:label ?plantLabel }
              }
            }
            LIMIT 1
            """.formatted(localName.replace("\"", ""))));
        if (header == null) {
            return null;
        }

        String diagnosisUri = header.get("diagnosis");
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("id", localName);
        result.put("label", header.getOrDefault("label", ""));
        result.put("plant", localName(header.getOrDefault("plant", "")));
        result.put("plantLabel", header.getOrDefault("plantLabel", ""));
        result.put("diseases", related(diagnosisUri, "menghasilkanPenyakit"));
        result.put("controls", related(diagnosisUri, "merekomendasikanPengendalian"));
        result.put("strongCandidates", related(diagnosisUri, "kandidatKuat"));
        result.put("recommendedVarieties", related(diagnosisUri, "merekomendasikanVarietas"));
        result.put("environmentalRisks", related(diagnosisUri, "menandaiRisikoLingkungan"));
        return result;
    }

    private List<Map<String, String>> related(String subjectUri, String property) {
        String sparql = """
            PREFIX kbr: <http://kbr.kelompok5.org/penyakit-tanaman-pangan#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT DISTINCT ?item ?label WHERE {
              <%s> kbr:%s ?item .
              OPTIONAL { ?item rdfs:label ?label }
            }
            ORDER BY ?label
            """.formatted(subjectUri, property);

        List<Map<String, String>> rows = new ArrayList<>();
        for (Map<String, String> row : select(sparql)) {
            Map<String, String> item = new LinkedHashMap<>();
            item.put("id", localName(row.getOrDefault("item", "")));
            item.put("label", row.getOrDefault("label", ""));
            rows.add(item);
        }
        return rows;
    }

    private List<Map<String, String>> select(String sparql) {
        Query query = QueryFactory.create(sparql);
        List<Map<String, String>> rows = new ArrayList<>();
        try (QueryExecution execution = QueryExecutionFactory.create(query, model)) {
            ResultSet resultSet = execution.execSelect();
            List<String> variables = resultSet.getResultVars();
            while (resultSet.hasNext()) {
                QuerySolution solution = resultSet.next();
                Map<String, String> row = new LinkedHashMap<>();
                for (String variable : variables) {
                    RDFNode node = solution.get(variable);
                    if (node == null) {
                        continue;
                    }
                    row.put(variable, lexical(node));
                }
                rows.add(row);
            }
        }
        return rows;
    }

    private Map<String, String> first(List<Map<String, String>> rows) {
        return rows.isEmpty() ? null : rows.getFirst();
    }

    private String lexical(RDFNode node) {
        if (node.isLiteral()) {
            return node.asLiteral().getLexicalForm();
        }
        return node.asResource().getURI();
    }

    private String localName(String uri) {
        if (uri == null || uri.isBlank()) {
            return "";
        }
        int hash = uri.lastIndexOf('#');
        int slash = uri.lastIndexOf('/');
        int index = Math.max(hash, slash);
        return index >= 0 ? uri.substring(index + 1) : uri;
    }
}
