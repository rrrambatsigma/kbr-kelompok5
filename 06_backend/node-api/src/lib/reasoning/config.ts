/**
 * Parameter model reasoning.
 *
 * Nilai ini adalah titik awal dan akan dikalibrasi pada Langkah 4. Jangan
 * menganggapnya final; semua angka yang memengaruhi skor dikumpulkan di sini
 * agar mudah diuji dan diubah.
 */
export const REASONING_CONFIG = {
  /** Batas atas bobot satu bukti agar CF tidak langsung mentok. */
  maxEvidenceWeight: 0.9,

  /** Specificitas minimum untuk gejala yang muncul di semua penyakit. */
  specificityFloor: 0.5,

  /** Bobot bukti kanonik relatif terhadap exact match. */
  canonicalWeight: 0.6,

  /** Faktor minimum untuk completeness pada skor akhir. */
  completenessFloor: 0.7,

  /** Faktor minimum untuk coverage pada skor akhir. */
  coverageFloor: 0.5,

  /**
   * Penyebut minimum untuk coverage. Penyakit dengan sangat sedikit gejala
   * tercatat (kb. 1-2) tidak boleh mendapat coverage 1.0 hanya karena datanya
   * miskin; ini penalti kelengkapan data, bukan biologi.
   */
  minCoverageDenominator: 4,

  /** Ambang skor untuk keyakinan tinggi. */
  highScoreThreshold: 0.7,

  /** Ambang skor untuk keyakinan sedang. */
  mediumScoreThreshold: 0.4,

  /** Jumlah bukti minimum untuk boleh berlabel SEDANG/TINGGI. */
  minEvidenceForConfidence: 2,

  /**
   * Faktor ranking lembut saat fase pertumbuhan yang dipilih cocok dengan
   * `menyerangFase` milik penyakit. Fase bukan bukti gejala, jadi faktornya
   * kecil dan tidak pernah menghukum kandidat yang tidak punya data fase.
   */
  phaseMatchFactor: 1.05,
} as const;
