
package id.ac.uns.kbr.reasoning_api.controller;

import id.ac.uns.kbr.reasoning_api.service.OntologyService;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/ontology")
public class OntologyController {

    private final OntologyService ontologyService;

    public OntologyController(OntologyService ontologyService) {
        this.ontologyService = ontologyService;
    }

    @PostMapping("/load")
    public ResponseEntity<Map<String, Object>> loadOntology() {
        try {
            Map<String, Object> result = ontologyService.loadOntology();
            return ResponseEntity.ok(result);

        } catch (Exception e) {
            return ResponseEntity
                .status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(Map.of(
                    "success", false,
                    "message", "Gagal memuat ontology",
                    "error", e.getMessage()
                ));
        }
    }

    @GetMapping("/status")
    public ResponseEntity<Map<String, Object>> getStatus() {

        boolean loaded = ontologyService.isOntologyLoaded();

        return ResponseEntity.ok(Map.of(
            "success", true,
            "loaded", loaded,
            "message", loaded
                ? "Ontology sudah dimuat"
                : "Ontology belum dimuat"
        ));
    }

    @GetMapping("/consistency")
    public ResponseEntity<Map<String, Object>> checkConsistency() {
        try {
            boolean consistent = ontologyService.checkConsistency();

            return ResponseEntity.ok(Map.of(
                "success", true,
                "consistent", consistent,
                "message", consistent
                    ? "Ontology konsisten"
                    : "Ontology tidak konsisten"
            ));

        } catch (Exception e) {
            return ResponseEntity
                .status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(Map.of(
                    "success", false,
                    "message", e.getMessage()
                ));
        }
    }
}
