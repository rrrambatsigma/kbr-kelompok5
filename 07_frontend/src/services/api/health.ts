import type { HealthStatus } from "../../types/api";
import { apiRequest } from "./client";

export async function getHealthReady(): Promise<HealthStatus> {
  return apiRequest<HealthStatus>("/api/health/ready", {}, 5_000);
}
