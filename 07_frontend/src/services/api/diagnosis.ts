import type { DiagnosisRequest, DiagnosisResult } from "../../types/api";
import { apiRequest } from "./client";

export async function submitDiagnosis(
  request: DiagnosisRequest
): Promise<DiagnosisResult> {
  return apiRequest<DiagnosisResult>("/api/diagnosis", {
    method: "POST",
    body: JSON.stringify({
      plantId: request.plantId,
      symptomIds: request.symptomIds,
      topN: request.topN ?? 5,
    }),
  });
}
