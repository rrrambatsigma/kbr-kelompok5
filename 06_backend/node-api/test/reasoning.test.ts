import assert from "node:assert/strict";
import test from "node:test";

import {
  classifyConfidence,
  combineEvidence,
  scoreCandidate,
} from "../src/lib/reasoning/certainty.js";
import { reason } from "../src/lib/reasoning/engine.js";
import { explainCandidate } from "../src/lib/reasoning/explain.js";
import { prepareDataset } from "../src/lib/reasoning/rules.js";
import {
  evidenceWeight,
  specificity,
} from "../src/lib/reasoning/specificity.js";
import type {
  DiagnosisDataset,
  DiagnosisDisease,
  DiagnosisSymptom,
} from "../src/services/knowledge.service.js";

function symptom(id: string, canonicalId?: string): DiagnosisSymptom {
  return {
    id,
    iri: `http://test.local/${id}`,
    label: id,
    canonical:
      canonicalId === undefined
        ? null
        : {
            id: canonicalId,
            iri: `http://test.local/${canonicalId}`,
            label: canonicalId,
          },
  };
}

function disease(
  id: string,
  symptoms: DiagnosisSymptom[],
  phases: DiagnosisDisease["phases"] = []
): DiagnosisDisease {
  return {
    id,
    iri: `http://test.local/${id}`,
    label: id,
    symptoms,
    riskFactors: [],
    phases,
    description: null,
    severity: null,
  };
}

function phase(id: string): DiagnosisDisease["phases"][number] {
  return {
    id,
    iri: `http://test.local/${id}`,
    label: id,
  };
}

function dataset(diseases: DiagnosisDisease[]): DiagnosisDataset {
  const observations = new Set(
    diseases.flatMap((item) => item.symptoms.map((entry) => entry.iri))
  );
  const canonicalObservations = new Set(
    diseases.flatMap((item) =>
      item.symptoms
        .filter((entry) => entry.canonical !== null)
        .map((entry) => entry.iri)
    )
  );
  const concepts = new Set(
    diseases.flatMap((item) =>
      item.symptoms.flatMap((entry) =>
        entry.canonical === null ? [] : [entry.canonical.iri]
      )
    )
  );

  return {
    plant: {
      id: "TanamanUji",
      iri: "http://test.local/TanamanUji",
      label: "Tanaman Uji",
      scientificName: null,
      diseaseCount: diseases.length,
    },
    diseases,
    stats: {
      diseaseCount: diseases.length,
      diseaseWithSymptomsCount: diseases.filter(
        (item) => item.symptoms.length > 0
      ).length,
      symptomObservationCount: observations.size,
      canonicalObservationCount: canonicalObservations.size,
      canonicalConceptCount: concepts.size,
    },
  };
}

test("specificity: gejala khas lebih tinggi dari gejala umum", () => {
  assert.equal(specificity(1, 5), 1);
  assert.equal(specificity(5, 5), 0.5);
  assert.ok(specificity(4, 5) > 0.5);
  assert.ok(specificity(4, 5) < 1);
});

test("evidenceWeight: bobot dibatasi maxEvidenceWeight", () => {
  assert.equal(evidenceWeight(1, 1), 0.9);
  assert.equal(evidenceWeight(0.6, 1), 0.6);
});

test("certainty: CF gabungan dan confidence", () => {
  assert.equal(combineEvidence([]), 0);
  assert.equal(combineEvidence([0.5, 0.5]), 0.75);
  assert.equal(scoreCandidate(1, 1, 1), 1);
  assert.equal(classifyConfidence(0.9, 1), "RENDAH");
  assert.equal(classifyConfidence(0.9, 2), "TINGGI");
  assert.equal(classifyConfidence(0.5, 2), "SEDANG");
});

test("engine: exact mengalahkan kanonik", () => {
  const d1 = disease("D1", [symptom("s1", "c1"), symptom("s1b")]);
  const d2 = disease("D2", [symptom("s2", "c1")]);
  const result = reason(dataset([d1, d2]), ["s1"]);

  const top = result.candidates[0]!;
  const second = result.candidates.find((item) => item.disease.id === "D2")!;

  assert.equal(top.disease.id, "D1");
  assert.equal(top.evidence[0]!.type, "exact");
  assert.equal(second.evidence[0]!.type, "canonical");
  assert.ok(top.score > second.score);
});

test("engine: gejala umum berbobot lebih rendah dari gejala khas", () => {
  const d1 = disease("D1", [symptom("s1", "c1"), symptom("s1b")]);
  const d2 = disease("D2", [symptom("s2", "c1")]);
  const d3 = disease("D3", [symptom("s3")]);
  const result = reason(dataset([d1, d2, d3]), ["s1", "s3"]);

  const common = result.candidates.find((item) => item.disease.id === "D1")!
    .evidence[0]!;
  const unique = result.candidates.find((item) => item.disease.id === "D3")!
    .evidence[0]!;

  assert.ok(unique.weight > common.weight);
});

test("engine: dua ID berbeda dengan kanonik sama bisa cocok", () => {
  const d1 = disease("D1", [symptom("s1", "c1")]);
  const d2 = disease("D2", [symptom("s2", "c1")]);
  const result = reason(dataset([d1, d2]), ["s2"]);

  const candidate = result.candidates.find((item) => item.disease.id === "D1")!;
  const evidence = candidate.evidence[0]!;

  assert.equal(evidence.type, "canonical");
  assert.equal(evidence.matchedObservationId, "s1");
  assert.equal(evidence.canonicalSymptomId, "c1");
  assert.equal(evidence.canonicalSymptomLabel, "c1");
});

test("engine: satu observasi penyakit tidak dihitung dua kali", () => {
  const d1 = disease("D1", [symptom("s1", "c1")]);
  const d2 = disease("D2", [symptom("s2", "c1")]);
  const d3 = disease("D3", [symptom("s3", "c1")]);
  const result = reason(dataset([d1, d2, d3]), ["s2", "s3"]);

  const candidate = result.candidates.find((item) => item.disease.id === "D1")!;

  assert.equal(candidate.evidence.length, 1);
  assert.equal(candidate.unexplainedSymptoms.length, 1);
});

test("engine: completeness dan coverage memengaruhi skor", () => {
  const narrow = disease("Narrow", [symptom("s1")]);
  const partial = disease("Partial", [symptom("s2"), symptom("s3")]);
  const broad = disease("Broad", [
    symptom("s4"),
    symptom("s5"),
    symptom("s6"),
    symptom("s7"),
    symptom("s8"),
  ]);

  const distractor = disease("Distractor", [symptom("s9")]);
  const partialResult = reason(
    dataset([partial, distractor]),
    ["s2", "s9"],
    { topN: 5 }
  );
  const partialCandidate = partialResult.candidates.find(
    (item) => item.disease.id === "Partial"
  )!;
  const fullResult = reason(dataset([partial]), ["s2", "s3"], { topN: 5 });

  assert.equal(partialCandidate.scoreComponents.completeness, 0.5);
  assert.equal(fullResult.candidates[0]!.scoreComponents.completeness, 1);

  const narrowResult = reason(dataset([narrow]), ["s1"], { topN: 5 });
  const broadResult = reason(dataset([broad]), ["s4"], { topN: 5 });

  assert.equal(narrowResult.candidates[0]!.scoreComponents.coverage, 0.25);
  assert.equal(broadResult.candidates[0]!.scoreComponents.coverage, 0.2);
  assert.ok(
    narrowResult.candidates[0]!.score > broadResult.candidates[0]!.score
  );
});

test("engine: satu bukti selalu RENDAH", () => {
  const d1 = disease("D1", [symptom("s1")]);
  const single = reason(dataset([d1]), ["s1"]);
  assert.equal(single.candidates[0]!.confidence, "RENDAH");

  const d2 = disease("D2", [symptom("s1"), symptom("s2")]);
  const two = reason(dataset([d2]), ["s1", "s2"]);
  assert.equal(two.candidates[0]!.confidence, "TINGGI");
});

test("engine: topN, totalMatched, dan urutan deterministik", () => {
  const d1 = disease("Alpha", [symptom("s1")]);
  const d2 = disease("Beta", [symptom("s2")]);
  const data = dataset([d1, d2]);

  const first = reason(data, ["s1", "s2"], { topN: 1 });
  const second = reason(data, ["s1", "s2"], { topN: 1 });

  assert.equal(first.candidates.length, 1);
  assert.equal(first.totalMatched, 2);
  assert.equal(first.candidates[0]!.disease.id, second.candidates[0]!.disease.id);
});

test("engine: ID tak dikenal diabaikan dengan warning", () => {
  const d1 = disease("D1", [symptom("s1")]);
  const result = reason(dataset([d1]), ["tidak-ada"]);

  assert.equal(result.candidates.length, 0);
  assert.ok(result.warnings.includes("UNKNOWN_SYMPTOM_IGNORED:tidak-ada"));
  assert.ok(result.warnings.includes("NO_SELECTED_SYMPTOMS"));
});

test("engine: tanpa data kanonik tetap berjalan dengan warning", () => {
  const d1 = disease("D1", [symptom("s1")]);
  const result = reason(dataset([d1]), ["s1"]);

  assert.ok(result.warnings.includes("CANONICAL_MATCHING_DISABLED"));
  assert.equal(result.candidates[0]!.evidence[0]!.type, "exact");
});

test("engine: dataset kosong tidak error", () => {
  const result = reason(dataset([]), ["s1"]);

  assert.equal(result.candidates.length, 0);
  assert.equal(result.totalMatched, 0);
  assert.ok(result.warnings.includes("UNKNOWN_SYMPTOM_IGNORED:s1"));
});

test("engine: evidence menyimpan rule ID dan komponen skor", () => {
  const d1 = disease("D1", [symptom("s1", "c1"), symptom("s2")]);
  const result = reason(dataset([d1]), ["s1", "s2"], { topN: 5 });
  const candidate = result.candidates[0]!;

  assert.equal(candidate.evidence.length, 2);
  assert.equal(candidate.evidence[0]!.ruleId, "R-EXACT-D1-s1");
  assert.equal(candidate.evidence[0]!.canonicalSymptomId, "c1");
  assert.equal(candidate.evidence[1]!.ruleId, "R-EXACT-D1-s2");
  assert.equal(candidate.evidence[1]!.canonicalSymptomId, null);
  assert.ok(candidate.scoreComponents.evidence > 0);
  assert.equal(candidate.scoreComponents.completeness, 1);
});

test("engine: evidenceFloor menyaring kandidat", () => {
  const d1 = disease("D1", [symptom("s1")]);
  const result = reason(dataset([d1]), ["s1"], { evidenceFloor: 2 });

  assert.equal(result.candidates.length, 0);
  assert.equal(result.totalMatched, 0);
  assert.ok(result.warnings.includes("NO_MATCHING_DISEASE"));
});

test("explain: narasi menyebut exact dan kanonik", () => {
  const d1 = disease("D1", [symptom("s1", "c1"), symptom("s2", "c2")]);
  const d2 = disease("D2", [symptom("s3", "c1"), symptom("s4", "c2")]);
  const result = reason(dataset([d1, d2]), ["s1", "s4"]);

  const candidate = result.candidates.find((item) => item.disease.id === "D1")!;
  const text = explainCandidate(candidate);

  assert.match(text, /1 gejala cocok persis/);
  assert.match(text, /1 gejala cocok pada konsep c2/);
  assert.match(text, /seluruh gejala yang dipilih/);
});

test("prepareDataset: df dan indeks kanonik", () => {
  const d1 = disease("D1", [symptom("s1", "c1")]);
  const d2 = disease("D2", [symptom("s2", "c1")]);
  const prepared = prepareDataset(dataset([d1, d2]));

  assert.equal(prepared.diseaseCount, 2);
  assert.equal(prepared.observationDf.get("http://test.local/s1"), 1);
  assert.equal(prepared.canonicalDf.get("http://test.local/c1"), 2);
  assert.equal(prepared.canonicalObservationCount, 2);
});

test("engine: fase cocok menaikkan skor tanpa menambah bukti gejala", () => {
  const selectedPhase = phase("FaseAnakanTanaman");
  const d1 = disease("D1", [symptom("s1")], [selectedPhase]);
  const d2 = disease("D2", [symptom("s2")]);
  const data = dataset([d1, d2]);

  const withoutPhase = reason(data, ["s1", "s2"], { topN: 5 });
  const withPhase = reason(data, ["s1", "s2"], {
    topN: 5,
    phaseIri: selectedPhase.iri,
  });

  const before = withoutPhase.candidates.find((item) => item.disease.id === "D1")!;
  const after = withPhase.candidates.find((item) => item.disease.id === "D1")!;
  const other = withPhase.candidates.find((item) => item.disease.id === "D2")!;

  assert.equal(before.phaseMatch, "unknown");
  assert.equal(after.phaseMatch, "match");
  assert.equal(after.scoreComponents.phase, 1.05);
  assert.ok(after.score > before.score);
  assert.equal(after.evidence.length, before.evidence.length);
  assert.equal(other.phaseMatch, "unknown");
});

test("engine: fase berbeda atau data fase kosong tidak menghukum kandidat", () => {
  const selectedPhase = phase("FaseAnakanTanaman");
  const otherPhase = phase("FaseGeneratifUmum");
  const d1 = disease("D1", [symptom("s1")], [selectedPhase]);
  const d2 = disease("D2", [symptom("s2")], [otherPhase]);
  const data = dataset([d1, d2]);

  const withoutPhase = reason(data, ["s1", "s2"], { topN: 5 });
  const withPhase = reason(data, ["s1", "s2"], {
    topN: 5,
    phaseIri: selectedPhase.iri,
  });

  const d1Before = withoutPhase.candidates.find((item) => item.disease.id === "D1")!;
  const d2Before = withoutPhase.candidates.find((item) => item.disease.id === "D2")!;
  const d1After = withPhase.candidates.find((item) => item.disease.id === "D1")!;
  const d2After = withPhase.candidates.find((item) => item.disease.id === "D2")!;

  assert.equal(d1After.phaseMatch, "match");
  assert.equal(d2After.phaseMatch, "mismatch");
  assert.equal(d2After.score, d2Before.score);
  assert.ok(d1After.score > d1Before.score);
});
