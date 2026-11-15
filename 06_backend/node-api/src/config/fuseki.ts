import { env } from "./env.js";

const baseUrl = env.fusekiBaseUrl;
const dataset = encodeURIComponent(env.fusekiDataset);

export const fusekiConfig = {
  baseUrl,
  dataset: env.fusekiDataset,
  queryUrl: `${baseUrl}/${dataset}/query`,
  timeoutMs: env.fusekiTimeoutMs,
} as const;

export const ptpNamespace =
  "http://kbr.kelompok5.org/penyakit-tanaman-pangan#";
