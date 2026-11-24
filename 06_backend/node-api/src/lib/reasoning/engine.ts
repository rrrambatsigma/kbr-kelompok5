import type {
  DiagnosisDataset,
  DiagnosisSymptom,
} from "../../services/knowledge.service.js";
import {
  classifyConfidence,
  round4,
  scoreCandidate,
} from "./certainty.js";
import { REASONING_CONFIG, partWeight } from "./config.js";
import {
  canonicalRuleId,
  exactRuleId,
  prepareDataset,
  type PreparedDataset,
} from "./rules.js";
import { evidenceWeight, specificity } from "./specificity.js";
import {
  DEFAULT_REASONING_OPTIONS,
  REASONING_MODEL_VERSION,
  type PhaseMatch,
  type ReasoningCandidate,
  type ReasoningEvidence,
  type ReasoningOptions,
  type ReasoningResult,
} from "./types.js";

function dfForSymptom(
  symptom: DiagnosisSymptom,
  prepared: PreparedDataset
): number {
  if (symptom.canonical !== null) {
    return prepared.canonicalDf.get(symptom.canonical.iri) ?? 1;
  }

  return prepared.observationDf.get(symptom.iri) ?? 1;
}

function resolveSelectedSymptoms(
  prepared: PreparedDataset,
  selectedSymptomIds: readonly string[],
  warnings: Set<string>
): DiagnosisSymptom[] {
  const selected: DiagnosisSymptom[] = [];
  const seen = new Set<string>();

  for (const id of selectedSymptomIds) {
    if (seen.has(id)) {
      continue;
    }
    seen.add(id);

    const symptom = prepared.symptomById.get(id);

    if (symptom === undefined) {
      warnings.add(`UNKNOWN_SYMPTOM_IGNORED:${id}`);
      continue;
    }

    selected.push(symptom);
  }

  return selected;
}

/**
 * Mesin reasoning diagnosis.
 *
 * Fungsi murni: tidak mengakses SPARQL/HTTP. Semua pengetahuan berasal dari
 * `DiagnosisDataset`, sehingga bisa diuji dengan fixture sintetis dan tidak
 * terikat pada ontology sementara.
 */
export function reason(
  dataset: DiagnosisDataset,
  selectedSymptomIds: readonly string[],
  options: Partial<ReasoningOptions> = {}
): ReasoningResult {
  const opts: ReasoningOptions = {
    topN: options.topN ?? DEFAULT_REASONING_OPTIONS.topN,
    canonicalWeight:
      options.canonicalWeight ?? DEFAULT_REASONING_OPTIONS.canonicalWeight,
    evidenceFloor:
      options.evidenceFloor ?? DEFAULT_REASONING_OPTIONS.evidenceFloor,
    phaseIri: options.phaseIri ?? null,
  };
  const warnings = new Set<string>();
  const prepared = prepareDataset(dataset);

  if (prepared.canonicalObservationCount === 0) {
    warnings.add("CANONICAL_MATCHING_DISABLED");
  }

  const selected = resolveSelectedSymptoms(
    prepared,
    selectedSymptomIds,
    warnings
  );

  if (selected.length === 0) {
    warnings.add("NO_SELECTED_SYMPTOMS");
    return {
      candidates: [],
      totalMatched: 0,
      warnings: [...warnings],
      modelVersion: REASONING_MODEL_VERSION,
    };
  }

  const candidates: ReasoningCandidate[] = [];

  for (const preparedDisease of prepared.diseases) {
    const disease = preparedDisease.disease;
    const phaseMatch: PhaseMatch =
      opts.phaseIri === null
        ? "unknown"
        : disease.phases.some((phase) => phase.iri === opts.phaseIri)
          ? "match"
          : disease.phases.length > 0
            ? "mismatch"
            : "unknown";
    const phaseFactor =
      phaseMatch === "match" ? REASONING_CONFIG.phaseMatchFactor : 1;
    const evidence: ReasoningEvidence[] = [];
    const matchedSymptoms: DiagnosisSymptom[] = [];
    const unexplainedSymptoms: DiagnosisSymptom[] = [];
    const usedObservations = new Set<string>();

    let cf = 0;

    for (const selectedSymptom of selected) {
      let matchedObservation: DiagnosisSymptom | null = null;
      let type: "exact" | "canonical" | null = null;
      let baseWeight = 1;

      if (
        preparedDisease.observations.has(selectedSymptom.iri) &&
        !usedObservations.has(selectedSymptom.iri)
      ) {
        matchedObservation = selectedSymptom;
        type = "exact";
        baseWeight = 1;
      } else if (selectedSymptom.canonical !== null) {
        const candidatesByConcept =
          preparedDisease.byCanonical.get(selectedSymptom.canonical.iri) ?? [];
        const available = candidatesByConcept.find(
          (symptom) => !usedObservations.has(symptom.iri)
        );

        if (available !== undefined) {
          matchedObservation = available;
          type = "canonical";
          baseWeight =
            selectedSymptom.id === selectedSymptom.canonical.id
              ? 1
              : opts.canonicalWeight;
        }
      }

      if (matchedObservation === null || type === null) {
        unexplainedSymptoms.push(selectedSymptom);
        continue;
      }

      usedObservations.add(matchedObservation.iri);

      const df =
        type === "canonical"
          ? prepared.canonicalDf.get(selectedSymptom.canonical!.iri) ?? 1
          : dfForSymptom(selectedSymptom, prepared);
      const spec = specificity(df, prepared.diseaseCount);
      const weight = evidenceWeight(
        baseWeight * partWeight(matchedObservation.part),
        spec
      );

      cf = cf + weight * (1 - cf);

      const canonical = selectedSymptom.canonical;

      evidence.push({
        type,
        ruleId:
          type === "exact"
            ? exactRuleId(disease.id, selectedSymptom.id)
            : canonicalRuleId(disease.id, canonical!.id),
        symptomId: selectedSymptom.id,
        symptomLabel: selectedSymptom.label,
        matchedObservationId: matchedObservation.id,
        canonicalSymptomId: canonical?.id ?? null,
        canonicalSymptomLabel: canonical?.label ?? null,
        weight: round4(weight),
        cfAfter: round4(cf),
      });
      matchedSymptoms.push(selectedSymptom);
    }

    if (evidence.length === 0) {
      continue;
    }

    const completeness = matchedSymptoms.length / selected.length;
    const coverage =
      disease.symptoms.length === 0
        ? 0
        : matchedSymptoms.length /
          Math.max(
            disease.symptoms.length,
            REASONING_CONFIG.minCoverageDenominator
          );
    const score = scoreCandidate(cf, completeness, coverage, phaseFactor);

    if (score < opts.evidenceFloor) {
      continue;
    }

    candidates.push({
      disease,
      score,
      confidence: classifyConfidence(score, evidence.length),
      phaseMatch,
      evidence,
      matchedSymptoms,
      unexplainedSymptoms,
      scoreComponents: {
        evidence: round4(cf),
        completeness: round4(completeness),
        coverage: round4(coverage),
        phase: round4(phaseFactor),
      },
    });
  }

  candidates.sort(
    (left, right) =>
      right.score - left.score ||
      right.evidence.length - left.evidence.length ||
      left.disease.label.localeCompare(right.disease.label, "id") ||
      left.disease.iri.localeCompare(right.disease.iri)
  );

  const totalMatched = candidates.length;
  const top = candidates.slice(0, Math.max(1, Math.floor(opts.topN)));

  if (totalMatched === 0) {
    warnings.add("NO_MATCHING_DISEASE");
  }

  return {
    candidates: top,
    totalMatched,
    warnings: [...warnings],
    modelVersion: REASONING_MODEL_VERSION,
  };
}
