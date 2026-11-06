package org.kbr.kelompok5.dto.response;

import java.util.List;

public record PlantDetailResponse(
        String id,
        String label,
        String scientificName,
        String description,
        List<DiseaseSummaryResponse> diseases,
        List<VarietyResponse> varieties,
        List<ControlResponse> generalControls,
        List<String> warnings) {
}
