import { Router } from "express";

import { InvalidRequestError } from "../lib/errors.js";
import { ok } from "../lib/response.js";
import {
  CASE_STATUSES,
  caseStats,
  deleteCase,
  getCase,
  listCases,
  parseCaseInput,
  saveCase,
  verifyCase,
  type CaseStatus,
} from "../services/case-store.service.js";
import { diagnose } from "../services/diagnosis.service.js";

const router = Router();

function requestIdOf(res: { locals: Record<string, unknown> }): string | undefined {
  return typeof res.locals["requestId"] === "string"
    ? (res.locals["requestId"] as string)
    : undefined;
}

function parseIntParam(
  value: unknown,
  field: string,
  fallback: number,
  min: number,
  max: number
): number {
  if (value === undefined) {
    return fallback;
  }

  if (typeof value !== "string" || value.trim() === "") {
    throw new InvalidRequestError(`${field} harus berupa angka`, [
      { field, message: `${field} harus berupa angka` },
    ]);
  }

  const parsed = Number(value);

  if (!Number.isInteger(parsed) || parsed < min || parsed > max) {
    throw new InvalidRequestError(`${field} harus integer ${min}-${max}`, [
      { field, message: `${field} harus integer ${min}-${max}` },
    ]);
  }

  return parsed;
}

router.post("/", async (req, res) => {
  const input = parseCaseInput(req.body);
  const requestId = requestIdOf(res);

  const diagnosis = await diagnose(
    {
      plantId: input.plantId,
      phaseId: input.phaseId,
      symptomIds: input.symptomIds,
      topN: input.topN,
    },
    requestId,
    { withCbr: false }
  );

  const saved = await saveCase(input, diagnosis);
  res.status(201).json(ok(res, saved));
});

router.get("/", async (req, res) => {
  const plantIdRaw = req.query["plantId"];
  const plantId =
    typeof plantIdRaw === "string" && plantIdRaw.trim() !== ""
      ? plantIdRaw.trim()
      : undefined;

  const statusRaw = req.query["status"];
  let status: CaseStatus | undefined;

  if (statusRaw !== undefined) {
    if (
      typeof statusRaw !== "string" ||
      !CASE_STATUSES.includes(statusRaw as CaseStatus)
    ) {
      throw new InvalidRequestError(
        `status harus salah satu: ${CASE_STATUSES.join(", ")}`,
        [
          {
            field: "status",
            message: `status harus salah satu: ${CASE_STATUSES.join(", ")}`,
          },
        ]
      );
    }
    status = statusRaw as CaseStatus;
  }

  const limit = parseIntParam(req.query["limit"], "limit", 20, 1, 100);
  const offset = parseIntParam(
    req.query["offset"],
    "offset",
    0,
    0,
    100000
  );

  const items = await listCases({ plantId, status, limit, offset });
  res.json(ok(res, { count: items.length, items, limit, offset }));
});

router.get("/stats", async (_req, res) => {
  res.json(ok(res, await caseStats()));
});

router.get("/:id", async (req, res) => {
  const caseId = req.params["id"] ?? "";
  res.json(ok(res, await getCase(caseId)));
});

router.post("/:id/verify", async (req, res) => {
  const caseId = req.params["id"] ?? "";
  const body = (req.body ?? {}) as Record<string, unknown>;
  const rawDisease = body["diseaseId"];

  let diseaseId: string | undefined;

  if (rawDisease !== undefined && rawDisease !== null) {
    if (typeof rawDisease !== "string" || rawDisease.trim() === "") {
      throw new InvalidRequestError("diseaseId harus string tidak kosong", [
        { field: "diseaseId", message: "diseaseId harus string tidak kosong" },
      ]);
    }
    diseaseId = rawDisease.trim();
  }

  res.json(ok(res, await verifyCase(caseId, diseaseId)));
});

router.delete("/:id", async (req, res) => {
  const caseId = req.params["id"] ?? "";
  await deleteCase(caseId);
  res.json(ok(res, { id: caseId, deleted: true }));
});

export default router;
