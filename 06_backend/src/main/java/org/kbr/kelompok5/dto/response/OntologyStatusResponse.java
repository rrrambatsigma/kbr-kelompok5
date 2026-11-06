package org.kbr.kelompok5.dto.response;

import java.util.Map;

public record OntologyStatusResponse(
        boolean loaded,
        long tripleCount,
        String file,
        Map<String, Long> counts,
        ReasoningAvailability reasoning,
        String message) {

    public record ReasoningAvailability(String engine, boolean available) {
    }
}
