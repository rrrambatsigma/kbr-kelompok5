package org.kbr.kelompok5.controller;

import org.kbr.kelompok5.dto.response.OntologyStatusResponse;
import org.kbr.kelompok5.reasoning.ReasoningEngine;
import org.kbr.kelompok5.service.OntologyService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/ontology")
public class OntologyController {

    private final OntologyService ontologyService;
    private final ReasoningEngine reasoningEngine;

    public OntologyController(
            OntologyService ontologyService,
            ReasoningEngine reasoningEngine) {
        this.ontologyService = ontologyService;
        this.reasoningEngine = reasoningEngine;
    }

    @GetMapping("/status")
    public OntologyStatusResponse getOntologyStatus() {
        boolean loaded = ontologyService.isLoaded();

        return new OntologyStatusResponse(
                loaded,
                ontologyService.getTripleCount(),
                ontologyService.getOntologyFile(),
                ontologyService.getCounts(),
                new OntologyStatusResponse.ReasoningAvailability(
                        reasoningEngine.name(),
                        reasoningEngine.isAvailable()),
                loaded
                        ? "Ontology berhasil dimuat menggunakan Apache Jena"
                        : "Ontology belum dimuat");
    }
}
