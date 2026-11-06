package org.kbr.kelompok5.dto.response;

import java.util.List;

public record DiseaseDetailResponse(
        String id,
        String label,
        String description,
        EntityRefResponse plant,
        String category,
        List<PathogenResponse> pathogens,
        List<SymptomResponse> symptoms,
        List<EntityRefResponse> affectedParts,
        List<EntityRefResponse> growthPhases,
        List<EntityRefResponse> environmentalFactors,
        List<ControlResponse> controls,
        List<ControlResponse> generalControls,
        List<ReferenceResponse> references,
        List<String> warnings) {
}
