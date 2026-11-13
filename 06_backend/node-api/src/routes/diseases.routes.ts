import { Router } from "express";
import { ok } from "../lib/response.js";
import {
  getDisease,
  listDiseases,
} from "../services/knowledge.service.js";

const router = Router();

router.get("/", async (req, res) => {
  const plantId = req.query["plantId"];
  const filter = typeof plantId === "string" && plantId.trim() !== ""
    ? plantId.trim()
    : undefined;

  const diseases = await listDiseases(filter);
  res.json(ok(res, { count: diseases.length, items: diseases }));
});

router.get("/:id", async (req, res) => {
  const disease = await getDisease(req.params["id"] ?? "");
  res.json(ok(res, disease));
});

export default router;
