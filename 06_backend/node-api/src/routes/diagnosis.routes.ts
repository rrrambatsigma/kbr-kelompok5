import { Router } from "express";
import { ok } from "../lib/response.js";
import {
  diagnose,
  parseDiagnosisInput,
} from "../services/diagnosis.service.js";

const router = Router();

router.post("/", async (req, res) => {
  const input = parseDiagnosisInput(req.body);
  const requestId =
    typeof res.locals.requestId === "string"
      ? res.locals.requestId
      : undefined;
  const result = await diagnose(input, requestId);
  res.status(200).json(ok(res, result));
});

export default router;
