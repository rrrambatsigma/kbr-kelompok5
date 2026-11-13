
import { Router } from "express";
import {
  queryFuseki,
  type SparqlSelectResponse,
} from "../services/fuseki.service.js";
import { fusekiConfig } from "../config/fuseki.js";

const router = Router();

router.get("/fuseki", async (_req, res) => {
  const query = `
    SELECT (COUNT(*) AS ?totalTriples)
    WHERE {
      ?s ?p ?o
    }
  `;

  try {
    const result = await queryFuseki<SparqlSelectResponse>(query);

    const totalTriples =
      result.results.bindings[0]?.totalTriples?.value;

    if (totalTriples === undefined) {
      throw new Error("Fuseki returned an invalid SPARQL response");
    }

    res.status(200).json({
      success: true,
      service: "apache-jena-fuseki",
      status: "connected",
      dataset: fusekiConfig.dataset,
      totalTriples: Number(totalTriples),
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    res.status(503).json({
      success: false,
      service: "apache-jena-fuseki",
      status: "disconnected",
      message:
        error instanceof Error
          ? error.message
          : "Unknown Fuseki connection error",
      timestamp: new Date().toISOString(),
    });
  }
});

export default router;
