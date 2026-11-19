import type { Symptom } from "../../types/api";
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
