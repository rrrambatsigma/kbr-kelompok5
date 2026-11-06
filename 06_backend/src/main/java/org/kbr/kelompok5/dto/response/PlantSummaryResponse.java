package org.kbr.kelompok5.dto.response;

public record PlantSummaryResponse(
        String id,
        String label,
        String scientificName,
        int diseaseCount,
        int varietyCount,
        int generalControlCount) {
}
