package org.kbr.kelompok5.dto.response;

public record ReferenceResponse(
        String id,
        String title,
        String authors,
        Integer year,
        String url) {
}
