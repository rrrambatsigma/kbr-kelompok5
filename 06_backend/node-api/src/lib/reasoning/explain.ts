import type { ReasoningCandidate } from "./types.js";

function formatConcepts(labels: readonly string[]): string {
  if (labels.length === 0) {
    return "konsep kanonik";
  }

  const [first, second] = labels;

  if (labels.length === 1) {
    return first!;
  }
  if (labels.length === 2) {
    return `${first!} dan ${second!}`;
  }

  return `${first!}, ${second!}, dan ${labels.length - 2} konsep lainnya`;
}

/**
 * Narasi alasan yang bisa dibaca manusia. Tidak mengklaim diagnosis pasti;
 * hanya menjelaskan bukti yang dipakai kandidat.
 */
export function explainCandidate(candidate: ReasoningCandidate): string {
  const exactCount = candidate.evidence.filter(
    (item) => item.type === "exact"
  ).length;
  const canonicalCount = candidate.evidence.filter(
    (item) => item.type === "canonical"
  ).length;
  const unexplainedCount = candidate.unexplainedSymptoms.length;

  if (candidate.evidence.length === 0) {
    return "Belum ada bukti gejala yang cocok untuk kandidat ini.";
  }

  const labels = [
    ...new Set(
      candidate.evidence.flatMap((item) =>
        item.type === "canonical" && item.canonicalSymptomLabel !== null
          ? [item.canonicalSymptomLabel]
          : []
      )
    ),
  ];

  const parts: string[] = [];

  if (exactCount > 0) {
    parts.push(`${exactCount} gejala cocok persis`);
  }
  if (canonicalCount > 0) {
    parts.push(
      `${canonicalCount} gejala cocok pada konsep ${formatConcepts(labels)}`
    );
  }

  let text = `${parts.join(" dan ")}.`;

  if (unexplainedCount > 0) {
    text += ` ${unexplainedCount} gejala belum dijelaskan kandidat ini.`;
  } else {
    text += " Kandidat ini menjelaskan seluruh gejala yang dipilih.";
  }

  return text;
}
