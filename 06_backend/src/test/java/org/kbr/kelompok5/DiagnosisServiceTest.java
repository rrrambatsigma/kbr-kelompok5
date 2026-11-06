package org.kbr.kelompok5;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.List;

import org.junit.jupiter.api.Test;
import org.kbr.kelompok5.dto.request.DiagnosisRequest;
import org.kbr.kelompok5.dto.response.DiagnosisResponse;
import org.kbr.kelompok5.exception.InvalidRequestException;
import org.kbr.kelompok5.service.DiagnosisService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest
class DiagnosisServiceTest {

    private static final String BLAS_SYMPTOM_1 =
            "GejalaBlasDaunMenunjukkanBercakBerwarna_2a00d88b";
    private static final String BLAS_SYMPTOM_2 =
            "GejalaGejalaPenyakitBlasDapatDitandai_c0feda66";
    private static final String TUNGRO_SYMPTOM =
            "GejalaIndikasiAdanyaInfeksiVirusTungro_02918429";
    private static final String KEDELAI_SYMPTOM =
            "GejalaGejalaPenyakitAntraknosaPadaKedelai_9344da2f";

    @Autowired
    private DiagnosisService diagnosisService;

    @Test
    void diagnosisWorksWithoutReasoningEngine() {
        DiagnosisResponse response = diagnosisService.diagnose(new DiagnosisRequest(
                "Padi",
                List.of(BLAS_SYMPTOM_1, BLAS_SYMPTOM_2),
                List.of("Daun"),
                null,
                List.of("KondisiMusimHujan"),
                null));

        assertThat(response.candidates()).hasSize(1);
        assertThat(response.candidates().get(0).disease().id())
                .isEqualTo("PenyakitBlasPadi");
        assertThat(response.candidates().get(0).disease().category()).isNull();
        assertThat(response.candidates().get(0).matchRatio()).isEqualTo(1.0);
        assertThat(response.candidates().get(0).coverage()).isEqualTo(0.286);
        assertThat(response.candidates().get(0).evidence().controls()).hasSize(8);
        assertThat(response.reasoning().status()).isEqualTo("NOT_CONFIGURED");
        assertThat(response.warnings()).contains("REASONING_NOT_CONFIGURED");
    }

    @Test
    void mixedSymptomsProduceMultipleCandidatesAndWarning() {
        DiagnosisResponse response = diagnosisService.diagnose(new DiagnosisRequest(
                "Padi",
                List.of(BLAS_SYMPTOM_1, BLAS_SYMPTOM_2, TUNGRO_SYMPTOM),
                List.of(),
                null,
                List.of(),
                null));

        assertThat(response.candidates()).hasSize(2);
        assertThat(response.warnings()).contains("MIXED_DISEASE_SYMPTOMS");
    }

    @Test
    void duplicateSymptomsAreDeduplicated() {
        DiagnosisResponse response = diagnosisService.diagnose(new DiagnosisRequest(
                "Padi",
                List.of(BLAS_SYMPTOM_1, BLAS_SYMPTOM_1),
                List.of(),
                null,
                List.of(),
                null));

        assertThat(response.input().symptomCount()).isEqualTo(1);
        assertThat(response.candidates()).hasSize(1);
        assertThat(response.warnings()).contains("DUPLICATE_SYMPTOM_IDS_IGNORED");
    }

    @Test
    void unknownSymptomIsRejected() {
        assertThatThrownBy(() -> diagnosisService.diagnose(new DiagnosisRequest(
                "Padi",
                List.of("GejalaTidakAda"),
                List.of(),
                null,
                List.of(),
                null)))
                .isInstanceOf(InvalidRequestException.class);
    }

    @Test
    void symptomFromAnotherPlantIsRejected() {
        assertThatThrownBy(() -> diagnosisService.diagnose(new DiagnosisRequest(
                "Padi",
                List.of(KEDELAI_SYMPTOM),
                List.of(),
                null,
                List.of(),
                null)))
                .isInstanceOf(InvalidRequestException.class);
    }

    @Test
    void topNLimitsReturnedCandidates() {
        DiagnosisResponse response = diagnosisService.diagnose(new DiagnosisRequest(
                "Padi",
                List.of(BLAS_SYMPTOM_1, TUNGRO_SYMPTOM),
                List.of(),
                null,
                List.of(),
                1));

        assertThat(response.candidates()).hasSize(1);
    }
}
