import type { DiseaseDetail, DiseaseSummary } from "../../types/api";
import { apiRequest } from "./client";

interface ListResponse {
  count: number;
  items: DiseaseSummary[];
}

export async function listDiseases(
  plantId?: string
): Promise<DiseaseSummary[]> {
  const query =
    plantId === undefined
      ? ""
      : `?plantId=${encodeURIComponent(plantId)}`;
  const data = await apiRequest<ListResponse>(`/api/diseases${query}`);
  return data.items;
}

export async function getDisease(id: string): Promise<DiseaseDetail> {
  return apiRequest<DiseaseDetail>(
    `/api/diseases/${encodeURIComponent(id)}`
  );
}
