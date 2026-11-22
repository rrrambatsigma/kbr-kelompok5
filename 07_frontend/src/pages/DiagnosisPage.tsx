import {
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCircle2,
  Leaf,
  RotateCcw,
  Search,
  Sparkles,
  Stethoscope,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Badge } from "../components/common/Badge";
import { Breadcrumb } from "../components/common/Breadcrumb";
import { Button } from "../components/common/Button";
import { ErrorState } from "../components/common/ErrorState";
import { PageHeader } from "../components/common/PageHeader";
import { SearchInput } from "../components/common/SearchInput";
import { Spinner } from "../components/common/Spinner";
import { Stepper } from "../components/common/Stepper";
import { useDiagnosis } from "../context/DiagnosisContext";
import { listPlants } from "../services/api/plants";
import { listPhases } from "../services/api/phases";
import { listSymptoms, matchSymptoms } from "../services/api/symptoms";
import { submitDiagnosis } from "../services/api/diagnosis";
import type {
  Phase,
  Plant,
  Symptom,
  SymptomSuggestion,
} from "../types/api";
import { friendlyApiError } from "../utils/apiError";

const steps = [
  { label: "Cari Tanaman", shortLabel: "Tanaman" },
  { label: "Fase Tumbuh", shortLabel: "Fase" },
  { label: "Pilih Gejala", shortLabel: "Gejala" },
  { label: "Konfirmasi", shortLabel: "Konfirmasi" },
];

function groupByPart(symptoms: Symptom[]): Array<[string, Symptom[]]> {
  const groups = new Map<string, Symptom[]>();
  for (const symptom of symptoms) {
    const key = symptom.partLabel ?? "Gejala umum";
    const list = groups.get(key) ?? [];
    list.push(symptom);
    groups.set(key, list);
  }
  return [...groups.entries()].sort(([left], [right]) =>
    left.localeCompare(right, "id")
  );
}

export function DiagnosisPage() {
  const navigate = useNavigate();
  const {
    draft,
    setPlant,
    setPhase,
    setSymptoms: setDraftSymptoms,
    setTopN,
    setSymptomQuery,
    setResult,
    reset,
  } = useDiagnosis();

  const [step, setStep] = useState(1);
  const [plants, setPlants] = useState<Plant[]>([]);
  const [phases, setPhases] = useState<Phase[]>([]);
  const [symptoms, setSymptoms] = useState<Symptom[]>([]);
  const [loadingPlants, setLoadingPlants] = useState(true);
  const [loadingPhases, setLoadingPhases] = useState(false);
  const [loadingSymptoms, setLoadingSymptoms] = useState(false);
  const [plantsError, setPlantsError] = useState<string | null>(null);
  const [phasesError, setPhasesError] = useState<string | null>(null);
  const [symptomsError, setSymptomsError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<SymptomSuggestion[]>([]);
  const [unmatchedTerms, setUnmatchedTerms] = useState<string[]>([]);
  const [matching, setMatching] = useState(false);
  const [matchError, setMatchError] = useState<string | null>(null);

  const loadPlants = useCallback(async () => {
    setLoadingPlants(true);
    setPlantsError(null);
    try {
      setPlants(await listPlants());
    } catch (error) {
      setPlantsError(friendlyApiError(error));
    } finally {
      setLoadingPlants(false);
    }
  }, []);

  useEffect(() => {
    void loadPlants();
  }, [loadPlants]);

  const plantId = draft.plant?.id ?? null;

  const loadPhases = useCallback(async (selectedPlantId: string) => {
    setLoadingPhases(true);
    setPhasesError(null);
    try {
      setPhases(await listPhases(selectedPlantId));
    } catch (error) {
      setPhasesError(friendlyApiError(error));
    } finally {
      setLoadingPhases(false);
    }
  }, []);

  useEffect(() => {
    if (plantId === null) {
      setPhases([]);
      return;
    }
    void loadPhases(plantId);
  }, [plantId, loadPhases]);

  const loadSymptoms = useCallback(async (selectedPlantId: string) => {
    setLoadingSymptoms(true);
    setSymptomsError(null);
    try {
      setSymptoms(await listSymptoms(selectedPlantId));
    } catch (error) {
      setSymptomsError(friendlyApiError(error));
    } finally {
      setLoadingSymptoms(false);
    }
  }, []);

  useEffect(() => {
    if (plantId === null) {
      setSymptoms([]);
      return;
    }
    void loadSymptoms(plantId);
  }, [plantId, loadSymptoms]);

  const filteredSymptoms = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (query === "") {
      return symptoms;
    }
    return symptoms.filter(
      (symptom) =>
        symptom.label.toLowerCase().includes(query) ||
        (symptom.partLabel ?? "").toLowerCase().includes(query)
    );
  }, [search, symptoms]);

  const grouped = useMemo(
    () => groupByPart(filteredSymptoms),
    [filteredSymptoms]
  );

  const selectedIds = useMemo(
    () => new Set(draft.symptoms.map((symptom) => symptom.id)),
    [draft.symptoms]
  );

  const toggleSymptom = (symptom: Symptom) => {
    const exists = draft.symptoms.some((item) => item.id === symptom.id);
    setDraftSymptoms(
      exists
        ? draft.symptoms.filter((item) => item.id !== symptom.id)
        : [...draft.symptoms, symptom]
    );
  };

  useEffect(() => {
    setSuggestions([]);
    setUnmatchedTerms([]);
    setMatchError(null);
  }, [plantId]);

  const handleMatch = async () => {
    if (plantId === null) {
      return;
    }

    const text = draft.symptomQuery.trim();

    if (text === "") {
      return;
    }

    setMatching(true);
    setMatchError(null);

    try {
      const result = await matchSymptoms(plantId, text);
      setSuggestions(result.suggestions);
      setUnmatchedTerms(result.unmatchedTerms);
    } catch (error) {
      setMatchError(friendlyApiError(error));
    } finally {
      setMatching(false);
    }
  };

  const canContinueStep1 = draft.plant !== null;
  const canContinueStep2 = true;
  const canContinueStep3 = draft.symptoms.length > 0;

  const handleReset = () => {
    reset();
    setStep(1);
    setSearch("");
    setSubmitError(null);
  };

  const handleSubmit = async () => {
    if (draft.plant === null || draft.symptoms.length === 0) {
      return;
    }

    setSubmitting(true);
    setSubmitError(null);

    try {
      const result = await submitDiagnosis({
        plantId: draft.plant.id,
        ...(draft.phase === null ? {} : { phaseId: draft.phase.id }),
        symptomIds: draft.symptoms.map((symptom) => symptom.id),
        topN: draft.topN,
      });
      setResult(result);
      navigate("/diagnosis/result");
    } catch (error) {
      setSubmitError(friendlyApiError(error));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-6xl space-y-7">
      <Breadcrumb
        items={[
          { label: "Beranda", to: "/" },
          { label: "Diagnosis" },
        ]}
      />

      <PageHeader
        eyebrow="Sistem Pakar Terpadu"
        title="Kenali Penyakit Tanaman Pangan Sejak Dini"
        description="Pilih tanaman dan gejala yang terlihat. TaniCare akan menampilkan kandidat penyakit beserta bukti dan langkah pengendalian dari knowledge base."
      />

      <section className="card p-5 sm:p-6">
        <Stepper steps={steps} current={step} />
      </section>

      {step === 1 && (
        <section className="space-y-5">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="font-heading text-lg font-bold text-foreground">
                Pilih komoditas
              </p>
              <p className="mt-1 text-sm text-muted">
                Daftar tanaman diambil langsung dari backend TaniCare.
              </p>
            </div>
            <Badge tone="neutral">
              {loadingPlants ? "Memuat…" : `${plants.length} tanaman`}
            </Badge>
          </div>

          {loadingPlants && <Spinner label="Memuat daftar tanaman" />}
          {plantsError && (
            <ErrorState message={plantsError} onRetry={() => void loadPlants()} />
          )}

          {!loadingPlants && !plantsError && (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {plants.map((plant) => {
                const selected = draft.plant?.id === plant.id;
                return (
                  <button
                    key={plant.id}
                    type="button"
                    onClick={() => {
                      setPlant(plant);
                      setSearch("");
                      setStep(2);
                    }}
                    className={`card flex flex-col items-start gap-3 p-4 text-left transition-all hover:-translate-y-0.5 hover:border-secondary/50 ${
                      selected
                        ? "border-primary-container ring-2 ring-primary-soft/60"
                        : ""
                    }`}
                    aria-pressed={selected}
                  >
                    <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-surface-low text-primary">
                      <Leaf className="h-5 w-5" aria-hidden="true" />
                    </span>
                    <span>
                      <span className="block font-heading text-base font-bold text-foreground">
                        {plant.label}
                      </span>
                      <span className="mt-1 block text-xs italic text-muted">
                        {plant.scientificName ?? "Nama ilmiah belum tersedia"}
                      </span>
                      <span className="mt-2 block text-[11px] text-muted">
                        {plant.diseaseCount} penyakit tercatat
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
          )}

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
            <p className="text-xs text-muted">
              Pilih tanaman, lalu tentukan fase pertumbuhan bila datanya
              tersedia. Fase bersifat opsional dan tidak menghalangi diagnosis.
            </p>
            <Button
              onClick={() => setStep(2)}
              disabled={!canContinueStep1}
            >
              Lanjutkan
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Button>
          </div>
        </section>
      )}

      {step === 2 && (
        <section className="space-y-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="font-heading text-lg font-bold text-foreground">
                Fase pertumbuhan {draft.plant?.label ?? "tanaman"}
              </p>
              <p className="mt-1 text-sm text-muted">
                Fase bersifat opsional. Pilih fase yang paling mendekati kondisi
                tanaman saat ini.
              </p>
            </div>
            <Badge tone={draft.phase === null ? "neutral" : "success"}>
              {draft.phase?.label ?? "Belum dipilih"}
            </Badge>
          </div>

          {loadingPhases && <Spinner label="Memuat fase pertumbuhan" />}
          {phasesError && (
            <ErrorState
              message={phasesError}
              onRetry={() => {
                if (plantId !== null) {
                  void loadPhases(plantId);
                }
              }}
            />
          )}

          {!loadingPhases && !phasesError && (
            <>
              {phases.length === 0 ? (
                <div className="card flex flex-col items-center gap-2 p-10 text-center">
                  <Leaf className="h-6 w-6 text-muted" aria-hidden="true" />
                  <p className="font-heading text-sm font-bold text-foreground">
                    Belum ada data fase pertumbuhan
                  </p>
                  <p className="max-w-md text-xs leading-5 text-muted">
                    Knowledge base belum mencatat fase untuk tanaman ini. Anda
                    tetap bisa melanjutkan diagnosis dengan tanaman dan gejala.
                  </p>
                </div>
              ) : (
                <div className="grid gap-3 sm:grid-cols-2">
                  {phases.map((phase) => {
                    const selected = draft.phase?.id === phase.id;
                    return (
                      <button
                        key={phase.id}
                        type="button"
                        onClick={() => setPhase(selected ? null : phase)}
                        className={`card flex flex-col items-start gap-2 p-4 text-left transition-all hover:-translate-y-0.5 hover:border-secondary/50 ${
                          selected
                            ? "border-primary-container ring-2 ring-primary-soft/60"
                            : ""
                        }`}
                        aria-pressed={selected}
                      >
                        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-surface-low text-primary">
                          <Leaf className="h-5 w-5" aria-hidden="true" />
                        </span>
                        <span className="font-heading text-base font-bold text-foreground">
                          {phase.label}
                        </span>
                        <span className="text-xs text-muted">
                          {phase.diseaseCount === 0
                            ? "Belum ada penyakit tertaut"
                            : `${phase.diseaseCount} penyakit pada fase ini`}
                        </span>
                      </button>
                    );
                  })}
                </div>
              )}

              {phases.length > 0 && (
                <button
                  type="button"
                  onClick={() => setPhase(null)}
                  className={`card flex w-full items-start gap-3 p-4 text-left transition-all hover:border-secondary/50 ${
                    draft.phase === null
                      ? "border-primary-container ring-2 ring-primary-soft/60"
                      : ""
                  }`}
                  aria-pressed={draft.phase === null}
                >
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-surface-low text-primary">
                    <Leaf className="h-4 w-4" aria-hidden="true" />
                  </span>
                  <span>
                    <span className="block font-heading text-sm font-bold text-foreground">
                      Lewati tanpa fase
                    </span>
                    <span className="mt-1 block text-xs text-muted">
                      Gunakan hanya tanaman dan gejala yang dipilih.
                    </span>
                  </span>
                </button>
              )}
            </>
          )}

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
            <Button variant="ghost" onClick={() => setStep(1)}>
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              Kembali
            </Button>
            <div className="flex gap-2">
              <Button variant="secondary" onClick={handleReset}>
                <RotateCcw className="h-4 w-4" aria-hidden="true" />
                Reset
              </Button>
              <Button
                onClick={() => setStep(3)}
                disabled={!canContinueStep2}
              >
                Lanjutkan
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Button>
            </div>
          </div>
        </section>
      )}

      {step === 3 && (
        <section className="space-y-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="font-heading text-lg font-bold text-foreground">
                Pilih gejala pada {draft.plant?.label ?? "tanaman"}
              </p>
              <p className="mt-1 text-sm text-muted">
                Pilih minimal satu gejala yang benar-benar terlihat.
              </p>
            </div>
            <Badge tone={draft.symptoms.length > 0 ? "success" : "neutral"}>
              {draft.symptoms.length} gejala dipilih
            </Badge>
          </div>

          {loadingSymptoms && <Spinner label="Memuat gejala tanaman" />}
          {symptomsError && (
            <ErrorState
              message={symptomsError}
              onRetry={() => {
                if (plantId !== null) {
                  void loadSymptoms(plantId);
                }
              }}
            />
          )}

          {!loadingSymptoms && !symptomsError && (
            <>
              <SearchInput
                value={search}
                onChange={setSearch}
                placeholder="Cari gejala atau bagian tanaman…"
              />

              <div className="card space-y-3 p-4">
                <div className="flex items-start gap-3">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-surface-low text-primary">
                    <Sparkles className="h-4 w-4" aria-hidden="true" />
                  </span>
                  <div>
                    <p className="font-heading text-sm font-bold text-foreground">
                      Ketik gejala dengan kata sendiri
                    </p>
                    <p className="mt-1 text-xs leading-5 text-muted">
                      Contoh: &quot;daun menguning dan ada bercak coklat&quot;.
                      Sistem akan menyarankan gejala yang cocok; pilih saran
                      untuk menambahkannya.
                    </p>
                  </div>
                </div>

                <div className="flex flex-col gap-2 sm:flex-row">
                  <input
                    className="input flex-1"
                    value={draft.symptomQuery}
                    onChange={(event) =>
                      setSymptomQuery(event.target.value)
                    }
                    onKeyDown={(event) => {
                      if (event.key === "Enter") {
                        event.preventDefault();
                        void handleMatch();
                      }
                    }}
                    maxLength={500}
                    placeholder="Tulis gejala yang terlihat..."
                    aria-label="Ketik gejala dengan kata sendiri"
                  />
                  <Button
                    variant="secondary"
                    onClick={() => void handleMatch()}
                    disabled={
                      matching || draft.symptomQuery.trim() === ""
                    }
                  >
                    {matching ? "Mencari..." : "Cari gejala"}
                  </Button>
                </div>

                {matchError !== null && (
                  <p className="text-xs font-semibold text-danger">
                    {matchError}
                  </p>
                )}

                {suggestions.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">
                      Saran gejala
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {suggestions.map((suggestion) => {
                        const symptom = symptoms.find(
                          (item) => item.id === suggestion.id
                        );
                        const selected = selectedIds.has(suggestion.id);

                        return (
                          <button
                            key={suggestion.id}
                            type="button"
                            onClick={() => {
                              if (symptom !== undefined) {
                                toggleSymptom(symptom);
                              }
                            }}
                            className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold transition-colors ${
                              selected
                                ? "border-primary-container bg-primary-soft text-primary"
                                : "border-border bg-white text-foreground hover:border-secondary/60"
                            }`}
                            aria-pressed={selected}
                          >
                            {suggestion.label}
                            <span className="font-mono text-[10px] text-muted">
                              {Math.round(suggestion.score * 100)}%
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}

                {suggestions.length === 0 && unmatchedTerms.length > 0 && (
                  <p className="text-xs leading-5 text-muted">
                    Belum ada gejala yang cocok untuk:{" "}
                    {unmatchedTerms.join(", ")}. Catatan ini tetap bisa
                    disimpan bersama kasus.
                  </p>
                )}
              </div>


              {grouped.length === 0 && (
                <div className="card flex flex-col items-center gap-2 p-10 text-center">
                  <Search className="h-6 w-6 text-muted" aria-hidden="true" />
                  <p className="font-heading text-sm font-bold text-foreground">
                    Gejala tidak ditemukan
                  </p>
                  <p className="text-xs text-muted">
                    Coba kata kunci lain atau hapus pencarian.
                  </p>
                </div>
              )}

              <div className="space-y-6">
                {grouped.map(([part, items]) => (
                  <div key={part} className="space-y-3">
                    <div className="flex items-center gap-2">
                      <h3 className="font-heading text-sm font-bold text-foreground">
                        {part}
                      </h3>
                      <span className="text-[11px] text-muted">
                        {items.length} gejala
                      </span>
                    </div>
                    <div className="grid gap-2 md:grid-cols-2">
                      {items.map((symptom) => {
                        const selected = selectedIds.has(symptom.id);
                        return (
                          <button
                            key={symptom.id}
                            type="button"
                            onClick={() => toggleSymptom(symptom)}
                            className="symptom-option text-left"
                            data-selected={selected}
                            aria-pressed={selected}
                          >
                            <span
                              className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md border ${
                                selected
                                  ? "border-white bg-white text-primary-container"
                                  : "border-border bg-white text-transparent"
                              }`}
                            >
                              <Check className="h-3.5 w-3.5" aria-hidden="true" />
                            </span>
                            <span className="min-w-0">
                              <span className="block text-sm font-medium leading-5">
                                {symptom.label}
                              </span>
                              <span className="symptom-part mt-1 block text-[11px] text-muted">
                                {symptom.partLabel ?? "Bagian belum tercatat"}
                              </span>
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
            <Button variant="ghost" onClick={() => setStep(2)}>
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              Kembali
            </Button>
            <div className="flex gap-2">
              <Button variant="secondary" onClick={handleReset}>
                <RotateCcw className="h-4 w-4" aria-hidden="true" />
                Reset
              </Button>
              <Button
                onClick={() => setStep(4)}
                disabled={!canContinueStep3}
              >
                Lanjutkan
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Button>
            </div>
          </div>
        </section>
      )}

      {step === 4 && (
        <section className="grid gap-5 lg:grid-cols-12">
          <div className="card space-y-5 p-6 lg:col-span-7">
            <div>
              <p className="font-heading text-lg font-bold text-foreground">
                Konfirmasi data diagnosis
              </p>
              <p className="mt-1 text-sm text-muted">
                Periksa kembali tanaman dan gejala sebelum mengirim permintaan
                ke mesin reasoning.
              </p>
            </div>

            <dl className="grid gap-4 sm:grid-cols-3">
              <div className="rounded-xl bg-surface-low p-4">
                <dt className="text-[11px] font-semibold uppercase tracking-wide text-muted">
                  Tanaman
                </dt>
                <dd className="mt-1 font-heading text-base font-bold text-primary">
                  {draft.plant?.label ?? "-"}
                </dd>
                <dd className="text-xs italic text-muted">
                  {draft.plant?.scientificName ?? ""}
                </dd>
              </div>
              <div className="rounded-xl bg-surface-low p-4">
                <dt className="text-[11px] font-semibold uppercase tracking-wide text-muted">
                  Fase tumbuh
                </dt>
                <dd className="mt-1 font-heading text-base font-bold text-primary">
                  {draft.phase?.label ?? "Tidak diisi"}
                </dd>
                <dd className="text-xs text-muted">
                  {draft.phase === null
                    ? "Diagnosis memakai tanaman dan gejala."
                    : `${draft.phase.diseaseCount} penyakit pada fase ini`}
                </dd>
              </div>
              <div className="rounded-xl bg-surface-low p-4">
                <dt className="text-[11px] font-semibold uppercase tracking-wide text-muted">
                  Jumlah kandidat
                </dt>
                <dd className="mt-1">
                  <select
                    className="select min-h-10 py-1"
                    value={draft.topN}
                    onChange={(event) => setTopN(Number(event.target.value))}
                    aria-label="Jumlah kandidat penyakit"
                  >
                    {[3, 5, 10].map((value) => (
                      <option key={value} value={value}>
                        {value} kandidat
                      </option>
                    ))}
                  </select>
                </dd>
              </div>
            </dl>

            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">
                Gejala terpilih
              </p>
              <ul className="mt-2 flex flex-wrap gap-2">
                {draft.symptoms.map((symptom) => (
                  <li
                    key={symptom.id}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-white px-2.5 py-1.5 text-xs text-foreground"
                  >
                    <CheckCircle2
                      className="h-3.5 w-3.5 text-secondary"
                      aria-hidden="true"
                    />
                    {symptom.label}
                  </li>
                ))}
              </ul>
            </div>

            {submitError && (
              <ErrorState title="Diagnosis gagal" message={submitError} />
            )}

            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
              <Button variant="ghost" onClick={() => setStep(3)}>
                <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                Ubah gejala
              </Button>
              <Button
                onClick={() => void handleSubmit()}
                loading={submitting}
                disabled={submitting}
              >
                <Stethoscope className="h-4 w-4" aria-hidden="true" />
                {submitting ? "Memproses diagnosis…" : "Proses Diagnosis"}
              </Button>
            </div>
          </div>

          <aside className="card space-y-3 p-6 lg:col-span-5">
            <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-surface-low text-primary">
              <Leaf className="h-5 w-5" aria-hidden="true" />
            </span>
            <h3 className="font-heading text-base font-bold text-foreground">
              Apa yang akan terjadi?
            </h3>
            <p className="text-sm leading-6 text-muted">
              TaniCare mengirim tanaman dan gejala terpilih ke backend. Mesin
              reasoning mencocokkan gejala dengan knowledge base, lalu
              mengembalikan kandidat penyakit, skor kecocokan, bukti, dan
              pengendalian.
            </p>
            <p className="rounded-xl bg-surface-low p-3 text-xs leading-5 text-muted">
              Hasil adalah kandidat berbasis aturan, bukan diagnosis pasti.
              Konsultasikan dengan ahli agronomi untuk keputusan penanganan.
            </p>
          </aside>
        </section>
      )}
    </div>
  );
}
