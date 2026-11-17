#!/usr/bin/env node
/**
 * Harness validasi reasoning diagnosis.
 *
 *   node run.mjs
 *   node run.mjs --base-url http://127.0.0.1:3000 --top-n 10
 *
 * Menjalankan kasus manual/gold, sanity, dan negative; menghitung top-1,
 * top-3, MRR; membandingkan dengan model lama (exact match 0.7/0.3); lalu
 * menulis results.json dan results.md.
 */
import { readFile, writeFile } from "node:fs/promises";
import { dirname, isAbsolute, join } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const TIMEOUT_MS = 30_000;

function arg(name, fallback) {
  const index = process.argv.indexOf(`--${name}`);
  if (index === -1 || process.argv[index + 1] === undefined) {
    return fallback;
  }
  return process.argv[index + 1];
}

function flag(name) {
  return process.argv.includes(`--${name}`);
}

function round4(value) {
  return Math.round(value * 10_000) / 10_000;
}

function pct(value) {
  return `${(value * 100).toFixed(1)}%`;
}

function fmt(value) {
  return Number.isFinite(value) ? value.toFixed(3) : "-";
}

function delta(value) {
  if (!Number.isFinite(value)) {
    return "-";
  }
  return `${value >= 0 ? "+" : ""}${value.toFixed(3)}`;
}

function normalizeLabel(value) {
  return value.trim().replace(/\s+/g, " ").toLowerCase();
}

const baseUrl = arg("base-url", "http://127.0.0.1:3000").replace(/\/$/, "");
const topN = Number.parseInt(arg("top-n", "10"), 10);
const manualPath = arg("manual", "cases/manual.json");
const sanityPath = arg("sanity", "cases/sanity.json");
const ambiguousPath = arg("ambiguous", "cases/ambiguous.json");
const negativePath = arg("negative", "cases/negative.json");
const outName = arg("out", "results");
const thresholdTop1 = Number.parseFloat(arg("threshold-top1", "0.70"));
const thresholdTop3 = Number.parseFloat(arg("threshold-top3", "0.90"));
const thresholdMrr = Number.parseFloat(arg("threshold-mrr", "0.80"));
const thresholdAmbiguousTop1 = Number.parseFloat(
  arg("threshold-ambiguous-top1", "0.50")
);
const skipHealth = flag("skip-health");
const withPerformance = flag("perf");
const noThresholds = flag("no-thresholds");

function resolvePath(value) {
  return isAbsolute(value) ? value : join(scriptDir, value);
}

async function readJson(path, fallback, label) {
  try {
    const raw = await readFile(resolvePath(path), "utf8");
    return JSON.parse(raw.replace(/^\uFEFF/, ""));
  } catch (error) {
    if (error.code === "ENOENT") {
      console.warn(`Lewati ${label}: file tidak ditemukan (${path})`);
      return fallback;
    }
    throw new Error(`Gagal membaca ${label} (${path}): ${error.message}`);
  }
}

async function fetchJson(path, init = {}) {
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init.body === undefined ? {} : { "Content-Type": "application/json" }),
      ...init.headers,
    },
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });

  const text = await response.text();
  let body = {};
  try {
    body = text === "" ? {} : JSON.parse(text);
  } catch {
    throw new Error(`Response bukan JSON: ${path} (HTTP ${response.status})`);
  }

  return { status: response.status, ok: response.ok, body };
}

async function getData(path) {
  const response = await fetchJson(path);
  if (!response.ok || response.body.success === false) {
    const message = response.body?.error?.message ?? `HTTP ${response.status}`;
    throw new Error(`${path}: ${message}`);
  }
  return response.body.data;
}

function computeMetrics(results, rankKey) {
  const total = results.length;
  const errors = results.filter((item) => item.error !== undefined).length;
  const top1 = results.filter((item) => item[rankKey] === 1).length;
  const top3 = results.filter(
    (item) => item[rankKey] !== null && item[rankKey] <= 3
  ).length;
  const mrr =
    total === 0
      ? 0
      : results.reduce((sum, item) => {
          const rank = item[rankKey];
          return sum + (rank === null ? 0 : 1 / rank);
        }, 0) / total;

  return {
    count: total,
    errors,
    top1,
    top3,
    top1Rate: total === 0 ? 0 : round4(top1 / total),
    top3Rate: total === 0 ? 0 : round4(top3 / total),
    mrr: round4(mrr),
  };
}

function groupBy(results, keyFn) {
  const groups = new Map();
  for (const item of results) {
    const key = keyFn(item);
    const list = groups.get(key) ?? [];
    list.push(item);
    groups.set(key, list);
  }
  return groups;
}

function legacyRank(caseItem, plantData) {
  const selected = new Set(caseItem.symptoms.map((symptom) => symptom.id));
  const candidates = [];

  for (const disease of plantData.diseases) {
    const diseaseSymptoms = new Set(
      disease.symptoms.map((symptom) => symptom.id)
    );
    let matched = 0;
    for (const id of selected) {
      if (diseaseSymptoms.has(id)) {
        matched += 1;
      }
    }
    if (matched === 0) {
      continue;
    }

    const matchRatio = matched / selected.size;
    const coverage =
      diseaseSymptoms.size === 0 ? 0 : matched / diseaseSymptoms.size;
    candidates.push({
      diseaseId: disease.id,
      label: disease.label,
      score: round4(0.7 * matchRatio + 0.3 * coverage),
      matched,
    });
  }

  candidates.sort(
    (left, right) =>
      right.score - left.score ||
      right.matched - left.matched ||
      left.label.localeCompare(right.label, "id")
  );

  const top = candidates.slice(0, topN);
  const index = top.findIndex(
    (candidate) => candidate.diseaseId === caseItem.expectedDiseaseId
  );

  return {
    rank: index === -1 ? null : index + 1,
    top,
  };
}

function ensureCaseShape(caseItem) {
  const problems = [];
  if (typeof caseItem.id !== "string" || caseItem.id.trim() === "") {
    problems.push("id kosong");
  }
  if (typeof caseItem.plantId !== "string" || caseItem.plantId.trim() === "") {
    problems.push("plantId kosong");
  }
  if (
    !Array.isArray(caseItem.symptoms) ||
    caseItem.symptoms.length === 0
  ) {
    problems.push("symptoms kosong");
  }
  if (
    typeof caseItem.expectedDiseaseId !== "string" ||
    caseItem.expectedDiseaseId.trim() === ""
  ) {
    problems.push("expectedDiseaseId kosong");
  }
  return problems;
}

const manualCases = await readJson(manualPath, [], "kasus manual");
const sanityCases = await readJson(sanityPath, [], "kasus sanity");
const ambiguousCases = await readJson(ambiguousPath, [], "kasus ambiguous");
const negativeCases = await readJson(negativePath, [], "kasus negative");
const normalCases = [...manualCases, ...sanityCases, ...ambiguousCases];

if (normalCases.length === 0 && negativeCases.length === 0) {
  throw new Error("Tidak ada kasus untuk dijalankan.");
}

if (!skipHealth) {
  const health = await fetchJson("/api/health/ready");
  if (!health.ok) {
    throw new Error(
      `Service belum siap: HTTP ${health.status}. Jalankan Fuseki, Java, dan Node dulu.`
    );
  }
}

const plants = (await getData("/api/plants")).items;
const plantById = new Map(plants.map((plant) => [plant.id, plant]));
const plantDataCache = new Map();

async function getPlantData(plantId) {
  const cached = plantDataCache.get(plantId);
  if (cached !== undefined) {
    return cached;
  }

  const diseases = (
    await getData(`/api/diseases?plantId=${encodeURIComponent(plantId)}`)
  ).items;

  const details = [];
  const symptomById = new Map();

  for (const summary of diseases) {
    const disease = await getData(
      `/api/diseases/${encodeURIComponent(summary.id)}`
    );
    details.push(disease);
    for (const symptom of disease.symptoms) {
      symptomById.set(symptom.id, symptom);
    }
  }

  const data = {
    diseases: details,
    diseaseById: new Map(details.map((disease) => [disease.id, disease])),
    symptomById,
  };
  plantDataCache.set(plantId, data);
  return data;
}

const validationErrors = [];
const validationWarnings = [];

for (const caseItem of normalCases) {
  const problems = ensureCaseShape(caseItem);
  if (problems.length > 0) {
    validationErrors.push(`${caseItem.id ?? "(tanpa id)"}: ${problems.join(", ")}`);
    continue;
  }

  if (!plantById.has(caseItem.plantId)) {
    validationErrors.push(`${caseItem.id}: tanaman tidak dikenal ${caseItem.plantId}`);
    continue;
  }

  const plantData = await getPlantData(caseItem.plantId);

  if (!plantData.diseaseById.has(caseItem.expectedDiseaseId)) {
    validationErrors.push(
      `${caseItem.id}: penyakit target tidak dikenal ${caseItem.expectedDiseaseId}`
    );
  }

  for (const symptom of caseItem.symptoms) {
    const known = plantData.symptomById.get(symptom.id);
    if (known === undefined) {
      validationErrors.push(
        `${caseItem.id}: gejala tidak ditemukan untuk ${caseItem.plantId}: ${symptom.id}`
      );
    } else if (
      symptom.label !== undefined &&
      normalizeLabel(symptom.label) !== normalizeLabel(known.label)
    ) {
      validationWarnings.push(
        `${caseItem.id}: label berbeda untuk ${symptom.id} (case: "${symptom.label}", ontology: "${known.label}")`
      );
    }
  }
}

if (validationErrors.length > 0) {
  console.error("Validasi kasus gagal:");
  for (const error of validationErrors) {
    console.error(`  - ${error}`);
  }
  process.exit(1);
}

const results = [];
const reasoningMeta = { modelVersion: null, ontology: null };

for (const caseItem of normalCases) {
  const body = {
    plantId: caseItem.plantId,
    symptomIds: caseItem.symptoms.map((symptom) => symptom.id),
    topN,
  };

  try {
    const response = await fetchJson("/api/diagnosis", {
      method: "POST",
      body: JSON.stringify(body),
    });

    if (!response.ok || response.body.success === false) {
      results.push({
        id: caseItem.id,
        type: caseItem.type,
        plantId: caseItem.plantId,
        expectedDiseaseId: caseItem.expectedDiseaseId,
        rank: null,
        legacyRank: null,
        error: response.body?.error?.code ?? `HTTP ${response.status}`,
      });
      continue;
    }

    const data = response.body.data;
    const index = data.candidates.findIndex(
      (candidate) => candidate.diseaseId === caseItem.expectedDiseaseId
    );
    const expected = index === -1 ? null : data.candidates[index];
    const legacy = legacyRank(caseItem, await getPlantData(caseItem.plantId));

    reasoningMeta.modelVersion =
      reasoningMeta.modelVersion ?? data.reasoning?.modelVersion ?? null;
    reasoningMeta.ontology = reasoningMeta.ontology ?? {
      version: data.reasoning?.ontologyVersion ?? null,
      checksum: data.reasoning?.checksum ?? null,
    };

    results.push({
      id: caseItem.id,
      type: caseItem.type,
      plantId: caseItem.plantId,
      expectedDiseaseId: caseItem.expectedDiseaseId,
      expectedTopK: caseItem.expectedTopK ?? 3,
      rank: index === -1 ? null : index + 1,
      legacyRank: legacy.rank,
      expectedScore: expected?.score ?? null,
      expectedConfidence: expected?.confidence ?? null,
      expectedExplanation: expected?.explanation ?? null,
      top: data.candidates.slice(0, 3).map((candidate) => ({
        diseaseId: candidate.diseaseId,
        label: candidate.label,
        score: candidate.score,
        confidence: candidate.confidence,
      })),
      legacyTop: legacy.top.slice(0, 3),
      warnings: data.warnings ?? [],
    });
  } catch (error) {
    results.push({
      id: caseItem.id,
      type: caseItem.type,
      plantId: caseItem.plantId,
      expectedDiseaseId: caseItem.expectedDiseaseId,
      rank: null,
      legacyRank: null,
      error: error instanceof Error ? error.message : String(error),
    });
  }
}

const negativeResults = [];

for (const caseItem of negativeCases) {
  const body = {
    plantId: caseItem.plantId,
    symptomIds: caseItem.symptomIds,
  };
  if (caseItem.topN !== undefined) {
    body.topN = caseItem.topN;
  }

  try {
    const response = await fetchJson("/api/diagnosis", {
      method: "POST",
      body: JSON.stringify(body),
    });
    const code = response.body?.error?.code ?? null;
    const warnings = response.body?.data?.warnings ?? [];
    const statusOk = response.status === caseItem.expectedStatus;
    const codeOk =
      caseItem.expectedErrorCode === undefined ||
      code === caseItem.expectedErrorCode;
    const warningOk =
      caseItem.expectedWarning === undefined ||
      warnings.includes(caseItem.expectedWarning);

    negativeResults.push({
      id: caseItem.id,
      expectedStatus: caseItem.expectedStatus,
      actualStatus: response.status,
      expectedErrorCode: caseItem.expectedErrorCode ?? null,
      actualErrorCode: code,
      expectedWarning: caseItem.expectedWarning ?? null,
      warnings,
      pass: statusOk && codeOk && warningOk,
      notes: caseItem.notes ?? null,
    });
  } catch (error) {
    negativeResults.push({
      id: caseItem.id,
      expectedStatus: caseItem.expectedStatus,
      actualStatus: null,
      pass: false,
      error: error instanceof Error ? error.message : String(error),
    });
  }
}

let determinism = null;
if (normalCases.length > 0) {
  const sample = normalCases[0];
  const body = {
    plantId: sample.plantId,
    symptomIds: sample.symptoms.map((symptom) => symptom.id),
    topN,
  };
  const runOnce = async () => {
    const response = await fetchJson("/api/diagnosis", {
      method: "POST",
      body: JSON.stringify(body),
    });
    return response.body.data.candidates
      .map((candidate) => candidate.diseaseId)
      .join("|");
  };
  const [first, second] = await Promise.all([runOnce(), runOnce()]);
  determinism = {
    caseId: sample.id,
    stable: first === second,
  };
}

let performance = null;
if (withPerformance && normalCases.length > 0) {
  const sample = normalCases[0];
  const body = {
    plantId: sample.plantId,
    symptomIds: sample.symptoms.map((symptom) => symptom.id),
    topN,
  };
  const times = [];
  for (let index = 0; index < 21; index += 1) {
    const started = performanceNow();
    await fetchJson("/api/diagnosis", {
      method: "POST",
      body: JSON.stringify(body),
    });
    const elapsed = performanceNow() - started;
    if (index > 0) {
      times.push(elapsed);
    }
  }
  times.sort((left, right) => left - right);
  performance = {
    samples: times.length,
    p50Ms: round4(times[Math.floor(times.length * 0.5)] ?? 0),
    p95Ms: round4(times[Math.floor(times.length * 0.95)] ?? 0),
  };
}

function performanceNow() {
  return globalThis.performance?.now?.() ?? Date.now();
}

const overall = computeMetrics(results, "rank");
const overallLegacy = computeMetrics(results, "legacyRank");

const byType = new Map();
for (const type of ["gold", "sanity", "ambiguous"]) {
  const list = results.filter((item) => item.type === type);
  if (list.length > 0) {
    byType.set(type, {
      current: computeMetrics(list, "rank"),
      legacy: computeMetrics(list, "legacyRank"),
    });
  }
}

const byPlant = new Map();
for (const [plantId, list] of groupBy(results, (item) => item.plantId)) {
  byPlant.set(plantId, {
    current: computeMetrics(list, "rank"),
    legacy: computeMetrics(list, "legacyRank"),
  });
}

const goldResults = results.filter((item) => item.type === "gold");
const goldMetrics =
  goldResults.length > 0 ? computeMetrics(goldResults, "rank") : null;
const goldLegacy =
  goldResults.length > 0 ? computeMetrics(goldResults, "legacyRank") : null;

const ambiguousResults = results.filter(
  (item) => item.type === "ambiguous"
);
const ambiguousMetrics =
  ambiguousResults.length > 0
    ? computeMetrics(ambiguousResults, "rank")
    : null;
const ambiguousLegacy =
  ambiguousResults.length > 0
    ? computeMetrics(ambiguousResults, "legacyRank")
    : null;

// Sanity sengaja tidak masuk fokus: kasusnya dibuat dari gejala penyakit itu
// sendiri sehingga selalu mudah. Fokus = gold + ambiguous.
const focusResults = results.filter(
  (item) => item.type === "gold" || item.type === "ambiguous"
);
const focusMetrics =
  focusResults.length > 0 ? computeMetrics(focusResults, "rank") : null;
const focusLegacy =
  focusResults.length > 0
    ? computeMetrics(focusResults, "legacyRank")
    : null;

const negativePassed = negativeResults.filter((item) => item.pass).length;

const thresholdChecks = [];
if (!noThresholds && focusMetrics !== null) {
  thresholdChecks.push({
    name: "Top-1 fokus (gold+ambiguous)",
    actual: focusMetrics.top1Rate,
    target: thresholdTop1,
    pass: focusMetrics.top1Rate >= thresholdTop1,
  });
  thresholdChecks.push({
    name: "Top-3 fokus (gold+ambiguous)",
    actual: focusMetrics.top3Rate,
    target: thresholdTop3,
    pass: focusMetrics.top3Rate >= thresholdTop3,
  });
  thresholdChecks.push({
    name: "MRR fokus (gold+ambiguous)",
    actual: focusMetrics.mrr,
    target: thresholdMrr,
    pass: focusMetrics.mrr >= thresholdMrr,
  });
}
if (!noThresholds && ambiguousMetrics !== null) {
  thresholdChecks.push({
    name: "Top-1 ambiguous",
    actual: ambiguousMetrics.top1Rate,
    target: thresholdAmbiguousTop1,
    pass: ambiguousMetrics.top1Rate >= thresholdAmbiguousTop1,
  });
}

const confidenceCalibration = new Map();
for (const item of focusResults) {
  if (item.error !== undefined || item.expectedConfidence === null) {
    continue;
  }
  const entry =
    confidenceCalibration.get(item.expectedConfidence) ?? {
      count: 0,
      top1: 0,
      top3: 0,
    };
  entry.count += 1;
  if (item.rank === 1) {
    entry.top1 += 1;
  }
  if (item.rank !== null && item.rank <= 3) {
    entry.top3 += 1;
  }
  confidenceCalibration.set(item.expectedConfidence, entry);
}

const failures = results.filter(
  (item) =>
    item.error !== undefined ||
    item.rank === null ||
    item.rank > (item.expectedTopK ?? 3)
);

const top1Misses = results.filter(
  (item) =>
    item.error === undefined &&
    item.rank !== null &&
    item.rank > 1 &&
    item.rank <= (item.expectedTopK ?? 3)
);

const failedThresholds = thresholdChecks.filter((check) => !check.pass);
const failedNegative = negativeResults.filter((item) => !item.pass);
const requestErrors = results.filter((item) => item.error !== undefined);

const summary = {
  totalNormal: results.length,
  totalNegative: negativeResults.length,
  requestErrors: requestErrors.length,
  overall,
  overallLegacy,
  focus: focusMetrics,
  focusLegacy,
  gold: goldMetrics,
  goldLegacy,
  ambiguous: ambiguousMetrics,
  ambiguousLegacy,
  negativePassed,
  negativeTotal: negativeResults.length,
  failedThresholds,
  passed:
    requestErrors.length === 0 &&
    failedNegative.length === 0 &&
    failedThresholds.length === 0 &&
    (determinism === null || determinism.stable) &&
    validationErrors.length === 0,
};

const output = {
  generatedAt: new Date().toISOString(),
  baseUrl,
  topN,
  reasoning: reasoningMeta,
  validation: {
    errors: validationErrors,
    warnings: validationWarnings,
  },
  summary,
  byType: Object.fromEntries(
    [...byType].map(([type, value]) => [type, value])
  ),
  byPlant: Object.fromEntries(
    [...byPlant].map(([plantId, value]) => [plantId, value])
  ),
  cases: results,
  top1Misses,
  negative: negativeResults,
  determinism,
  performance,
  thresholds: thresholdChecks,
  confidenceCalibration: Object.fromEntries(confidenceCalibration),
};

const jsonPath = join(scriptDir, `${outName}.json`);
const markdownPath = join(scriptDir, `${outName}.md`);

await writeFile(jsonPath, `${JSON.stringify(output, null, 2)}\n`, "utf8");

function metricsRow(label, current, legacy, key) {
  const currentValue =
    key === "mrr" ? current.mrr : current[`${key}Rate`];
  const legacyValue =
    legacy === null
      ? null
      : key === "mrr"
        ? legacy.mrr
        : legacy[`${key}Rate`];
  const diff =
    legacyValue === null ? null : round4(currentValue - legacyValue);
  return `| ${label} | ${legacyValue === null ? "-" : fmt(legacyValue)} | ${fmt(currentValue)} | ${diff === null ? "-" : delta(diff)} |`;
}

const summaryCurrent = focusMetrics ?? overall;
const summaryLegacy = focusLegacy ?? overallLegacy;

const lines = [
  "# Hasil Validasi Reasoning Diagnosis",
  "",
  `- Waktu: ${output.generatedAt}`,
  `- Base URL: ${baseUrl}`,
  `- Model: ${reasoningMeta.modelVersion ?? "-"}`,
  `- Ontology: ${reasoningMeta.ontology?.version ?? "-"} / ${reasoningMeta.ontology?.checksum ?? "-"}`,
  "",
  "## Ringkasan (fokus: gold + ambiguous)",
  "",
  "| Metrik | Baseline (0.7/0.3) | Model baru | Delta |",
  "|---|---:|---:|---:|",
  metricsRow("Top-1", summaryCurrent, summaryLegacy, "top1"),
  metricsRow("Top-3", summaryCurrent, summaryLegacy, "top3"),
  metricsRow("MRR", summaryCurrent, summaryLegacy, "mrr"),
  "",
  `Kasus fokus: **${focusResults.length}**; semua kasus normal: **${results.length}**; error request: **${requestErrors.length}**; negative: **${negativePassed}/${negativeResults.length}** lulus.`,
  `Sanity (${sanityCases.length} kasus) tidak masuk fokus karena dibuat dari gejala penyakit itu sendiri.`,
  "",
  "## Per tipe kasus",
  "",
  "| Tipe | Kasus | Top-1 baru | Top-3 baru | MRR baru | Top-1 baseline | Top-3 baseline |",
  "|---|---:|---:|---:|---:|---:|---:|",
];

for (const [type, value] of [...byType]) {
  lines.push(
    `| ${type} | ${value.current.count} | ${pct(value.current.top1Rate)} | ${pct(value.current.top3Rate)} | ${fmt(value.current.mrr)} | ${pct(value.legacy.top1Rate)} | ${pct(value.legacy.top3Rate)} |`
  );
}

lines.push(
  "",
  "## Per tanaman (semua kasus normal)",
  "",
  "| Tanaman | Kasus | Top-1 | Top-3 | MRR |",
  "|---|---:|---:|---:|---:|"
);

for (const [plantId, value] of [...byPlant]) {
  lines.push(
    `| ${plantId} | ${value.current.count} | ${pct(value.current.top1Rate)} | ${pct(value.current.top3Rate)} | ${fmt(value.current.mrr)} |`
  );
}

lines.push(
  "",
  "## Negative tests",
  "",
  "| Kasus | Expected | Actual | Status |",
  "|---|---:|---:|---|"
);

for (const item of negativeResults) {
  lines.push(
    `| ${item.id} | ${item.expectedStatus} | ${item.actualStatus ?? "-"} | ${item.pass ? "lulus" : "gagal"} |`
  );
}

if (thresholdChecks.length > 0) {
  lines.push("", "## Ambang", "", "| Cek | Target | Aktual | Status |", "|---|---:|---:|---|");
  for (const check of thresholdChecks) {
    lines.push(
      `| ${check.name} | ${fmt(check.target)} | ${fmt(check.actual)} | ${check.pass ? "lulus" : "gagal"} |`
    );
  }
}

if (confidenceCalibration.size > 0) {
  lines.push(
    "",
    "## Kalibrasi confidence (fokus)",
    "",
    "| Confidence | Kasus | Top-1 | Top-3 |",
    "|---|---:|---:|---:|"
  );
  for (const [label, value] of confidenceCalibration) {
    lines.push(
      `| ${label} | ${value.count} | ${pct(value.top1 / value.count)} | ${pct(value.top3 / value.count)} |`
    );
  }
}

if (validationWarnings.length > 0) {
  lines.push("", "## Peringatan validasi", "");
  for (const warning of validationWarnings) {
    lines.push(`- ${warning}`);
  }
}

lines.push("", "## Kasus gagal", "");

if (failures.length === 0) {
  lines.push("Tidak ada kasus yang gagal.");
} else {
  for (const item of failures) {
    if (item.error !== undefined) {
      lines.push(`- **${item.id}** error: ${item.error}`);
      continue;
    }
    lines.push(
      `- **${item.id}** expected \`${item.expectedDiseaseId}\`, rank ${item.rank ?? "tidak muncul"} (target top-${item.expectedTopK ?? 3})`
    );
    if (item.top.length > 0) {
      lines.push(
        `  - top-3: ${item.top.map((candidate) => `${candidate.diseaseId} (${fmt(candidate.score)}, ${candidate.confidence})`).join("; ")}`
      );
    }
    if (item.expectedExplanation !== null) {
      lines.push(`  - alasan kandidat target: ${item.expectedExplanation}`);
    }
  }
}

lines.push("", "## Top-1 meleset (masih dalam top-3)", "");

if (top1Misses.length === 0) {
  lines.push("Tidak ada.");
} else {
  for (const item of top1Misses) {
    lines.push(
      `- **${item.id}** expected \`${item.expectedDiseaseId}\`, rank ${item.rank}`
    );
    if (item.top.length > 0) {
      lines.push(
        `  - top-3: ${item.top.map((candidate) => `${candidate.diseaseId} (${fmt(candidate.score)}, ${candidate.confidence})`).join("; ")}`
      );
    }
  }
}

lines.push(
  "",
  "## Determinism & performa",
  "",
  `- Determinism: ${determinism === null ? "-" : determinism.stable ? "stabil" : "TIDAK stabil"} (${determinism?.caseId ?? "-"})`
);

if (performance !== null) {
  lines.push(
    `- Performa: p50 ${performance.p50Ms} ms; p95 ${performance.p95Ms} ms (${performance.samples} sampel)`
  );
} else {
  lines.push("- Performa: tidak dijalankan (pakai `--perf`)");
}

lines.push(
  "",
  "## Catatan",
  "",
  "- Kasus `gold` saat ini di-seed dari ontology dan bertanda `source: ontology-temporary`; verifikasi halaman buku sebelum mengklaim akurasi independen.",
  "- Kasus `sanity` dibuat otomatis dari gejala penyakit itu sendiri; hanya untuk regression, bukan akurasi.",
  "- Baseline memakai exact match + rumus lama 0,7/0,3 pada kasus yang sama.",
  ""
);

await writeFile(markdownPath, lines.join("\n"), "utf8");

const printMetrics = focusMetrics ?? overall;

console.log(`Hasil: ${jsonPath}`);
console.log(`Laporan: ${markdownPath}`);
console.log(
  `Fokus top-1 ${pct(printMetrics.top1Rate)} | top-3 ${pct(printMetrics.top3Rate)} | MRR ${fmt(printMetrics.mrr)} | negative ${negativePassed}/${negativeResults.length}`
);
if (ambiguousMetrics !== null) {
  console.log(
    `Ambiguous top-1 ${pct(ambiguousMetrics.top1Rate)} (baseline ${pct(ambiguousLegacy.top1Rate)})`
  );
}

if (failedThresholds.length > 0) {
  console.error(
    `Ambang gagal: ${failedThresholds.map((check) => check.name).join(", ")}`
  );
}
if (failedNegative.length > 0) {
  console.error(
    `Negative gagal: ${failedNegative.map((item) => item.id).join(", ")}`
  );
}
if (determinism !== null && !determinism.stable) {
  console.error("Determinism gagal: urutan kandidat berubah.");
}

process.exitCode = summary.passed ? 0 : 1;
