package org.kbr.kelompok5.dto.response;

import java.util.List;

public record DiagnosisCandidateResponse(
        DiseaseSummaryResponse disease,
        double score,
        double matchRatio,
        double coverage,
        List<SymptomMatchResponse> matchedSymptoms,
        List<SymptomMatchResponse> unmatchedSymptoms,
        DiagnosisEvidenceResponse evidence) {
}
