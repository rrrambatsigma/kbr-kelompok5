package id.ac.uns.kbr.reasoning_api.exception;

import org.springframework.http.HttpStatus;

public class OntologyInconsistentException extends ApiException {

    public OntologyInconsistentException(String message) {
        super("ONTOLOGY_INCONSISTENT", HttpStatus.UNPROCESSABLE_ENTITY, message);
    }
}
