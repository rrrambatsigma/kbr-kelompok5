package id.ac.uns.kbr.reasoning_api;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.file.Files;
import java.nio.file.Path;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import id.ac.uns.kbr.reasoning_api.exception.OntologyLoadException;
import id.ac.uns.kbr.reasoning_api.model.OntologySnapshot;
import id.ac.uns.kbr.reasoning_api.service.OntologyProvider;

class OntologyProviderAtomicReloadTest {

    private static final String MINIMAL_ONTOLOGY = """
            @prefix owl: <http://www.w3.org/2002/07/owl#> .
            @prefix ptp: <http://kbr.kelompok5.org/penyakit-tanaman-pangan#> .

            <http://kbr.kelompok5.org/penyakit-tanaman-pangan> a owl:Ontology .
            ptp:Penyakit a owl:Class .
            ptp:Contoh a ptp:Penyakit, owl:NamedIndividual .
            """;

    @Test
    void failedReloadKeepsPreviousSnapshot(@TempDir Path tempDir) throws Exception {
        Path ontology = tempDir.resolve("minimal.ttl");
        Files.writeString(ontology, MINIMAL_ONTOLOGY);

        OntologyProvider provider = new OntologyProvider(
                ontology.toString(),
                120_000L,
                false
        );

        provider.init();

        try {
            OntologySnapshot before = provider.current().orElse(null);
            assertNotNull(before);
            assertTrue(provider.isLoaded());

            Files.delete(ontology);

            assertThrows(OntologyLoadException.class, provider::reload);

            OntologySnapshot after = provider.current().orElse(null);
            assertNotNull(after, "snapshot lama harus tetap ada setelah reload gagal");
            assertTrue(provider.isLoaded());
            assertEquals(before.checksum(), after.checksum());
            assertEquals(before.loadedAt(), after.loadedAt());
        } finally {
            provider.shutdown();
        }
    }
}
