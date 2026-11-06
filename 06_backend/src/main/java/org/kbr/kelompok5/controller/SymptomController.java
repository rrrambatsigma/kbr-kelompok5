package org.kbr.kelompok5.controller;

import org.kbr.kelompok5.dto.response.ListResponse;
import org.kbr.kelompok5.dto.response.SymptomResponse;
import org.kbr.kelompok5.service.SymptomService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/symptoms")
public class SymptomController {

    private final SymptomService symptomService;

    public SymptomController(SymptomService symptomService) {
        this.symptomService = symptomService;
    }

    @GetMapping
    public ListResponse<SymptomResponse> findAll(
            @RequestParam(required = false) String plantId,
            @RequestParam(required = false) String diseaseId,
            @RequestParam(required = false) String partId) {

        return ListResponse.of(symptomService.findAll(plantId, diseaseId, partId));
    }
}
