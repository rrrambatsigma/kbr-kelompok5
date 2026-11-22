import test from "node:test";
import assert from "node:assert/strict";

import { InvalidRequestError } from "../src/lib/errors.js";
import { escapeIri, escapeLiteral } from "../src/lib/sparql.js";
import {
  buildCaseInsert,
  parseCaseInput,
} from "../src/services/case-store.service.js";
import type { DiagnosisResult } from "../src/services/diagnosis.service.js";

test("escapeIri menolak karakter tidak aman", () => {
  for (const bad of ["a b", "a>b", 'a"b', "a{b}", "a|b", ""]) {
    assert.throws(() => escapeIri(bad), InvalidRequestError);
  }

  assert.equal(
    escapeIri("http://kbr.kelompok5.org/penyakit-tanaman-pangan#Padi"),
    "<http://kbr.kelompok5.org/penyakit-tanaman-pangan#Padi>"
  );
});

test("escapeLiteral meng-escape kutip, backslash, dan newline", () => {
  assert.equal(escapeLiteral('a"b\\c\nd'), '"a\\"b\\\\c\\nd"');
});

test("parseCaseInput menerima payload valid", () => {
  const input = parseCaseInput({
    plantId: " Padi ",
    symptomIds: ["PengamatanA", "PengamatanB"],
    note: "  daun menguning  ",
    freeTextSymptoms: "daun menguning",
    confirmedDiseaseId: "PenyakitBlasPadi",
    source: "uji",
  });

  assert.equal(input.plantId, "Padi");
  assert.deepEqual(input.symptomIds, ["PengamatanA", "PengamatanB"]);
  assert.equal(input.note, "daun menguning");
  assert.equal(input.freeTextSymptoms, "daun menguning");
  assert.equal(input.confirmedDiseaseId, "PenyakitBlasPadi");
  assert.equal(input.source, "uji");
  assert.equal(input.topN, 5);
});

test("parseCaseInput menolak catatan terlalu panjang", () => {
  assert.throws(
    () =>
      parseCaseInput({
        plantId: "Padi",
        symptomIds: ["A"],
        note: "x".repeat(501),
      }),
    InvalidRequestError
  );
});

test("parseCaseInput menolak sumber tidak dikenal", () => {
  assert.throws(
    () =>
      parseCaseInput({
        plantId: "Padi",
        symptomIds: ["A"],
        source: "orang",
      }),
    InvalidRequestError
  );
});

test("parseCaseInput menolak symptomIds kosong", () => {
  assert.throws(
    () => parseCaseInput({ plantId: "Padi", symptomIds: [] }),
    InvalidRequestError
  );
});

test("buildCaseInsert menulis diagnosis, gejala, dan kandidat", () => {
  const result = {
    input: {
      plantIri: "http://kbr.kelompok5.org/penyakit-tanaman-pangan#Padi",
      plantLabel: "Padi",
      phaseIri: null,
      symptoms: [
        {
          iri: "http://kbr.kelompok5.org/penyakit-tanaman-pangan#PengamatanA",
          label: "Bercak daun",
        },
      ],
    },
    candidates: [
      {
        diseaseId: "PenyakitBlasPadi",
        diseaseIri:
          "http://kbr.kelompok5.org/penyakit-tanaman-pangan#PenyakitBlasPadi",
        label: "Penyakit Blas",
        score: 0.823,
        confidence: "TINGGI",
        explanation: "3 gejala cocok persis.",
      },
    ],
  } as unknown as DiagnosisResult;

  const input = parseCaseInput({
    plantId: "Padi",
    symptomIds: ["PengamatanA"],
    note: "catatan",
    freeTextSymptoms: "daun menguning",
    source: "pengguna",
  });

  const insert = buildCaseInsert({
    caseId: "11111111-2222-3333-4444-555555555555",
    createdAt: "2026-11-22T10:00:00.000Z",
    input,
    result,
  });

  assert.match(insert, /INSERT DATA/);
  assert.match(insert, /GRAPH <urn:kbr:kasus>/);
  assert.match(insert, /a ptp:Diagnosis/);
  assert.match(insert, /ptp:idKasus "11111111-2222-3333-4444-555555555555"/);
  assert.match(insert, /ptp:waktuKasus "2026-11-22T10:00:00.000Z"\^\^/);
  assert.match(insert, /ptp:memilikiTanaman <http:\/\/kbr\.kelompok5\.org\/penyakit-tanaman-pangan#Padi>/);
  assert.match(insert, /ptp:memilikiObservasi <http:\/\/kbr\.kelompok5\.org\/penyakit-tanaman-pangan#PengamatanA>/);
  assert.match(insert, /ptp:teksGejalaBebas "daun menguning"\^\^/);
  assert.match(insert, /ptp:catatanPengguna "catatan"\^\^/);
  assert.match(insert, /ptp:peringkat "1"\^\^/);
  assert.match(insert, /ptp:skorKecocokan "0\.823"\^\^/);
  assert.match(insert, /ptp:tingkatKeyakinan "TINGGI"\^\^/);
  assert.match(insert, /ptp:kandidat <urn:kbr:kasus\/11111111-2222-3333-4444-555555555555\/kandidat-1>/);
});
