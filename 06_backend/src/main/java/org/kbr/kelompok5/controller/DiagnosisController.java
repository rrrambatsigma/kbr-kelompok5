package org.kbr.kelompok5.controller;

import java.util.List;
import java.util.Map;

import org.kbr.kelompok5.service.DiagnosisService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/diagnosis")
public class DiagnosisController {

    private final DiagnosisService diagnosisService;

    public DiagnosisController(DiagnosisService diagnosisService) {
        this.diagnosisService = diagnosisService;
    }

    @GetMapping
    public List<Map<String, String>> listDiagnoses() {
        return diagnosisService.listDiagnoses();
    }

    @GetMapping("/{id}")
    public ResponseEntity<Map<String, Object>> getDiagnosis(@PathVariable String id) {
        Map<String, Object> diagnosis = diagnosisService.getDiagnosis(id);
        if (diagnosis == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(diagnosis);
    }
}
