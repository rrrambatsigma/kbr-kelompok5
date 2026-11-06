package org.kbr.kelompok5.reasoning;

import java.util.List;

public record ReasoningInput(
        String plantId,
        List<String> symptomIds,
        List<String> candidateDiseaseIds) {
}
