import { Router } from "express";

import { fusekiConfig } from "../config/fuseki.js";
import { fail, meta, ok, requestIdOf } from "../lib/response.js";
import {
  getOntologyHealth,
  type OntologyChecks,
  type OntologyHealth,
  type OntologyHealthStatus,
} from "../services/ontology-health.service.js";
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

interface OntologyDependencyStatus extends DependencyStatus {
  ontologyStatus: OntologyHealthStatus;
  checks: OntologyChecks | null;
  warnings: string[];
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

/**
 * Diagnostik tiga sumber ontology:
 * file di disk, Java (checksum yang dimuat), dan Fuseki (fingerprint data).
 *
 * Endpoint ini selalu 200 selama service bisa menjawab; keputusan readiness
 * ada di /api/health/ready.
 */
router.get("/ontology", async (_req, res) => {
  try {
    const health = await getOntologyHealth(requestIdOf(res));
    res.status(200).json(ok(res, health));
  } catch (error) {
    res
      .status(503)
      .json(
        fail(res, "ONTOLOGY_HEALTH_UNAVAILABLE", messageOf(error))
      );
  }
});

router.get("/ready", async (_req, res) => {
  const startedAt = Date.now();
  const requestId = requestIdOf(res);

  const [fusekiResult, reasoningResult, ontologyResult] =
    await Promise.allSettled([
      checkFuseki(),
      checkReasoning(requestId),
      getOntologyHealth(requestId),
    ]);

  const ontology = ontologyResultOf(ontologyResult, startedAt);

  const dependencies = {
    fuseki: resultOf(fusekiResult),
    reasoning: resultOf(reasoningResult),
    ontology,
  };

  const ready =
    dependencies.fuseki.status === "UP" &&
    dependencies.reasoning.status === "UP" &&
    dependencies.ontology.status === "UP";

  const mismatch =
    ontologyResult.status === "fulfilled" &&
    ontologyResult.value.status === "MISMATCH";

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
            code: mismatch ? "ONTOLOGY_MISMATCH" : "DEPENDENCY_UNAVAILABLE",
            message: mismatch
              ? "Checksum ontology tidak cocok dengan file yang dimuat Java"
              : "Satu atau lebih dependency belum siap",
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

async function checkReasoning(
  requestId?: string
): Promise<DependencyStatus> {
  const startedAt = Date.now();

  try {
    const status = await getReasoningStatus(requestId);
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

function ontologyResultOf(
  result: PromiseSettledResult<OntologyHealth>,
  startedAt: number
): OntologyDependencyStatus {
  if (result.status === "rejected") {
    return {
      status: "DOWN",
      latencyMs: Date.now() - startedAt,
      detail: messageOf(result.reason),
      ontologyVersion: null,
      checksum: null,
      ontologyStatus: "DOWN",
      checks: null,
      warnings: [],
    };
  }

  const health = result.value;
  const up = health.status === "OK" || health.status === "UNKNOWN";

  return {
    status: up ? "UP" : "DOWN",
    latencyMs: Date.now() - startedAt,
    detail:
      health.status === "OK"
        ? null
        : health.warnings.join("; ") || `Status ontology: ${health.status}`,
    ontologyVersion: health.java?.version ?? null,
    checksum: health.java?.checksum ?? null,
    ontologyStatus: health.status,
    checks: health.checks,
    warnings: health.warnings,
  };
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
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
}

export default router;
