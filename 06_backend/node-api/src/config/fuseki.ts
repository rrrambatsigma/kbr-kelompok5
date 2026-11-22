import { env } from "./env.js";
import { PTP_NAMESPACE } from "./ontology.js";

const baseUrl = env.fusekiBaseUrl;
const dataset = encodeURIComponent(env.fusekiDataset);
const caseDataset = encodeURIComponent(env.fusekiCaseDataset);

export const fusekiConfig = {
  baseUrl,
  dataset: env.fusekiDataset,
  queryUrl: `${baseUrl}/${dataset}/query`,

  caseDataset: env.fusekiCaseDataset,
  caseQueryUrl: `${baseUrl}/${caseDataset}/query`,
  caseUpdateUrl: `${baseUrl}/${caseDataset}/update`,

  timeoutMs: env.fusekiTimeoutMs,
  caseTimeoutMs: env.cbrTimeoutMs,
} as const;

export const ptpNamespace = PTP_NAMESPACE;

/** Nama graf tempat kasus pengguna disimpan. */
export const CASE_GRAPH = "urn:kbr:kasus";
