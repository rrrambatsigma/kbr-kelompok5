package org.kbr.kelompok5.exception;

import java.util.List;

import org.kbr.kelompok5.dto.response.ApiFieldError;

public class InvalidRequestException extends RuntimeException {

    private final List<ApiFieldError> errors;

    public InvalidRequestException(String message, List<ApiFieldError> errors) {
        super(message);
        this.errors = errors == null ? List.of() : List.copyOf(errors);
    }

    public List<ApiFieldError> getErrors() {
        return errors;
    }
}
