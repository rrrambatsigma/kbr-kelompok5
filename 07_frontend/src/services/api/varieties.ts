import type { Variety } from "../../types/api";
import { apiRequest } from "./client";

interface ListResponse {
  count: number;
  items: Variety[];
}

export async function listVarieties(plantId: string): Promise<Variety[]> {
  const data = await apiRequest<ListResponse>(
    `/api/varieties?plantId=${encodeURIComponent(plantId)}`
  );
  return data.items;
}
