import type {
  DiagnosisDataset,
  DiagnosisDisease,
  DiagnosisSymptom,
} from "../../services/knowledge.service.js";

export interface PreparedDisease {
  disease: DiagnosisDisease;
  observations: Set<string>;
  /** canonical IRI -> observasi penyakit yang memakai konsep itu. */
  byCanonical: Map<string, DiagnosisSymptom[]>;
}

export interface PreparedDataset {
  diseaseCount: number;
  diseases: PreparedDisease[];
  /** ID local (dipakai API) -> gejala. */
  symptomById: Map<string, DiagnosisSymptom>;
  /** IRI -> gejala, untuk lookup internal berbasis graph. */
  symptomByIri: Map<string, DiagnosisSymptom>;
  observationDf: Map<string, number>;
  canonicalDf: Map<string, number>;
  canonicalObservationCount: number;
}

function compareSymptoms(
  left: DiagnosisSymptom,
  right: DiagnosisSymptom
): number {
  return (
    left.label.localeCompare(right.label, "id") ||
    left.iri.localeCompare(right.iri)
  );
}

/**
 * Menyiapkan index yang dipakai engine:
 *
 * - observasi -> penyakit (untuk exact match dan df)
 * - kanonik -> penyakit (untuk specificitas)
 * - observasi per penyakit per kanonik (untuk canonical match)
 *
 * Semua urutan dibuat deterministik supaya hasil diagnosis stabil.
 */
export function prepareDataset(dataset: DiagnosisDataset): PreparedDataset {
  const symptomById = new Map<string, DiagnosisSymptom>();
  const symptomByIri = new Map<string, DiagnosisSymptom>();
  const observationDiseases = new Map<string, Set<string>>();
  const canonicalDiseases = new Map<string, Set<string>>();
  const canonicalObservationIris = new Set<string>();
  const diseases: PreparedDisease[] = [];

  for (const disease of dataset.diseases) {
    if (disease.symptoms.length === 0) {
      continue;
    }

    const observations = new Set<string>();
    const byCanonical = new Map<string, DiagnosisSymptom[]>();

    for (const symptom of disease.symptoms) {
      if (!symptomById.has(symptom.id)) {
        symptomById.set(symptom.id, symptom);
      }
      if (!symptomByIri.has(symptom.iri)) {
        symptomByIri.set(symptom.iri, symptom);
      }

      observations.add(symptom.iri);

      const observationDiseaseSet =
        observationDiseases.get(symptom.iri) ?? new Set<string>();
      observationDiseaseSet.add(disease.iri);
      observationDiseases.set(symptom.iri, observationDiseaseSet);

      if (symptom.canonical !== null) {
        canonicalObservationIris.add(symptom.iri);

        const canonicalDiseaseSet =
          canonicalDiseases.get(symptom.canonical.iri) ?? new Set<string>();
        canonicalDiseaseSet.add(disease.iri);
        canonicalDiseases.set(symptom.canonical.iri, canonicalDiseaseSet);

        const list = byCanonical.get(symptom.canonical.iri) ?? [];
        list.push(symptom);
        byCanonical.set(symptom.canonical.iri, list);
      }
    }

    for (const list of byCanonical.values()) {
      list.sort(compareSymptoms);
    }

    diseases.push({ disease, observations, byCanonical });
  }

  const observationDf = new Map<string, number>();
  for (const [iri, diseaseSet] of observationDiseases) {
    observationDf.set(iri, diseaseSet.size);
  }

  const canonicalDf = new Map<string, number>();
  for (const [iri, diseaseSet] of canonicalDiseases) {
    canonicalDf.set(iri, diseaseSet.size);
  }

  return {
    diseaseCount: diseases.length,
    diseases,
    symptomById,
    symptomByIri,
    observationDf,
    canonicalDf,
    canonicalObservationCount: canonicalObservationIris.size,
  };
}

export function exactRuleId(
  diseaseId: string,
  observationId: string
): string {
  return `R-EXACT-${diseaseId}-${observationId}`;
}

export function canonicalRuleId(
  diseaseId: string,
  canonicalId: string
): string {
  return `R-CANON-${diseaseId}-${canonicalId}`;
}
