import { Router } from "express";
import { ok } from "../lib/response.js";
import { listPhases } from "../services/knowledge.service.js";

const router = Router();

router.get("/", async (req, res) => {
  const plantId = req.query["plantId"];
  const filter =
    typeof plantId === "string" && plantId.trim() !== ""
      ? plantId.trim()
      : undefined;

  const phases = await listPhases(filter);
  res.json(ok(res, { count: phases.length, items: phases }));
});

export default router;
