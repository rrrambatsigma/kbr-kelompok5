
package org.kbr.kelompok5.service;

import org.apache.jena.rdf.model.Model;
import org.springframework.stereotype.Service;

@Service
public class OntologyService {

    private final Model ontologyModel;

    public OntologyService(Model ontologyModel) {
        this.ontologyModel = ontologyModel;
    }

    public long getTripleCount() {
        return ontologyModel.size();
    }

    public boolean isLoaded() {
        return ontologyModel != null && !ontologyModel.isClosed();
    }
}
