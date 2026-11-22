import test from "node:test";
import assert from "node:assert/strict";

import {
  matchSymptoms,
  tokenize,
  type MatchableSymptom,
} from "../src/lib/symptom-match.js";

const symptoms: MatchableSymptom[] = [
  {
    id: "Klorosis",
    label: "Klorosis daun pada Penyakit Blas",
    description: "Daun menguning dan pucat.",
  },
  {
    id: "Bercak",
    label: "Bercak daun pada Penyakit Blas",
    description: "Bercak coklat pada daun.",
  },
  {
    id: "Layu",
    label: "Layu daun pada Penyakit Layu Stewart",
    description: null,
  },
];

test("tokenize membuang stopword dan tanda baca", () => {
  assert.deepEqual(tokenize("Daun menguning, ada bercak pada daun!"), [
    "daun",
    "menguning",
    "bercak",
    "daun",
  ]);
});

test("matchSymptoms memetakan 'daun menguning' ke klorosis", () => {
  const result = matchSymptoms(symptoms, "daun menguning", {
    limit: 5,
    minScore: 0.3,
  });

  assert.ok(result.suggestions.length >= 1);
  assert.equal(result.suggestions[0]?.id, "Klorosis");
});

test("matchSymptoms memetakan 'bercak coklat pada daun' ke bercak", () => {
  const result = matchSymptoms(symptoms, "bercak coklat pada daun", {
    limit: 5,
    minScore: 0.3,
  });

  assert.ok(result.suggestions.length >= 1);
  assert.equal(result.suggestions[0]?.id, "Bercak");
});

test("matchSymptoms mengembalikan kosong untuk teks kosong", () => {
  const result = matchSymptoms(symptoms, "   ", { limit: 5, minScore: 0.3 });
  assert.deepEqual(result.suggestions, []);
  assert.deepEqual(result.unmatchedTerms, []);
});

test("matchSymptoms membuang skor di bawah threshold", () => {
  const result = matchSymptoms(symptoms, "bercak coklat pada daun", {
    limit: 5,
    minScore: 0.95,
  });

  assert.deepEqual(result.suggestions, []);
});

test("matchSymptoms menandai kata yang tidak dikenali", () => {
  const result = matchSymptoms(symptoms, "ulat bulu", {
    limit: 5,
    minScore: 0.3,
  });

  assert.ok(result.unmatchedTerms.includes("ulat"));
});
