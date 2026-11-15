import { Router } from "express";
import { ok } from "../lib/response.js";
import {
  diagnose,
  parseDiagnosisInput,
} from "../services/diagnosis.service.js";

const router = Router();

router.post("/", async (req, res) => {
  const input = parseDiagnosisInput(req.body);
  const result = await diagnose(input);
  res.status(200).json(ok(res, result));
});

export default router;
