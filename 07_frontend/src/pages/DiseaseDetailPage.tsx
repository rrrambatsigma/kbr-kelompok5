import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  CalendarRange,
  CheckCircle2,
  Leaf,
  MapPin,
  Microscope,
  ShieldCheck,
  Stethoscope,
  TriangleAlert,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { Badge } from "../components/common/Badge";
import { Breadcrumb } from "../components/common/Breadcrumb";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorState } from "../components/common/ErrorState";
import { PageHeader } from "../components/common/PageHeader";
import { Spinner } from "../components/common/Spinner";
import { getDisease } from "../services/api/diseases";
import type { DiseaseSymptom, DiseaseDetail } from "../types/api";
import { friendlyApiError } from "../utils/apiError";

function groupSymptoms(
  symptoms: DiseaseSymptom[]
): Array<[string, DiseaseSymptom[]]> {
  const groups = new Map<string, DiseaseSymptom[]>();
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

export function DiseaseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<DiseaseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) {
      setError("ID penyakit tidak ditemukan pada URL.");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      setDetail(await getDisease(id));
    } catch (cause) {
      setError(friendlyApiError(cause));
      setDetail(null);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  const groups = useMemo(
    () => groupSymptoms(detail?.symptoms ?? []),
    [detail]
  );

  const uniquePathogens = useMemo(() => {
    const seen = new Set<string>();
    return (detail?.pathogens ?? []).filter((pathogen) => {
      const key = `${pathogen.label}|${pathogen.scientificName ?? ""}`;
      if (seen.has(key)) {
        return false;
      }
      seen.add(key);
      return true;
    });
  }, [detail]);

  const uniqueControls = useMemo(() => {
    const seen = new Set<string>();
    return (detail?.controls ?? []).filter((control) => {
      const key = `${control.label}|${control.description ?? ""}`;
      if (seen.has(key)) {
        return false;
      }
      seen.add(key);
      return true;
    });
  }, [detail]);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <Breadcrumb
        items={[
          { label: "Beranda", to: "/" },
          { label: "Knowledge Base", to: "/knowledge-base" },
          { label: detail?.label ?? "Detail penyakit" },
        ]}
      />

      {loading && <Spinner label="Memuat detail penyakit" />}

      {!loading && error && (
        <>
          <ErrorState message={error} onRetry={() => void load()} />
          <Link to="/knowledge-base" className="btn-secondary w-fit">
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Kembali ke katalog
          </Link>
        </>
      )}

      {!loading && !error && detail === null && (
        <EmptyState
          title="Detail penyakit tidak ditemukan"
          description="Entri yang Anda cari tidak tersedia di knowledge base."
          action={
            <Link to="/knowledge-base" className="btn-primary">
              Kembali ke katalog
            </Link>
          }
        />
      )}

      {!loading && !error && detail !== null && (
        <>
          <PageHeader
            eyebrow={detail.plantLabel ?? detail.plantId ?? "Tanaman"}
            title={detail.label}
            description="Detail patologi dari knowledge base TaniCare. Seluruh isi berasal dari data backend."
            actions={
              <Link to="/diagnosis" className="btn-primary">
                <Stethoscope className="h-4 w-4" aria-hidden="true" />
                Diagnosis dengan gejala
              </Link>
            }
          />

          <div className="grid gap-5 lg:grid-cols-12">
            <div className="space-y-5 lg:col-span-8">
              <section className="card p-5 sm:p-6">
                <div className="flex items-center gap-2">
                  <Microscope className="h-5 w-5 text-secondary" aria-hidden="true" />
                  <h2 className="font-heading text-lg font-bold text-foreground">
                    Patogen penyebab
                  </h2>
                </div>
                {uniquePathogens.length === 0 ? (
                  <p className="mt-3 text-sm text-muted">
                    Relasi patogen belum tercatat untuk penyakit ini.
                  </p>
                ) : (
                  <ul className="mt-3 space-y-2">
                    {uniquePathogens.map((pathogen) => (
                      <li
                        key={pathogen.id}
                        className="rounded-xl border border-border bg-surface-low p-3"
                      >
                        <p className="text-sm font-semibold text-foreground">
                          {pathogen.label}
                        </p>
                        {pathogen.scientificName &&
                          pathogen.scientificName !== pathogen.label && (
                            <p className="mt-0.5 text-xs italic text-secondary">
                              {pathogen.scientificName}
                            </p>
                          )}
                      </li>
                    ))}
                  </ul>
                )}
              </section>

              <section className="card p-5 sm:p-6">
                <div className="flex items-center gap-2">
                  <TriangleAlert className="h-5 w-5 text-warning" aria-hidden="true" />
                  <h2 className="font-heading text-lg font-bold text-foreground">
                    Gejala dan bagian terdampak
                  </h2>
                </div>
                {groups.length === 0 ? (
                  <p className="mt-3 text-sm text-muted">
                    Gejala belum tercatat untuk penyakit ini.
                  </p>
                ) : (
                  <div className="mt-4 space-y-5">
                    {groups.map(([part, symptoms]) => (
                      <div key={part}>
                        <div className="flex items-center gap-2">
                          <MapPin className="h-4 w-4 text-secondary" aria-hidden="true" />
                          <h3 className="font-heading text-sm font-bold text-foreground">
                            {part}
                          </h3>
                        </div>
                        <ul className="mt-2 space-y-1.5">
                          {symptoms.map((symptom) => (
                            <li
                              key={symptom.id}
                              className="flex items-start gap-2 text-sm leading-6 text-muted"
                            >
                              <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-secondary" />
                              {symptom.label}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                )}
              </section>

              <section className="card p-5 sm:p-6">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="h-5 w-5 text-secondary" aria-hidden="true" />
                  <h2 className="font-heading text-lg font-bold text-foreground">
                    Pengendalian
                  </h2>
                </div>
                {uniqueControls.length === 0 ? (
                  <p className="mt-3 text-sm text-muted">
                    Belum ada tindakan pengendalian yang tercatat di knowledge
                    base untuk penyakit ini.
                  </p>
                ) : (
                  <ul className="mt-3 space-y-2">
                    {uniqueControls.map((control) => (
                      <li
                        key={control.id}
                        className="rounded-xl border border-border bg-surface-low p-3"
                      >
                        <p className="flex items-start gap-2 text-sm font-semibold text-foreground">
                          <CheckCircle2
                            className="mt-0.5 h-4 w-4 shrink-0 text-secondary"
                            aria-hidden="true"
                          />
                          {control.label}
                        </p>
                        {control.description && (
                          <p className="mt-1 pl-6 text-xs leading-5 text-muted">
                            {control.description}
                          </p>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            </div>

            <aside className="space-y-5 lg:col-span-4">
              <section className="card p-5">
                <h2 className="font-heading text-sm font-bold text-foreground">
                  Ringkasan entri
                </h2>
                <dl className="mt-3 space-y-3 text-sm">
                  <div className="flex items-start justify-between gap-3">
                    <dt className="text-muted">Tanaman</dt>
                    <dd className="text-right font-semibold text-foreground">
                      {detail.plantLabel ?? detail.plantId ?? "-"}
                    </dd>
                  </div>
                  <div className="flex items-start justify-between gap-3">
                    <dt className="text-muted">Jumlah gejala</dt>
                    <dd className="font-mono font-bold text-primary">
                      {detail.symptomCount}
                    </dd>
                  </div>
                  <div className="flex items-start justify-between gap-3">
                    <dt className="text-muted">Patogen</dt>
                    <dd className="text-right font-semibold text-foreground">
                      {uniquePathogens.length}
                    </dd>
                  </div>
                </dl>
              </section>

              <section className="card space-y-4 p-5">
                <div>
                  <h2 className="flex items-center gap-2 font-heading text-sm font-bold text-foreground">
                    <Leaf className="h-4 w-4 text-secondary" aria-hidden="true" />
                    Bagian tanaman
                  </h2>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {detail.parts.length === 0 && (
                      <span className="text-xs text-muted">Belum tercatat</span>
                    )}
                    {detail.parts.map((part) => (
                      <Badge key={part.id} tone="neutral">
                        {part.label}
                      </Badge>
                    ))}
                  </div>
                </div>

                <div>
                  <h2 className="flex items-center gap-2 font-heading text-sm font-bold text-foreground">
                    <CalendarRange className="h-4 w-4 text-secondary" aria-hidden="true" />
                    Fase rentan
                  </h2>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {detail.phases.length === 0 && (
                      <span className="text-xs text-muted">Belum tercatat</span>
                    )}
                    {detail.phases.map((phase) => (
                      <Badge key={phase.id} tone="neutral">
                        {phase.label}
                      </Badge>
                    ))}
                  </div>
                </div>

                <div>
                  <h2 className="flex items-center gap-2 font-heading text-sm font-bold text-foreground">
                    <TriangleAlert className="h-4 w-4 text-warning" aria-hidden="true" />
                    Faktor risiko
                  </h2>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {detail.riskFactors.length === 0 && (
                      <span className="text-xs text-muted">Belum tercatat</span>
                    )}
                    {detail.riskFactors.map((factor) => (
                      <Badge key={factor.id} tone="warning">
                        {factor.label}
                      </Badge>
                    ))}
                  </div>
                </div>
              </section>

              <section className="card space-y-3 bg-primary-container p-5 text-white">
                <BookOpen className="h-6 w-6 text-[#c4e19c]" aria-hidden="true" />
                <h2 className="font-heading text-base font-bold">
                  Punya gejala serupa?
                </h2>
                <p className="text-xs leading-5 text-white/75">
                  Pilih tanaman dan gejala di halaman diagnosis untuk memperoleh
                  kandidat dari mesin reasoning.
                </p>
                <Link
                  to="/diagnosis"
                  className="btn bg-white text-primary hover:bg-primary-soft"
                >
                  Mulai diagnosis
                  <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </Link>
              </section>
            </aside>
          </div>

          <Link to="/knowledge-base" className="btn-ghost w-fit">
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Kembali ke knowledge base
          </Link>
        </>
      )}
    </div>
  );
}
