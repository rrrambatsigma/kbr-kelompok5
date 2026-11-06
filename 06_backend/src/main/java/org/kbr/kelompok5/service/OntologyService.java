package org.kbr.kelompok5.service;

import java.util.LinkedHashMap;
import java.util.Map;

import org.apache.jena.rdf.model.Model;
import org.kbr.kelompok5.repository.OntologyRepository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

@Service
public class OntologyService {

    private final Model ontologyModel;
    private final OntologyRepository repository;
    private final String ontologyFile;

    public OntologyService(
            Model ontologyModel,
            OntologyRepository repository,
            @Value("${ontology.file}") String ontologyFile) {
        this.ontologyModel = ontologyModel;
        this.repository = repository;
        this.ontologyFile = ontologyFile;
    }

    public long getTripleCount() {
        return ontologyModel.size();
    }

    public boolean isLoaded() {
        return ontologyModel != null && !ontologyModel.isClosed();
    }

    public String getOntologyFile() {
        return ontologyFile;
    }

    public Map<String, Long> getCounts() {
        Map<String, Long> counts = new LinkedHashMap<>();
        counts.put("plants", repository.countByType("TanamanPangan"));
        counts.put("diseases", repository.countByType("Penyakit"));
        counts.put("symptoms", repository.countByType("Gejala"));
        counts.put("pathogens", repository.countByType("Patogen"));
        counts.put("controls", repository.countByType("Pengendalian"));
        counts.put("varieties", repository.countByType("Varietas"));
        counts.put("plantParts", repository.countByType("BagianTanaman"));
        counts.put("growthPhases", repository.countByType("FasePertumbuhan"));
        counts.put("environmentalFactors", repository.countByType("FaktorLingkungan"));
        counts.put("references", repository.countByType("Referensi"));
        return counts;
    }
}
