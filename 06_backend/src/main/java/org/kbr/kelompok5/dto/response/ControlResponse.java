package org.kbr.kelompok5.dto.response;

import java.util.List;

public record ControlResponse(
        String id,
        String label,
        List<String> types,
        String source) {
}
