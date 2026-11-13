package id.ac.uns.kbr.reasoning_api.exception;

import org.springframework.http.HttpStatus;

public class ReasoningTimeoutException extends ApiException {

    public ReasoningTimeoutException(String message) {
        super("REASONING_TIMEOUT", HttpStatus.GATEWAY_TIMEOUT, message);
    }
}
