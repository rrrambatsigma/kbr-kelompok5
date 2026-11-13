package id.ac.uns.kbr.reasoning_api;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import id.ac.uns.kbr.reasoning_api.exception.OntologyInconsistentException;
import id.ac.uns.kbr.reasoning_api.service.OntologyProvider;
import id.ac.uns.kbr.reasoning_api.service.ReasoningService;

class OntologyProviderInconsistentTest {

    private static final String INCONSISTENT_ONTOLOGY = """
            @prefix owl: <http://www.w3.org/2002/07/owl#> .
            @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
            @prefix ptp: <http://kbr.kelompok5.org/penyakit-tanaman-pangan#> .

            <http://kbr.kelompok5.org/penyakit-tanaman-pangan> a owl:Ontology .

            ptp:Penyakit a owl:Class .
            ptp:PenyakitJamur a owl:Class ;
                rdfs:subClassOf ptp:Penyakit ;
                owl:disjointWith ptp:PenyakitBakteri .
            ptp:PenyakitBakteri a owl:Class ;
                rdfs:subClassOf ptp:Penyakit .

            ptp:Konflik a ptp:PenyakitJamur,
                    ptp:PenyakitBakteri,
                    owl:NamedIndividual .
            """;

    @Test
    void inconsistentOntologyIsLoadedButNotReady(@TempDir Path tempDir) throws Exception {
        Path ontology = tempDir.resolve("inconsistent.ttl");
        Files.writeString(ontology, INCONSISTENT_ONTOLOGY);

        OntologyProvider provider = new OntologyProvider(
                ontology.toString(),
                120_000L,
                false
        );

        provider.init();

        try {
            assertTrue(provider.isLoaded(), "ontology tetap dimuat untuk diagnosis status");
            assertFalse(provider.isReady(), "ontology inkonsisten tidak boleh siap");

            ReasoningService service = new ReasoningService(provider);

            assertThrows(
                    OntologyInconsistentException.class,
                    () -> service.diseaseCategories(List.of())
            );
        } finally {
            provider.shutdown();
        }
    }
}
