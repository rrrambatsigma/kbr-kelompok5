package org.kbr.kelompok5.dto.response;

import java.util.List;

public record ListResponse<T>(int count, List<T> items) {

    public static <T> ListResponse<T> of(List<T> items) {
        List<T> safeItems = items == null ? List.of() : items;
        return new ListResponse<>(safeItems.size(), safeItems);
    }
}
