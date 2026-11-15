package id.ac.uns.kbr.reasoning_api.service;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.springframework.stereotype.Service;

import id.ac.uns.kbr.reasoning_api.exception.OntologyInconsistentException;
import id.ac.uns.kbr.reasoning_api.model.OntologySnapshot;

/**
 * Read-only reasoning operations built on top of {@link OntologyProvider}.
 *
 * <p>Disease categories are computed during reload and served from an
 * immutable cache. No request handler queries the reasoner directly, so
 * concurrent requests cannot corrupt Openllet state.</p>
 */
@Service
public class ReasoningService {

    private final OntologyProvider ontologyProvider;

    public ReasoningService(OntologyProvider ontologyProvider) {
        this.ontologyProvider = ontologyProvider;
    }

    public Map<String, Object> status() {
        Map<String, Object> data = new LinkedHashMap<>();

        OntologySnapshot snapshot = ontologyProvider.current().orElse(null);

        data.put("loaded", snapshot != null);
        data.put("ready", snapshot != null && snapshot.consistent());
        data.put("consistent", snapshot != null && snapshot.consistent());

        if (snapshot == null) {
            data.put("ontologyIri", null);
            data.put("version", null);
            data.put("checksum", null);
            data.put("sourceFile", ontologyProvider.ontologyPath().getFileName().toString());
            data.put("loadedAt", null);
            data.put("classCount", 0);
            data.put("individualCount", 0);
            data.put("objectPropertyCount", 0);
            data.put("dataPropertyCount", 0);
            data.put("diseaseCategoryCounts", zeroCategoryCounts());
            data.put("unclassifiedDiseaseCount", 0);
            data.put("lastError", ontologyProvider.lastError());
            return data;
        }

        data.put("ontologyIri", snapshot.ontologyIri());
        data.put("version", snapshot.versionInfo());
        data.put("checksum", snapshot.checksum());
        data.put("sourceFile", snapshot.sourceFile());
        data.put("loadedAt", snapshot.loadedAt().toString());
        data.put("classCount", snapshot.classCount());
        data.put("individualCount", snapshot.individualCount());
        data.put("objectPropertyCount", snapshot.objectPropertyCount());
        data.put("dataPropertyCount", snapshot.dataPropertyCount());
        data.put("diseaseCategoryCounts", snapshot.diseaseCategoryCounts());
        data.put("unclassifiedDiseaseCount", snapshot.unclassifiedDiseaseCount());
        data.put("lastError", ontologyProvider.lastError());

        return data;
    }

    public Map<String, Object> consistency() {
        Map<String, Object> data = new LinkedHashMap<>();
        OntologySnapshot snapshot = ontologyProvider.current().orElse(null);

        data.put("loaded", snapshot != null);
        data.put("consistent", snapshot != null && snapshot.consistent());
        data.put("ready", snapshot != null && snapshot.consistent());
        return data;
    }

    /**
     * Returns the inferred disease category for the requested IRIs.
     *
     * <p>If {@code diseaseIris} is null or empty, the full cached mapping is
     * returned. IRIs may be full IRIs or local names in the ptp: namespace.</p>
     */
    public Map<String, Object> diseaseCategories(List<String> diseaseIris) {
        return ontologyProvider.withSnapshot(snapshot -> {
            if (!snapshot.consistent()) {
                throw new OntologyInconsistentException(
                        "Ontology tidak konsisten; kategori penyakit tidak dapat dihitung"
                );
            }

            Map<String, String> allCategories = snapshot.diseaseCategoryByIri();
            Map<String, String> categories = new LinkedHashMap<>();

            List<String> requested = normaliseRequest(diseaseIris);

            if (requested.isEmpty()) {
                categories.putAll(allCategories);
            } else {
                for (String iri : requested) {
                    String category = allCategories.get(iri);
                    if (category != null) {
                        categories.put(iri, category);
                    }
                }
            }

            List<String> missing = new ArrayList<>();
            if (!requested.isEmpty()) {
                for (String iri : requested) {
                    if (!categories.containsKey(iri)) {
                        missing.add(iri);
                    }
                }
            }

            Map<String, Object> data = new LinkedHashMap<>();
            data.put("categories", categories);
            data.put("counts", snapshot.diseaseCategoryCounts());
            data.put("unclassifiedDiseaseCount", snapshot.unclassifiedDiseaseCount());
            data.put("requestedCount", requested.isEmpty() ? allCategories.size() : requested.size());
            data.put("foundCount", categories.size());
            data.put("missing", missing);
            return data;
        });
    }

    public List<String> diseaseCategoryNames() {
        return OntologyProvider.DISEASE_CATEGORIES;
    }

    private List<String> normaliseRequest(List<String> diseaseIris) {
        List<String> result = new ArrayList<>();
        if (diseaseIris == null) {
            return result;
        }

        for (String raw : diseaseIris) {
            if (raw == null || raw.isBlank()) {
                continue;
            }
            String trimmed = raw.trim();
            if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
                result.add(trimmed);
            } else {
                result.add(OntologyProvider.PTP_NAMESPACE + trimmed);
            }
        }
        return result;
    }

    private Map<String, Long> zeroCategoryCounts() {
        Map<String, Long> counts = new LinkedHashMap<>();
        for (String category : diseaseCategoryNames()) {
            counts.put(category, 0L);
        }
        return counts;
    }
}
