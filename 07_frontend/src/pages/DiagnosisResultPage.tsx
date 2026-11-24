import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Download,
  FileText,
  Leaf,
  Microscope,
  RefreshCw,
  ShieldCheck,
  Stethoscope,
  XCircle,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Badge } from "../components/common/Badge";
import { Breadcrumb } from "../components/common/Breadcrumb";
import { Button } from "../components/common/Button";
import { ConfidenceMeter } from "../components/common/ConfidenceMeter";
import { EmptyState } from "../components/common/EmptyState";
import { PageHeader } from "../components/common/PageHeader";
import { useDiagnosis } from "../context/DiagnosisContext";
import { getDisease } from "../services/api/diseases";
import type {
  Control,
  DiagnosisCandidate,
  DiseaseDetail,
  ReasoningEvidence,
} from "../types/api";
import {
  categoryLabel,
  confidenceLabel,
  confidenceTone,
  formatRiskFactorLabel,
  scorePercent,
} from "../utils/format";

function evidenceLabel(evidence: ReasoningEvidence): string {
  if (evidence.type === "condition") {
    return evidence.conditionLabel;
  }
  if (evidence.type === "canonical") {
    return `Cocok melalui konsep ${evidence.canonicalSymptomLabel ?? "kanonik"}`;
  }
  return "Cocok persis dengan pengamatan";
}

function phaseMatchLabel(
  match: DiagnosisCandidate["phaseMatch"]
): string {
  if (match === "match") {
    return "Sesuai fase";
  }
  if (match === "mismatch") {
    return "Fase berbeda";
  }
  return "Fase belum tercatat";
}

function EvidenceRow({ evidence }: { evidence: ReasoningEvidence }) {
  return (
    <li className="flex items-start gap-2 rounded-xl border border-border bg-white p-3">
      {evidence.type === "exact" ? (
        <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-secondary" aria-hidden="true" />
      ) : (
        <RefreshCw className="mt-0.5 h-4 w-4 shrink-0 text-secondary" aria-hidden="true" />
      )}
      <div className="min-w-0">
        <p className="text-sm font-medium text-foreground">
          {evidence.type === "condition"
            ? evidence.conditionLabel
            : evidence.symptomLabel}
        </p>
        <p className="mt-0.5 text-[11px] text-muted">{evidenceLabel(evidence)}</p>
      </div>
      <span className="ml-auto shrink-0 font-mono text-[11px] text-muted">
        {Math.round(evidence.weight * 100)}%
      </span>
    </li>
  );
}

function CandidateCard({
  candidate,
  rank,
  showPhase,
}: {
  candidate: DiagnosisCandidate;
  rank: number;
  showPhase: boolean;
}) {
  return (
    <article className="card flex flex-col gap-3 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2">
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-surface-low font-mono text-xs font-bold text-primary">
            {rank}
          </span>
          <div>
            <h3 className="font-heading text-sm font-bold leading-5 text-foreground">
              {candidate.label}
            </h3>
            <p className="mt-0.5 text-[11px] text-muted">
              {categoryLabel(candidate.category)}
            </p>
            {showPhase && (
              <p className="mt-1 text-[11px] font-semibold text-secondary">
                {phaseMatchLabel(candidate.phaseMatch)}
              </p>
            )}
          </div>
        </div>
        <Badge tone={confidenceTone(candidate.confidence)}>
          {confidenceLabel(candidate.confidence)}
        </Badge>
      </div>
      <div className="flex items-center gap-3">
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[#dbe5dc]">
          <div
            className="h-full rounded-full bg-secondary"
            style={{ width: `${scorePercent(candidate.score)}%` }}
          />
        </div>
        <span className="font-mono text-xs font-bold text-primary">
          {scorePercent(candidate.score)}%
        </span>
      </div>
      <p className="line-clamp-2 text-xs leading-5 text-muted">
        {candidate.explanation}
      </p>
      <Link
        to={`/knowledge-base/${encodeURIComponent(candidate.diseaseId)}`}
        className="inline-flex items-center gap-1 text-[11px] font-semibold text-secondary hover:text-primary"
      >
        Lihat detail penyakit
        <ArrowRight className="h-3 w-3" aria-hidden="true" />
      </Link>
    </article>
  );
}

export function DiagnosisResultPage() {
  const navigate = useNavigate();
  const { draft, result, reset } = useDiagnosis();
  const [detail, setDetail] = useState<DiseaseDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const topCandidate = result?.candidates[0] ?? null;

  useEffect(() => {
    if (topCandidate === null) {
      setDetail(null);
      return;
    }

    let cancelled = false;
    setDetailLoading(true);

    getDisease(topCandidate.diseaseId)
      .then((data) => {
        if (!cancelled) {
          setDetail(data);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setDetail(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setDetailLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [topCandidate?.diseaseId]);

  const controls: Control[] = useMemo(() => {
    if (detail !== null && detail.controls.length > 0) {
      return detail.controls;
    }
    return (topCandidate?.controls ?? []).map((control) => ({
      ...control,
      description: null,
    }));
  }, [detail, topCandidate]);

  const riskFactors = useMemo(() => {
    const candidateFactors = topCandidate?.riskFactors ?? [];
    const source =
      candidateFactors.length > 0
        ? candidateFactors
        : (detail?.riskFactors ?? []);
    const seen = new Set<string>();

    return source.filter((factor) => {
      if (seen.has(factor.id)) {
        return false;
      }
      seen.add(factor.id);
      return true;
    });
  }, [detail, topCandidate]);

  if (result === null || topCandidate === null) {
    return (
      <div className="mx-auto max-w-4xl space-y-6">
        <Breadcrumb
          items={[
            { label: "Beranda", to: "/" },
            { label: "Diagnosis", to: "/diagnosis" },
            { label: "Hasil Diagnosa" },
          ]}
        />
        <EmptyState
          title="Belum ada hasil diagnosis"
          description="Lakukan diagnosis terlebih dahulu. Halaman ini hanya menampilkan hasil yang benar-benar dikirim oleh backend."
          icon={<Stethoscope className="h-6 w-6" aria-hidden="true" />}
          action={
            <Link to="/diagnosis" className="btn-primary">
              Mulai Diagnosis
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          }
        />
      </div>
    );
  }

  const pathogen = detail?.pathogens[0] ?? null;
  const remaining = result.candidates.slice(1);
  const degraded = result.reasoning.status === "DEGRADED";

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <Breadcrumb
        items={[
          { label: "Beranda", to: "/" },
          { label: "Diagnosis", to: "/diagnosis" },
          { label: "Hasil Diagnosa" },
        ]}
      />

      <PageHeader
        eyebrow="Hasil Reasoning"
        title="Hasil Diagnosis & Rekomendasi Penanganan"
        description="Berdasarkan tanaman dan gejala yang Anda kirim, berikut kandidat penyakit dari mesin reasoning TaniCare."
        actions={
          <Button variant="secondary" onClick={() => window.print()}>
            <Download className="h-4 w-4" aria-hidden="true" />
            Cetak / PDF
          </Button>
        }
      />

      {degraded && (
        <div className="flex items-start gap-3 rounded-xl border border-warning/25 bg-[#fffaf5] p-4 text-sm text-[#9a3412]">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <p>
            Layanan penalaran sedang terbatas. Kandidat tetap ditampilkan, tetapi
            kategori penyakit mungkin belum tersedia.
          </p>
        </div>
      )}

      <section className="card p-4 sm:p-5">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-wide text-muted">
            Data yang dikirim
          </span>
          <Badge tone="neutral">
            <Leaf className="h-3 w-3" aria-hidden="true" />
            {draft.plant?.label ?? result.input.plantLabel ?? result.input.plantId}
          </Badge>
          {result.input.phaseLabel !== null && (
            <Badge tone="neutral">
              <Leaf className="h-3 w-3" aria-hidden="true" />
              Fase: {result.input.phaseLabel}
            </Badge>
          )}
          <Badge tone="neutral">{result.input.symptoms.length} gejala</Badge>
          <Badge tone="neutral">{result.input.topN} kandidat diminta</Badge>
        </div>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {result.input.symptoms.map((symptom) => (
            <span
              key={symptom.id}
              className="rounded-lg bg-surface-low px-2.5 py-1 text-[11px] text-foreground"
            >
              {symptom.label}
            </span>
          ))}
        </div>
      </section>

      <section className="card p-4 sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-wide text-muted">
            Hasil inferensi ontology
          </span>
          <Badge tone={degraded ? "warning" : "success"}>
            {degraded ? "Terbatas" : "Aktif"}
          </Badge>
        </div>
        <p className="mt-2 text-sm text-muted">
          Kategori penyakit dihitung oleh reasoner OWL (Openllet) dari ontology
          yang dimuat backend.
          {result.reasoning.ontologyVersion !== null
            ? ` Versi ontology ${result.reasoning.ontologyVersion}.`
            : ""}
        </p>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {Object.entries(result.reasoning.categoryCounts ?? {})
            .filter(([, count]) => count > 0)
            .sort((left, right) => right[1] - left[1])
            .map(([category, count]) => (
              <span
                key={category}
                className="rounded-lg bg-surface-low px-2.5 py-1 text-[11px] text-foreground"
              >
                {categoryLabel(category)}: <strong>{count}</strong>
              </span>
            ))}
        </div>
      </section>

      <div className="grid gap-5 lg:grid-cols-12">
        <section className="card space-y-5 p-5 sm:p-6 lg:col-span-5">
          <div className="flex items-center justify-between gap-2">
            <Badge tone="danger">
              <Stethoscope className="h-3 w-3" aria-hidden="true" />
              Kandidat terkuat
            </Badge>
            <span className="font-mono text-[11px] text-muted">
              Peringkat 1 / {result.candidates.length}
            </span>
          </div>

          <div className="rounded-2xl bg-gradient-to-br from-[#174b35] via-[#1d5f43] to-[#2f7a52] p-5 text-white">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-white/70">
              Kemungkinan penyakit
            </p>
            <h2 className="mt-2 font-heading text-2xl font-extrabold leading-tight">
              {topCandidate.label}
            </h2>
            {pathogen ? (
              <p className="mt-1 text-sm italic text-[#c4e19c]">
                {pathogen.scientificName ?? pathogen.label}
              </p>
            ) : detailLoading ? (
              <p className="mt-1 text-xs text-white/70">Memuat patogen…</p>
            ) : (
              <p className="mt-1 text-xs text-white/70">
                Nama ilmiah patogen belum tersedia.
              </p>
            )}
            <div className="mt-4 flex flex-wrap gap-2">
              <span className="rounded-full bg-white/10 px-2.5 py-1 text-[11px] font-semibold">
                {categoryLabel(topCandidate.category)}
              </span>
              <span className="rounded-full bg-white/10 px-2.5 py-1 text-[11px] font-semibold">
                {confidenceLabel(topCandidate.confidence)}
              </span>
              {result.input.phaseLabel !== null && (
                <span className="rounded-full bg-white/10 px-2.5 py-1 text-[11px] font-semibold">
                  {phaseMatchLabel(topCandidate.phaseMatch)}
                </span>
              )}
            </div>
          </div>

          <ConfidenceMeter
            score={topCandidate.score}
            confidence={topCandidate.confidence}
          />

          <div>
            <h3 className="text-xs font-bold uppercase tracking-wide text-muted">
              Penjelasan reasoning
            </h3>
            <p className="mt-2 text-sm leading-7 text-muted">
              {topCandidate.explanation}
            </p>
          </div>

          <div className="grid grid-cols-3 gap-2 text-center">
            <div className="rounded-xl bg-surface-low p-3">
              <p className="font-mono text-lg font-bold text-primary">
                {topCandidate.matchedCount}
              </p>
              <p className="text-[10px] text-muted">bukti cocok</p>
            </div>
            <div className="rounded-xl bg-surface-low p-3">
              <p className="font-mono text-lg font-bold text-primary">
                {scorePercent(topCandidate.matchRatio)}
              </p>
              <p className="text-[10px] text-muted">
                kelengkapan
              </p>
            </div>
            <div className="rounded-xl bg-surface-low p-3">
              <p className="font-mono text-lg font-bold text-primary">
                {scorePercent(topCandidate.coverage)}
              </p>
              <p className="text-[10px] text-muted">cakupan</p>
            </div>
          </div>
          <p className="text-[10px] leading-4 text-muted">
            Kelengkapan = proporsi gejala terpilih yang dijelaskan kandidat.
            Cakupan = proporsi gejala penyakit yang terjelaskan.
          </p>
        </section>

        <div className="space-y-5 lg:col-span-7">
          <section className="card space-y-4 p-5 sm:p-6">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-secondary" aria-hidden="true" />
              <h2 className="font-heading text-lg font-bold text-foreground">
                Bukti gejala
              </h2>
            </div>

            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                Gejala yang cocok
              </p>
              <ul className="mt-2 space-y-2">
                {topCandidate.evidence.map((evidence, index) => (
                  <EvidenceRow
                    evidence={evidence}
                    key={`${evidence.ruleId}-${index}`}
                  />
                ))}
                {topCandidate.evidence.length === 0 && (
                  <li className="text-sm text-muted">Belum ada bukti gejala.</li>
                )}
              </ul>
            </div>

            {topCandidate.unmatchedSelectedSymptoms.length > 0 && (
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                  Gejala belum dijelaskan kandidat ini
                </p>
                <ul className="mt-2 space-y-1.5">
                  {topCandidate.unmatchedSelectedSymptoms.map((symptom) => (
                    <li
                      key={symptom.id}
                      className="flex items-start gap-2 text-xs text-muted"
                    >
                      <XCircle
                        className="mt-0.5 h-3.5 w-3.5 shrink-0 text-warning"
                        aria-hidden="true"
                      />
                      {symptom.label}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>

          <section className="card space-y-4 p-5 sm:p-6">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-warning" aria-hidden="true" />
                <h2 className="font-heading text-lg font-bold text-foreground">
                  Faktor risiko &amp; pemicu
                </h2>
              </div>
              <Badge tone={riskFactors.length > 0 ? "warning" : "neutral"}>
                {riskFactors.length} faktor
              </Badge>
            </div>

            {riskFactors.length === 0 ? (
              <p className="text-sm leading-6 text-muted">
                Belum ada faktor risiko yang tercatat untuk penyakit ini di
                knowledge base.
              </p>
            ) : (
              <ul className="space-y-2">
                {riskFactors.map((factor) => (
                  <li
                    key={factor.id}
                    className="flex items-start gap-2.5 rounded-xl border border-warning/15 bg-[#fffaf5] p-3"
                  >
                    <span
                      className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-warning"
                      aria-hidden="true"
                    />
                    <span className="text-sm leading-6 text-foreground">
                      {formatRiskFactorLabel(factor.label)}
                    </span>
                  </li>
                ))}
              </ul>
            )}

            <p className="text-[10px] leading-4 text-muted">
              Berdasarkan relasi <code>dipengaruhiOleh</code> pada knowledge
              base. Faktor risiko membantu menjelaskan kondisi yang meningkatkan
              peluang penyakit, bukan diagnosis pasti.
            </p>
          </section>

          <section className="card space-y-4 p-5 sm:p-6">
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-secondary" aria-hidden="true" />
              <h2 className="font-heading text-lg font-bold text-foreground">
                Pengendalian dari knowledge base
              </h2>
            </div>
            {controls.length === 0 ? (
              <p className="text-sm leading-6 text-muted">
                Belum ada data pengendalian yang tercatat untuk penyakit ini di
                knowledge base.
              </p>
            ) : (
              <ul className="space-y-2">
                {controls.map((control) => (
                  <li
                    key={control.id}
                    className="rounded-xl border border-border bg-surface-low p-3"
                  >
                    <p className="flex items-start gap-2 text-sm font-medium text-foreground">
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

          <section className="card space-y-3 p-5 sm:p-6">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="font-heading text-base font-bold text-foreground">
                Kandidat lain
              </h2>
              <Link
                to="/knowledge-base"
                className="text-xs font-semibold text-secondary hover:text-primary"
              >
                Buka katalog
              </Link>
            </div>
            {remaining.length === 0 ? (
              <p className="text-sm text-muted">
                Tidak ada kandidat lain pada daftar yang diminta.
              </p>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2">
                {remaining.map((candidate, index) => (
                  <CandidateCard
                    key={candidate.diseaseId}
                    candidate={candidate}
                    rank={index + 2}
                    showPhase={result.input.phaseId !== null}
                  />
                ))}
              </div>
            )}
          </section>
        </div>
      </div>

      <section className="no-print flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border bg-surface p-4">
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => navigate("/diagnosis")}>
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Ubah data diagnosis
          </Button>
          <Button
            variant="ghost"
            onClick={() => {
              reset();
              navigate("/diagnosis");
            }}
          >
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            Diagnosis tanaman lain
          </Button>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-muted">
          <Microscope className="h-3.5 w-3.5" aria-hidden="true" />
          {result.reasoning.modelVersion}
          {result.reasoning.ontologyVersion
            ? ` · ontology ${result.reasoning.ontologyVersion}`
            : ""}
        </div>
      </section>

      <div className="print-only text-xs text-muted">
        <p>
          TaniCare — hasil identifikasi berbasis knowledge base. Bukan pengganti
          pemeriksaan ahli agronomi.
        </p>
      </div>
    </div>
  );
}
