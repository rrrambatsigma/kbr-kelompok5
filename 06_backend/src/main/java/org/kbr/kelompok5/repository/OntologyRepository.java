package org.kbr.kelompok5.repository;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

import org.apache.jena.query.Query;
import org.apache.jena.query.QueryExecution;
import org.apache.jena.query.QueryExecutionDatasetBuilder;
import org.apache.jena.query.QueryFactory;
import org.apache.jena.query.QuerySolution;
import org.apache.jena.query.ResultSet;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.NodeIterator;
import org.apache.jena.rdf.model.Property;
import org.apache.jena.rdf.model.RDFNode;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdf.model.Statement;
import org.apache.jena.vocabulary.RDF;
import org.apache.jena.vocabulary.RDFS;
import org.kbr.kelompok5.repository.OntologyRows.ControlRow;
import org.kbr.kelompok5.repository.OntologyRows.DiseaseRow;
import org.kbr.kelompok5.repository.OntologyRows.EntityRef;
import org.kbr.kelompok5.repository.OntologyRows.PathogenRow;
import org.kbr.kelompok5.repository.OntologyRows.PlantRow;
import org.kbr.kelompok5.repository.OntologyRows.ReferenceRow;
import org.kbr.kelompok5.repository.OntologyRows.SymptomRow;
import org.kbr.kelompok5.repository.OntologyRows.VarietyRow;
import org.kbr.kelompok5.util.OntologyIds;
import org.springframework.stereotype.Repository;

/**
 * Satu-satunya layer yang mengetahui detail query RDF/SPARQL.
 */
@Repository
public class OntologyRepository {

    private static final List<String> PATHOGEN_TYPES = List.of(
            "Jamur", "Bakteri", "Virus", "OrganismeLain");

    private static final List<String> CONTROL_TYPES = List.of(
            "PengendalianKulturTeknis",
            "PengendalianKimiawi",
            "PengendalianBiologis",
            "PengendalianMekanis",
            "PengendalianTerpadu");

    private final Model model;

    public OntologyRepository(Model ontologyModel) {
        this.model = ontologyModel;
    }

    // ---------------------------------------------------------------------
    // Katalog tanaman
    // ---------------------------------------------------------------------

    public List<PlantRow> findAllPlants() {
        Query query = QueryFactory.create(OntologyQueries.FIND_ALL_PLANTS);
        List<PlantRow> rows = new ArrayList<>();

        try (QueryExecution execution = QueryExecution.create(query, model)) {
            ResultSet resultSet = execution.execSelect();
            while (resultSet.hasNext()) {
                QuerySolution row = resultSet.next();
                Resource plant = row.getResource("plant");
                rows.add(new PlantRow(
                        localName(plant),
                        text(row, "label", localName(plant)),
                        text(row, "sci", null),
                        null,
                        integer(row, "diseaseCount"),
                        integer(row, "varietyCount"),
                        integer(row, "generalControlCount")));
            }
        }

        return rows;
    }

    public Optional<PlantRow> findPlant(String plantId) {
        Resource plant = resource(plantId);
        if (!hasType(plant, "TanamanPangan")) {
            return Optional.empty();
        }

        return Optional.of(new PlantRow(
                plantId,
                label(plant),
                literal(plant, "namaIlmiah"),
                literal(plant, "deskripsiTanaman"),
                countDistinct(plant, "diserangPenyakit"),
                countDistinct(plant, "memilikiVarietas"),
                countDistinct(plant, "pengendalianUmum")));
    }

    public boolean existsPlant(String plantId) {
        return hasType(resource(plantId), "TanamanPangan");
    }

    // ---------------------------------------------------------------------
    // Katalog penyakit
    // ---------------------------------------------------------------------

    public List<DiseaseRow> findAllDiseases() {
        return diseaseQuery(OntologyQueries.FIND_ALL_DISEASES, null);
    }

    public List<DiseaseRow> findDiseasesByPlant(String plantId) {
        return diseaseQuery(OntologyQueries.FIND_DISEASES_BY_PLANT, plantId);
    }

    public Optional<DiseaseRow> findDisease(String diseaseId) {
        Resource disease = resource(diseaseId);
        if (!hasType(disease, "Penyakit")) {
            return Optional.empty();
        }

        Resource plant = firstResource(disease, "menyerangTanaman");

        return Optional.of(new DiseaseRow(
                diseaseId,
                label(disease),
                ref(plant),
                pathogenNames(disease),
                literal(disease, "deskripsiPenyakit"),
                countDistinct(disease, "memilikiGejala"),
                countDistinct(disease, "dikendalikanDengan")));
    }

    public boolean existsDisease(String diseaseId) {
        return hasType(resource(diseaseId), "Penyakit");
    }

    private List<DiseaseRow> diseaseQuery(String sparql, String plantId) {
        Query query = QueryFactory.create(sparql);
        QueryExecutionDatasetBuilder builder = QueryExecution.create()
                .query(query)
                .model(model);

        if (plantId != null) {
            builder.substitution("plantParam", resource(plantId));
        }

        List<DiseaseRow> rows = new ArrayList<>();

        try (QueryExecution execution = builder.build()) {
            ResultSet resultSet = execution.execSelect();
            while (resultSet.hasNext()) {
                QuerySolution row = resultSet.next();
                Resource disease = row.getResource("disease");
                Resource plant = row.getResource("plant");

                rows.add(new DiseaseRow(
                        localName(disease),
                        text(row, "label", localName(disease)),
                        plant == null ? null : ref(plant),
                        pathogenNames(disease),
                        null,
                        integer(row, "symptomCount"),
                        integer(row, "controlCount")));
            }
        }

        return rows;
    }

    // ---------------------------------------------------------------------
    // Katalog gejala
    // ---------------------------------------------------------------------

    public List<SymptomRow> findAllSymptoms() {
        return symptomQuery(OntologyQueries.FIND_ALL_SYMPTOMS, null, null);
    }

    public List<SymptomRow> findSymptomsByDisease(String diseaseId) {
        return symptomQuery(OntologyQueries.FIND_SYMPTOMS_BY_DISEASE, "diseaseParam", diseaseId);
    }

    public List<SymptomRow> findSymptomsByPlant(String plantId) {
        return symptomQuery(OntologyQueries.FIND_SYMPTOMS_BY_PLANT, "plantParam", plantId);
    }

    public boolean existsSymptom(String symptomId) {
        return hasType(resource(symptomId), "Gejala");
    }

    private List<SymptomRow> symptomQuery(String sparql, String paramName, String paramValue) {
        Query query = QueryFactory.create(sparql);
        QueryExecutionDatasetBuilder builder = QueryExecution.create()
                .query(query)
                .model(model);

        if (paramName != null && paramValue != null) {
            builder.substitution(paramName, resource(paramValue));
        }

        Map<String, SymptomRow> rows = new LinkedHashMap<>();

        try (QueryExecution execution = builder.build()) {
            ResultSet resultSet = execution.execSelect();
            while (resultSet.hasNext()) {
                QuerySolution row = resultSet.next();
                Resource symptom = row.getResource("symptom");
                Resource disease = row.getResource("disease");

                rows.putIfAbsent(localName(symptom), new SymptomRow(
                        localName(symptom),
                        text(row, "label", localName(symptom)),
                        partsOfSymptom(symptom),
                        disease == null ? null : new EntityRef(
                                localName(disease),
                                text(row, "diseaseLabel", label(disease)))));
            }
        }

        return new ArrayList<>(rows.values());
    }

    private List<EntityRef> partsOfSymptom(Resource symptom) {
        return refs(symptom, "terdapatPada");
    }

    // ---------------------------------------------------------------------
    // Detail relasi penyakit
    // ---------------------------------------------------------------------

    public List<PathogenRow> findPathogensOfDisease(String diseaseId) {
        List<PathogenRow> pathogens = new ArrayList<>();

        for (Resource pathogen : resources(resource(diseaseId), "disebabkanOleh")) {
            List<String> types = typesOf(pathogen, PATHOGEN_TYPES);

            pathogens.add(new PathogenRow(
                    localName(pathogen),
                    label(pathogen),
                    firstNonNull(literal(pathogen, "namaIlmiahPatogen"), label(pathogen)),
                    types.isEmpty() ? null : types.get(0)));
        }

        pathogens.sort(Comparator.comparing(
                PathogenRow::id,
                Comparator.nullsLast(String.CASE_INSENSITIVE_ORDER)));

        return pathogens;
    }

    public List<ControlRow> findControlsOfDisease(String diseaseId) {
        return controls(resource(diseaseId), "dikendalikanDengan", "DISEASE");
    }

    public List<ControlRow> findGeneralControlsOfPlant(String plantId) {
        return controls(resource(plantId), "pengendalianUmum", "GENERAL");
    }

    public List<EntityRef> findPartsOfDisease(String diseaseId) {
        return refs(resource(diseaseId), "menyerangBagian");
    }

    public List<EntityRef> findPhasesOfDisease(String diseaseId) {
        return refs(resource(diseaseId), "menyerangFase");
    }

    public List<EntityRef> findEnvironmentalFactorsOfDisease(String diseaseId) {
        return refs(resource(diseaseId), "dipengaruhiOleh");
    }

    public List<ReferenceRow> findReferencesOfDisease(String diseaseId) {
        List<ReferenceRow> references = new ArrayList<>();

        for (Resource reference : resources(resource(diseaseId), "memilikiReferensi")) {
            references.add(new ReferenceRow(
                    localName(reference),
                    literal(reference, "judulReferensi"),
                    literal(reference, "namaPenulis"),
                    year(reference),
                    literal(reference, "urlReferensi")));
        }

        references.sort(Comparator.comparing(
                ReferenceRow::title,
                Comparator.nullsLast(String.CASE_INSENSITIVE_ORDER)));

        return references;
    }

    public List<VarietyRow> findVarietiesOfPlant(String plantId) {
        List<VarietyRow> varieties = new ArrayList<>();

        for (Resource variety : resources(resource(plantId), "memilikiVarietas")) {
            varieties.add(new VarietyRow(
                    localName(variety),
                    label(variety),
                    refs(variety, "tahanTerhadap")));
        }

        varieties.sort(Comparator.comparing(
                VarietyRow::label,
                Comparator.nullsLast(String.CASE_INSENSITIVE_ORDER)));

        return varieties;
    }

    public boolean existsPart(String partId) {
        return hasType(resource(partId), "BagianTanaman");
    }

    // ---------------------------------------------------------------------
    // Count / status
    // ---------------------------------------------------------------------

    public long countByType(String typeLocalName) {
        return model.listSubjectsWithProperty(RDF.type, type(typeLocalName))
                .toList()
                .stream()
                .distinct()
                .count();
    }

    // ---------------------------------------------------------------------
    // Helper RDF
    // ---------------------------------------------------------------------

    private List<ControlRow> controls(Resource subject, String propertyName, String source) {
        Map<String, ControlRow> rows = new LinkedHashMap<>();

        for (Resource control : resources(subject, propertyName)) {
            rows.putIfAbsent(localName(control), new ControlRow(
                    localName(control),
                    firstNonNull(
                            literal(control, "deskripsiPengendalian"),
                            label(control)),
                    typesOf(control, CONTROL_TYPES),
                    source));
        }

        List<ControlRow> result = new ArrayList<>(rows.values());
        result.sort(Comparator.comparing(
                ControlRow::label,
                Comparator.nullsLast(String.CASE_INSENSITIVE_ORDER)));
        return result;
    }

    private List<String> pathogenNames(Resource disease) {
        return resources(disease, "disebabkanOleh").stream()
                .map(pathogen -> firstNonNull(
                        literal(pathogen, "namaIlmiahPatogen"),
                        label(pathogen)))
                .sorted(String.CASE_INSENSITIVE_ORDER)
                .toList();
    }

    private List<EntityRef> refs(Resource subject, String propertyName) {
        Map<String, EntityRef> refs = new LinkedHashMap<>();

        for (Resource resource : resources(subject, propertyName)) {
            refs.putIfAbsent(localName(resource), ref(resource));
        }

        List<EntityRef> result = new ArrayList<>(refs.values());
        result.sort(Comparator.comparing(
                EntityRef::label,
                Comparator.nullsLast(String.CASE_INSENSITIVE_ORDER)));
        return result;
    }

    private EntityRef ref(Resource resource) {
        if (resource == null) {
            return null;
        }
        return new EntityRef(localName(resource), label(resource));
    }

    private List<String> typesOf(Resource subject, List<String> candidates) {
        Set<String> allowed = new LinkedHashSet<>(candidates);

        return model.listObjectsOfProperty(subject, RDF.type)
                .toList()
                .stream()
                .filter(RDFNode::isResource)
                .map(node -> node.asResource().getLocalName())
                .filter(allowed::contains)
                .sorted()
                .toList();
    }

    private List<Resource> resources(Resource subject, String propertyName) {
        Map<String, Resource> resources = new LinkedHashMap<>();

        NodeIterator iterator = model.listObjectsOfProperty(subject, property(propertyName));
        try {
            while (iterator.hasNext()) {
                RDFNode node = iterator.next();
                if (node.isResource()) {
                    Resource resource = node.asResource();
                    resources.putIfAbsent(resource.getURI(), resource);
                }
            }
        } finally {
            iterator.close();
        }

        return new ArrayList<>(resources.values());
    }

    private Resource firstResource(Resource subject, String propertyName) {
        NodeIterator iterator = model.listObjectsOfProperty(subject, property(propertyName));
        try {
            while (iterator.hasNext()) {
                RDFNode node = iterator.next();
                if (node.isResource()) {
                    return node.asResource();
                }
            }
        } finally {
            iterator.close();
        }
        return null;
    }

    private int countDistinct(Resource subject, String propertyName) {
        return (int) model.listObjectsOfProperty(subject, property(propertyName))
                .toList()
                .stream()
                .distinct()
                .count();
    }

    private boolean hasType(Resource resource, String typeLocalName) {
        return model.contains(resource, RDF.type, type(typeLocalName));
    }

    private String label(Resource resource) {
        if (resource == null) {
            return null;
        }

        Statement statement = resource.getProperty(RDFS.label);
        String label = null;
        if (statement != null && statement.getObject().isLiteral()) {
            label = statement.getObject().asLiteral().getLexicalForm();
        }

        return firstNonNull(label, localName(resource));
    }

    private String literal(Resource resource, String propertyLocalName) {
        if (resource == null) {
            return null;
        }

        Statement statement = resource.getProperty(property(propertyLocalName));
        if (statement == null) {
            return null;
        }

        RDFNode object = statement.getObject();
        if (object.isLiteral()) {
            return object.asLiteral().getLexicalForm();
        }
        if (object.isResource()) {
            return localName(object.asResource());
        }
        return object.toString();
    }

    private Integer year(Resource reference) {
        String value = literal(reference, "tahunTerbit");
        if (value == null) {
            return null;
        }

        String digits = value.replaceAll("[^0-9]", "");
        if (digits.length() < 4) {
            return null;
        }

        try {
            return Integer.valueOf(digits.substring(0, 4));
        } catch (NumberFormatException exception) {
            return null;
        }
    }

    private Resource resource(String localName) {
        return model.getResource(OntologyIds.iri(localName));
    }

    private Resource type(String localName) {
        return model.getResource(OntologyIds.iri(localName));
    }

    private Property property(String localName) {
        return model.createProperty(OntologyIds.iri(localName));
    }

    private String localName(Resource resource) {
        return OntologyIds.localName(resource);
    }

    private String text(QuerySolution row, String variable, String fallback) {
        RDFNode node = row.get(variable);
        if (node == null || !node.isLiteral()) {
            return fallback;
        }
        return node.asLiteral().getLexicalForm();
    }

    private int integer(QuerySolution row, String variable) {
        RDFNode node = row.get(variable);
        if (node == null || !node.isLiteral()) {
            return 0;
        }
        return node.asLiteral().getInt();
    }

    private String firstNonNull(String first, String second) {
        return first != null ? first : second;
    }
}
