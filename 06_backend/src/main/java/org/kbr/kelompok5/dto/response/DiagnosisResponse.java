package org.kbr.kelompok5.dto.response;

import java.util.List;

public record DiagnosisResponse(
        DiagnosisInputResponse input,
        List<DiagnosisCandidateResponse> candidates,
        ReasoningInfoResponse reasoning,
        List<String> warnings,
        String message) {
}
