package org.kbr.kelompok5.dto.response;

import java.util.List;

public record SymptomResponse(
        String id,
        String label,
        List<String> partIds,
        List<String> partLabels,
        String diseaseId,
        String diseaseLabel) {
}
