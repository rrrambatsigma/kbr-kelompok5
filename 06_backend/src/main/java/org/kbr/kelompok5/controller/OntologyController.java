
package org.kbr.kelompok5.controller;

import java.util.Map;

import org.kbr.kelompok5.service.OntologyService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/ontology")
public class OntologyController {

    private final OntologyService ontologyService;

    public OntologyController(OntologyService ontologyService) {
        this.ontologyService = ontologyService;
    }

    @GetMapping("/status")
    public Map<String, Object> getOntologyStatus() {

        return Map.of(
            "loaded", ontologyService.isLoaded(),
            "tripleCount", ontologyService.getTripleCount(),
            "message", "Ontology berhasil dimuat menggunakan Apache Jena"
        );
    }
}
