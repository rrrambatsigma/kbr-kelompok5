package org.kbr.kelompok5.service;

import java.util.ArrayList;
import java.util.List;

import org.kbr.kelompok5.dto.response.DiseaseDetailResponse;
import org.kbr.kelompok5.dto.response.DiseaseSummaryResponse;
import org.kbr.kelompok5.exception.ResourceNotFoundException;
import org.kbr.kelompok5.repository.OntologyRepository;
import org.kbr.kelompok5.repository.OntologyRows.ControlRow;
import org.kbr.kelompok5.repository.OntologyRows.DiseaseRow;
import org.kbr.kelompok5.repository.OntologyRows.PathogenRow;
import org.springframework.stereotype.Service;

@Service
public class DiseaseService {

    private final OntologyRepository repository;
    private final OntologyMapper mapper;

    public DiseaseService(OntologyRepository repository, OntologyMapper mapper) {
        this.repository = repository;
        this.mapper = mapper;
    }

    public List<DiseaseSummaryResponse> findAll(String plantId) {
        String normalizedPlantId = normalize(plantId);

        if (normalizedPlantId != null) {
            if (!repository.existsPlant(normalizedPlantId)) {
                throw new ResourceNotFoundException("Tanaman", normalizedPlantId);
            }

            return repository.findDiseasesByPlant(normalizedPlantId).stream()
                    .map(row -> mapper.toDiseaseSummary(row, null))
                    .toList();
        }

        return repository.findAllDiseases().stream()
                .map(row -> mapper.toDiseaseSummary(row, null))
                .toList();
    }

    public DiseaseDetailResponse findById(String diseaseId) {
        DiseaseRow disease = repository.findDisease(diseaseId)
                .orElseThrow(() -> new ResourceNotFoundException("Penyakit", diseaseId));

        List<PathogenRow> pathogenRows = repository.findPathogensOfDisease(diseaseId);

        List<ControlRow> controlRows = repository.findControlsOfDisease(diseaseId);
        List<ControlRow> generalControlRows = disease.plant() == null
                ? List.of()
                : repository.findGeneralControlsOfPlant(disease.plant().id());

        List<String> warnings = new ArrayList<>();
        if (disease.description() == null) {
            warnings.add("DESCRIPTION_NOT_AVAILABLE");
        }
        if (pathogenRows.isEmpty()) {
            warnings.add("PATHOGEN_NOT_AVAILABLE");
        }
        if (controlRows.isEmpty() && generalControlRows.isEmpty()) {
            warnings.add("DISEASE_CONTROL_NOT_AVAILABLE");
        } else if (controlRows.isEmpty()) {
            warnings.add("GENERAL_CONTROL_FALLBACK_USED");
        }

        return new DiseaseDetailResponse(
                disease.id(),
                disease.label(),
                disease.description(),
                mapper.toRef(disease.plant()),
                null,
                mapper.toPathogens(pathogenRows),
                mapper.toSymptoms(repository.findSymptomsByDisease(diseaseId)),
                mapper.toRefs(repository.findPartsOfDisease(diseaseId)),
                mapper.toRefs(repository.findPhasesOfDisease(diseaseId)),
                mapper.toRefs(repository.findEnvironmentalFactorsOfDisease(diseaseId)),
                mapper.toControls(controlRows),
                mapper.toControls(generalControlRows),
                mapper.toReferences(repository.findReferencesOfDisease(diseaseId)),
                warnings);
    }

    private String normalize(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }
}
