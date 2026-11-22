import { Router } from "express";

import { env } from "../config/env.js";
import { InvalidRequestError } from "../lib/errors.js";
import { ok } from "../lib/response.js";
import {
  matchSymptoms,
  type MatchableSymptom,
} from "../lib/symptom-match.js";
import {
  getDiagnosisDataset,
  listSymptoms,
} from "../services/knowledge.service.js";

const router = Router();

router.get("/", async (req, res) => {
  const plantId = req.query["plantId"];
  const filter = typeof plantId === "string" && plantId.trim() !== ""
    ? plantId.trim()
    : undefined;

  const symptoms = await listSymptoms(filter);
  res.json(ok(res, { count: symptoms.length, items: symptoms }));
});

router.post("/match", async (req, res) => {
  const body = (req.body ?? {}) as Record<string, unknown>;

  const rawPlantId = body["plantId"];
  const rawText = body["text"];

  if (typeof rawPlantId !== "string" || rawPlantId.trim() === "") {
    throw new InvalidRequestError("plantId wajib diisi", [
      { field: "plantId", message: "plantId wajib diisi" },
    ]);
  }

  if (typeof rawText !== "string" || rawText.trim() === "") {
    throw new InvalidRequestError("text wajib diisi", [
      { field: "text", message: "text wajib diisi" },
    ]);
  }

  const text = rawText.trim();

  if (text.length > 500) {
    throw new InvalidRequestError("text maksimal 500 karakter", [
      { field: "text", message: "text maksimal 500 karakter" },
    ]);
  }

  const dataset = await getDiagnosisDataset(rawPlantId.trim());
  const byId = new Map<string, MatchableSymptom>();

  for (const disease of dataset.diseases) {
    for (const symptom of disease.symptoms) {
      if (!byId.has(symptom.id)) {
        byId.set(symptom.id, {
          id: symptom.id,
          label: symptom.label,
          description: symptom.description,
        });
      }
    }
  }

  const result = matchSymptoms([...byId.values()], text, {
    limit: env.symptomMatchLimit,
    minScore: env.symptomMatchMinScore,
  });

  res.json(
    ok(res, {
      plantId: dataset.plant.id,
      text,
      suggestions: result.suggestions,
      unmatchedTerms: result.unmatchedTerms,
    })
  );
});

export default router;
