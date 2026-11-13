
package id.ac.uns.kbr.reasoning_api.service;

import openllet.owlapi.OpenlletReasoner;
import openllet.owlapi.OpenlletReasonerFactory;

import org.semanticweb.owlapi.apibinding.OWLManager;
import org.semanticweb.owlapi.model.OWLOntology;
import org.semanticweb.owlapi.model.OWLOntologyManager;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.File;
import java.util.HashMap;
import java.util.Map;

@Service
public class OntologyService {

    @Value("${ontology.file-path}")
    private String ontologyFilePath;

    private OWLOntology ontology;
    private OpenlletReasoner reasoner;

    public Map<String, Object> loadOntology() throws Exception {

        File ontologyFile = new File(ontologyFilePath);

        if (!ontologyFile.exists()) {
            throw new IllegalStateException(
                "File ontology tidak ditemukan: " + ontologyFilePath
            );
        }

        OWLOntologyManager manager =
            OWLManager.createOWLOntologyManager();

        ontology = manager.loadOntologyFromOntologyDocument(ontologyFile);

        reasoner = OpenlletReasonerFactory.getInstance()
            .createReasoner(ontology);

        Map<String, Object> result = new HashMap<>();

        result.put("success", true);
        result.put("message", "Ontology berhasil dimuat");
        result.put("ontologyFile", ontologyFile.getAbsolutePath());
        result.put("consistent", reasoner.isConsistent());
        result.put("classCount", ontology.getClassesInSignature().size());
        result.put("individualCount", ontology.getIndividualsInSignature().size());
        result.put("objectPropertyCount", ontology.getObjectPropertiesInSignature().size());
        result.put("dataPropertyCount", ontology.getDataPropertiesInSignature().size());

        return result;
    }

    public boolean isOntologyLoaded() {
        return ontology != null && reasoner != null;
    }

    public boolean checkConsistency() {
        if (!isOntologyLoaded()) {
            throw new IllegalStateException("Ontology belum dimuat");
        }

        return reasoner.isConsistent();
    }
}
