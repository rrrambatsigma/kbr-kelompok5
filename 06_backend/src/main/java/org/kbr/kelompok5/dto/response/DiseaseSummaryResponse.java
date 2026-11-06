package org.kbr.kelompok5.dto.response;

import java.util.List;

public record DiseaseSummaryResponse(
        String id,
        String label,
        String plantId,
        String plantLabel,
        List<String> pathogenNames,
        int symptomCount,
        int controlCount,
        String category) {
}
