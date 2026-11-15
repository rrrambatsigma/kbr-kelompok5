package id.ac.uns.kbr.reasoning_api.exception;

import org.springframework.http.HttpStatus;

public class OntologyNotLoadedException extends ApiException {

    public OntologyNotLoadedException(String message) {
        super("ONTOLOGY_NOT_LOADED", HttpStatus.SERVICE_UNAVAILABLE, message);
    }
}
