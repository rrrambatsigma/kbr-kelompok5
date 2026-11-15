package id.ac.uns.kbr.reasoning_api.web;

import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.servlet.resource.NoResourceFoundException;

import id.ac.uns.kbr.reasoning_api.exception.ApiException;

@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    @ExceptionHandler(ApiException.class)
    public ResponseEntity<Map<String, Object>> handleApiException(ApiException exception) {
        log.warn(
                "API error {} ({}): {}",
                exception.getCode(),
                exception.getStatus().value(),
                safeMessage(exception)
        );
        return ResponseEntity
                .status(exception.getStatus())
                .body(ApiResponse.error(exception.getCode(), safeMessage(exception)));
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<Map<String, Object>> handleUnreadableBody(
            HttpMessageNotReadableException exception
    ) {
        log.warn("Request body tidak dapat dibaca: {}", safeMessage(exception));
        return ResponseEntity
                .badRequest()
                .body(ApiResponse.error(
                        "INVALID_REQUEST",
                        "Body request tidak valid atau bukan JSON yang benar"
                ));
    }

    @ExceptionHandler(NoResourceFoundException.class)
    public ResponseEntity<Map<String, Object>> handleNotFound(
            NoResourceFoundException exception
    ) {
        return ResponseEntity
                .status(HttpStatus.NOT_FOUND)
                .body(ApiResponse.error(
                        "NOT_FOUND",
                        "Endpoint tidak ditemukan: " + exception.getResourcePath()
                ));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<Map<String, Object>> handleUnexpected(Exception exception) {
        log.error("Unhandled error: {}", safeMessage(exception), exception);
        return ResponseEntity
                .status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(ApiResponse.error(
                        "INTERNAL_ERROR",
                        "Terjadi kesalahan internal pada reasoning API"
                ));
    }

    private static String safeMessage(Throwable throwable) {
        String message = throwable.getMessage();
        if (message == null || message.isBlank()) {
            return throwable.getClass().getSimpleName();
        }
        return message;
    }
}
