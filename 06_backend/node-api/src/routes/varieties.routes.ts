import { Router } from "express";

import { ok } from "../lib/response.js";
import { listVarieties } from "../services/knowledge.service.js";

const router = Router();

router.get("/", async (req, res) => {
  const plantId = req.query["plantId"];
  const filter =
    typeof plantId === "string" && plantId.trim() !== ""
      ? plantId.trim()
      : undefined;

  const varieties = await listVarieties(filter);
  res.json(ok(res, { count: varieties.length, items: varieties }));
});

export default router;
