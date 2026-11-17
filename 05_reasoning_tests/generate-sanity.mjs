#!/usr/bin/env node
/**
 * Generate sanity cases dari ontology yang sedang dimuat.
 *
 *   node generate-sanity.mjs --base-url http://127.0.0.1:3000
 *
 * Kasus sanity adalah regression test, bukan gold/akurasi: gejalanya diambil
 * dari penyakit itu sendiri sehingga hasilnya bias tinggi.
 */
import { writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));

function readArg(name, fallback) {
  const index = process.argv.indexOf(`--${name}`);
  if (index === -1 || process.argv[index + 1] === undefined) {
    return fallback;
  }
  return process.argv[index + 1];
}

const baseUrl = readArg("base-url", "http://127.0.0.1:3000").replace(/\/$/, "");
const perDisease = Number.parseInt(readArg("per-disease", "3"), 10);
const ontologyTag = readArg("ontology", "temporary-v2");
const outPath = join(scriptDir, "cases", "sanity.json");

async function getJson(path) {
  const response = await fetch(`${baseUrl}${path}`, {
    headers: { Accept: "application/json" },
    signal: AbortSignal.timeout(15_000),
  });

  const text = await response.text();
  let body;
  try {
    body = text === "" ? {} : JSON.parse(text);
  } catch {
    throw new Error(`Response bukan JSON: ${path}`);
  }

  if (!response.ok || body.success === false) {
    const message = body?.error?.message ?? `HTTP ${response.status}`;
    throw new Error(`${path}: ${message}`);
  }

  return body.data;
}

function pickSymptoms(symptoms, limit) {
  // Label yang bukan "Pengamatan gejala ..." biasanya merupakan konsep
  // kanonik yang lebih informatif. Utamakan itu, lalu lengkapi sisanya.
  const preferred = symptoms.filter(
    (symptom) => !symptom.label.startsWith("Pengamatan gejala")
  );
  const rest = symptoms.filter((symptom) =>
    symptom.label.startsWith("Pengamatan gejala")
  );
  const ordered = [...preferred, ...rest].sort(
    (left, right) =>
      left.label.localeCompare(right.label, "id") ||
      left.id.localeCompare(right.id)
  );
  return ordered.slice(0, Math.max(1, limit));
}

const plants = (await getJson("/api/plants")).items;
const cases = [];

for (const plant of plants) {
  const diseases = (await getJson(`/api/diseases?plantId=${encodeURIComponent(plant.id)}`))
    .items;

  for (const summary of diseases) {
    const disease = await getJson(`/api/diseases/${encodeURIComponent(summary.id)}`);
    if (disease.symptoms.length === 0) {
      continue;
    }

    const selected = pickSymptoms(disease.symptoms, perDisease);
    cases.push({
      id: `SANITY-${disease.id}`,
      type: "sanity",
      plantId: plant.id,
      symptoms: selected.map((symptom) => ({
        id: symptom.id,
        label: symptom.label,
      })),
      expectedDiseaseId: disease.id,
      expectedTopK: 3,
      source: "generated-from-ontology",
      ontology: ontologyTag,
      verified: false,
      notes: "generated; regression only",
    });
  }
}

await writeFile(outPath, `${JSON.stringify(cases, null, 2)}\n`, "utf8");
console.log(
  `Generated ${cases.length} sanity cases -> ${outPath} (perDisease=${perDisease})`
);
