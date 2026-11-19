import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import type { ReactNode } from "react";

import {
  DiagnosisProvider,
  useDiagnosis,
} from "./DiagnosisContext";
import type { Phase, Plant } from "../types/api";

const plant: Plant = {
  id: "Padi",
  iri: "http://test.local/Padi",
  label: "Padi",
  scientificName: "Oryza sativa",
  diseaseCount: 5,
};

const phase: Phase = {
  id: "FaseAnakanTanaman",
  iri: "http://test.local/FaseAnakanTanaman",
  label: "Fase anakan",
  diseaseCount: 1,
};

function wrapper({ children }: { children: ReactNode }) {
  return <DiagnosisProvider>{children}</DiagnosisProvider>;
}

describe("DiagnosisContext fase pertumbuhan", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
  });

  it("mereset fase saat tanaman diganti", () => {
    const { result } = renderHook(() => useDiagnosis(), { wrapper });

    act(() => result.current.setPlant(plant));
    act(() => result.current.setPhase(phase));
    expect(result.current.draft.phase?.id).toBe("FaseAnakanTanaman");

    act(() => result.current.setPlant({ ...plant, id: "Jagung" }));
    expect(result.current.draft.phase).toBeNull();
  });

  it("membaca state lama yang belum punya phase sebagai null", () => {
    window.sessionStorage.setItem(
      "tanicare.diagnosis.v1",
      JSON.stringify({
        draft: { plant, symptoms: [], topN: 5 },
        result: null,
      })
    );

    const { result } = renderHook(() => useDiagnosis(), { wrapper });
    expect(result.current.draft.phase).toBeNull();
    expect(result.current.draft.plant?.id).toBe("Padi");
  });

  it("reset mengosongkan fase", () => {
    const { result } = renderHook(() => useDiagnosis(), { wrapper });

    act(() => result.current.setPlant(plant));
    act(() => result.current.setPhase(phase));
    act(() => result.current.reset());

    expect(result.current.draft.phase).toBeNull();
    expect(result.current.draft.plant).toBeNull();
  });
});
