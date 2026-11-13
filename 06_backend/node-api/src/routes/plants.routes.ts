import { Router } from "express";
import { ok } from "../lib/response.js";
import { getPlant, listPlants } from "../services/knowledge.service.js";

const router = Router();

router.get("/", async (_req, res) => {
  const plants = await listPlants();
  res.json(ok(res, { count: plants.length, items: plants }));
});

router.get("/:id", async (req, res) => {
  const plant = await getPlant(req.params["id"] ?? "");
  res.json(ok(res, plant));
});

export default router;
