import test from "node:test";
import assert from "node:assert/strict";

import { compareCandidates, scoreCandidate } from "../src/lib/scoring.js";
import { parseDiagnosisInput } from "../src/services/diagnosis.service.js";
import { InvalidRequestError } from "../src/lib/errors.js";
import {
  localName,
  requireIntegerTerm,
} from "../src/services/fuseki.service.js";
import { toIri } from "../src/services/knowledge.service.js";

test("scoreCandidate: exact match scores 1", () => {
  const result = scoreCandidate(["a", "b"], ["a", "b"]);
  assert.equal(result.matchedCount, 2);
  assert.equal(result.matchRatio, 1);
  assert.equal(result.coverage, 1);
  assert.equal(result.score, 1);
});

test("scoreCandidate: all selected symptoms explained, narrow disease is penalised by coverage", () => {
  const result = scoreCandidate(["a", "b"], ["a", "b", "c", "d"]);
  assert.equal(result.score, 0.85);
});

test("scoreCandidate: partial match combines matchRatio and coverage", () => {
  const result = scoreCandidate(["a", "x"], ["a", "b"]);
  assert.equal(result.matchedCount, 1);
  assert.equal(result.matchRatio, 0.5);
  assert.equal(result.coverage, 0.5);
  assert.equal(result.score, 0.5);
});

test("scoreCandidate: empty selection does not divide by zero", () => {
  const result = scoreCandidate([], ["a"]);
  assert.equal(result.score, 0);
  assert.equal(result.matchRatio, 0);
});

test("compareCandidates orders by score, matched count, then label", () => {
  const ordered = [
    { score: 0.5, matchedCount: 1, label: "B" },
    { score: 0.9, matchedCount: 1, label: "C" },
    { score: 0.9, matchedCount: 2, label: "A" },
    { score: 0.5, matchedCount: 1, label: "A" },
  ].sort(compareCandidates);

  assert.deepEqual(
    ordered.map((item) => item.label),
    ["A", "C", "A", "B"]
  );
});

test("parseDiagnosisInput applies defaults and trims values", () => {
  const parsed = parseDiagnosisInput({
    plantId: " Padi ",
    symptomIds: [" GejalaA ", "GejalaB"],
  });

  assert.equal(parsed.plantId, "Padi");
  assert.equal(parsed.phaseId, null);
  assert.deepEqual(parsed.symptomIds, ["GejalaA", "GejalaB"]);
  assert.equal(parsed.topN, 5);
});

test("parseDiagnosisInput accepts and trims phaseId", () => {
  const parsed = parseDiagnosisInput({
    plantId: "Padi",
    phaseId: " FaseAnakanTanaman ",
    symptomIds: ["GejalaA"],
  });

  assert.equal(parsed.phaseId, "FaseAnakanTanaman");
});

test("parseDiagnosisInput rejects empty phaseId", () => {
  assert.throws(
    () =>
      parseDiagnosisInput({
        plantId: "Padi",
        phaseId: "  ",
        symptomIds: ["GejalaA"],
      }),
    InvalidRequestError
  );
});

test("parseDiagnosisInput rejects empty symptom list", () => {
  assert.throws(
    () => parseDiagnosisInput({ plantId: "Padi", symptomIds: [] }),
    (error: unknown) =>
      error instanceof InvalidRequestError &&
      error.code === "INVALID_REQUEST" &&
      (error.details?.length ?? 0) > 0
  );
});

test("parseDiagnosisInput rejects topN outside 1-10", () => {
  assert.throws(
    () =>
      parseDiagnosisInput({
        plantId: "Padi",
        symptomIds: ["GejalaA"],
        topN: 50,
      }),
    InvalidRequestError
  );
});

test("localName and toIri handle local names and reject unsafe input", () => {
  const iri = toIri("Padi");
  assert.equal(localName(iri), "Padi");
  assert.ok(iri.startsWith("http://kbr.kelompok5.org/"));
  assert.throws(() => toIri("Padi masuk> ; DROP"), InvalidRequestError);
});

test("requireIntegerTerm rejects non-numeric Fuseki bindings", () => {
  assert.equal(
    requireIntegerTerm({ total: { type: "literal", value: "42" } }, "total"),
    42
  );

  assert.throws(
    () =>
      requireIntegerTerm(
        { total: { type: "literal", value: "bukan-angka" } },
        "total"
      ),
    /integer/
  );
});
