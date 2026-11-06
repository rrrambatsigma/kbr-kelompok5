package org.kbr.kelompok5.util;

import org.apache.jena.rdf.model.RDFNode;
import org.apache.jena.rdf.model.Resource;

/**
 * Konstanta dan helper untuk namespace ontology KBR.
 */
public final class OntologyIds {

    public static final String NAMESPACE =
            "http://kbr.kelompok5.org/penyakit-tanaman-pangan#";

    public static final String PREFIX = "ptp";

    private OntologyIds() {
    }

    public static String iri(String localName) {
        return NAMESPACE + localName;
    }

    public static String localName(Resource resource) {
        if (resource == null) {
            return null;
        }
        return resource.getLocalName();
    }

    public static String localName(RDFNode node) {
        if (node == null) {
            return null;
        }
        if (node.isResource()) {
            return localName(node.asResource());
        }
        return node.toString();
    }
}
