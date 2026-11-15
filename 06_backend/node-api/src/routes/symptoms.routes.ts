import { Router } from "express";
import { ok } from "../lib/response.js";
import { listSymptoms } from "../services/knowledge.service.js";

const router = Router();

router.get("/", async (req, res) => {
  const plantId = req.query["plantId"];
  const filter = typeof plantId === "string" && plantId.trim() !== ""
    ? plantId.trim()
    : undefined;

  const symptoms = await listSymptoms(filter);
  res.json(ok(res, { count: symptoms.length, items: symptoms }));
});

export default router;
