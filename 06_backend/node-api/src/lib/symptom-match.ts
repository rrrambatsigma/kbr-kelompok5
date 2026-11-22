import { SYMPTOM_SYNONYMS } from "../data/symptom-synonyms.js";

/**
 * Pencocokan kata kunci gejala — bukan pemahaman bahasa.
 *
 * Hasilnya hanya saran ID gejala; pengguna tetap harus memilih ID yang benar.
 */

export interface MatchableSymptom {
  id: string;
  label: string;
  description?: string | null;
}

export interface SymptomSuggestion {
  id: string;
  label: string;
  score: number;
  matchedTerms: string[];
}

export interface SymptomMatchResult {
  suggestions: SymptomSuggestion[];
  unmatchedTerms: string[];
}

export interface SymptomMatchOptions {
  limit: number;
  minScore: number;
  synonyms?: Record<string, string[]>;
}

const STOPWORDS = new Set([
  "yang",
  "ada",
  "pada",
  "dan",
  "di",
  "dengan",
  "terlihat",
  "sedikit",
  "agak",
  "juga",
  "atau",
  "dari",
  "ke",
  "ini",
  "itu",
  "saya",
  "kami",
  "nya",
  "tanaman",
  "penyakit",
]);

const LABEL_WEIGHT = 1;
const DESCRIPTION_WEIGHT = 0.7;

export function normalizeText(text: string): string {
  return text
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function tokenize(text: string): string[] {
  return normalizeText(text)
    .split(" ")
    .filter((token) => token.length >= 3 && !STOPWORDS.has(token));
}

export function matchSymptoms(
  symptoms: MatchableSymptom[],
  text: string,
  options: SymptomMatchOptions
): SymptomMatchResult {
  const queryTokens = tokenize(text);

  if (queryTokens.length === 0) {
    return { suggestions: [], unmatchedTerms: [] };
  }

  const synonyms = options.synonyms ?? SYMPTOM_SYNONYMS;
  const suggestions: SymptomSuggestion[] = [];

  for (const symptom of symptoms) {
    const labelTokens = new Set(tokenize(symptom.label));
    const descriptionTokens = new Set(tokenize(symptom.description ?? ""));

    let weight = 0;
    const matchedTerms: string[] = [];

    for (const token of queryTokens) {
      const variants = [token, ...(synonyms[token] ?? [])];
      const labelHit = variants.find((variant) => labelTokens.has(variant));

      if (labelHit !== undefined) {
        weight += LABEL_WEIGHT;
        matchedTerms.push(labelHit);
        continue;
      }

      const descriptionHit = variants.find((variant) =>
        descriptionTokens.has(variant)
      );

      if (descriptionHit !== undefined) {
        weight += DESCRIPTION_WEIGHT;
        matchedTerms.push(descriptionHit);
      }
    }

    if (matchedTerms.length === 0) {
      continue;
    }

    const score = Math.round((weight / queryTokens.length) * 1000) / 1000;

    if (score < options.minScore) {
      continue;
    }

    suggestions.push({
      id: symptom.id,
      label: symptom.label,
      score,
      matchedTerms,
    });
  }

  suggestions.sort(
    (left, right) =>
      right.score - left.score || left.label.localeCompare(right.label, "id")
  );

  const topSuggestions = suggestions.slice(0, options.limit);
  const matchedVocabulary = new Set(
    topSuggestions.flatMap((suggestion) => suggestion.matchedTerms)
  );

  const unmatchedTerms = queryTokens.filter((token) => {
    const variants = [token, ...(synonyms[token] ?? [])];
    return !variants.some((variant) => matchedVocabulary.has(variant));
  });

  return { suggestions: topSuggestions, unmatchedTerms };
}
