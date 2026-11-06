package org.kbr.kelompok5.controller;

import org.kbr.kelompok5.dto.response.DiseaseDetailResponse;
import org.kbr.kelompok5.dto.response.DiseaseSummaryResponse;
import org.kbr.kelompok5.dto.response.ListResponse;
import org.kbr.kelompok5.service.DiseaseService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/diseases")
public class DiseaseController {

    private final DiseaseService diseaseService;

    public DiseaseController(DiseaseService diseaseService) {
        this.diseaseService = diseaseService;
    }

    @GetMapping
    public ListResponse<DiseaseSummaryResponse> findAll(
            @RequestParam(required = false) String plantId) {

        return ListResponse.of(diseaseService.findAll(plantId));
    }

    @GetMapping("/{id}")
    public DiseaseDetailResponse findById(@PathVariable String id) {
        return diseaseService.findById(id);
    }
}
