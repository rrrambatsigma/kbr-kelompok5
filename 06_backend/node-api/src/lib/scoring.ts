export interface CandidateScore {
  matchedCount: number;
  selectedCount: number;
  totalSymptoms: number;
  matchRatio: number;
  coverage: number;
  score: number;
}

function round4(value: number): number {
  return Math.round(value * 10_000) / 10_000;
}

/**
 * Scoring model ported from the previous backend:
 *
 *   matchRatio = matchedSelected / selectedSymptoms
 *   coverage   = matchedSelected / diseaseSymptoms
 *   score      = 0.7 * matchRatio + 0.3 * coverage
 *
 * matchRatio rewards diseases that explain more of the selected symptoms.
 * coverage penalises very broad diseases that contain every symptom.
 */
export function scoreCandidate(
  selectedSymptomIds: readonly string[],
  diseaseSymptomIds: readonly string[]
): CandidateScore {
  const selected = new Set(selectedSymptomIds);
  const diseaseSymptoms = new Set(diseaseSymptomIds);

  let matchedCount = 0;
  for (const id of selected) {
    if (diseaseSymptoms.has(id)) {
      matchedCount++;
    }
  }

  const selectedCount = selected.size;
  const totalSymptoms = diseaseSymptoms.size;

  const matchRatio =
    selectedCount === 0 ? 0 : matchedCount / selectedCount;
  const coverage =
    totalSymptoms === 0 ? 0 : matchedCount / totalSymptoms;
  const score = 0.7 * matchRatio + 0.3 * coverage;

  return {
    matchedCount,
    selectedCount,
    totalSymptoms,
    matchRatio: round4(matchRatio),
    coverage: round4(coverage),
    score: round4(score),
  };
}

export interface RankableCandidate {
  score: number;
  matchedCount: number;
  label: string;
}

export function compareCandidates(
  left: RankableCandidate,
  right: RankableCandidate
): number {
  if (right.score !== left.score) {
    return right.score - left.score;
  }
  if (right.matchedCount !== left.matchedCount) {
    return right.matchedCount - left.matchedCount;
  }
  return left.label.localeCompare(right.label, "id");
}
