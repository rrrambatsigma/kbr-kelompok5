package org.kbr.kelompok5.service;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

import org.kbr.kelompok5.dto.request.DiagnosisRequest;
import org.kbr.kelompok5.dto.response.ApiFieldError;
import org.kbr.kelompok5.dto.response.DiagnosisCandidateResponse;
import org.kbr.kelompok5.dto.response.DiagnosisEvidenceResponse;
import org.kbr.kelompok5.dto.response.DiagnosisInputResponse;
import org.kbr.kelompok5.dto.response.DiagnosisResponse;
import org.kbr.kelompok5.dto.response.DiseaseSummaryResponse;
import org.kbr.kelompok5.dto.response.ReasoningInfoResponse;
import org.kbr.kelompok5.dto.response.SymptomMatchResponse;
import org.kbr.kelompok5.exception.InvalidRequestException;
import org.kbr.kelompok5.exception.ResourceNotFoundException;
import org.kbr.kelompok5.reasoning.ReasoningEngine;
import org.kbr.kelompok5.reasoning.ReasoningInput;
import org.kbr.kelompok5.reasoning.ReasoningResult;
import org.kbr.kelompok5.reasoning.ReasoningStatus;
import org.kbr.kelompok5.repository.OntologyRepository;
import org.kbr.kelompok5.repository.OntologyRows.DiseaseRow;
import org.kbr.kelompok5.repository.OntologyRows.EntityRef;
import org.kbr.kelompok5.repository.OntologyRows.PlantRow;
import org.kbr.kelompok5.repository.OntologyRows.SymptomRow;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

@Service
public class DiagnosisService {

    private static final Logger log = LoggerFactory.getLogger(DiagnosisService.class);

    private static final Set<String> DISEASE_CATEGORIES = Set.of(
            "PenyakitJamur",
            "PenyakitBakteri",
            "PenyakitVirus",
            "PenyakitLainnya");

    private final OntologyRepository repository;
    private final OntologyMapper mapper;
    private final ReasoningEngine reasoningEngine;

    public DiagnosisService(
            OntologyRepository repository,
            OntologyMapper mapper,
            ReasoningEngine reasoningEngine) {
        this.repository = repository;
        this.mapper = mapper;
        this.reasoningEngine = reasoningEngine;
    }

    public DiagnosisResponse diagnose(DiagnosisRequest request) {
        validateRequest(request);

        String plantId = request.plantId().trim();
        PlantRow plant = repository.findPlant(plantId)
                .orElseThrow(() -> new ResourceNotFoundException("Tanaman", plantId));

        List<String> rawSymptomIds = request.symptomIds().stream()
                .filter(Objects::nonNull)
                .map(String::trim)
                .filter(id -> !id.isEmpty())
                .toList();

        if (rawSymptomIds.isEmpty()) {
            throw new InvalidRequestException(
                    "Minimal satu symptomIds harus diisi.",
                    List.of(new ApiFieldError("symptomIds", "Minimal satu ID gejala")));
        }

        LinkedHashSet<String> uniqueSymptomIds = new LinkedHashSet<>(rawSymptomIds);
        boolean duplicatesIgnored = uniqueSymptomIds.size() < rawSymptomIds.size();

        List<SymptomRow> plantSymptoms = repository.findSymptomsByPlant(plantId);
        Map<String, SymptomRow> symptomById = new LinkedHashMap<>();
        for (SymptomRow symptom : plantSymptoms) {
            symptomById.putIfAbsent(symptom.id(), symptom);
        }

        List<ApiFieldError> errors = new ArrayList<>();
        for (String symptomId : uniqueSymptomIds) {
            if (!repository.existsSymptom(symptomId)) {
                errors.add(new ApiFieldError(
                        "symptomIds",
                        "ID gejala tidak ditemukan: " + symptomId));
            } else if (!symptomById.containsKey(symptomId)) {
                errors.add(new ApiFieldError(
                        "symptomIds",
                        "Gejala '" + symptomId + "' bukan milik tanaman " + plantId));
            }
        }

        if (!errors.isEmpty()) {
            throw new InvalidRequestException("Validasi symptomIds gagal.", errors);
        }

        Map<String, DiseaseMatch> matches = new LinkedHashMap<>();
        for (String symptomId : uniqueSymptomIds) {
            SymptomRow symptom = symptomById.get(symptomId);
            if (symptom == null || symptom.disease() == null) {
                continue;
            }

            matches.computeIfAbsent(
                    symptom.disease().id(),
                    id -> new DiseaseMatch(symptom.disease()))
                    .symptoms.add(symptom);
        }

        List<String> candidateIds = new ArrayList<>(matches.keySet());
        ReasoningResult reasoning = safeAnalyze(new ReasoningInput(
                plantId,
                List.copyOf(uniqueSymptomIds),
                candidateIds));

        Map<String, String> inferredCategories = inferredCategories(reasoning);
        int selectedCount = uniqueSymptomIds.size();
        List<DiagnosisCandidateResponse> candidates = new ArrayList<>();

        for (DiseaseMatch match : matches.values()) {
            DiseaseRow disease = repository.findDisease(match.disease.id()).orElse(null);
            if (disease == null) {
                continue;
            }

            int matchedCount = match.symptoms.size();
            int totalSymptoms = Math.max(disease.symptomCount(), 1);
            double matchRatio = (double) matchedCount / selectedCount;
            double coverage = (double) matchedCount / totalSymptoms;
            double score = round(0.7 * matchRatio + 0.3 * coverage);

            DiseaseSummaryResponse diseaseSummary = mapper.toDiseaseSummary(
                    disease,
                    inferredCategories.get(disease.id()));

            List<SymptomMatchResponse> matchedSymptoms = match.symptoms.stream()
                    .map(symptom -> new SymptomMatchResponse(symptom.id(), symptom.label()))
                    .toList();

            List<SymptomMatchResponse> unmatchedSymptoms = uniqueSymptomIds.stream()
                    .filter(id -> match.symptoms.stream()
                            .noneMatch(symptom -> symptom.id().equals(id)))
                    .map(id -> new SymptomMatchResponse(id, symptomById.get(id).label()))
                    .toList();

            DiagnosisEvidenceResponse evidence = evidenceFor(
                    disease.id(),
                    disease.plant() == null ? null : disease.plant().id());

            candidates.add(new DiagnosisCandidateResponse(
                    diseaseSummary,
                    score,
                    round(matchRatio),
                    round(coverage),
                    matchedSymptoms,
                    unmatchedSymptoms,
                    evidence));
        }

        candidates.sort((first, second) -> {
            int byScore = Double.compare(second.score(), first.score());
            if (byScore != 0) {
                return byScore;
            }

            int byMatched = Integer.compare(
                    second.matchedSymptoms().size(),
                    first.matchedSymptoms().size());
            if (byMatched != 0) {
                return byMatched;
            }

            return first.disease().label().compareToIgnoreCase(second.disease().label());
        });

        int topN = request.topN() == null ? 5 : Math.max(1, Math.min(10, request.topN()));
        if (candidates.size() > topN) {
            candidates = new ArrayList<>(candidates.subList(0, topN));
        }

        List<String> warnings = new ArrayList<>();
        if (duplicatesIgnored) {
            warnings.add("DUPLICATE_SYMPTOM_IDS_IGNORED");
        }
        if (matches.size() > 1) {
            warnings.add("MIXED_DISEASE_SYMPTOMS");
        }
        if (candidates.isEmpty()) {
            warnings.add("NO_MATCHING_DISEASE");
        }
        addReasoningWarnings(warnings, reasoning.status());

        ReasoningInfoResponse reasoningInfo = new ReasoningInfoResponse(
                reasoning.engine(),
                reasoning.status().name(),
                reasoning.used(),
                inferredCategories,
                reasoning.consistency(),
                reasoning.durationMs(),
                reasoning.message());

        String message = candidates.isEmpty()
                ? "Tidak ada penyakit yang cocok dengan kombinasi gejala yang dipilih."
                : "Ditemukan " + candidates.size() + " kandidat penyakit.";

        return new DiagnosisResponse(
                new DiagnosisInputResponse(
                        plantId,
                        plant.label(),
                        selectedCount,
                        safeList(request.partIds()),
                        request.phaseId(),
                        safeList(request.environmentalFactorIds())),
                candidates,
                reasoningInfo,
                warnings,
                message);
    }

    private void validateRequest(DiagnosisRequest request) {
        if (request == null) {
            throw new InvalidRequestException(
                    "Body request diagnosis wajib diisi.",
                    List.of(new ApiFieldError("body", "Body request wajib diisi")));
        }
        if (request.plantId() == null || request.plantId().isBlank()) {
            throw new InvalidRequestException(
                    "plantId wajib diisi.",
                    List.of(new ApiFieldError("plantId", "plantId wajib diisi")));
        }
        if (request.symptomIds() == null || request.symptomIds().isEmpty()) {
            throw new InvalidRequestException(
                    "symptomIds minimal berisi satu ID.",
                    List.of(new ApiFieldError("symptomIds", "Minimal satu ID gejala")));
        }
    }

    private DiagnosisEvidenceResponse evidenceFor(String diseaseId, String plantId) {
        return new DiagnosisEvidenceResponse(
                mapper.toRefs(repository.findPartsOfDisease(diseaseId)),
                mapper.toRefs(repository.findPhasesOfDisease(diseaseId)),
                mapper.toRefs(repository.findEnvironmentalFactorsOfDisease(diseaseId)),
                mapper.toControls(repository.findControlsOfDisease(diseaseId)),
                plantId == null
                        ? List.of()
                        : mapper.toControls(repository.findGeneralControlsOfPlant(plantId)),
                mapper.toReferences(repository.findReferencesOfDisease(diseaseId)));
    }

    private ReasoningResult safeAnalyze(ReasoningInput input) {
        try {
            ReasoningResult result = reasoningEngine.analyze(input);
            if (result == null) {
                return ReasoningResult.error(
                        reasoningEngine.name(),
                        ReasoningStatus.ERROR,
                        "Reasoning engine mengembalikan hasil kosong.");
            }
            return result;
        } catch (Exception exception) {
            log.warn("Reasoning engine gagal: {}", exception.getMessage());
            return ReasoningResult.error(
                    reasoningEngine.name(),
                    ReasoningStatus.ERROR,
                    "Reasoning engine gagal: " + exception.getMessage());
        }
    }

    private Map<String, String> inferredCategories(ReasoningResult reasoning) {
        Map<String, String> categories = new LinkedHashMap<>();

        reasoning.inferredTypes().forEach((diseaseId, types) -> {
            for (String type : types) {
                String localName = localName(type);
                if (DISEASE_CATEGORIES.contains(localName)) {
                    categories.put(diseaseId, localName);
                    return;
                }
            }
        });

        return categories;
    }

    private void addReasoningWarnings(List<String> warnings, ReasoningStatus status) {
        switch (status) {
            case NOT_CONFIGURED -> warnings.add("REASONING_NOT_CONFIGURED");
            case UNAVAILABLE -> warnings.add("REASONING_UNAVAILABLE");
            case TIMEOUT -> warnings.add("REASONING_TIMEOUT");
            case INCONSISTENT -> warnings.add("REASONING_INCONSISTENT");
            case ERROR -> warnings.add("REASONING_ERROR");
            case OK -> {
                // tidak ada warning
            }
        }
    }

    private List<String> safeList(List<String> values) {
        return values == null ? List.of() : List.copyOf(values);
    }

    private String localName(String value) {
        if (value == null) {
            return "";
        }
        int separator = Math.max(value.lastIndexOf('#'), value.lastIndexOf('/'));
        return separator >= 0 ? value.substring(separator + 1) : value;
    }

    private double round(double value) {
        return Math.round(value * 1000.0) / 1000.0;
    }

    private static final class DiseaseMatch {

        private final EntityRef disease;
        private final List<SymptomRow> symptoms = new ArrayList<>();

        private DiseaseMatch(EntityRef disease) {
            this.disease = disease;
        }
    }
}
