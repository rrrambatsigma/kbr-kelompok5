import { env } from "./env.js";
import { PTP_NAMESPACE } from "./ontology.js";

const baseUrl = env.fusekiBaseUrl;
const dataset = encodeURIComponent(env.fusekiDataset);

export const fusekiConfig = {
  baseUrl,
  dataset: env.fusekiDataset,
  queryUrl: `${baseUrl}/${dataset}/query`,
  timeoutMs: env.fusekiTimeoutMs,
} as const;

export const ptpNamespace = PTP_NAMESPACE;
