package id.ac.uns.kbr.reasoning_api.controller;

import java.util.Map;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import id.ac.uns.kbr.reasoning_api.service.OntologyProvider;
import id.ac.uns.kbr.reasoning_api.service.ReasoningService;
import id.ac.uns.kbr.reasoning_api.web.ApiResponse;

@RestController
@RequestMapping("/api/ontology")
public class OntologyController {

    private final OntologyProvider ontologyProvider;
    private final ReasoningService reasoningService;

    public OntologyController(
            OntologyProvider ontologyProvider,
            ReasoningService reasoningService
    ) {
        this.ontologyProvider = ontologyProvider;
        this.reasoningService = reasoningService;
    }

    /**
     * Reloads the ontology. Kept for admin/diagnostic use; the API loads the
     * ontology automatically at startup.
     */
    @PostMapping({"/reload", "/load"})
    public ResponseEntity<Map<String, Object>> reload() {
        ontologyProvider.reload();
        return ResponseEntity.ok(ApiResponse.ok(reasoningService.status()));
    }

    @GetMapping("/status")
    public ResponseEntity<Map<String, Object>> status() {
        return ResponseEntity.ok(ApiResponse.ok(reasoningService.status()));
    }

    @GetMapping("/consistency")
    public ResponseEntity<Map<String, Object>> consistency() {
        return ResponseEntity.ok(ApiResponse.ok(reasoningService.consistency()));
    }
}
