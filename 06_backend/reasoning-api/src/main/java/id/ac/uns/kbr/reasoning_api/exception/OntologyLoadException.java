package id.ac.uns.kbr.reasoning_api.exception;

import org.springframework.http.HttpStatus;

public class OntologyLoadException extends ApiException {

    public OntologyLoadException(String message) {
        super("ONTOLOGY_LOAD_FAILED", HttpStatus.INTERNAL_SERVER_ERROR, message);
    }

    public OntologyLoadException(String message, Throwable cause) {
        super("ONTOLOGY_LOAD_FAILED", HttpStatus.INTERNAL_SERVER_ERROR, message, cause);
    }
}
