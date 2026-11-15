import { Router } from "express";
import { fusekiConfig } from "../config/fuseki.js";
import { fail, meta, ok } from "../lib/response.js";
import {
  ask,
  requireIntegerTerm,
  select,
} from "../services/fuseki.service.js";
import { getReasoningStatus } from "../services/reasoning.service.js";

interface DependencyStatus {
  status: "UP" | "DOWN";
  latencyMs: number;
  detail: string | null;
  ontologyVersion: string | null;
  checksum: string | null;
}

const router = Router();

router.get("/", (_req, res) => {
  res.status(200).json(
    ok(res, {
      status: "UP",
      service: "kbr-node-api",
      uptimeSeconds: Math.round(process.uptime()),
    })
  );
});

router.get("/live", (_req, res) => {
  res.status(200).json(
    ok(res, {
      status: "UP",
      service: "kbr-node-api",
      uptimeSeconds: Math.round(process.uptime()),
    })
  );
});

router.get("/fuseki", async (_req, res) => {
  try {
    const result = await select(`
      SELECT (COUNT(*) AS ?totalTriples)
      WHERE { ?s ?p ?o }
    `);

    const binding = result.results.bindings[0];
    if (binding === undefined) {
      throw new Error("Fuseki tidak mengembalikan hasil COUNT(*)");
    }

    const totalTriples = requireIntegerTerm(binding, "totalTriples");

    res.status(200).json(
      ok(res, {
        service: "apache-jena-fuseki",
        status: "UP",
        dataset: fusekiConfig.dataset,
        totalTriples,
      })
    );
  } catch (error) {
    res
      .status(503)
      .json(fail(res, "FUSEKI_UNAVAILABLE", messageOf(error)));
  }
});

router.get("/ready", async (_req, res) => {
  const startedAt = Date.now();

  const [fusekiResult, reasoningResult] = await Promise.allSettled([
    checkFuseki(),
    checkReasoning(),
  ]);

  const dependencies = {
    fuseki: resultOf(fusekiResult),
    reasoning: resultOf(reasoningResult),
  };

  const ready =
    dependencies.fuseki.status === "UP" &&
    dependencies.reasoning.status === "UP";

  const body = {
    success: ready,
    data: {
      status: ready ? "UP" : "DOWN",
      latencyMs: Date.now() - startedAt,
      dependencies,
    },
    ...(ready
      ? {}
      : {
          error: {
            code: "DEPENDENCY_UNAVAILABLE",
            message: "Satu atau lebih dependency belum siap",
            details: null,
          },
        }),
    meta: meta(res),
  };

  res.status(ready ? 200 : 503).json(body);
});

async function checkFuseki(): Promise<DependencyStatus> {
  const startedAt = Date.now();

  try {
    const available = await ask("ASK { ?s ?p ?o }");
    return {
      status: available ? "UP" : "DOWN",
      latencyMs: Date.now() - startedAt,
      detail: available ? null : "Dataset kosong",
      ontologyVersion: null,
      checksum: null,
    };
  } catch (error) {
    return down(startedAt, messageOf(error));
  }
}

async function checkReasoning(): Promise<DependencyStatus> {
  const startedAt = Date.now();

  try {
    const status = await getReasoningStatus();
    return {
      status: status.ready ? "UP" : "DOWN",
      latencyMs: Date.now() - startedAt,
      detail: status.ready ? null : "Ontology belum siap atau tidak konsisten",
      ontologyVersion: status.version,
      checksum: status.checksum,
    };
  } catch (error) {
    return down(startedAt, messageOf(error));
  }
}

function down(startedAt: number, detail: string): DependencyStatus {
  return {
    status: "DOWN",
    latencyMs: Date.now() - startedAt,
    detail,
    ontologyVersion: null,
    checksum: null,
  };
}

function resultOf(
  result: PromiseSettledResult<DependencyStatus>
): DependencyStatus {
  if (result.status === "fulfilled") {
    return result.value;
  }
  return down(Date.now(), messageOf(result.reason));
}

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

export default router;
