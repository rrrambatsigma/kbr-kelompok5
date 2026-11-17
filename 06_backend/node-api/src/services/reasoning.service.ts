import { env } from "../config/env.js";
import { ReasoningError } from "../lib/errors.js";
import { createReasoningClient } from "./reasoning.client.js";

const client = createReasoningClient({
  baseUrl: env.reasoningApiUrl,
  timeoutMs: env.reasoningTimeoutMs,
});

export interface ReasoningStatus {
  loaded: boolean;
  ready: boolean;
  consistent: boolean;
  ontologyIri: string | null;
  version: string | null;
  checksum: string | null;
  sourceFile: string | null;
  loadedAt: string | null;
  classCount: number;
  individualCount: number;
  objectPropertyCount: number;
  dataPropertyCount: number;
  diseaseCategoryCounts: Record<string, number>;
  unclassifiedDiseaseCount: number;
  lastError: string | null;
}

export interface DiseaseCategoriesData {
  categories: Record<string, string>;
  counts: Record<string, number>;
  unclassifiedDiseaseCount: number;
  requestedCount: number;
  foundCount: number;
  missing: string[];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export async function getReasoningStatus(
  requestId?: string
): Promise<ReasoningStatus> {
  const data = await client.getStatus(requestId);

  if (!isRecord(data) || typeof data["loaded"] !== "boolean") {
    throw new ReasoningError(
      "REASONING_INVALID_RESPONSE",
      502,
      "Struktur status reasoning tidak valid"
    );
  }

  return data as unknown as ReasoningStatus;
}

export async function getDiseaseCategories(
  diseaseIris: readonly string[],
  requestId?: string
): Promise<DiseaseCategoriesData> {
  const data = await client.getDiseaseCategories(diseaseIris, requestId);

  if (!isRecord(data) || !isRecord(data["categories"])) {
    throw new ReasoningError(
      "REASONING_INVALID_RESPONSE",
      502,
      "Struktur kategori penyakit tidak valid"
    );
  }

  return data as unknown as DiseaseCategoriesData;
}
