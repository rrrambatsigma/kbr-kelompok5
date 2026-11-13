import { InvalidRequestError, NotFoundError } from "../lib/errors.js";
import { compareCandidates, scoreCandidate } from "../lib/scoring.js";
import {
  getControlsForDiseases,
  getDiagnosisDataset,
  listPlants,
  toIri,
  type DiagnosisDisease,
  type NamedEntity,
} from "./knowledge.service.js";
import {
  getDiseaseCategories,
  getReasoningStatus,
  type ReasoningStatus,
} from "./reasoning.service.js";

export interface DiagnosisInput {
  plantId: string;
  symptomIds: string[];
  topN: number;
}

export interface DiagnosisSymptom {
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
  matchedSymptoms: DiagnosisSymptom[];
  unmatchedSelectedSymptoms: DiagnosisSymptom[];
  category: string | null;
  controls: NamedEntity[];
}

export interface DiagnosisReasoningInfo {
  status: "UP" | "DEGRADED";
  ontologyVersion: string | null;
  checksum: string | null;
  categoryCounts: Record<string, number> | null;
}

export interface DiagnosisResult {
  input: {
    plantId: string;
    plantIri: string;
    plantLabel: string | null;
    symptomIds: string[];
    symptoms: DiagnosisSymptom[];
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
): Map<string, DiagnosisSymptom> {
  const index = new Map<string, DiagnosisSymptom>();

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

export async function diagnose(input: DiagnosisInput): Promise<DiagnosisResult> {
  const plantIri = toIri(input.plantId);

  const [plants, dataset] = await Promise.all([
    listPlants(),
    getDiagnosisDataset(input.plantId),
  ]);

  const plant = plants.find((item) => item.iri === plantIri);

  if (plant === undefined) {
    throw new NotFoundError(`Tanaman tidak ditemukan: ${input.plantId}`);
  }

  const plantLabel = plant.label;

  const warnings: string[] = [];

  const { unique: selectedIds, hadDuplicates } = dedupePreservingOrder(
    input.symptomIds
  );

  if (hadDuplicates) {
    warnings.push("DUPLICATE_SYMPTOM_IDS_IGNORED");
  }

  if (dataset.length === 0) {
    warnings.push("NO_DISEASE_DATA_FOR_PLANT");
    return {
      input: {
        plantId: input.plantId,
        plantIri,
        plantLabel,
        symptomIds: selectedIds,
        symptoms: [],
        topN: input.topN,
      },
      candidates: [],
      reasoning: {
        status: "DEGRADED",
        ontologyVersion: null,
        checksum: null,
        categoryCounts: null,
      },
      warnings,
      message:
        "Tidak ada data penyakit untuk tanaman ini di knowledge base.",
    };
  }

  const symptomsById = symptomIndex(dataset);
  const selectedSymptoms: DiagnosisSymptom[] = [];
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

  const scored = dataset.map((disease) => {
    const score = scoreCandidate(
      selected,
      disease.symptoms.map((symptom) => symptom.id)
    );

    return {
      disease,
      score,
    };
  });

  const matchedCandidates = scored
    .filter((entry) => entry.score.matchedCount > 0)
    .sort((left, right) =>
      compareCandidates(
        {
          score: left.score.score,
          matchedCount: left.score.matchedCount,
          label: left.disease.label,
        },
        {
          score: right.score.score,
          matchedCount: right.score.matchedCount,
          label: right.disease.label,
        }
      )
    );

  const top = matchedCandidates.slice(0, input.topN);
  const topIris = top.map((entry) => entry.disease.iri);

  let reasoning: DiagnosisReasoningInfo = {
    status: "DEGRADED",
    ontologyVersion: null,
    checksum: null,
    categoryCounts: null,
  };
  let categories: Record<string, string> = {};

  try {
    const [categoryData, status] = await Promise.all([
      getDiseaseCategories(topIris),
      getReasoningStatus(),
    ]);

    categories = categoryData.categories;
    reasoning = toReasoningInfo(status, categoryData.counts);
  } catch (error) {
    warnings.push("REASONING_UNAVAILABLE");
    console.warn(
      "Diagnosis berjalan tanpa reasoning API:",
      error instanceof Error ? error.message : String(error)
    );
  }

  const controlsByDisease = await getControlsForDiseases(topIris);

  let unclassifiedCount = 0;

  const candidates: DiagnosisCandidate[] = top.map((entry) => {
    const matchedSet = new Set(
      entry.disease.symptoms.map((symptom) => symptom.id)
    );

    const category = categories[entry.disease.iri] ?? null;
    if (category === null && reasoning.status === "UP") {
      unclassifiedCount++;
    }

    return {
      diseaseId: entry.disease.id,
      diseaseIri: entry.disease.iri,
      label: entry.disease.label,
      score: entry.score.score,
      matchRatio: entry.score.matchRatio,
      coverage: entry.score.coverage,
      matchedCount: entry.score.matchedCount,
      selectedCount: entry.score.selectedCount,
      totalSymptoms: entry.score.totalSymptoms,
      matchedSymptoms: selectedSymptoms.filter((symptom) =>
        matchedSet.has(symptom.id)
      ),
      unmatchedSelectedSymptoms: selectedSymptoms.filter(
        (symptom) => !matchedSet.has(symptom.id)
      ),
      category,
      controls: controlsByDisease[entry.disease.iri] ?? [],
    };
  });

  if (matchedCandidates.length === 0) {
    warnings.push("NO_MATCHING_DISEASE");
  }

  if (unclassifiedCount > 0) {
    warnings.push("DISEASE_CATEGORY_UNCLASSIFIED");
  }

  return {
    input: {
      plantId: input.plantId,
      plantIri,
      plantLabel,
      symptomIds: selected,
      symptoms: selectedSymptoms,
      topN: input.topN,
    },
    candidates,
    reasoning,
    warnings,
    message: buildMessage(candidates.length, matchedCandidates.length),
  };
}

function toReasoningInfo(
  status: ReasoningStatus,
  counts: Record<string, number>
): DiagnosisReasoningInfo {
  return {
    status: status.ready ? "UP" : "DEGRADED",
    ontologyVersion: status.version ?? null,
    checksum: status.checksum ?? null,
    categoryCounts: counts,
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
