import express from "express";
import cors from "cors";

import { env } from "./config/env.js";
import { errorHandler, notFoundHandler } from "./middleware/error-handler.js";
import { requestContext } from "./middleware/request-context.js";
import { ok } from "./lib/response.js";
import healthRouter from "./routes/health.routes.js";
import plantsRouter from "./routes/plants.routes.js";
import diseasesRouter from "./routes/diseases.routes.js";
import symptomsRouter from "./routes/symptoms.routes.js";
import diagnosisRouter from "./routes/diagnosis.routes.js";

const app = express();

app.disable("x-powered-by");

app.use(
  cors({
    origin: env.frontendUrl,
  })
);

app.use(requestContext);
app.use(express.json({ limit: "1mb" }));

app.get("/", (_req, res) => {
  res.json(
    ok(res, {
      message: "KBR Plant Disease Expert System API",
      status: "running",
      endpoints: [
        "GET /api/health",
        "GET /api/health/live",
        "GET /api/health/ready",
        "GET /api/health/fuseki",
        "GET /api/plants",
        "GET /api/plants/:id",
        "GET /api/diseases",
        "GET /api/diseases/:id",
        "GET /api/symptoms",
        "POST /api/diagnosis",
      ],
    })
  );
});

app.use("/api/health", healthRouter);
app.use("/api/plants", plantsRouter);
app.use("/api/diseases", diseasesRouter);
app.use("/api/symptoms", symptomsRouter);
app.use("/api/diagnosis", diagnosisRouter);

app.use(notFoundHandler);
app.use(errorHandler);

export default app;
