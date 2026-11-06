package org.kbr.kelompok5.dto.response;

import java.util.List;

public record DiagnosisEvidenceResponse(
        List<EntityRefResponse> affectedParts,
        List<EntityRefResponse> growthPhases,
        List<EntityRefResponse> environmentalFactors,
        List<ControlResponse> controls,
        List<ControlResponse> generalControls,
        List<ReferenceResponse> references) {
}
