import type { Confidence } from "../types/api";

export function scorePercent(score: number): number {
  return Math.max(0, Math.min(100, Math.round(score * 100)));
}

export function confidenceLabel(confidence: Confidence): string {
  switch (confidence) {
    case "TINGGI":
      return "Keyakinan tinggi";
    case "SEDANG":
      return "Keyakinan sedang";
    default:
      return "Keyakinan rendah";
  }
}

export function confidenceTone(
  confidence: Confidence
): "success" | "warning" | "danger" {
  switch (confidence) {
    case "TINGGI":
      return "success";
    case "SEDANG":
      return "warning";
    default:
      return "danger";
  }
}

const CATEGORY_LABELS: Record<string, string> = {
  PenyakitJamur: "Jamur",
  PenyakitBakteri: "Bakteri",
  PenyakitVirus: "Virus",
  PenyakitOomycete: "Oomycete",
  PenyakitFitoplasma: "Fitoplasma",
  PenyakitNematoda: "Nematoda",
  PenyakitLainnya: "Lainnya",
};

export function categoryLabel(category: string | null): string {
  if (category === null) {
    return "Belum terklasifikasi";
  }
  return CATEGORY_LABELS[category] ?? category;
}

export function pluralize(
  count: number,
  singular: string,
  plural: string
): string {
  return `${count} ${count === 1 ? singular : plural}`;
}

/**
 * Membersihkan artefak penulisan label faktor risiko dari sumber/ontology.
 * Hanya untuk tampilan; data asli tidak diubah.
 */
export function formatRiskFactorLabel(label: string): string {
  return label
    .replace(/Koma/gi, ",")
    .replace(/Sampai/gi, " sampai ")
    .replace(/\uFFFD\s*C/g, "°C")
    .replace(/Celsius/gi, "°C")
    .replace(/Persen/gi, "%")
    .replace(/\s+/g, " ")
    .replace(/\s+([,.;])/g, "$1")
    .trim();
}

export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("id-ID", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}
