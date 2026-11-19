import type { Plant } from "../../types/api";
import { apiRequest } from "./client";

interface ListResponse {
  count: number;
  items: Plant[];
}

export async function listPlants(): Promise<Plant[]> {
  const data = await apiRequest<ListResponse>("/api/plants");
  return data.items;
}

export async function getPlant(id: string): Promise<Plant> {
  return apiRequest<Plant>(`/api/plants/${encodeURIComponent(id)}`);
}
