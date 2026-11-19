import {
  ArrowRight,
  BookOpen,
  Database,
  Filter,
  Leaf,
  SearchX,
  SlidersHorizontal,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { Badge } from "../components/common/Badge";
import { Breadcrumb } from "../components/common/Breadcrumb";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorState } from "../components/common/ErrorState";
import { PageHeader } from "../components/common/PageHeader";
import { Pagination } from "../components/common/Pagination";
import { SearchInput } from "../components/common/SearchInput";
import { Spinner } from "../components/common/Spinner";
import { DiseaseCard } from "../components/knowledge-base/DiseaseCard";
import { listDiseases } from "../services/api/diseases";
import { listPlants } from "../services/api/plants";
import type { DiseaseSummary, Plant } from "../types/api";
import { friendlyApiError } from "../utils/apiError";

type SortOption = "name" | "plant" | "symptoms";

const PAGE_SIZE = 9;

const sortLabels: Record<SortOption, string> = {
  name: "Nama penyakit (A–Z)",
  plant: "Tanaman (A–Z)",
  symptoms: "Gejala terbanyak",
};

export function KnowledgeBasePage() {
  const [plants, setPlants] = useState<Plant[]>([]);
  const [diseases, setDiseases] = useState<DiseaseSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [plantFilter, setPlantFilter] = useState("all");
  const [sort, setSort] = useState<SortOption>("plant");
  const [page, setPage] = useState(1);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [plantItems, diseaseItems] = await Promise.all([
        listPlants(),
        listDiseases(),
      ]);
      setPlants(plantItems);
      setDiseases(diseaseItems);
    } catch (cause) {
      setError(friendlyApiError(cause));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    const items = diseases.filter((disease) => {
      const matchesPlant =
        plantFilter === "all" || disease.plantId === plantFilter;
      const matchesSearch =
        query === "" ||
        disease.label.toLowerCase().includes(query) ||
        (disease.plantLabel ?? "").toLowerCase().includes(query);
      return matchesPlant && matchesSearch;
    });

    return [...items].sort((left, right) => {
      if (sort === "symptoms") {
        return right.symptomCount - left.symptomCount;
      }
      if (sort === "plant") {
        return (
          (left.plantLabel ?? "").localeCompare(right.plantLabel ?? "", "id") ||
          left.label.localeCompare(right.label, "id")
        );
      }
      return left.label.localeCompare(right.label, "id");
    });
  }, [diseases, plantFilter, search, sort]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const visible = filtered.slice(
    (safePage - 1) * PAGE_SIZE,
    safePage * PAGE_SIZE
  );

  useEffect(() => {
    setPage(1);
  }, [search, plantFilter, sort]);

  return (
    <div className="mx-auto max-w-7xl space-y-7">
      <Breadcrumb
        items={[{ label: "Beranda", to: "/" }, { label: "Knowledge Base" }]}
      />

      <PageHeader
        eyebrow="Basis Pengetahuan"
        title="Ensiklopedia Penyakit & Gangguan Tanaman Pangan"
        description="Katalog penyakit dari knowledge base TaniCare. Cari entri, filter berdasarkan komoditas, lalu buka detail patologi."
      />

      <section className="grid gap-3 sm:grid-cols-3">
        <div className="stat-card">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-surface-low text-primary">
            <BookOpen className="h-5 w-5" aria-hidden="true" />
          </span>
          <div>
            <p className="font-mono text-xl font-bold text-primary">
              {error ? "—" : loading ? "…" : diseases.length}
            </p>
            <p className="text-xs text-muted">entri penyakit</p>
          </div>
        </div>
        <div className="stat-card">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-surface-low text-primary">
            <Leaf className="h-5 w-5" aria-hidden="true" />
          </span>
          <div>
            <p className="font-mono text-xl font-bold text-primary">
              {error ? "—" : loading ? "…" : plants.length}
            </p>
            <p className="text-xs text-muted">komoditas</p>
          </div>
        </div>
        <div className="stat-card">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-surface-low text-primary">
            <Database className="h-5 w-5" aria-hidden="true" />
          </span>
          <div>
            <p className="font-heading text-sm font-bold text-primary">
              Dari backend
            </p>
            <p className="text-xs text-muted">bukan statistik statis</p>
          </div>
        </div>
      </section>

      <section className="space-y-4 rounded-2xl border border-border bg-surface p-4 shadow-card sm:p-5">
        <SearchInput
          value={search}
          onChange={setSearch}
          placeholder="Cari nama penyakit atau tanaman…"
          label="Cari penyakit"
        />
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="flex items-center gap-2 text-xs font-semibold text-muted">
            <Filter className="h-4 w-4" aria-hidden="true" />
            Filter
          </div>
          <div className="flex flex-1 flex-col gap-2 sm:flex-row">
            <label className="flex-1">
              <span className="sr-only">Filter tanaman</span>
              <select
                className="select min-h-11 py-2 text-xs"
                value={plantFilter}
                onChange={(event) => setPlantFilter(event.target.value)}
                aria-label="Filter tanaman"
              >
                <option value="all">Semua komoditas</option>
                {plants.map((plant) => (
                  <option key={plant.id} value={plant.id}>
                    {plant.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex-1">
              <span className="sr-only">Urutan</span>
              <div className="relative">
                <SlidersHorizontal
                  className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted"
                  aria-hidden="true"
                />
                <select
                  className="select min-h-11 py-2 pr-9 text-xs"
                  value={sort}
                  onChange={(event) =>
                    setSort(event.target.value as SortOption)
                  }
                  aria-label="Urutan katalog"
                >
                  {(Object.keys(sortLabels) as SortOption[]).map((option) => (
                    <option key={option} value={option}>
                      {sortLabels[option]}
                    </option>
                  ))}
                </select>
              </div>
            </label>
          </div>
          <Badge tone="neutral">{filtered.length} hasil</Badge>
        </div>
      </section>

      {loading && <Spinner label="Memuat knowledge base" />}
      {error && <ErrorState message={error} onRetry={() => void load()} />}

      {!loading && !error && visible.length === 0 && (
        <EmptyState
          title="Tidak ada penyakit yang cocok"
          description="Coba ubah kata kunci atau filter komoditas."
          icon={<SearchX className="h-6 w-6" aria-hidden="true" />}
          action={
            <button
              type="button"
              className="btn-secondary"
              onClick={() => {
                setSearch("");
                setPlantFilter("all");
              }}
            >
              Reset filter
            </button>
          }
        />
      )}

      {!loading && !error && visible.length > 0 && (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {visible.map((disease) => (
              <DiseaseCard key={disease.id} disease={disease} />
            ))}
          </div>
          <Pagination
            page={safePage}
            totalPages={totalPages}
            onChange={setPage}
          />
        </>
      )}

      <section className="flex flex-col items-start justify-between gap-4 rounded-2xl bg-primary-container p-5 text-white sm:flex-row sm:items-center">
        <div>
          <h2 className="font-heading text-lg font-bold">
            Menemukan gejala serupa di lahan?
          </h2>
          <p className="mt-1 text-sm text-white/75">
            Gunakan diagnosis untuk mencocokkan gejala dengan knowledge base.
          </p>
        </div>
        <Link
          to="/diagnosis"
          className="btn bg-white text-primary hover:bg-primary-soft"
        >
          Buka Diagnosis
          <ArrowRight className="h-4 w-4" aria-hidden="true" />
        </Link>
      </section>
    </div>
  );
}
