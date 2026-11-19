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
