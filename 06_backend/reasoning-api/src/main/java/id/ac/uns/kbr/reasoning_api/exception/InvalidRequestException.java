package id.ac.uns.kbr.reasoning_api.exception;

import org.springframework.http.HttpStatus;

public class InvalidRequestException extends ApiException {

    public InvalidRequestException(String message) {
        super("INVALID_REQUEST", HttpStatus.BAD_REQUEST, message);
    }
}
