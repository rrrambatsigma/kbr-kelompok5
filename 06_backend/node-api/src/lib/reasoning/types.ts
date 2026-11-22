/**
 * Kontrak reasoning diagnosis.
 *
 * Engine pada Langkah 3 akan menerima `DiagnosisDataset` (data ternormalisasi
 * dari knowledge.service) dan mengembalikan `ReasoningResult`. API Node
 * kemudian memetakan hasil ini ke response `/api/diagnosis`.
 *
 * File ini sengaja tidak berisi akses SPARQL/HTTP agar bisa diuji dengan
 * dataset sintetis dan tidak terikat pada ontology sementara.
 */
import type {
  DiagnosisDataset,
  DiagnosisDisease,
  DiagnosisSymptom,
} from "../../services/knowledge.service.js";
import { REASONING_CONFIG } from "./config.js";

export type {
  DiagnosisDataset,
  DiagnosisDisease,
  DiagnosisSymptom,
};

export type Confidence = "TINGGI" | "SEDANG" | "RENDAH";

export type PhaseMatch = "match" | "mismatch" | "unknown";

export const REASONING_MODEL_VERSION = "forward-chaining-cf-v1";

interface EvidenceBase {
  /** ID aturan yang menyala, mis. R-EXACT-PenyakitBlasPadi-... */
  ruleId: string;
  /** Bobot bukti setelah specificitas (0..1). */
  weight: number;
  /** Nilai CF setelah bukti ini digabungkan (0..1). */
  cfAfter: number;
}

export interface SymptomEvidence extends EvidenceBase {
  type: "exact" | "canonical";
  symptomId: string;
  symptomLabel: string;
  /** Pengamatan milik penyakit yang cocok dengan gejala terpilih. */
  matchedObservationId: string;
  /** Konsep kanonik yang dipakai untuk membobot bukti, bila ada. */
  canonicalSymptomId: string | null;
  canonicalSymptomLabel: string | null;
}

export interface ConditionEvidence extends EvidenceBase {
  type: "condition";
  conditionId: string;
  conditionLabel: string;
}

/** Satu bukti yang mendukung satu kandidat penyakit. */
export type ReasoningEvidence = SymptomEvidence | ConditionEvidence;

export interface ScoreComponents {
  /** Kekuatan bukti gabungan (CF). */
  evidence: number;
  /** Proporsi gejala terpilih yang bisa dijelaskan kandidat. */
  completeness: number;
  /** Proporsi gejala penyakit yang terjelaskan. */
  coverage: number;
  /** Faktor ranking fase pertumbuhan; 1.0 jika tidak ada kecocokan. */
  phase: number;
}

export interface ReasoningCandidate {
  disease: DiagnosisDisease;
  score: number;
  confidence: Confidence;
  phaseMatch: PhaseMatch;
  evidence: ReasoningEvidence[];
  matchedSymptoms: DiagnosisSymptom[];
  unexplainedSymptoms: DiagnosisSymptom[];
  scoreComponents: ScoreComponents;
}

/**
 * Parameter model. Nilai awal ini akan dikalibrasi pada Langkah 4; jangan
 * menganggapnya final.
 */
export interface ReasoningOptions {
  topN: number;
  /** Bobot bukti kanonik relatif terhadap exact match (0..1). */
  canonicalWeight: number;
  /** Ambang minimum CF agar kandidat dipertimbangkan. */
  evidenceFloor: number;
  /** IRI fase pertumbuhan yang dipilih, atau null bila tidak diisi. */
  phaseIri: string | null;
}

export interface ReasoningResult {
  candidates: ReasoningCandidate[];
  /** Jumlah kandidat sebelum dipotong topN. */
  totalMatched: number;
  warnings: string[];
  modelVersion: string;
}

export const DEFAULT_REASONING_OPTIONS: ReasoningOptions = {
  topN: 5,
  canonicalWeight: REASONING_CONFIG.canonicalWeight,
  evidenceFloor: 0.01,
  phaseIri: null,
};
