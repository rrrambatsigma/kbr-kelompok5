package org.kbr.kelompok5.config;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFDataMgr;
import org.kbr.kelompok5.util.OntologyIds;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class OntologyConfig {

    private static final Logger log = LoggerFactory.getLogger(OntologyConfig.class);

    @Value("${ontology.file}")
    private String ontologyFile;

    @Bean
    public Model ontologyModel() throws IOException {
        Path path = resolveOntologyPath();

        Model model = ModelFactory.createDefaultModel();
        try (InputStream input = Files.newInputStream(path)) {
            RDFDataMgr.read(model, input, Lang.TURTLE);
        }

        model.setNsPrefix(OntologyIds.PREFIX, OntologyIds.NAMESPACE);

        log.info("Ontology berhasil dimuat dari {}", path);
        log.info("Jumlah triple ontology: {}", model.size());

        return model;
    }

    private Path resolveOntologyPath() {
        Path configured = Path.of(ontologyFile);
        List<Path> candidates = new ArrayList<>();
        candidates.add(configured);

        // Fallback agar backend tetap bisa dijalankan dari root repository
        // maupun dari folder 06_backend.
        if (!configured.isAbsolute()) {
            candidates.add(Path.of("04_ontology", "ontology.ttl"));
            candidates.add(Path.of("..", "04_ontology", "ontology.ttl"));
        }

        List<Path> attempted = new ArrayList<>();
        for (Path candidate : candidates) {
            Path absolute = candidate.toAbsolutePath().normalize();
            if (attempted.contains(absolute)) {
                continue;
            }
            attempted.add(absolute);
            if (Files.exists(absolute)) {
                return absolute;
            }
        }

        throw new IllegalStateException(
                "File ontology tidak ditemukan. Path yang dicoba: " + attempted
                        + ". Set property ontology.file ke path absolut jika perlu.");
    }
}
