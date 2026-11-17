import { REASONING_CONFIG } from "./config.js";
import type { Confidence } from "./types.js";

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

export function round4(value: number): number {
  return Math.round(value * 10_000) / 10_000;
}

/**
 * Menggabungkan bukti positif ala MYCIN:
 *
 *   CF = CF + w * (1 - CF)
 *
 * Ekuivalen dengan noisy-OR: 1 - produk(1 - w). Urutan bukti tidak
 * memengaruhi hasil.
 */
export function combineEvidence(weights: readonly number[]): number {
  let cf = 0;

  for (const weight of weights) {
    const w = clamp(weight, 0, 1);
    cf = cf + w * (1 - cf);
  }

  return clamp(cf, 0, 1);
}

/**
 * Skor akhir = kekuatan bukti x kelengkapan penjelasan x cakupan penyakit.
 * Kedua faktor penalti tidak pernah nol, supaya kandidat yang punya bukti
 * tetap muncul dengan skor kecil.
 */
export function scoreCandidate(
  evidence: number,
  completeness: number,
  coverage: number
): number {
  const cf = clamp(evidence, 0, 1);
  const complete = clamp(completeness, 0, 1);
  const cover = clamp(coverage, 0, 1);

  const score =
    cf *
    (REASONING_CONFIG.completenessFloor +
      (1 - REASONING_CONFIG.completenessFloor) * complete) *
    (REASONING_CONFIG.coverageFloor +
      (1 - REASONING_CONFIG.coverageFloor) * cover);

  return round4(score);
}

/**
 * Satu bukti saja selalu RENDAH. Ini disengaja: sistem tidak boleh terlalu
 * percaya diri hanya dari satu gejala.
 */
export function classifyConfidence(
  score: number,
  evidenceCount: number
): Confidence {
  if (
    score >= REASONING_CONFIG.highScoreThreshold &&
    evidenceCount >= REASONING_CONFIG.minEvidenceForConfidence
  ) {
    return "TINGGI";
  }

  if (
    score >= REASONING_CONFIG.mediumScoreThreshold &&
    evidenceCount >= REASONING_CONFIG.minEvidenceForConfidence
  ) {
    return "SEDANG";
  }

  return "RENDAH";
}
