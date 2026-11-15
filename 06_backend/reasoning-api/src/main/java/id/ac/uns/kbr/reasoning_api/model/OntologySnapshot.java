package id.ac.uns.kbr.reasoning_api.model;

import java.time.Instant;
import java.util.Map;

import openllet.owlapi.OpenlletReasoner;

import org.semanticweb.owlapi.model.OWLOntology;
import org.semanticweb.owlapi.model.OWLOntologyManager;

/**
 * Immutable view of one loaded ontology + reasoner pair.
 *
 * <p>The reasoner is never handed to controllers. All reads must happen under
 * the provider's read lock; reloads swap the whole snapshot atomically.</p>
 */
public record OntologySnapshot(
        OWLOntologyManager manager,
        OWLOntology ontology,
        OpenlletReasoner reasoner,
        String ontologyIri,
        String versionInfo,
        String sourceFile,
        String checksum,
        boolean consistent,
        Instant loadedAt,
        int classCount,
        int individualCount,
        int objectPropertyCount,
        int dataPropertyCount,
        Map<String, String> diseaseCategoryByIri,
        Map<String, Long> diseaseCategoryCounts,
        long unclassifiedDiseaseCount
) {
}
