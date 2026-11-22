import type { Symptom, SymptomMatchResult } from "../../types/api";
import { apiRequest } from "./client";

interface ListResponse {
  count: number;
  items: Symptom[];
}

export async function listSymptoms(plantId: string): Promise<Symptom[]> {
  const data = await apiRequest<ListResponse>(
    `/api/symptoms?plantId=${encodeURIComponent(plantId)}`
  );
  return data.items;
}

export async function matchSymptoms(
  plantId: string,
  text: string
): Promise<SymptomMatchResult> {
  return apiRequest<SymptomMatchResult>("/api/symptoms/match", {
    method: "POST",
    body: JSON.stringify({ plantId, text }),
  });
}
