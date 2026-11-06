package org.kbr.kelompok5.controller;

import org.kbr.kelompok5.dto.request.DiagnosisRequest;
import org.kbr.kelompok5.dto.response.DiagnosisResponse;
import org.kbr.kelompok5.service.DiagnosisService;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import jakarta.validation.Valid;

@RestController
@RequestMapping("/api/diagnosis")
public class DiagnosisController {

    private final DiagnosisService diagnosisService;

    public DiagnosisController(DiagnosisService diagnosisService) {
        this.diagnosisService = diagnosisService;
    }

    @PostMapping
    public DiagnosisResponse diagnose(@Valid @RequestBody DiagnosisRequest request) {
        return diagnosisService.diagnose(request);
    }
}
