package org.kbr.kelompok5.service;

import java.util.List;

import org.kbr.kelompok5.dto.response.ApiFieldError;
import org.kbr.kelompok5.dto.response.SymptomResponse;
import org.kbr.kelompok5.exception.InvalidRequestException;
import org.kbr.kelompok5.exception.ResourceNotFoundException;
import org.kbr.kelompok5.repository.OntologyRepository;
import org.kbr.kelompok5.repository.OntologyRows.DiseaseRow;
import org.kbr.kelompok5.repository.OntologyRows.SymptomRow;
import org.springframework.stereotype.Service;

@Service
public class SymptomService {

    private final OntologyRepository repository;
    private final OntologyMapper mapper;

    public SymptomService(OntologyRepository repository, OntologyMapper mapper) {
        this.repository = repository;
        this.mapper = mapper;
    }

    public List<SymptomResponse> findAll(String plantId, String diseaseId, String partId) {
        String plant = normalize(plantId);
        String disease = normalize(diseaseId);
        String part = normalize(partId);

        if (plant != null && !repository.existsPlant(plant)) {
            throw new ResourceNotFoundException("Tanaman", plant);
        }
        if (disease != null && !repository.existsDisease(disease)) {
            throw new ResourceNotFoundException("Penyakit", disease);
        }
        if (part != null && !repository.existsPart(part)) {
            throw new ResourceNotFoundException("BagianTanaman", part);
        }
        if (plant != null && disease != null) {
            validateDiseaseBelongsToPlant(disease, plant, "diseaseId");
        }

        List<SymptomRow> rows;
        if (disease != null) {
            rows = repository.findSymptomsByDisease(disease);
        } else if (plant != null) {
            rows = repository.findSymptomsByPlant(plant);
        } else {
            rows = repository.findAllSymptoms();
        }

        if (part != null) {
            rows = rows.stream()
                    .filter(row -> row.parts().stream()
                            .anyMatch(ref -> part.equals(ref.id())))
                    .toList();
        }

        return rows.stream().map(mapper::toSymptom).toList();
    }

    public List<SymptomResponse> findByPlant(String plantId, String diseaseId) {
        if (!repository.existsPlant(plantId)) {
            throw new ResourceNotFoundException("Tanaman", plantId);
        }

        String disease = normalize(diseaseId);
        if (disease != null) {
            validateDiseaseBelongsToPlant(disease, plantId, "diseaseId");
            return repository.findSymptomsByDisease(disease).stream()
                    .map(mapper::toSymptom)
                    .toList();
        }

        return repository.findSymptomsByPlant(plantId).stream()
                .map(mapper::toSymptom)
                .toList();
    }

    private void validateDiseaseBelongsToPlant(String diseaseId, String plantId, String field) {
        DiseaseRow disease = repository.findDisease(diseaseId)
                .orElseThrow(() -> new ResourceNotFoundException("Penyakit", diseaseId));

        if (disease.plant() == null || !plantId.equals(disease.plant().id())) {
            throw new InvalidRequestException(
                    "Penyakit '" + diseaseId + "' bukan milik tanaman '" + plantId + "'.",
                    List.of(new ApiFieldError(
                            field,
                            "Penyakit tidak terkait dengan tanaman yang diminta")));
        }
    }

    private String normalize(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }
}
