import { randomUUID } from "node:crypto";

import { env } from "../config/env.js";
import { CASE_GRAPH, fusekiConfig } from "../config/fuseki.js";
import { AppError, InvalidRequestError, NotFoundError } from "../lib/errors.js";
import {
  escapeIri,
  literalDateTime,
  literalDecimal,
  literalInteger,
  literalString,
} from "../lib/sparql.js";
import type { DiagnosisResult } from "./diagnosis.service.js";
import {
  localName,
  selectAt,
  termValue,
  update,
  type SparqlBinding,
} from "./fuseki.service.js";
import { toIri } from "./knowledge.service.js";

const PREFIXES = `
PREFIX ptp: <http://kbr.kelompok5.org/penyakit-tanaman-pangan#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
`;

export const CASE_STATUSES = ["belum_diverifikasi", "terverifikasi"] as const;
export type CaseStatus = (typeof CASE_STATUSES)[number];

export const CASE_SOURCES = ["pengguna", "uji"] as const;
export type CaseSource = (typeof CASE_SOURCES)[number];

export interface CaseSaveInput {
  plantId: string;
  phaseId: string | null;
  symptomIds: string[];
  topN: number;
  note: string | null;
  freeTextSymptoms: string | null;
  confirmedDiseaseId: string | null;
  source: CaseSource;
}

export interface CaseCandidateView {
  diseaseId: string;
  diseaseIri: string;
  diseaseLabel: string | null;
  rank: number;
  score: number;
  confidence: string;
  explanation: string;
}

export interface CaseSummary {
  id: string;
  createdAt: string;
  plantId: string;
  plantLabel: string | null;
  phaseId: string | null;
  symptomCount: number;
  symptomLabels: string[];
  note: string | null;
  freeTextSymptoms: string | null;
  status: CaseStatus;
  source: CaseSource;
  topDiseaseId: string | null;
  topDiseaseLabel: string | null;
  topScore: number | null;
  candidateCount: number;
}

export interface CaseDetail extends CaseSummary {
  symptomIds: string[];
  candidates: CaseCandidateView[];
}

export interface CaseStats {
  total: number;
  verified: number;
  unverified: number;
  byPlant: Array<{ plantId: string; label: string | null; count: number }>;
  byDisease: Array<{
    diseaseId: string;
    label: string | null;
    count: number;
  }>;
}

export interface SimilarCaseInfo {
  count: number;
  maxOverlap: number;
  lastSeen: string | null;
}

export interface CaseListFilter {
  plantId?: string | undefined;
  status?: CaseStatus | undefined;
  limit: number;
  offset: number;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function optionalText(
  value: unknown,
  field: string,
  maxLength: number,
  details: Array<{ field: string; message: string }>
): string | null {
  if (value === undefined || value === null) {
    return null;
  }

  if (typeof value !== "string") {
    details.push({ field, message: `${field} harus string` });
    return null;
  }

  const trimmed = value.trim();

  if (trimmed === "") {
    return null;
  }

  if (trimmed.length > maxLength) {
    details.push({
      field,
      message: `${field} maksimal ${maxLength} karakter`,
    });
    return null;
  }

  return trimmed;
}

export function parseCaseInput(body: unknown): CaseSaveInput {
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

  const rawSymptoms = body["symptomIds"];
  const symptomIds: string[] = [];
  if (!Array.isArray(rawSymptoms) || rawSymptoms.length === 0) {
    details.push({
      field: "symptomIds",
      message: "symptomIds minimal berisi satu ID",
    });
  } else if (rawSymptoms.length > 100) {
    details.push({
      field: "symptomIds",
      message: "symptomIds maksimal 100 ID",
    });
  } else {
    rawSymptoms.forEach((value, index) => {
      if (typeof value !== "string" || value.trim() === "") {
        details.push({
          field: `symptomIds[${index}]`,
          message: "symptomIds tidak boleh berisi ID kosong",
        });
      } else {
        symptomIds.push(value.trim());
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

  const note = optionalText(body["note"], "note", 500, details);
  const freeTextSymptoms = optionalText(
    body["freeTextSymptoms"],
    "freeTextSymptoms",
    500,
    details
  );

  const rawConfirmed = body["confirmedDiseaseId"];
  let confirmedDiseaseId: string | null = null;
  if (rawConfirmed !== undefined && rawConfirmed !== null) {
    if (typeof rawConfirmed !== "string" || rawConfirmed.trim() === "") {
      details.push({
        field: "confirmedDiseaseId",
        message: "confirmedDiseaseId harus string tidak kosong",
      });
    } else {
      confirmedDiseaseId = rawConfirmed.trim();
    }
  }

  const rawSource = body["source"];
  let source: CaseSource = "pengguna";
  if (rawSource !== undefined && rawSource !== null) {
    if (
      typeof rawSource !== "string" ||
      !CASE_SOURCES.includes(rawSource as CaseSource)
    ) {
      details.push({
        field: "source",
        message: `source harus salah satu: ${CASE_SOURCES.join(", ")}`,
      });
    } else {
      source = rawSource as CaseSource;
    }
  }

  if (details.length > 0) {
    throw new InvalidRequestError("Request kasus tidak valid", details);
  }

  return {
    plantId: (plantId as string).trim(),
    phaseId,
    symptomIds,
    topN,
    note,
    freeTextSymptoms,
    confirmedDiseaseId,
    source,
  };
}

interface BuildCaseParams {
  caseId: string;
  createdAt: string;
  input: CaseSaveInput;
  result: DiagnosisResult;
  confirmedCandidateIndex?: number | undefined;
}

/**
 * Membangun satu blok INSERT DATA untuk kasus + kandidat.
 * Fungsi murni supaya mudah diuji tanpa Fuseki.
 */
export function buildCaseInsert(params: BuildCaseParams): string {
  const { caseId, createdAt, input, result, confirmedCandidateIndex } = params;
  const caseIri = escapeIri(caseIriOf(caseId));
  const plantIri = escapeIri(result.input.plantIri);

  const chosenIndex =
    confirmedCandidateIndex !== undefined && confirmedCandidateIndex >= 0
      ? confirmedCandidateIndex
      : 0;
  const chosen = result.candidates[chosenIndex] ?? null;

  const lines: string[] = [];
  lines.push(`${caseIri} a ptp:Diagnosis`);
  lines.push(`  ; ptp:idKasus ${literalString(caseId)}`);
  lines.push(`  ; ptp:waktuKasus ${literalDateTime(createdAt)}`);
  lines.push(`  ; ptp:sumberKasus ${literalString(input.source)}`);
  lines.push(`  ; ptp:statusVerifikasi ${literalString("belum_diverifikasi")}`);
  lines.push(`  ; ptp:memilikiTanaman ${plantIri}`);
  lines.push(
    `  ; ptp:namaTanaman ${literalString(result.input.plantLabel ?? localName(result.input.plantIri))}`
  );
  lines.push(
    `  ; ptp:ringkasanGejala ${literalString(
      result.input.symptoms.map((symptom) => symptom.label).join(" | ")
    )}`
  );

  if (result.input.phaseIri !== null) {
    lines.push(`  ; ptp:faseKasus ${escapeIri(result.input.phaseIri)}`);
  }

  const symptomIris = result.input.symptoms.map((symptom) =>
    escapeIri(symptom.iri)
  );
  if (symptomIris.length > 0) {
    lines.push(`  ; ptp:memilikiObservasi ${symptomIris.join(", ")}`);
  }

  if (input.note !== null) {
    lines.push(`  ; ptp:catatanPengguna ${literalString(input.note)}`);
  }

  if (input.freeTextSymptoms !== null) {
    lines.push(
      `  ; ptp:teksGejalaBebas ${literalString(input.freeTextSymptoms)}`
    );
  }

  if (chosen !== null) {
    lines.push(`  ; ptp:menghasilkanPenyakit ${escapeIri(chosen.diseaseIri)}`);
    lines.push(`  ; ptp:namaPenyakit ${literalString(chosen.label)}`);
  }

  const candidateIris = result.candidates.map((_, index) =>
    escapeIri(`${caseIriOf(caseId)}/kandidat-${index + 1}`)
  );

  if (candidateIris.length > 0) {
    lines.push(`  ; ptp:kandidat ${candidateIris.join(", ")}`);
  }

  lines[lines.length - 1] += " .";

  const candidateBlocks: string[] = [];

  result.candidates.forEach((candidate, index) => {
    const iri = escapeIri(`${caseIriOf(caseId)}/kandidat-${index + 1}`);
    const block = [
      `${iri} a ptp:KandidatDiagnosis`,
      `  ; ptp:peringkat ${literalInteger(index + 1)}`,
      `  ; ptp:skorKecocokan ${literalDecimal(candidate.score)}`,
      `  ; ptp:tingkatKeyakinan ${literalString(candidate.confidence)}`,
      `  ; ptp:alasanKecocokan ${literalString(candidate.explanation)}`,
      `  ; ptp:menghasilkanPenyakit ${escapeIri(candidate.diseaseIri)}`,
      `  ; ptp:namaPenyakit ${literalString(candidate.label)} .`,
    ];
    candidateBlocks.push(block.join("\n"));
  });

  return `${PREFIXES}
INSERT DATA {
  GRAPH <${CASE_GRAPH}> {
${lines.join("\n")}
${candidateBlocks.join("\n")}
  }
}`;
}

function caseIriOf(caseId: string): string {
  return `urn:kbr:kasus/${caseId}`;
}

function parseStatus(value: string | undefined): CaseStatus {
  return value === "terverifikasi" ? "terverifikasi" : "belum_diverifikasi";
}

function parseSource(value: string | undefined): CaseSource {
  return value === "uji" ? "uji" : "pengguna";
}

function numberValue(binding: SparqlBinding, key: string): number | null {
  const raw = termValue(binding, key);
  if (raw === undefined) {
    return null;
  }
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
}

function splitLabels(value: string | undefined): string[] {
  if (value === undefined || value.trim() === "") {
    return [];
  }
  return value
    .split(" | ")
    .map((item) => item.trim())
    .filter((item) => item !== "");
}

export async function saveCase(
  input: CaseSaveInput,
  result: DiagnosisResult
): Promise<CaseDetail> {
  if (!env.caseLogEnabled) {
    throw new AppError(
      "CASE_LOG_DISABLED",
      503,
      "Log kasus sedang dinonaktifkan (CASE_LOG_ENABLED=false)"
    );
  }

  let confirmedIndex = -1;

  if (input.confirmedDiseaseId !== null) {
    confirmedIndex = result.candidates.findIndex(
      (candidate) =>
        candidate.diseaseId === input.confirmedDiseaseId ||
        candidate.diseaseIri === toIri(input.confirmedDiseaseId as string)
    );

    if (confirmedIndex < 0) {
      throw new InvalidRequestError(
        "Penyakit terkonfirmasi bukan salah satu kandidat diagnosis",
        [
          {
            field: "confirmedDiseaseId",
            message: `Tidak ada kandidat dengan ID ${input.confirmedDiseaseId}`,
          },
        ]
      );
    }
  }

  const caseId = randomUUID();
  const createdAt = new Date().toISOString();

  await update(
    buildCaseInsert({
      caseId,
      createdAt,
      input,
      result,
      confirmedCandidateIndex: confirmedIndex >= 0 ? confirmedIndex : undefined,
    })
  );

  return getCase(caseId);
}

async function selectCases(query: string): Promise<SparqlBinding[]> {
  const response = await selectAt(
    fusekiConfig.caseQueryUrl,
    query,
    fusekiConfig.caseTimeoutMs
  );
  return response.results.bindings;
}

export async function listCases(
  filter: CaseListFilter
): Promise<CaseSummary[]> {
  const conditions = [`?case a ptp:Diagnosis`];

  if (filter.plantId !== undefined) {
    conditions.push(`?case ptp:memilikiTanaman ${escapeIri(toIri(filter.plantId))}`);
  }

  if (filter.status !== undefined) {
    conditions.push(
      `?case ptp:statusVerifikasi ${literalString(filter.status)}`
    );
  }

  const query = `${PREFIXES}
SELECT ?case ?id ?when ?status ?source ?plant ?plantLabel ?phase
       ?disease ?diseaseLabel ?note ?freeText ?symptoms ?topScore
       (COUNT(DISTINCT ?candidate) AS ?candidateCount)
WHERE {
  GRAPH <${CASE_GRAPH}> {
    ${conditions.join(" . ")} .
    ?case ptp:idKasus ?id ;
          ptp:waktuKasus ?when ;
          ptp:statusVerifikasi ?status ;
          ptp:sumberKasus ?source ;
          ptp:memilikiTanaman ?plant .
    OPTIONAL { ?case ptp:namaTanaman ?plantLabel }
    OPTIONAL { ?case ptp:faseKasus ?phase }
    OPTIONAL { ?case ptp:menghasilkanPenyakit ?disease }
    OPTIONAL { ?case ptp:namaPenyakit ?diseaseLabel }
    OPTIONAL { ?case ptp:catatanPengguna ?note }
    OPTIONAL { ?case ptp:teksGejalaBebas ?freeText }
    OPTIONAL { ?case ptp:ringkasanGejala ?symptoms }
    OPTIONAL { ?case ptp:kandidat ?candidate }
    OPTIONAL {
      ?case ptp:kandidat ?top .
      ?top ptp:peringkat ?topRank .
      FILTER(?topRank = 1)
      ?top ptp:skorKecocokan ?topScore .
    }
  }
}
GROUP BY ?case ?id ?when ?status ?source ?plant ?plantLabel ?phase
         ?disease ?diseaseLabel ?note ?freeText ?symptoms ?topScore
ORDER BY DESC(?when)
LIMIT ${filter.limit}
OFFSET ${filter.offset}`;

  const bindings = await selectCases(query);

  return bindings.map((binding) => {
    const symptomLabels = splitLabels(termValue(binding, "symptoms"));
    return {
      id: termValue(binding, "id") ?? "",
      createdAt: termValue(binding, "when") ?? "",
      plantId: localName(termValue(binding, "plant") ?? ""),
      plantLabel: termValue(binding, "plantLabel") ?? null,
      phaseId: termValue(binding, "phase")
        ? localName(termValue(binding, "phase") as string)
        : null,
      symptomCount: symptomLabels.length,
      symptomLabels,
      note: termValue(binding, "note") ?? null,
      freeTextSymptoms: termValue(binding, "freeText") ?? null,
      status: parseStatus(termValue(binding, "status")),
      source: parseSource(termValue(binding, "source")),
      topDiseaseId: termValue(binding, "disease")
        ? localName(termValue(binding, "disease") as string)
        : null,
      topDiseaseLabel: termValue(binding, "diseaseLabel") ?? null,
      topScore: numberValue(binding, "topScore"),
      candidateCount: numberValue(binding, "candidateCount") ?? 0,
    };
  });
}

async function exists(caseId: string): Promise<boolean> {
  const rows = await selectCases(`${PREFIXES}
SELECT ?case WHERE {
  GRAPH <${CASE_GRAPH}> { ${escapeIri(caseIriOf(caseId))} a ptp:Diagnosis }
}
LIMIT 1`);

  return rows.length > 0;
}

export async function getCase(caseId: string): Promise<CaseDetail> {
  const caseIri = escapeIri(caseIriOf(caseId));

  const [caseRows, symptomRows, candidateRows] = await Promise.all([
    selectCases(`${PREFIXES}
SELECT ?id ?when ?status ?source ?plant ?plantLabel ?phase
       ?disease ?diseaseLabel ?note ?freeText ?symptoms
WHERE {
  GRAPH <${CASE_GRAPH}> {
    ${caseIri} a ptp:Diagnosis ;
      ptp:idKasus ?id ;
      ptp:waktuKasus ?when ;
      ptp:statusVerifikasi ?status ;
      ptp:sumberKasus ?source ;
      ptp:memilikiTanaman ?plant .
    OPTIONAL { ${caseIri} ptp:namaTanaman ?plantLabel }
    OPTIONAL { ${caseIri} ptp:faseKasus ?phase }
    OPTIONAL { ${caseIri} ptp:menghasilkanPenyakit ?disease }
    OPTIONAL { ${caseIri} ptp:namaPenyakit ?diseaseLabel }
    OPTIONAL { ${caseIri} ptp:catatanPengguna ?note }
    OPTIONAL { ${caseIri} ptp:teksGejalaBebas ?freeText }
    OPTIONAL { ${caseIri} ptp:ringkasanGejala ?symptoms }
  }
}
LIMIT 1`),
    selectCases(`${PREFIXES}
SELECT ?symptom WHERE {
  GRAPH <${CASE_GRAPH}> { ${caseIri} ptp:memilikiObservasi ?symptom }
}`),
    selectCases(`${PREFIXES}
SELECT ?candidate ?rank ?score ?confidence ?explanation ?disease ?diseaseLabel
WHERE {
  GRAPH <${CASE_GRAPH}> {
    ${caseIri} ptp:kandidat ?candidate .
    ?candidate ptp:peringkat ?rank ;
               ptp:skorKecocokan ?score ;
               ptp:menghasilkanPenyakit ?disease .
    OPTIONAL { ?candidate ptp:tingkatKeyakinan ?confidence }
    OPTIONAL { ?candidate ptp:alasanKecocokan ?explanation }
    OPTIONAL { ?candidate ptp:namaPenyakit ?diseaseLabel }
  }
}
ORDER BY ?rank`),
  ]);

  const row = caseRows[0];

  if (row === undefined) {
    throw new NotFoundError(`Kasus tidak ditemukan: ${caseId}`);
  }

  const symptomLabels = splitLabels(termValue(row, "symptoms"));
  const candidates: CaseCandidateView[] = candidateRows.map((binding) => ({
    diseaseId: localName(termValue(binding, "disease") ?? ""),
    diseaseIri: termValue(binding, "disease") ?? "",
    diseaseLabel: termValue(binding, "diseaseLabel") ?? null,
    rank: numberValue(binding, "rank") ?? 0,
    score: numberValue(binding, "score") ?? 0,
    confidence: termValue(binding, "confidence") ?? "",
    explanation: termValue(binding, "explanation") ?? "",
  }));

  const top = candidates.find((candidate) => candidate.rank === 1) ?? null;

  return {
    id: termValue(row, "id") ?? caseId,
    createdAt: termValue(row, "when") ?? "",
    plantId: localName(termValue(row, "plant") ?? ""),
    plantLabel: termValue(row, "plantLabel") ?? null,
    phaseId: termValue(row, "phase")
      ? localName(termValue(row, "phase") as string)
      : null,
    symptomCount: symptomLabels.length,
    symptomLabels,
    symptomIds: symptomRows.map((binding) =>
      localName(termValue(binding, "symptom") ?? "")
    ),
    note: termValue(row, "note") ?? null,
    freeTextSymptoms: termValue(row, "freeText") ?? null,
    status: parseStatus(termValue(row, "status")),
    source: parseSource(termValue(row, "source")),
    topDiseaseId: top?.diseaseId ?? null,
    topDiseaseLabel: top?.diseaseLabel ?? null,
    topScore: top?.score ?? null,
    candidateCount: candidates.length,
    candidates,
  };
}

export async function verifyCase(
  caseId: string,
  diseaseId?: string
): Promise<CaseDetail> {
  if (!(await exists(caseId))) {
    throw new NotFoundError(`Kasus tidak ditemukan: ${caseId}`);
  }

  const caseIri = escapeIri(caseIriOf(caseId));

  if (diseaseId === undefined) {
    await update(`${PREFIXES}
DELETE { GRAPH <${CASE_GRAPH}> { ${caseIri} ptp:statusVerifikasi ?old } }
INSERT { GRAPH <${CASE_GRAPH}> { ${caseIri} ptp:statusVerifikasi ${literalString("terverifikasi")} } }
WHERE { GRAPH <${CASE_GRAPH}> { ${caseIri} ptp:statusVerifikasi ?old } }`);

    return getCase(caseId);
  }

  const current = await getCase(caseId);
  const candidate = current.candidates.find(
    (item) =>
      item.diseaseId === diseaseId || item.diseaseIri === toIri(diseaseId)
  );

  if (candidate === undefined) {
    throw new InvalidRequestError(
      "Penyakit verifikasi bukan salah satu kandidat kasus",
      [
        {
          field: "diseaseId",
          message: `Tidak ada kandidat dengan ID ${diseaseId}`,
        },
      ]
    );
  }

  await update(`${PREFIXES}
DELETE {
  GRAPH <${CASE_GRAPH}> {
    ${caseIri} ptp:statusVerifikasi ?oldStatus ;
              ptp:menghasilkanPenyakit ?oldDisease ;
              ptp:namaPenyakit ?oldName .
  }
}
INSERT {
  GRAPH <${CASE_GRAPH}> {
    ${caseIri} ptp:statusVerifikasi ${literalString("terverifikasi")} ;
              ptp:menghasilkanPenyakit ${escapeIri(candidate.diseaseIri)} ;
              ptp:namaPenyakit ${literalString(candidate.diseaseLabel ?? candidate.diseaseId)} .
  }
}
WHERE {
  GRAPH <${CASE_GRAPH}> {
    ${caseIri} ptp:statusVerifikasi ?oldStatus .
    OPTIONAL { ${caseIri} ptp:menghasilkanPenyakit ?oldDisease }
    OPTIONAL { ${caseIri} ptp:namaPenyakit ?oldName }
  }
}`);

  return getCase(caseId);
}

export async function deleteCase(caseId: string): Promise<void> {
  if (!(await exists(caseId))) {
    throw new NotFoundError(`Kasus tidak ditemukan: ${caseId}`);
  }

  const caseIri = escapeIri(caseIriOf(caseId));

  await update(`${PREFIXES}
DELETE {
  GRAPH <${CASE_GRAPH}> {
    ${caseIri} ?p ?o .
    ?candidate ?cp ?co .
  }
}
WHERE {
  GRAPH <${CASE_GRAPH}> {
    ${caseIri} ?p ?o .
    OPTIONAL {
      ${caseIri} ptp:kandidat ?candidate .
      ?candidate ?cp ?co .
    }
  }
}`);
}

export async function caseStats(): Promise<CaseStats> {
  const [totalRows, verifiedRows, plantRows, diseaseRows] = await Promise.all([
    selectCases(`${PREFIXES}
SELECT (COUNT(*) AS ?n) WHERE { GRAPH <${CASE_GRAPH}> { ?case a ptp:Diagnosis } }`),
    selectCases(`${PREFIXES}
SELECT (COUNT(*) AS ?n) WHERE {
  GRAPH <${CASE_GRAPH}> {
    ?case a ptp:Diagnosis ;
          ptp:statusVerifikasi ${literalString("terverifikasi")} .
  }
}`),
    selectCases(`${PREFIXES}
SELECT ?plant ?label (COUNT(*) AS ?n) WHERE {
  GRAPH <${CASE_GRAPH}> {
    ?case a ptp:Diagnosis ;
          ptp:memilikiTanaman ?plant .
    OPTIONAL { ?case ptp:namaTanaman ?label }
  }
}
GROUP BY ?plant ?label
ORDER BY DESC(?n)`),
    selectCases(`${PREFIXES}
SELECT ?disease ?label (COUNT(*) AS ?n) WHERE {
  GRAPH <${CASE_GRAPH}> {
    ?case a ptp:Diagnosis ;
          ptp:menghasilkanPenyakit ?disease .
    OPTIONAL { ?case ptp:namaPenyakit ?label }
  }
}
GROUP BY ?disease ?label
ORDER BY DESC(?n)`),
  ]);

  const total = numberValue(totalRows[0] ?? {}, "n") ?? 0;
  const verified = numberValue(verifiedRows[0] ?? {}, "n") ?? 0;

  return {
    total,
    verified,
    unverified: Math.max(0, total - verified),
    byPlant: plantRows.map((binding) => ({
      plantId: localName(termValue(binding, "plant") ?? ""),
      label: termValue(binding, "label") ?? null,
      count: numberValue(binding, "n") ?? 0,
    })),
    byDisease: diseaseRows.map((binding) => ({
      diseaseId: localName(termValue(binding, "disease") ?? ""),
      label: termValue(binding, "label") ?? null,
      count: numberValue(binding, "n") ?? 0,
    })),
  };
}

export async function healthCases(): Promise<{
  status: "UP" | "DOWN";
  totalKasus: number;
  terverifikasi: number;
  detail: string | null;
}> {
  try {
    const stats = await caseStats();
    return {
      status: "UP",
      totalKasus: stats.total,
      terverifikasi: stats.verified,
      detail: null,
    };
  } catch (error) {
    return {
      status: "DOWN",
      totalKasus: 0,
      terverifikasi: 0,
      detail: error instanceof Error ? error.message : String(error),
    };
  }
}

/**
 * CBR: cari kasus terverifikasi dengan gejala yang beririsan.
 * Hanya membaca; tidak pernah mengubah skor diagnosis.
 */
export async function findSimilarCases(
  plantIri: string,
  symptomIris: string[]
): Promise<Map<string, SimilarCaseInfo>> {
  const result = new Map<string, SimilarCaseInfo>();

  if (!env.caseLogEnabled || symptomIris.length === 0) {
    return result;
  }

  const symptomList = symptomIris.map((iri) => escapeIri(iri)).join(", ");
  const statusFilter = env.cbrIncludeUnverified
    ? ""
    : `ptp:statusVerifikasi ${literalString("terverifikasi")} ; `;

  const rows = await selectCases(`${PREFIXES}
SELECT ?case ?disease (COUNT(DISTINCT ?symptom) AS ?overlap)
       (MAX(?when) AS ?when)
WHERE {
  GRAPH <${CASE_GRAPH}> {
    ?case a ptp:Diagnosis ;
          ptp:memilikiTanaman ${escapeIri(plantIri)} ;
          ptp:sumberKasus ${literalString("pengguna")} ;
          ${statusFilter}ptp:menghasilkanPenyakit ?disease ;
          ptp:waktuKasus ?when ;
          ptp:memilikiObservasi ?symptom .
    FILTER(?symptom IN (${symptomList}))
  }
}
GROUP BY ?case ?disease`);

  for (const binding of rows) {
    const diseaseIri = termValue(binding, "disease");
    if (diseaseIri === undefined) {
      continue;
    }

    const overlap = numberValue(binding, "overlap") ?? 0;
    if (overlap < env.cbrMinOverlap) {
      continue;
    }

    const when = termValue(binding, "when") ?? null;
    const current = result.get(diseaseIri) ?? {
      count: 0,
      maxOverlap: 0,
      lastSeen: null,
    };

    current.count += 1;
    current.maxOverlap = Math.max(current.maxOverlap, overlap);
    if (
      when !== null &&
      (current.lastSeen === null || when > current.lastSeen)
    ) {
      current.lastSeen = when;
    }

    result.set(diseaseIri, current);
  }

  return result;
}
