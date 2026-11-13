
import express from "express";
import cors from "cors";
import healthRouter from "./routes/health.routes.js";


const app = express();

app.use(
  cors({
    origin: process.env.FRONTEND_URL || "http://localhost:5173",
  })
);

app.use(express.json());

app.get("/", (_req, res) => {
  res.json({
    message: "KBR Plant Disease Expert System API",
    status: "running",
  });
});

app.get("/api/health", (_req, res) => {
  res.status(200).json({
    success: true,
    service: "kbr-node-api",
    status: "healthy",
    timestamp: new Date().toISOString(),
  });
});

app.use("/api/health", healthRouter);

export default app;
