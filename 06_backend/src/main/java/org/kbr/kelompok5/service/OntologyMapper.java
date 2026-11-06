package org.kbr.kelompok5.service;

import java.util.List;

import org.kbr.kelompok5.dto.response.ControlResponse;
import org.kbr.kelompok5.dto.response.DiseaseSummaryResponse;
import org.kbr.kelompok5.dto.response.EntityRefResponse;
import org.kbr.kelompok5.dto.response.PathogenResponse;
import org.kbr.kelompok5.dto.response.ReferenceResponse;
import org.kbr.kelompok5.dto.response.SymptomResponse;
import org.kbr.kelompok5.dto.response.VarietyResponse;
import org.kbr.kelompok5.repository.OntologyRows.ControlRow;
import org.kbr.kelompok5.repository.OntologyRows.DiseaseRow;
import org.kbr.kelompok5.repository.OntologyRows.EntityRef;
import org.kbr.kelompok5.repository.OntologyRows.PathogenRow;
import org.kbr.kelompok5.repository.OntologyRows.ReferenceRow;
import org.kbr.kelompok5.repository.OntologyRows.SymptomRow;
import org.kbr.kelompok5.repository.OntologyRows.VarietyRow;
import org.springframework.stereotype.Component;

@Component
public class OntologyMapper {

    public EntityRefResponse toRef(EntityRef ref) {
        if (ref == null) {
            return null;
        }
        return new EntityRefResponse(ref.id(), ref.label());
    }

    public List<EntityRefResponse> toRefs(List<EntityRef> refs) {
        return refs.stream().map(this::toRef).toList();
    }

    public ControlResponse toControl(ControlRow row) {
        return new ControlResponse(row.id(), row.label(), row.types(), row.source());
    }

    public List<ControlResponse> toControls(List<ControlRow> rows) {
        return rows.stream().map(this::toControl).toList();
    }

    public PathogenResponse toPathogen(PathogenRow row) {
        if (row == null) {
            return null;
        }
        return new PathogenResponse(
                row.id(), row.label(), row.scientificName(), row.type());
    }

    public List<PathogenResponse> toPathogens(List<PathogenRow> rows) {
        return rows.stream().map(this::toPathogen).toList();
    }

    public SymptomResponse toSymptom(SymptomRow row) {
        return new SymptomResponse(
                row.id(),
                row.label(),
                row.parts().stream().map(EntityRef::id).toList(),
                row.parts().stream().map(EntityRef::label).toList(),
                row.disease() == null ? null : row.disease().id(),
                row.disease() == null ? null : row.disease().label());
    }

    public List<SymptomResponse> toSymptoms(List<SymptomRow> rows) {
        return rows.stream().map(this::toSymptom).toList();
    }

    public VarietyResponse toVariety(VarietyRow row) {
        return new VarietyResponse(
                row.id(), row.label(), toRefs(row.resistantTo()));
    }

    public List<VarietyResponse> toVarieties(List<VarietyRow> rows) {
        return rows.stream().map(this::toVariety).toList();
    }

    public ReferenceResponse toReference(ReferenceRow row) {
        return new ReferenceResponse(
                row.id(), row.title(), row.authors(), row.year(), row.url());
    }

    public List<ReferenceResponse> toReferences(List<ReferenceRow> rows) {
        return rows.stream().map(this::toReference).toList();
    }

    public DiseaseSummaryResponse toDiseaseSummary(DiseaseRow row, String category) {
        return new DiseaseSummaryResponse(
                row.id(),
                row.label(),
                row.plant() == null ? null : row.plant().id(),
                row.plant() == null ? null : row.plant().label(),
                row.pathogenNames(),
                row.symptomCount(),
                row.controlCount(),
                category);
    }
}
