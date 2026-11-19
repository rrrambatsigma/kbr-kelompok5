import type { Phase } from "../../types/api";
import { apiRequest } from "./client";

interface ListResponse {
  count: number;
  items: Phase[];
}

export async function listPhases(plantId: string): Promise<Phase[]> {
  const data = await apiRequest<ListResponse>(
    `/api/phases?plantId=${encodeURIComponent(plantId)}`
  );
  return data.items;
}
