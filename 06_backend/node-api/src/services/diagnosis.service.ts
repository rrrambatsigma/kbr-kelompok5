import { InvalidRequestError } from "../lib/errors.js";
import { reason } from "../lib/reasoning/engine.js";
import { explainCandidate } from "../lib/reasoning/explain.js";
import {
  REASONING_MODEL_VERSION,
  type Confidence,
  type PhaseMatch,
  type ReasoningEvidence,
  type ScoreComponents,
} from "../lib/reasoning/types.js";
import {
  getControlsForDiseases,
  getDiagnosisDataset,
  type DiagnosisDataset,
  type DiagnosisDisease,
  type DiagnosisSymptom,
  type NamedEntity,
} from "./knowledge.service.js";
import {
  getDiseaseCategories,
  getReasoningStatus,
  type ReasoningStatus,
} from "./reasoning.service.js";

export interface DiagnosisInput {
  plantId: string;
  phaseId: string | null;
  symptomIds: string[];
  topN: number;
}

export interface DiagnosisSymptomView {
  id: string;
  iri: string;
  label: string;
}

export interface DiagnosisCandidate {
  diseaseId: string;
  diseaseIri: string;
  label: string;
  score: number;
  matchRatio: number;
  coverage: number;
  matchedCount: number;
  selectedCount: number;
  totalSymptoms: number;
  matchedSymptoms: DiagnosisSymptomView[];
  unmatchedSelectedSymptoms: DiagnosisSymptomView[];
  category: string | null;
  controls: NamedEntity[];
  riskFactors: NamedEntity[];
  confidence: Confidence;
  phaseMatch: PhaseMatch;
  evidence: ReasoningEvidence[];
  explanation: string;
  scoreComponents: ScoreComponents;
}

export interface DiagnosisReasoningInfo {
  status: "UP" | "DEGRADED";
  modelVersion: string;
  ontologyVersion: string | null;
  checksum: string | null;
  categoryCounts: Record<string, number> | null;
}

export interface DiagnosisResult {
  input: {
    plantId: string;
    plantIri: string;
    plantLabel: string | null;
    phaseId: string | null;
    phaseIri: string | null;
    phaseLabel: string | null;
    symptomIds: string[];
    symptoms: DiagnosisSymptomView[];
    topN: number;
  };
  candidates: DiagnosisCandidate[];
  reasoning: DiagnosisReasoningInfo;
  warnings: string[];
  message: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function parseDiagnosisInput(body: unknown): DiagnosisInput {
  if (!isRecord(body)) {
    throw new InvalidRequestError("Body request harus berupa objek JSON");
  }

  const details: Array<{ field: string; message: string }> = [];

  const plantId = body["plantId"];
  if (typeof plantId !== "string" || plantId.trim() === "") {
    details.push({ field: "plantId", message: "plantId wajib diisi" });
  }

  const rawPhaseId = body["phaseId"];
  let phaseId: string | null = null;
  if (rawPhaseId !== undefined && rawPhaseId !== null) {
    if (typeof rawPhaseId !== "string" || rawPhaseId.trim() === "") {
      details.push({
        field: "phaseId",
        message: "phaseId harus string tidak kosong",
      });
    } else {
      phaseId = rawPhaseId.trim();
    }
  }

  const symptomIds = body["symptomIds"];
  if (!Array.isArray(symptomIds) || symptomIds.length === 0) {
    details.push({
      field: "symptomIds",
      message: "symptomIds minimal berisi satu ID",
    });
  } else if (symptomIds.length > 100) {
    details.push({
      field: "symptomIds",
      message: "symptomIds maksimal 100 ID",
    });
  } else {
    symptomIds.forEach((value, index) => {
      if (typeof value !== "string" || value.trim() === "") {
        details.push({
          field: `symptomIds[${index}]`,
          message: "symptomIds tidak boleh berisi ID kosong",
        });
      }
    });
  }

  const rawTopN = body["topN"];
  let topN = 5;
  if (rawTopN !== undefined && rawTopN !== null) {
    if (
      typeof rawTopN !== "number" ||
      !Number.isInteger(rawTopN) ||
      rawTopN < 1 ||
      rawTopN > 10
    ) {
      details.push({
        field: "topN",
        message: "topN harus integer 1-10",
      });
    } else {
      topN = rawTopN;
    }
  }

  if (details.length > 0) {
    throw new InvalidRequestError("Request diagnosis tidak valid", details);
  }

  return {
    plantId: (plantId as string).trim(),
    phaseId,
    symptomIds: (symptomIds as string[]).map((value) => value.trim()),
    topN,
  };
}

function dedupePreservingOrder(values: string[]): {
  unique: string[];
  hadDuplicates: boolean;
} {
  const unique: string[] = [];
  const seen = new Set<string>();

  for (const value of values) {
    if (seen.has(value)) {
      continue;
    }
    seen.add(value);
    unique.push(value);
  }

  return { unique, hadDuplicates: unique.length !== values.length };
}

function symptomIndex(
  diseases: DiagnosisDisease[]
): Map<string, DiagnosisSymptomView> {
  const index = new Map<string, DiagnosisSymptomView>();

  for (const disease of diseases) {
    for (const symptom of disease.symptoms) {
      if (!index.has(symptom.id)) {
        index.set(symptom.id, {
          id: symptom.id,
          iri: symptom.iri,
          label: symptom.label,
        });
      }
    }
  }

  return index;
}

function findPhase(
  dataset: DiagnosisDataset,
  phaseId: string
): NamedEntity | null {
  const phase = dataset.phaseOptions.find(
    (item) => item.id === phaseId || item.iri === phaseId
  );

  return phase ?? null;
}

function explainWithPhase(
  base: string,
  phaseMatch: PhaseMatch,
  phaseLabel: string | null
): string {
  if (phaseLabel === null) {
    return base;
  }

  if (phaseMatch === "match") {
    return `${base} ${phaseLabel} juga tercatat sebagai fase rentan penyakit ini.`;
  }

  if (phaseMatch === "mismatch") {
    return `${base} ${phaseLabel} tidak tercatat sebagai fase rentan kandidat ini.`;
  }

  return `${base} Data fase pertumbuhan untuk kandidat ini belum tersedia.`;
}

export async function diagnose(
  input: DiagnosisInput,
  requestId?: string
): Promise<DiagnosisResult> {
  const dataset = await getDiagnosisDataset(input.plantId);
  const plant = dataset.plant;
  const plantIri = plant.iri;
  const plantLabel = plant.label;

  const selectedPhase =
    input.phaseId === null ? null : findPhase(dataset, input.phaseId);

  if (input.phaseId !== null && selectedPhase === null) {
    throw new InvalidRequestError(
      "Fase pertumbuhan tidak dikenali untuk tanaman ini",
      [
        {
          field: "phaseId",
          message: `Fase tidak ditemukan pada tanaman ${input.plantId}: ${input.phaseId}`,
        },
      ]
    );
  }

  const phaseId = selectedPhase?.id ?? null;
  const phaseIri = selectedPhase?.iri ?? null;
  const phaseLabel = selectedPhase?.label ?? null;

  const diseasesWithSymptoms = dataset.diseases.filter(
    (disease) => disease.symptoms.length > 0
  );

  const warnings: string[] = [];

  const { unique: selectedIds, hadDuplicates } = dedupePreservingOrder(
    input.symptomIds
  );

  if (hadDuplicates) {
    warnings.push("DUPLICATE_SYMPTOM_IDS_IGNORED");
  }

  if (diseasesWithSymptoms.length === 0) {
    warnings.push("NO_DISEASE_DATA_FOR_PLANT");
    return {
      input: {
        plantId: input.plantId,
        plantIri,
        plantLabel,
        phaseId,
        phaseIri,
        phaseLabel,
        symptomIds: selectedIds,
        symptoms: [],
        topN: input.topN,
      },
      candidates: [],
      reasoning: {
        status: "DEGRADED",
        modelVersion: REASONING_MODEL_VERSION,
        ontologyVersion: null,
        checksum: null,
        categoryCounts: null,
      },
      warnings,
      message:
        "Tidak ada data penyakit untuk tanaman ini di knowledge base.",
    };
  }

  const symptomsById = symptomIndex(diseasesWithSymptoms);
  const selectedSymptoms: DiagnosisSymptomView[] = [];
  const unknownSymptoms: string[] = [];

  for (const id of selectedIds) {
    const symptom = symptomsById.get(id);
    if (symptom === undefined) {
      unknownSymptoms.push(id);
    } else {
      selectedSymptoms.push(symptom);
    }
  }

  if (unknownSymptoms.length > 0) {
    throw new InvalidRequestError(
      "Ada gejala yang tidak dikenali untuk tanaman ini",
      unknownSymptoms.map((id) => ({
        field: "symptomIds",
        message: `Gejala tidak ditemukan pada tanaman ${input.plantId}: ${id}`,
      }))
    );
  }

  const selected = selectedSymptoms.map((symptom) => symptom.id);

  const reasoningResult = reason(dataset, selected, {
    topN: input.topN,
    phaseIri,
  });
  const top = reasoningResult.candidates;
  const topIris = top.map((candidate) => candidate.disease.iri);

  for (const warning of reasoningResult.warnings) {
    if (!warnings.includes(warning)) {
      warnings.push(warning);
    }
  }

  let reasoning: DiagnosisReasoningInfo = {
    status: "DEGRADED",
    modelVersion: REASONING_MODEL_VERSION,
    ontologyVersion: null,
    checksum: null,
    categoryCounts: null,
  };
  let categories: Record<string, string> = {};

  try {
    const [categoryData, status] = await Promise.all([
      getDiseaseCategories(topIris, requestId),
      getReasoningStatus(requestId),
    ]);

    categories = categoryData.categories;
    reasoning = toReasoningInfo(status, categoryData.counts);
  } catch (error) {
    warnings.push("REASONING_UNAVAILABLE");
    console.warn(
      `[${requestId ?? "-"}] Diagnosis berjalan tanpa reasoning API:`,
      error instanceof Error ? error.message : String(error)
    );
  }

  const controlsByDisease = await getControlsForDiseases(topIris);

  let unclassifiedCount = 0;

  const candidates: DiagnosisCandidate[] = top.map((candidate) => {
    const category = categories[candidate.disease.iri] ?? null;
    if (category === null && reasoning.status === "UP") {
      unclassifiedCount++;
    }

    return {
      diseaseId: candidate.disease.id,
      diseaseIri: candidate.disease.iri,
      label: candidate.disease.label,
      score: candidate.score,
      matchRatio: candidate.scoreComponents.completeness,
      coverage: candidate.scoreComponents.coverage,
      matchedCount: candidate.evidence.length,
      selectedCount: selected.length,
      totalSymptoms: candidate.disease.symptoms.length,
      matchedSymptoms: candidate.matchedSymptoms.map(toSymptomView),
      unmatchedSelectedSymptoms: candidate.unexplainedSymptoms.map(
        toSymptomView
      ),
      category,
      controls: controlsByDisease[candidate.disease.iri] ?? [],
      riskFactors: candidate.disease.riskFactors.map((factor) => ({
        id: factor.id,
        iri: factor.iri,
        label: factor.label,
      })),
      confidence: candidate.confidence,
      phaseMatch: candidate.phaseMatch,
      evidence: candidate.evidence,
      explanation: explainWithPhase(
        explainCandidate(candidate),
        candidate.phaseMatch,
        phaseLabel
      ),
      scoreComponents: candidate.scoreComponents,
    };
  });

  if (candidates.length === 0) {
    if (!warnings.includes("NO_MATCHING_DISEASE")) {
      warnings.push("NO_MATCHING_DISEASE");
    }
  }

  if (unclassifiedCount > 0) {
    warnings.push("DISEASE_CATEGORY_UNCLASSIFIED");
  }

  return {
    input: {
      plantId: input.plantId,
      plantIri,
      plantLabel,
      phaseId,
      phaseIri,
      phaseLabel,
      symptomIds: selected,
      symptoms: selectedSymptoms,
      topN: input.topN,
    },
    candidates,
    reasoning,
    warnings,
    message: buildMessage(candidates.length, reasoningResult.totalMatched),
  };
}

function toReasoningInfo(
  status: ReasoningStatus,
  counts: Record<string, number>
): DiagnosisReasoningInfo {
  return {
    status: status.ready ? "UP" : "DEGRADED",
    modelVersion: REASONING_MODEL_VERSION,
    ontologyVersion: status.version ?? null,
    checksum: status.checksum ?? null,
    categoryCounts: counts,
  };
}

function toSymptomView(symptom: DiagnosisSymptom): DiagnosisSymptomView {
  return {
    id: symptom.id,
    iri: symptom.iri,
    label: symptom.label,
  };
}

function buildMessage(candidateCount: number, totalMatched: number): string {
  if (candidateCount === 0) {
    return "Tidak ada penyakit yang cocok dengan gejala yang dipilih.";
  }
  if (candidateCount === totalMatched) {
    return `Ditemukan ${totalMatched} kandidat penyakit berdasarkan gejala yang dipilih.`;
  }
  return `Menampilkan ${candidateCount} dari ${totalMatched} kandidat penyakit yang cocok.`;
}
