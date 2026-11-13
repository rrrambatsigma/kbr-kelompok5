import { env } from "../config/env.js";
import { ReasoningError, ReasoningUnavailableError } from "../lib/errors.js";

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

interface Envelope {
  success?: unknown;
  data?: unknown;
  error?: {
    code?: unknown;
    message?: unknown;
  };
}

function describeFetchFailure(error: unknown): string {
  if (error instanceof DOMException && error.name === "TimeoutError") {
    return `Reasoning API tidak merespons dalam ${env.reasoningTimeoutMs} ms`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

async function request(path: string, init: RequestInit): Promise<unknown> {
  let response: Response;

  try {
    response = await fetch(`${env.reasoningApiUrl}${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
        ...(init.body === undefined ? {} : { "Content-Type": "application/json" }),
        ...init.headers,
      },
      signal: AbortSignal.timeout(env.reasoningTimeoutMs),
    });
  } catch (error) {
    throw new ReasoningUnavailableError(
      `Reasoning API tidak dapat dihubungi: ${describeFetchFailure(error)}`
    );
  }

  const text = await response.text();
  let parsed: unknown;

  try {
    parsed = text === "" ? {} : (JSON.parse(text) as unknown);
  } catch {
    throw new ReasoningError(
      "REASONING_INVALID_RESPONSE",
      502,
      "Reasoning API mengembalikan body yang bukan JSON valid"
    );
  }

  const envelope: Envelope = isRecord(parsed) ? parsed : {};

  if (!response.ok || envelope.success === false) {
    const code =
      typeof envelope.error?.code === "string"
        ? envelope.error.code
        : "REASONING_ERROR";
    const message =
      typeof envelope.error?.message === "string"
        ? envelope.error.message
        : `Reasoning API mengembalikan HTTP ${response.status}`;

    throw new ReasoningError(code, response.status, message);
  }

  return envelope.data;
}

export async function getReasoningStatus(): Promise<ReasoningStatus> {
  const data = await request("/api/reasoning/status", { method: "GET" });

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
  diseaseIris: string[]
): Promise<DiseaseCategoriesData> {
  const data = await request("/api/reasoning/disease-categories", {
    method: "POST",
    body: JSON.stringify({ diseaseIris }),
  });

  if (!isRecord(data) || !isRecord(data["categories"])) {
    throw new ReasoningError(
      "REASONING_INVALID_RESPONSE",
      502,
      "Struktur kategori penyakit tidak valid"
    );
  }

  return data as unknown as DiseaseCategoriesData;
}
