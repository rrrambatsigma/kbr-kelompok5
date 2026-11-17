import { createHash } from "node:crypto";
import { readFile, stat } from "node:fs/promises";

import { env } from "../config/env.js";
import { ptpNamespace } from "../config/fuseki.js";
import {
  requireIntegerTerm,
  select,
  type SparqlBinding,
} from "./fuseki.service.js";
import {
  getReasoningStatus,
  type ReasoningStatus,
} from "./reasoning.service.js";

export type OntologyHealthStatus =
  | "OK"
  | "MISMATCH"
  | "UNKNOWN"
  | "DOWN";

export interface OntologyFileInfo {
  path: string | null;
  sha256: string | null;
  readable: boolean;
  error: string | null;
}

export interface OntologyFusekiInfo {
  totalTriples: number;
  deskripsiPenyakit: number;
  memilikiKondisiTumbuh: number;
}

export interface OntologyChecks {
  fileMatchesJava: boolean | null;
  fusekiHasV2Fingerprint: boolean;
}

export interface OntologyHealth {
  status: OntologyHealthStatus;
  file: OntologyFileInfo;
  java: ReasoningStatus | null;
  fuseki: OntologyFusekiInfo | null;
  checks: OntologyChecks;
  warnings: string[];
}

let fileCache:
  | {
      path: string;
      mtimeMs: number;
      size: number;
      sha256: string;
    }
  | null = null;

async function inspectFile(): Promise<OntologyFileInfo> {
  if (env.ontologyFilePath === "") {
    return {
      path: null,
      sha256: null,
      readable: false,
      error: "ONTOLOGY_FILE_PATH tidak diatur",
    };
  }

  try {
    const info = await stat(env.ontologyFilePath);

    if (!info.isFile()) {
      return {
        path: env.ontologyFilePath,
        sha256: null,
        readable: false,
        error: "Path bukan file biasa",
      };
    }

    if (
      fileCache !== null &&
      fileCache.path === env.ontologyFilePath &&
      fileCache.mtimeMs === info.mtimeMs &&
      fileCache.size === info.size
    ) {
      return {
        path: fileCache.path,
        sha256: fileCache.sha256,
        readable: true,
        error: null,
      };
    }

    const buffer = await readFile(env.ontologyFilePath);
    const sha256 = createHash("sha256").update(buffer).digest("hex");

    fileCache = {
      path: env.ontologyFilePath,
      mtimeMs: info.mtimeMs,
      size: info.size,
      sha256,
    };

    return {
      path: env.ontologyFilePath,
      sha256,
      readable: true,
      error: null,
    };
  } catch (error) {
    return {
      path: env.ontologyFilePath,
      sha256: null,
      readable: false,
      error: messageOf(error),
    };
  }
}

async function countQuery(query: string): Promise<number> {
  const result = await select(query);
  const binding: SparqlBinding = result.results.bindings[0] ?? {};
  return requireIntegerTerm(binding, "n");
}

async function inspectFuseki(): Promise<OntologyFusekiInfo> {
  const prefixes = `
    PREFIX ptp: <${ptpNamespace}>
  `;

  const [totalTriples, deskripsiPenyakit, memilikiKondisiTumbuh] =
    await Promise.all([
      countQuery(`
        SELECT (COUNT(*) AS ?n)
        WHERE { ?s ?p ?o }
      `),
      countQuery(`
        ${prefixes}
        SELECT (COUNT(*) AS ?n)
        WHERE { ?s ptp:deskripsiPenyakit ?o }
      `),
      countQuery(`
        ${prefixes}
        SELECT (COUNT(*) AS ?n)
        WHERE { ?s ptp:memilikiKondisiTumbuh ?o }
      `),
    ]);

  return {
    totalTriples,
    deskripsiPenyakit,
    memilikiKondisiTumbuh,
  };
}

async function inspectJava(
  requestId?: string
): Promise<{ status: ReasoningStatus | null; error: string | null }> {
  try {
    return { status: await getReasoningStatus(requestId), error: null };
  } catch (error) {
    return { status: null, error: messageOf(error) };
  }
}

/**
 * Menggabungkan tiga sumber kebenaran:
 *
 * - file ontology di disk (SHA-256),
 * - Java (checksum yang benar-benar dimuat),
 * - Fuseki (jumlah triple + fingerprint enrichment).
 *
 * Pemeriksaan otomatis yang mengikat adalah file vs Java. Fingerprint Fuseki
 * dilaporkan sebagai warning karena ontology final boleh mengubah isinya.
 */
export async function getOntologyHealth(
  requestId?: string
): Promise<OntologyHealth> {
  const [file, javaResult, fusekiResult] = await Promise.all([
    inspectFile(),
    inspectJava(requestId),
    inspectFuseki()
      .then((data) => ({ data, error: null as string | null }))
      .catch((error: unknown) => ({
        data: null,
        error: messageOf(error),
      })),
  ]);

  const warnings: string[] = [];

  if (file.error !== null) {
    warnings.push(`ONTOLOGY_FILE: ${file.error}`);
  }
  if (javaResult.error !== null) {
    warnings.push(`REASONING: ${javaResult.error}`);
  }
  if (fusekiResult.error !== null) {
    warnings.push(`FUSEKI: ${fusekiResult.error}`);
  }

  const java = javaResult.status;
  const fuseki = fusekiResult.data;

  const javaChecksum = java?.checksum ?? null;
  const fileMatchesJava =
    file.sha256 !== null && javaChecksum !== null
      ? file.sha256.toLowerCase() === javaChecksum.toLowerCase()
      : null;

  if (fileMatchesJava === false) {
    warnings.push("Checksum file ontology berbeda dengan yang dimuat Java");
  }

  const fusekiHasV2Fingerprint =
    fuseki !== null &&
    fuseki.deskripsiPenyakit > 0 &&
    fuseki.memilikiKondisiTumbuh > 0;

  if (fuseki !== null && !fusekiHasV2Fingerprint) {
    warnings.push(
      "Fingerprint enrichment Fuseki tidak lengkap (deskripsi/kondisi tumbuh kosong)"
    );
  }

  let status: OntologyHealthStatus;

  if (
    java === null ||
    fuseki === null ||
    !java.loaded ||
    !java.ready ||
    !java.consistent
  ) {
    status = "DOWN";
  } else if (fileMatchesJava === false) {
    status = "MISMATCH";
  } else if (fileMatchesJava === null) {
    status = "UNKNOWN";
  } else {
    status = "OK";
  }

  return {
    status,
    file,
    java,
    fuseki,
    checks: {
      fileMatchesJava,
      fusekiHasV2Fingerprint,
    },
    warnings,
  };
}

function messageOf(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
}
