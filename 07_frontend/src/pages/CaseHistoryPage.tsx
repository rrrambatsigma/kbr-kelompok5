import {
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  History,
  Leaf,
  RefreshCw,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Badge } from "../components/common/Badge";
import { Breadcrumb } from "../components/common/Breadcrumb";
import { Button } from "../components/common/Button";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorState } from "../components/common/ErrorState";
import { PageHeader } from "../components/common/PageHeader";
import { Spinner } from "../components/common/Spinner";
import {
  deleteCase,
  getCase,
  getCaseStats,
  listCases,
  verifyCase,
} from "../services/api/cases";
import type {
  CaseDetail,
  CaseStats,
  CaseStatus,
  CaseSummary,
} from "../types/api";
import { friendlyApiError } from "../utils/apiError";

function formatDate(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("id-ID", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function statusBadge(status: CaseStatus) {
  return status === "terverifikasi" ? (
    <Badge tone="success">
      <ShieldCheck className="h-3 w-3" aria-hidden="true" />
      Terverifikasi
    </Badge>
  ) : (
    <Badge tone="warning">Belum diverifikasi</Badge>
  );
}

export function CaseHistoryPage() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [stats, setStats] = useState<CaseStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [plantFilter, setPlantFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<"" | CaseStatus>("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [items, statsData] = await Promise.all([
        listCases({
          ...(plantFilter === "" ? {} : { plantId: plantFilter }),
          ...(statusFilter === "" ? {} : { status: statusFilter }),
          limit: 100,
        }),
        getCaseStats(),
      ]);

      setCases(items);
      setStats(statsData);
    } catch (caught) {
      setError(friendlyApiError(caught));
    } finally {
      setLoading(false);
    }
  }, [plantFilter, statusFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleToggleDetail = async (caseId: string) => {
    if (expandedId === caseId) {
      setExpandedId(null);
      setDetail(null);
      return;
    }

    setExpandedId(caseId);
    setDetail(null);
    setDetailLoading(true);
    setActionError(null);

    try {
      setDetail(await getCase(caseId));
    } catch (caught) {
      setActionError(friendlyApiError(caught));
    } finally {
      setDetailLoading(false);
    }
  };

  const handleVerify = async (caseId: string, diseaseId?: string) => {
    setBusyId(caseId);
    setActionError(null);

    try {
      const updated = await verifyCase(caseId, diseaseId);
      if (expandedId === caseId) {
        setDetail(updated);
      }
      await load();
    } catch (caught) {
      setActionError(friendlyApiError(caught));
    } finally {
      setBusyId(null);
    }
  };

  const handleDelete = async (caseId: string) => {
    const confirmed = window.confirm(
      "Hapus kasus ini dari log? Tindakan ini tidak bisa dibatalkan."
    );

    if (!confirmed) {
      return;
    }

    setBusyId(caseId);
    setActionError(null);

    try {
      await deleteCase(caseId);
      if (expandedId === caseId) {
        setExpandedId(null);
        setDetail(null);
      }
      await load();
    } catch (caught) {
      setActionError(friendlyApiError(caught));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <Breadcrumb
        items={[
          { label: "Beranda", to: "/" },
          { label: "Riwayat Kasus" },
        ]}
      />

      <PageHeader
        eyebrow="Log Kasus"
        title="Riwayat Kasus Diagnosis"
        description="Kasus yang disimpan pengguna. Setelah diverifikasi, kasus dipakai sebagai bukti tambahan (kasus serupa), bukan untuk mengubah skor."
        actions={
          <Button variant="secondary" onClick={() => void load()}>
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            Muat ulang
          </Button>
        }
      />

      {stats !== null && (
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="card p-4">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">
              Total kasus
            </p>
            <p className="mt-1 font-heading text-2xl font-extrabold text-primary">
              {stats.total}
            </p>
          </div>
          <div className="card p-4">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">
              Terverifikasi
            </p>
            <p className="mt-1 font-heading text-2xl font-extrabold text-secondary">
              {stats.verified}
            </p>
          </div>
          <div className="card p-4">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">
              Belum diverifikasi
            </p>
            <p className="mt-1 font-heading text-2xl font-extrabold text-foreground">
              {stats.unverified}
            </p>
          </div>
        </div>
      )}

      <section className="card flex flex-col gap-3 p-4 sm:flex-row sm:items-end">
        <label className="flex-1 text-xs font-semibold text-muted">
          Tanaman
          <select
            className="input mt-1 w-full"
            value={plantFilter}
            onChange={(event) => setPlantFilter(event.target.value)}
          >
            <option value="">Semua tanaman</option>
            {stats?.byPlant.map((plant) => (
              <option key={plant.plantId} value={plant.plantId}>
                {plant.label ?? plant.plantId} ({plant.count})
              </option>
            ))}
          </select>
        </label>
        <label className="flex-1 text-xs font-semibold text-muted">
          Status
          <select
            className="input mt-1 w-full"
            value={statusFilter}
            onChange={(event) =>
              setStatusFilter(event.target.value as "" | CaseStatus)
            }
          >
            <option value="">Semua status</option>
            <option value="belum_diverifikasi">Belum diverifikasi</option>
            <option value="terverifikasi">Terverifikasi</option>
          </select>
        </label>
      </section>

      {actionError !== null && (
        <p className="text-xs font-semibold text-danger">{actionError}</p>
      )}

      {loading && <Spinner label="Memuat kasus" />}

      {!loading && error !== null && (
        <ErrorState message={error} onRetry={() => void load()} />
      )}

      {!loading && error === null && cases.length === 0 && (
        <EmptyState
          title="Belum ada kasus"
          description="Simpan hasil diagnosis dari halaman hasil untuk mulai mengisi log kasus."
          icon={<History className="h-6 w-6" aria-hidden="true" />}
        />
      )}

      {!loading && error === null && cases.length > 0 && (
        <div className="space-y-3">
          {cases.map((item) => {
            const expanded = expandedId === item.id;
            const busy = busyId === item.id;

            return (
              <article key={item.id} className="card space-y-3 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge tone="neutral">
                        <Leaf className="h-3 w-3" aria-hidden="true" />
                        {item.plantLabel ?? item.plantId}
                      </Badge>
                      {statusBadge(item.status)}
                      <span className="inline-flex items-center gap-1 text-[11px] text-muted">
                        <Clock className="h-3 w-3" aria-hidden="true" />
                        {formatDate(item.createdAt)}
                      </span>
                    </div>
                    <p className="mt-2 font-heading text-sm font-bold text-foreground">
                      {item.topDiseaseLabel ?? "Belum ada kandidat"}
                    </p>
                    <p className="text-[11px] text-muted">
                      {item.topScore === null
                        ? `${item.symptomCount} gejala`
                        : `${Math.round(item.topScore * 100)}% · ${item.symptomCount} gejala`}
                    </p>
                  </div>

                  <div className="flex shrink-0 flex-wrap gap-2">
                    {item.status === "belum_diverifikasi" && (
                      <Button
                        variant="secondary"
                        onClick={() => void handleVerify(item.id)}
                        disabled={busy}
                      >
                        <CheckCircle2
                          className="h-4 w-4"
                          aria-hidden="true"
                        />
                        {busy ? "Memproses..." : "Verifikasi"}
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      onClick={() => void handleToggleDetail(item.id)}
                    >
                      {expanded ? (
                        <ChevronUp className="h-4 w-4" aria-hidden="true" />
                      ) : (
                        <ChevronDown className="h-4 w-4" aria-hidden="true" />
                      )}
                      Detail
                    </Button>
                    <Button
                      variant="ghost"
                      onClick={() => void handleDelete(item.id)}
                      disabled={busy}
                    >
                      <Trash2 className="h-4 w-4" aria-hidden="true" />
                      Hapus
                    </Button>
                  </div>
                </div>

                {item.symptomLabels.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {item.symptomLabels.map((label, index) => (
                      <span
                        key={`${item.id}-symptom-${index}`}
                        className="rounded-lg bg-surface-low px-2 py-0.5 text-[11px] text-foreground"
                      >
                        {label}
                      </span>
                    ))}
                  </div>
                )}

                {item.freeTextSymptoms !== null && (
                  <p className="rounded-xl bg-surface-low px-3 py-2 text-xs leading-5 text-muted">
                    <span className="font-semibold text-foreground">
                      Gejala diketik:
                    </span>{" "}
                    {item.freeTextSymptoms}
                  </p>
                )}

                {item.note !== null && (
                  <p className="text-xs leading-5 text-muted">
                    <span className="font-semibold text-foreground">
                      Catatan:
                    </span>{" "}
                    {item.note}
                  </p>
                )}

                {expanded && (
                  <div className="space-y-2 border-t border-border pt-3">
                    {detailLoading && <Spinner label="Memuat detail kasus" />}
                    {!detailLoading && detail !== null && (
                      <>
                        <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">
                          Kandidat tersimpan
                        </p>
                        <ul className="space-y-2">
                          {detail.candidates.map((candidate) => (
                            <li
                              key={candidate.diseaseId}
                              className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-border p-3"
                            >
                              <span className="min-w-0">
                                <span className="block text-sm font-semibold text-foreground">
                                  {candidate.rank}.{" "}
                                  {candidate.diseaseLabel ??
                                    candidate.diseaseId}
                                </span>
                                <span className="text-[11px] text-muted">
                                  {Math.round(candidate.score * 100)}% ·{" "}
                                  {candidate.confidence || "TANPA KEYAKINAN"}
                                </span>
                              </span>
                              <Button
                                variant="ghost"
                                onClick={() =>
                                  void handleVerify(
                                    item.id,
                                    candidate.diseaseId
                                  )
                                }
                                disabled={busy}
                              >
                                <ShieldCheck
                                  className="h-4 w-4"
                                  aria-hidden="true"
                                />
                                Verifikasi ini
                              </Button>
                            </li>
                          ))}
                        </ul>
                      </>
                    )}
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
