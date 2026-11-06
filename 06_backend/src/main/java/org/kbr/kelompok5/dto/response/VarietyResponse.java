package org.kbr.kelompok5.dto.response;

import java.util.List;

public record VarietyResponse(
        String id,
        String label,
        List<EntityRefResponse> resistantTo) {
}
