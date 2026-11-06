package org.kbr.kelompok5.dto.response;

import java.util.List;

public record DiagnosisInputResponse(
        String plantId,
        String plantLabel,
        int symptomCount,
        List<String> partIds,
        String phaseId,
        List<String> environmentalFactorIds) {
}
