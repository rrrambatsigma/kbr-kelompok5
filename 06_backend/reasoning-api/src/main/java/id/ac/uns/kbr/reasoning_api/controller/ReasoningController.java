package id.ac.uns.kbr.reasoning_api.controller;

import java.util.List;
import java.util.Map;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import id.ac.uns.kbr.reasoning_api.dto.DiseaseCategoriesRequest;
import id.ac.uns.kbr.reasoning_api.service.ReasoningService;
import id.ac.uns.kbr.reasoning_api.web.ApiResponse;

@RestController
@RequestMapping("/api/reasoning")
public class ReasoningController {

    private final ReasoningService reasoningService;

    public ReasoningController(ReasoningService reasoningService) {
        this.reasoningService = reasoningService;
    }

    @GetMapping("/status")
    public ResponseEntity<Map<String, Object>> status() {
        return ResponseEntity.ok(ApiResponse.ok(reasoningService.status()));
    }

    @GetMapping("/consistency")
    public ResponseEntity<Map<String, Object>> consistency() {
        return ResponseEntity.ok(ApiResponse.ok(reasoningService.consistency()));
    }

    /**
     * Returns inferred disease categories. An empty body returns the complete
     * cached mapping; a body with {@code diseaseIris} filters the mapping.
     */
    @PostMapping("/disease-categories")
    public ResponseEntity<Map<String, Object>> diseaseCategories(
            @RequestBody(required = false) DiseaseCategoriesRequest request
    ) {
        List<String> diseaseIris = request == null ? null : request.diseaseIris();
        return ResponseEntity.ok(
                ApiResponse.ok(reasoningService.diseaseCategories(diseaseIris))
        );
    }
}
