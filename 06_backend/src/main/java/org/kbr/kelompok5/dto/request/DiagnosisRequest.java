package org.kbr.kelompok5.dto.request;

import java.util.List;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Size;

public record DiagnosisRequest(
        @NotBlank(message = "plantId wajib diisi")
        String plantId,

        @NotEmpty(message = "symptomIds minimal berisi satu ID")
        @Size(max = 100, message = "symptomIds maksimal 100 ID")
        List<@NotBlank(message = "symptomIds tidak boleh berisi ID kosong") String> symptomIds,

        List<String> partIds,

        String phaseId,

        List<String> environmentalFactorIds,

        @Min(value = 1, message = "topN minimal 1")
        @Max(value = 10, message = "topN maksimal 10")
        Integer topN) {
}
