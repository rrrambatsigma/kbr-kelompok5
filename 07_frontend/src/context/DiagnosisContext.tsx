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
  Plant,
  Symptom,
} from "../types/api";

interface DiagnosisDraft {
  plant: Plant | null;
  symptoms: Symptom[];
  topN: number;
}

interface DiagnosisContextValue {
  draft: DiagnosisDraft;
  result: DiagnosisResult | null;
  setPlant: (plant: Plant | null) => void;
  setSymptoms: (symptoms: Symptom[]) => void;
  setTopN: (topN: number) => void;
  setResult: (result: DiagnosisResult | null) => void;
  reset: () => void;
}

const STORAGE_KEY = "tanicare.diagnosis.v1";

const emptyDraft: DiagnosisDraft = {
  plant: null,
  symptoms: [],
  topN: 5,
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
        symptoms: Array.isArray(parsed.draft.symptoms)
          ? parsed.draft.symptoms
          : [],
        topN:
          typeof parsed.draft.topN === "number" ? parsed.draft.topN : 5,
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
        symptoms: [],
      },
      result: null,
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
      setSymptoms,
      setTopN,
      setResult,
      reset,
    }),
    [state.draft, state.result, setPlant, setSymptoms, setTopN, setResult, reset]
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
