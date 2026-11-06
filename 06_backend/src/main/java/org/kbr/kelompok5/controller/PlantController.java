package org.kbr.kelompok5.controller;

import org.kbr.kelompok5.dto.response.ListResponse;
import org.kbr.kelompok5.dto.response.PlantDetailResponse;
import org.kbr.kelompok5.dto.response.PlantSummaryResponse;
import org.kbr.kelompok5.dto.response.SymptomResponse;
import org.kbr.kelompok5.service.PlantService;
import org.kbr.kelompok5.service.SymptomService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/plants")
public class PlantController {

    private final PlantService plantService;
    private final SymptomService symptomService;

    public PlantController(PlantService plantService, SymptomService symptomService) {
        this.plantService = plantService;
        this.symptomService = symptomService;
    }

    @GetMapping
    public ListResponse<PlantSummaryResponse> findAll() {
        return ListResponse.of(plantService.findAll());
    }

    @GetMapping("/{id}")
    public PlantDetailResponse findById(@PathVariable String id) {
        return plantService.findById(id);
    }

    @GetMapping("/{id}/symptoms")
    public ListResponse<SymptomResponse> findSymptoms(
            @PathVariable String id,
            @RequestParam(required = false) String diseaseId) {

        return ListResponse.of(symptomService.findByPlant(id, diseaseId));
    }
}
