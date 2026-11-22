import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import type {
  DiagnosisResult,
  Phase,
  Plant,
  Symptom,
} from "../types/api";

interface DiagnosisDraft {
  plant: Plant | null;
  phase: Phase | null;
  symptoms: Symptom[];
  topN: number;
  symptomQuery: string;
}

interface DiagnosisContextValue {
  draft: DiagnosisDraft;
  result: DiagnosisResult | null;
  setPlant: (plant: Plant | null) => void;
  setPhase: (phase: Phase | null) => void;
  setSymptoms: (symptoms: Symptom[]) => void;
  setTopN: (topN: number) => void;
  setSymptomQuery: (query: string) => void;
  setResult: (result: DiagnosisResult | null) => void;
  reset: () => void;
}

const STORAGE_KEY = "tanicare.diagnosis.v1";

const emptyDraft: DiagnosisDraft = {
  plant: null,
  phase: null,
  symptoms: [],
  topN: 5,
  symptomQuery: "",
};

interface StoredState {
  draft: DiagnosisDraft;
  result: DiagnosisResult | null;
}

function readStoredState(): StoredState {
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return { draft: emptyDraft, result: null };
    }
    const parsed = JSON.parse(raw) as Partial<StoredState>;
    if (
      typeof parsed !== "object" ||
      parsed === null ||
      typeof parsed.draft !== "object" ||
      parsed.draft === null
    ) {
      return { draft: emptyDraft, result: null };
    }
    return {
      draft: {
        plant: parsed.draft.plant ?? null,
        phase: parsed.draft.phase ?? null,
        symptoms: Array.isArray(parsed.draft.symptoms)
          ? parsed.draft.symptoms
          : [],
        topN:
          typeof parsed.draft.topN === "number" ? parsed.draft.topN : 5,
        symptomQuery:
          typeof parsed.draft.symptomQuery === "string"
            ? parsed.draft.symptomQuery
            : "",
      },
      result: parsed.result ?? null,
    };
  } catch {
    return { draft: emptyDraft, result: null };
  }
}

const DiagnosisContext = createContext<DiagnosisContextValue | null>(null);

export function DiagnosisProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<StoredState>(readStoredState);

  useEffect(() => {
    try {
      window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      // sessionStorage bisa penuh/diblokir; state in-memory tetap jalan.
    }
  }, [state]);

  const setPlant = useCallback((plant: Plant | null) => {
    setState((current) => ({
      draft: {
        ...current.draft,
        plant,
        phase: null,
        symptoms: [],
        symptomQuery: "",
      },
      result: null,
    }));
  }, []);

  const setPhase = useCallback((phase: Phase | null) => {
    setState((current) => ({
      ...current,
      draft: { ...current.draft, phase },
    }));
  }, []);

  const setSymptoms = useCallback((symptoms: Symptom[]) => {
    setState((current) => ({
      ...current,
      draft: { ...current.draft, symptoms },
    }));
  }, []);

  const setTopN = useCallback((topN: number) => {
    setState((current) => ({
      ...current,
      draft: { ...current.draft, topN },
    }));
  }, []);

  const setSymptomQuery = useCallback((symptomQuery: string) => {
    setState((current) => ({
      ...current,
      draft: { ...current.draft, symptomQuery },
    }));
  }, []);

  const setResult = useCallback((result: DiagnosisResult | null) => {
    setState((current) => ({ ...current, result }));
  }, []);

  const reset = useCallback(() => {
    setState({ draft: emptyDraft, result: null });
  }, []);

  const value = useMemo<DiagnosisContextValue>(
    () => ({
      draft: state.draft,
      result: state.result,
      setPlant,
      setPhase,
      setSymptoms,
      setTopN,
      setSymptomQuery,
      setResult,
      reset,
    }),
    [
      state.draft,
      state.result,
      setPlant,
      setPhase,
      setSymptoms,
      setTopN,
      setSymptomQuery,
      setResult,
      reset,
    ]
  );

  return (
    <DiagnosisContext.Provider value={value}>
      {children}
    </DiagnosisContext.Provider>
  );
}

export function useDiagnosis(): DiagnosisContextValue {
  const value = useContext(DiagnosisContext);
  if (value === null) {
    throw new Error("useDiagnosis harus dipakai di dalam DiagnosisProvider");
  }
  return value;
}
