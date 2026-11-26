package org.kbr.kelompok5;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.kbr.kelompok5.service.DiagnosisService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest
class DiagnosisServiceTest {

    @Autowired
    private DiagnosisService diagnosisService;

    @Test
    void listsFiftyDemoDiagnoses() {
        assertThat(diagnosisService.listDiagnoses()).hasSize(50);
    }

    @Test
    void returnsInferredLinksForDemoDiagnosis() {
        var diagnosis = diagnosisService.getDiagnosis("DiagnosisDemo01");

        assertThat(diagnosis).isNotNull();
        assertThat((Iterable<?>) diagnosis.get("diseases")).isNotEmpty();
        assertThat((Iterable<?>) diagnosis.get("controls")).isNotEmpty();
    }
}
