package org.kbr.kelompok5.service;

import java.util.ArrayList;
import java.util.List;

import org.kbr.kelompok5.dto.response.PlantDetailResponse;
import org.kbr.kelompok5.dto.response.PlantSummaryResponse;
import org.kbr.kelompok5.exception.ResourceNotFoundException;
import org.kbr.kelompok5.repository.OntologyRepository;
import org.kbr.kelompok5.repository.OntologyRows.PlantRow;
import org.springframework.stereotype.Service;

@Service
public class PlantService {

    private final OntologyRepository repository;
    private final OntologyMapper mapper;

    public PlantService(OntologyRepository repository, OntologyMapper mapper) {
        this.repository = repository;
        this.mapper = mapper;
    }

    public List<PlantSummaryResponse> findAll() {
        return repository.findAllPlants().stream()
                .map(this::toSummary)
                .toList();
    }

    public PlantDetailResponse findById(String plantId) {
        PlantRow plant = repository.findPlant(plantId)
                .orElseThrow(() -> new ResourceNotFoundException("Tanaman", plantId));

        List<String> warnings = new ArrayList<>();
        if (plant.scientificName() == null) {
            warnings.add("SCIENTIFIC_NAME_NOT_AVAILABLE");
        }
        if (plant.description() == null) {
            warnings.add("DESCRIPTION_NOT_AVAILABLE");
        }

        return new PlantDetailResponse(
                plant.id(),
                plant.label(),
                plant.scientificName(),
                plant.description(),
                repository.findDiseasesByPlant(plantId).stream()
                        .map(row -> mapper.toDiseaseSummary(row, null))
                        .toList(),
                mapper.toVarieties(repository.findVarietiesOfPlant(plantId)),
                mapper.toControls(repository.findGeneralControlsOfPlant(plantId)),
                warnings);
    }

    private PlantSummaryResponse toSummary(PlantRow row) {
        return new PlantSummaryResponse(
                row.id(),
                row.label(),
                row.scientificName(),
                row.diseaseCount(),
                row.varietyCount(),
                row.generalControlCount());
    }
}
