
package org.kbr.kelompok5.config;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFDataMgr;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class OntologyConfig {

    @Value("${ontology.file}")
    private String ontologyFile;

    @Bean
    public Model ontologyModel() throws IOException {

        Path path = Path.of(ontologyFile)
                .toAbsolutePath()
                .normalize();

        if (!Files.exists(path)) {
            throw new IllegalStateException(
                "File ontology tidak ditemukan: " + path
            );
        }

        Model model = ModelFactory.createDefaultModel();

        RDFDataMgr.read(
            model,
            path.toUri().toString(),
            Lang.TURTLE
        );

        System.out.println("=================================");
        System.out.println("ONTOLOGY BERHASIL DIMUAT");
        System.out.println("Lokasi: " + path);
        System.out.println("Jumlah triples: " + model.size());
        System.out.println("=================================");

        return model;
    }
}
