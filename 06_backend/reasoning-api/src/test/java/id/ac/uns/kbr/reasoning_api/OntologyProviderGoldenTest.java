package id.ac.uns.kbr.reasoning_api;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.Test;

import id.ac.uns.kbr.reasoning_api.service.OntologyProvider;
import id.ac.uns.kbr.reasoning_api.service.ReasoningService;

/**
 * Golden test against the real repository ontology. It verifies that Openllet
 * infers the disease categories documented in 04_ontology/README.md.
 */
class OntologyProviderGoldenTest {

    private static final String ONTOLOGY_PATH = "../../04_ontology/ontology.ttl";

    @Test
    void loadsOntologyAndInfersDiseaseCategories() {
        OntologyProvider provider = new OntologyProvider(
                ONTOLOGY_PATH,
                120_000L,
                false
        );

        provider.init();

        try {
            assertTrue(provider.isLoaded(), "ontology harus dimuat otomatis");
            assertTrue(provider.isReady(), "ontology harus konsisten dan siap");

            ReasoningService service = new ReasoningService(provider);

            Map<String, Object> status = service.status();
            assertEquals(Boolean.TRUE, status.get("loaded"));
            assertEquals(Boolean.TRUE, status.get("ready"));
            assertEquals(Boolean.TRUE, status.get("consistent"));

            @SuppressWarnings("unchecked")
            Map<String, Long> counts =
                    (Map<String, Long>) status.get("diseaseCategoryCounts");

            assertEquals(29L, counts.get("PenyakitJamur"));
            assertEquals(5L, counts.get("PenyakitBakteri"));
            assertEquals(5L, counts.get("PenyakitVirus"));
            assertEquals(0L, counts.get("PenyakitLainnya"));

            Map<String, Object> categories =
                    service.diseaseCategories(List.of(
                            "PenyakitBlasPadi",
                            "PenyakitHawarDaunBakteriPadi"
                    ));

            @SuppressWarnings("unchecked")
            Map<String, String> mapping =
                    (Map<String, String>) categories.get("categories");

            assertEquals(
                    "PenyakitJamur",
                    mapping.get(OntologyProvider.PTP_NAMESPACE + "PenyakitBlasPadi")
            );
            assertEquals(
                    "PenyakitBakteri",
                    mapping.get(
                            OntologyProvider.PTP_NAMESPACE
                                    + "PenyakitHawarDaunBakteriPadi"
                    )
            );
        } finally {
            provider.shutdown();
        }
    }
}
