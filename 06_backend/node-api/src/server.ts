import "dotenv/config";
import app from "./app.js";
import { env } from "./config/env.js";

const server = app.listen(env.port, env.host, () => {
  const baseUrl = `http://${env.host}:${env.port}`;
  console.log("------------------------------------");
  console.log("KBR NODE API");
  console.log("------------------------------------");
  console.log(`Environment:   ${env.nodeEnv}`);
  console.log(`Server:        ${baseUrl}`);
  console.log(`Liveness:      ${baseUrl}/api/health/live`);
  console.log(`Readiness:     ${baseUrl}/api/health/ready`);
  console.log(`Phases:        ${baseUrl}/api/phases`);
  console.log(`Diagnosis:     POST ${baseUrl}/api/diagnosis`);
  console.log("------------------------------------");
});

function shutdown(signal: string): void {
  console.log(`\n${signal} diterima, menutup server...`);
  server.close((error) => {
    if (error) {
      console.error("Gagal menutup server:", error);
      process.exitCode = 1;
    }
    process.exit();
  });

  setTimeout(() => {
    console.error("Server tidak berhenti dalam 10 detik, memaksa keluar.");
    process.exit(1);
  }, 10_000).unref();
}

process.on("SIGINT", () => shutdown("SIGINT"));
process.on("SIGTERM", () => shutdown("SIGTERM"));
