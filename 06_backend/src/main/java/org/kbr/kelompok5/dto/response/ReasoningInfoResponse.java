package org.kbr.kelompok5.dto.response;

import java.util.Map;

public record ReasoningInfoResponse(
        String engine,
        String status,
        boolean used,
        Map<String, String> inferredCategories,
        String consistency,
        long durationMs,
        String message) {
}
