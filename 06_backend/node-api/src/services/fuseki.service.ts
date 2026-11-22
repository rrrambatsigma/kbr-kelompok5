import { fusekiConfig } from "../config/fuseki.js";
import {
  FusekiInvalidResponseError,
  FusekiQueryError,
  FusekiUnavailableError,
} from "../lib/errors.js";

export interface SparqlTerm {
  type: string;
  value: string;
  datatype?: string;
  "xml:lang"?: string;
}

export type SparqlBinding = Record<string, SparqlTerm | undefined>;

export interface SparqlSelectResponse {
  head: {
    vars: string[];
  };
  results: {
    bindings: SparqlBinding[];
  };
}

interface SparqlAskResponse {
  boolean: boolean;
}

const MAX_ERROR_BODY = 2000;

async function readErrorBody(response: Response): Promise<string> {
  try {
    const text = await response.text();
    return text.slice(0, MAX_ERROR_BODY);
  } catch {
    return "";
  }
}

function describeFetchFailure(error: unknown): string {
  if (error instanceof DOMException && error.name === "TimeoutError") {
    return `Fuseki tidak merespons dalam ${fusekiConfig.timeoutMs} ms`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
}

async function postQuery(
  url: string,
  query: string,
  accept: string,
  timeoutMs: number
): Promise<Response> {
  try {
    return await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        Accept: accept,
      },
      body: new URLSearchParams({ query }),
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch (error) {
    throw new FusekiUnavailableError(
      `Fuseki tidak dapat dihubungi: ${describeFetchFailure(error)}`
    );
  }
}

async function readJson(response: Response): Promise<unknown> {
  const text = await response.text();
  try {
    return JSON.parse(text) as unknown;
  } catch {
    throw new FusekiInvalidResponseError(
      "Fuseki mengembalikan body yang bukan JSON valid"
    );
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function assertSelectResponse(value: unknown): asserts value is SparqlSelectResponse {
  if (
    !isRecord(value) ||
    !isRecord(value["head"]) ||
    !Array.isArray((value["head"] as Record<string, unknown>)["vars"]) ||
    !isRecord(value["results"]) ||
    !Array.isArray((value["results"] as Record<string, unknown>)["bindings"])
  ) {
    throw new FusekiInvalidResponseError(
      "Struktur SPARQL SELECT dari Fuseki tidak valid"
    );
  }
}

function assertAskResponse(value: unknown): asserts value is SparqlAskResponse {
  if (!isRecord(value) || typeof value["boolean"] !== "boolean") {
    throw new FusekiInvalidResponseError(
      "Struktur SPARQL ASK dari Fuseki tidak valid"
    );
  }
}

export async function select(query: string): Promise<SparqlSelectResponse> {
  return selectAt(fusekiConfig.queryUrl, query);
}

export async function selectAt(
  url: string,
  query: string,
  timeoutMs: number = fusekiConfig.timeoutMs
): Promise<SparqlSelectResponse> {
  const response = await postQuery(
    url,
    query,
    "application/sparql-results+json",
    timeoutMs
  );

  if (!response.ok) {
    const upstreamBody = await readErrorBody(response);
    if (response.status >= 500) {
      throw new FusekiUnavailableError(
        `Fuseki mengembalikan HTTP ${response.status}: ${upstreamBody || "tanpa body"}`
      );
    }
    throw new FusekiQueryError(
      `Query SPARQL ditolak Fuseki: ${upstreamBody || "tanpa body"}`,
      response.status
    );
  }

  const parsed = await readJson(response);
  assertSelectResponse(parsed);
  return parsed;
}

export async function ask(query: string): Promise<boolean> {
  const response = await postQuery(
    fusekiConfig.queryUrl,
    query,
    "application/sparql-results+json",
    fusekiConfig.timeoutMs
  );

  if (!response.ok) {
    const upstreamBody = await readErrorBody(response);
    if (response.status >= 500) {
      throw new FusekiUnavailableError(
        `Fuseki mengembalikan HTTP ${response.status}: ${upstreamBody || "tanpa body"}`
      );
    }
    throw new FusekiQueryError(
      `Query SPARQL ditolak Fuseki: ${upstreamBody || "tanpa body"}`,
      response.status
    );
  }

  const parsed = await readJson(response);
  assertAskResponse(parsed);
  return parsed.boolean;
}

/**
 * Menjalankan SPARQL Update ke dataset kasus (plant-kb-kasus).
 * Hanya dipakai untuk log kasus; dataset ontology tetap read-only.
 */
export async function update(
  sparqlUpdate: string,
  timeoutMs: number = fusekiConfig.timeoutMs
): Promise<void> {
  let response: Response;

  try {
    response = await fetch(fusekiConfig.caseUpdateUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/sparql-update",
        Accept: "*/*",
      },
      body: sparqlUpdate,
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch (error) {
    throw new FusekiUnavailableError(
      `Fuseki (case store) tidak dapat dihubungi: ${describeFetchFailure(error)}`
    );
  }

  if (!response.ok) {
    const upstreamBody = await readErrorBody(response);
    if (response.status >= 500) {
      throw new FusekiUnavailableError(
        `Fuseki (case store) mengembalikan HTTP ${response.status}: ${upstreamBody || "tanpa body"}`
      );
    }
    throw new FusekiQueryError(
      `Update SPARQL ditolak Fuseki: ${upstreamBody || "tanpa body"}`,
      response.status
    );
  }
}

export function termValue(
  binding: SparqlBinding,
  key: string
): string | undefined {
  return binding[key]?.value;
}

export function requireIntegerTerm(binding: SparqlBinding, key: string): number {
  const raw = termValue(binding, key);

  if (raw === undefined) {
    throw new FusekiInvalidResponseError(
      `Fuseki tidak mengembalikan binding "${key}"`
    );
  }

  const parsed = Number(raw);

  if (!Number.isInteger(parsed) || parsed < 0) {
    throw new FusekiInvalidResponseError(
      `Binding "${key}" bukan integer valid: "${raw}"`
    );
  }

  return parsed;
}

export function localName(iri: string): string {
  const hashIndex = iri.lastIndexOf("#");
  if (hashIndex >= 0) {
    return iri.slice(hashIndex + 1);
  }
  const slashIndex = iri.lastIndexOf("/");
  return slashIndex >= 0 ? iri.slice(slashIndex + 1) : iri;
}
