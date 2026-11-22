import type {
  CaseDetail,
  CaseStats,
  CaseStatus,
  CaseSummary,
  SaveCaseRequest,
} from "../../types/api";
import { apiRequest } from "./client";

interface ListResponse {
  count: number;
  items: CaseSummary[];
  limit: number;
  offset: number;
}

export async function saveCase(
  request: SaveCaseRequest
): Promise<CaseDetail> {
  return apiRequest<CaseDetail>("/api/cases", {
    method: "POST",
    body: JSON.stringify({
      plantId: request.plantId,
      ...(request.phaseId === undefined ? {} : { phaseId: request.phaseId }),
      symptomIds: request.symptomIds,
      topN: request.topN ?? 5,
      ...(request.note === undefined ? {} : { note: request.note }),
      ...(request.freeTextSymptoms === undefined
        ? {}
        : { freeTextSymptoms: request.freeTextSymptoms }),
      ...(request.confirmedDiseaseId === undefined
        ? {}
        : { confirmedDiseaseId: request.confirmedDiseaseId }),
    }),
  });
}

export async function listCases(filter?: {
  plantId?: string;
  status?: CaseStatus;
  limit?: number;
  offset?: number;
}): Promise<CaseSummary[]> {
  const params = new URLSearchParams();
  if (filter?.plantId !== undefined) {
    params.set("plantId", filter.plantId);
  }
  if (filter?.status !== undefined) {
    params.set("status", filter.status);
  }
  params.set("limit", String(filter?.limit ?? 50));
  params.set("offset", String(filter?.offset ?? 0));

  const data = await apiRequest<ListResponse>(
    `/api/cases?${params.toString()}`
  );
  return data.items;
}

export async function getCase(id: string): Promise<CaseDetail> {
  return apiRequest<CaseDetail>(`/api/cases/${encodeURIComponent(id)}`);
}

export async function verifyCase(
  id: string,
  diseaseId?: string
): Promise<CaseDetail> {
  return apiRequest<CaseDetail>(
    `/api/cases/${encodeURIComponent(id)}/verify`,
    {
      method: "POST",
      body: JSON.stringify(diseaseId === undefined ? {} : { diseaseId }),
    }
  );
}

export async function deleteCase(id: string): Promise<void> {
  await apiRequest<{ id: string; deleted: boolean }>(
    `/api/cases/${encodeURIComponent(id)}`,
    { method: "DELETE" }
  );
}

export async function getCaseStats(): Promise<CaseStats> {
  return apiRequest<CaseStats>("/api/cases/stats");
}
