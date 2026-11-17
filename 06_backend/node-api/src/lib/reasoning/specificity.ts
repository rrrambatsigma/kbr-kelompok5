import { REASONING_CONFIG } from "./config.js";

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

/**
 * Specificitas gejala berdasarkan seberapa banyak penyakit yang memakainya.
 *
 *   df = 1  -> 1.0  (gejala khas)
 *   df = N  -> 0.5  (gejala umum)
 *
 * Memakai konsep kanonik (bila ada), bukan ID pengamatan, karena pengamatan
 * di ontology ini spesifik per penyakit.
 */
export function specificity(df: number, diseaseCount: number): number {
  if (diseaseCount <= 1 || df <= 1) {
    return 1;
  }

  const safeDiseaseCount = Math.max(1, diseaseCount);
  const safeDf = Math.min(safeDiseaseCount, Math.max(1, df));
  const ratio =
    Math.log((safeDiseaseCount + 1) / (safeDf + 1)) /
    Math.log(safeDiseaseCount + 1);

  return clamp(
    REASONING_CONFIG.specificityFloor +
      (1 - REASONING_CONFIG.specificityFloor) * ratio,
    REASONING_CONFIG.specificityFloor,
    1
  );
}

/** Bobot satu bukti = bobot dasar (exact/kanonik) x specificitas. */
export function evidenceWeight(baseWeight: number, spec: number): number {
  return Math.min(
    REASONING_CONFIG.maxEvidenceWeight,
    clamp(baseWeight, 0, 1) * clamp(spec, 0, 1)
  );
}
