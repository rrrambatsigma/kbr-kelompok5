export interface ApiEnvelope<T> {
  success: boolean;
  data: T;
  meta: {
    requestId: string;
    timestamp: string;
  };
}

export interface ApiErrorPayload {
  success: false;
  data: null;
  error: {
    code: string;
    message: string;
    details: Array<{ field?: string; message: string }> | null;
  };
  meta: {
    requestId: string;
    timestamp: string;
  };
}

export interface NamedEntity {
  id: string;
  iri: string;
  label: string;
}

export interface Plant extends NamedEntity {
  scientificName: string | null;
  diseaseCount: number;
}

export interface Symptom extends NamedEntity {
  partId: string | null;
  partLabel: string | null;
  canonicalId?: string | null;
  canonicalLabel?: string | null;
  observationCount?: number;
  diseaseCount?: number;
}

export interface Phase extends NamedEntity {
  diseaseCount: number;
}

export interface DiseaseSummary extends NamedEntity {
  plantId: string | null;
  plantLabel: string | null;
  symptomCount: number;
}

export interface DiseaseSymptom extends NamedEntity {
  partId: string | null;
  partLabel: string | null;
}

export interface Control extends NamedEntity {
  description: string | null;
}

export interface Pathogen extends NamedEntity {
  scientificName: string | null;
}

export interface DiseaseDetail extends DiseaseSummary {
  symptoms: DiseaseSymptom[];
  controls: Control[];
  pathogens: Pathogen[];
  parts: NamedEntity[];
  phases: NamedEntity[];
  riskFactors: NamedEntity[];
}

export type Confidence = "TINGGI" | "SEDANG" | "RENDAH";

interface EvidenceBase {
  ruleId: string;
  weight: number;
  cfAfter: number;
}

export interface SymptomEvidence extends EvidenceBase {
  type: "exact" | "canonical";
  symptomId: string;
  symptomLabel: string;
  matchedObservationId: string;
  canonicalSymptomId: string | null;
  canonicalSymptomLabel: string | null;
}

export interface ConditionEvidence extends EvidenceBase {
  type: "condition";
  conditionId: string;
  conditionLabel: string;
}

export type ReasoningEvidence = SymptomEvidence | ConditionEvidence;

export interface ScoreComponents {
  evidence: number;
  completeness: number;
  coverage: number;
  phase: number;
}

export interface DiagnosisSymptom {
  id: string;
  iri: string;
  label: string;
}

export interface DiagnosisCandidate {
  diseaseId: string;
  diseaseIri: string;
  label: string;
  score: number;
  matchRatio: number;
  coverage: number;
  matchedCount: number;
  selectedCount: number;
  totalSymptoms: number;
  matchedSymptoms: DiagnosisSymptom[];
  unmatchedSelectedSymptoms: DiagnosisSymptom[];
  category: string | null;
  controls: NamedEntity[];
  riskFactors: NamedEntity[];
  confidence: Confidence;
  phaseMatch: "match" | "mismatch" | "unknown";
  evidence: ReasoningEvidence[];
  explanation: string;
  scoreComponents: ScoreComponents;
}

export interface DiagnosisReasoningInfo {
  status: "UP" | "DEGRADED";
  modelVersion: string;
  ontologyVersion: string | null;
  checksum: string | null;
  categoryCounts: Record<string, number> | null;
}

export interface DiagnosisResult {
  input: {
    plantId: string;
    plantIri: string;
    plantLabel: string | null;
    phaseId: string | null;
    phaseIri: string | null;
    phaseLabel: string | null;
    symptomIds: string[];
    symptoms: DiagnosisSymptom[];
    topN: number;
  };
  candidates: DiagnosisCandidate[];
  reasoning: DiagnosisReasoningInfo;
  warnings: string[];
  message: string;
}

export interface DiagnosisRequest {
  plantId: string;
  phaseId?: string;
  symptomIds: string[];
  topN?: number;
}

export interface HealthStatus {
  status: "UP" | "DOWN";
  latencyMs: number;
  dependencies: Record<
    string,
    {
      status: "UP" | "DOWN";
      detail: string | null;
      ontologyStatus?: string;
    }
  >;
}
