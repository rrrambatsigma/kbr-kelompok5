package org.kbr.kelompok5.repository;

import java.util.List;

/**
 * Projection internal repository. Tidak diekspos langsung ke API.
 */
public final class OntologyRows {

    private OntologyRows() {
    }

    public record EntityRef(String id, String label) {
    }

    public record PlantRow(
            String id,
            String label,
            String scientificName,
            String description,
            int diseaseCount,
            int varietyCount,
            int generalControlCount) {
    }

    public record DiseaseRow(
            String id,
            String label,
            EntityRef plant,
            List<String> pathogenNames,
            String description,
            int symptomCount,
            int controlCount) {
    }

    public record SymptomRow(
            String id,
            String label,
            List<EntityRef> parts,
            EntityRef disease) {
    }

    public record PathogenRow(
            String id,
            String label,
            String scientificName,
            String type) {
    }

    public record ControlRow(
            String id,
            String label,
            List<String> types,
            String source) {
    }

    public record VarietyRow(
            String id,
            String label,
            List<EntityRef> resistantTo) {
    }

    public record ReferenceRow(
            String id,
            String title,
            String authors,
            Integer year,
            String url) {
    }
}
