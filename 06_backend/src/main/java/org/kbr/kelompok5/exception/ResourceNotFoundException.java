package org.kbr.kelompok5.exception;

public class ResourceNotFoundException extends RuntimeException {

    private final String resourceType;
    private final String id;

    public ResourceNotFoundException(String resourceType, String id) {
        super(resourceType + " dengan id '" + id + "' tidak ditemukan");
        this.resourceType = resourceType;
        this.id = id;
    }

    public String getResourceType() {
        return resourceType;
    }

    public String getId() {
        return id;
    }
}
