package org.kbr.kelompok5.reasoning;

import java.util.List;
import java.util.Map;

public record ReasoningResult(
        String engine,
        ReasoningStatus status,
        boolean used,
        Map<String, List<String>> inferredTypes,
        String consistency,
        long durationMs,
        String message) {

    public static ReasoningResult notConfigured() {
        return new ReasoningResult(
                "noop",
                ReasoningStatus.NOT_CONFIGURED,
                false,
                Map.of(),
                "UNKNOWN",
                0,
                "Reasoning engine belum dikonfigurasi; diagnosis hanya berbasis pencocokan gejala.");
    }

    public static ReasoningResult error(String engine, ReasoningStatus status, String message) {
        return new ReasoningResult(
                engine,
                status,
                false,
                Map.of(),
                "UNKNOWN",
                0,
                message);
    }
}
